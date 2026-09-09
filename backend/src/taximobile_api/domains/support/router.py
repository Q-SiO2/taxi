"""Authenticated, participant-owned support ticket endpoints."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.auth.dependencies import CurrentPrincipal, authenticated_principal
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.drivers.service import DriverMissing, driver_for_user
from taximobile_api.domains.rides.models import Ride
from taximobile_api.domains.markets.constants import LEGACY_CITY_ID
from taximobile_api.domains.markets.models import City, CityLifecycleStatus
from taximobile_api.domains.support.models import SupportTicket
from taximobile_api.domains.support.schemas import (
    SupportTicketCreateRequest,
    SupportTicketListResponse,
    SupportTicketResponse,
)
from taximobile_api.domains.support.service import create_support_ticket_record
from taximobile_api.domains.idempotency.service import (
    IdempotencyKeyReuse,
    IdempotentReplay,
    InvalidIdempotencyKey,
    begin_command,
    finish_command,
)


router = APIRouter(prefix="/support", tags=["support"])


def ticket_response(ticket: SupportTicket) -> SupportTicketResponse:
    return SupportTicketResponse(
        id=ticket.id,
        city_id=ticket.city_id,
        category=ticket.category,
        subject=ticket.subject,
        description=ticket.description,
        ride_id=ticket.ride_id,
        status=ticket.status.value,
        latest_public_message=ticket.latest_public_message,
        latest_public_message_at=ticket.latest_public_message_at,
        resolved_at=ticket.resolved_at,
        closed_at=ticket.closed_at,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


async def participant_ride(
    session: AsyncSession,
    user_id: UUID,
    ride_id: UUID,
) -> Ride | None:
    """Allow a ticket reference only for the passenger or assigned driver."""
    ride = await session.get(Ride, ride_id)
    if ride is None:
        return None
    if ride.passenger_id == user_id:
        return ride
    try:
        profile = await driver_for_user(session, user_id)
    except DriverMissing:
        return None
    return ride if ride.driver_id == profile.id else None


async def user_can_reference_ride(session: AsyncSession, user_id: UUID, ride_id: UUID) -> bool:
    """Compatibility predicate retained for focused authorization tests."""

    return await participant_ride(session, user_id, ride_id) is not None


@router.post("/tickets", response_model=SupportTicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: SupportTicketCreateRequest,
    request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> SupportTicketResponse:
    try:
        async with session.begin():
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="support.ticket.create",
                key=idempotency_key,
                payload=payload.model_dump(mode="json"),
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            if not await request.app.state.rate_limiter.allow(
                f"support-create:{principal.user_id}",
                limit=request.app.state.settings.support_ticket_rate_limit_per_minute,
                window_seconds=60,
            ):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many support requests. Try again shortly.",
                )
            ride = None
            if payload.ride_id is not None:
                ride = await participant_ride(session, principal.user_id, payload.ride_id)
                if ride is None:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You cannot reference this ride.",
                    )
                if payload.city_id is not None and payload.city_id != ride.city_id:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="The selected city does not match the referenced ride.",
                    )
                city_id = ride.city_id
            else:
                city_id = payload.city_id or LEGACY_CITY_ID
                city = await session.get(City, city_id)
                if city is None or city.lifecycle_status not in {
                    CityLifecycleStatus.PILOT,
                    CityLifecycleStatus.ACTIVE,
                    CityLifecycleStatus.PAUSED,
                }:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Select a city that is available for participant support.",
                    )
            created_at = datetime.now(UTC)
            ticket = create_support_ticket_record(
                city_id=city_id,
                user_id=principal.user_id,
                ride_id=payload.ride_id,
                category=payload.category,
                subject=payload.subject,
                description=payload.description,
                created_at=created_at,
            )
            session.add(ticket)
            await session.flush()
            response = ticket_response(ticket)
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


@router.get("/tickets", response_model=SupportTicketListResponse)
async def list_tickets(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> SupportTicketListResponse:
    filters = [SupportTicket.user_id == principal.user_id]
    tickets = list(
        await session.scalars(
            select(SupportTicket)
            .where(*filters)
            .order_by(SupportTicket.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    total = await session.scalar(select(func.count()).select_from(SupportTicket).where(*filters))
    return SupportTicketListResponse(
        items=[ticket_response(ticket) for ticket in tickets], page=page, limit=limit, total=total or 0
    )


@router.get("/tickets/{ticket_id}", response_model=SupportTicketResponse)
async def get_ticket(
    ticket_id: UUID,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> SupportTicketResponse:
    ticket = await session.get(SupportTicket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support ticket not found.")
    if ticket.user_id != principal.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot access this support ticket.")
    return ticket_response(ticket)
