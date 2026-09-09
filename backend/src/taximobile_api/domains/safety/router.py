"""Participant-owned safety reporting, separate from emergency services and support."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.auth.dependencies import CurrentPrincipal, authenticated_principal
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.drivers.models import DriverProfile
from taximobile_api.domains.idempotency.service import (
    IdempotencyKeyReuse,
    IdempotentReplay,
    InvalidIdempotencyKey,
    begin_command,
    finish_command,
)
from taximobile_api.domains.rides.models import Ride
from taximobile_api.domains.safety.models import SafetyReport
from taximobile_api.domains.safety.schemas import (
    SafetyReportCreateRequest,
    SafetyReportListResponse,
    SafetyReportResponse,
)
from taximobile_api.domains.safety.service import create_safety_report_record


router = APIRouter(prefix="/safety", tags=["safety"])


def safety_report_response(report: SafetyReport) -> SafetyReportResponse:
    return SafetyReportResponse(
        id=report.id,
        city_id=report.city_id,
        ride_id=report.ride_id,
        category=report.category,
        status=report.status,
        latest_public_message=report.latest_public_message,
        latest_public_message_at=report.latest_public_message_at,
        resolved_at=report.resolved_at,
        closed_at=report.closed_at,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


async def safety_participants(
    session: AsyncSession,
    *,
    ride_id: UUID,
    reporter_user_id: UUID,
) -> tuple[Ride, UUID | None]:
    """Authorize the ride and derive the other participant server-side."""

    ride = await session.get(Ride, ride_id)
    if ride is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot report this ride.")
    if ride.passenger_id == reporter_user_id:
        if ride.driver_id is None:
            return ride, None
        driver_user_id = await session.scalar(
            select(DriverProfile.user_id).where(DriverProfile.id == ride.driver_id)
        )
        return ride, driver_user_id
    driver_id = await session.scalar(
        select(DriverProfile.id).where(DriverProfile.user_id == reporter_user_id)
    )
    if driver_id is None or ride.driver_id != driver_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot report this ride.")
    return ride, ride.passenger_id


@router.post("/reports", response_model=SafetyReportResponse, status_code=status.HTTP_201_CREATED)
async def create_safety_report(
    payload: SafetyReportCreateRequest,
    request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> SafetyReportResponse:
    try:
        async with session.begin():
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="safety.report.create",
                key=idempotency_key,
                payload=payload.model_dump(mode="json"),
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            if not await request.app.state.rate_limiter.allow(
                f"safety-create:{principal.user_id}",
                limit=request.app.state.settings.support_ticket_rate_limit_per_minute,
                window_seconds=60,
            ):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many safety reports. Contact emergency services for immediate danger.",
                )
            ride, reported_user_id = await safety_participants(
                session,
                ride_id=payload.ride_id,
                reporter_user_id=principal.user_id,
            )
            created_at = datetime.now(UTC)
            report = create_safety_report_record(
                city_id=ride.city_id,
                ride_id=payload.ride_id,
                reporter_user_id=principal.user_id,
                reported_user_id=reported_user_id,
                category=payload.category,
                description=payload.description,
                created_at=created_at,
            )
            session.add(report)
            await session.flush()
            response = safety_report_response(report)
            await finish_command(
                session,
                command,
                status_code=status.HTTP_201_CREATED,
                payload=response.model_dump(mode="json"),
            )
    except InvalidIdempotencyKey as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except IdempotencyKeyReuse as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return response


@router.get("/reports", response_model=SafetyReportListResponse)
async def list_my_safety_reports(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> SafetyReportListResponse:
    filters = [SafetyReport.reporter_user_id == principal.user_id]
    reports = list(
        await session.scalars(
            select(SafetyReport)
            .where(*filters)
            .order_by(SafetyReport.created_at.desc(), SafetyReport.id.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    total = await session.scalar(select(func.count()).select_from(SafetyReport).where(*filters))
    return SafetyReportListResponse(
        items=[safety_report_response(report) for report in reports],
        page=page,
        limit=limit,
        total=total or 0,
    )


@router.get("/reports/{report_id}", response_model=SafetyReportResponse)
async def get_my_safety_report(
    report_id: UUID,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> SafetyReportResponse:
    report = await session.get(SafetyReport, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Safety report not found.")
    if report.reporter_user_id != principal.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot access this safety report.")
    return safety_report_response(report)
