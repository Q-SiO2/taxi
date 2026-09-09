"""City-scoped operations reads for restricted safety cases."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.administration.case_assignees import (
    has_active_city_case_grant,
)
from taximobile_api.domains.administration.models import AdministrativeRoleTemplate
from taximobile_api.domains.administration.operations_dependencies import (
    require_operations_permission,
)
from taximobile_api.domains.administration.permissions import (
    OperationsPermission,
    OperationsPrincipal,
)
from taximobile_api.domains.administration.service import audit
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.idempotency.service import (
    IdempotencyKeyReuse,
    IdempotentReplay,
    InvalidIdempotencyKey,
    begin_command,
    finish_command,
)
from taximobile_api.domains.safety.admin_router import (
    safety_admin_detail,
    safety_admin_summary,
)
from taximobile_api.domains.safety.models import (
    SafetyReport,
    SafetyReportCategory,
    SafetyReportStatus,
)
from taximobile_api.domains.safety.schemas import (
    SafetyReportAdminDetailResponse,
    SafetyReportAdminListResponse,
    SafetyTransitionRequest,
)
from taximobile_api.domains.safety.service import (
    InvalidSafetyTransition,
    add_safety_note,
    transition_safety_report,
)
from taximobile_api.domains.support.models import CaseNoteVisibility, SupportPriority


router = APIRouter(prefix="/operations/safety", tags=["operations-safety"])
PERMISSION = OperationsPermission.MANAGE_SAFETY_CASES


def _overdue_condition(now: datetime):
    terminal = (SafetyReportStatus.RESOLVED, SafetyReportStatus.CLOSED)
    return (
        SafetyReport.first_acknowledged_at.is_(None)
        & (SafetyReport.response_due_at < now)
        & SafetyReport.status.not_in(terminal)
    )


async def _locked_scoped_report_or_404(
    session: AsyncSession,
    *,
    report_id: UUID,
    principal: OperationsPrincipal,
) -> SafetyReport:
    report = await session.scalar(
        select(SafetyReport)
        .where(
            SafetyReport.id == report_id,
            SafetyReport.city_id.in_(principal.city_ids_for(PERMISSION)),
            SafetyReport.retention_processed_at.is_(None),
        )
        .with_for_update()
    )
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Safety report not found.",
        )
    return report


async def _require_safety_assignee(
    session: AsyncSession,
    *,
    user_id: UUID,
    city_id: UUID,
) -> None:
    if not await has_active_city_case_grant(
        session,
        user_id=user_id,
        city_id=city_id,
        city_role=AdministrativeRoleTemplate.SAFETY_RESPONDER,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The selected assignee does not have an active safety grant for this city.",
        )


@router.get("/reports", response_model=SafetyReportAdminListResponse)
async def list_scoped_safety_reports(
    city_id: UUID | None = Query(default=None),
    report_status: SafetyReportStatus | None = Query(default=None, alias="status"),
    category: SafetyReportCategory | None = Query(default=None),
    priority: SupportPriority | None = Query(default=None),
    assigned_to_user_id: UUID | None = Query(default=None),
    overdue: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> SafetyReportAdminListResponse:
    allowed_city_ids = principal.city_ids_for(PERMISSION)
    if city_id is not None and city_id not in allowed_city_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="City not found.")
    filters = [
        SafetyReport.city_id.in_(allowed_city_ids),
        SafetyReport.retention_processed_at.is_(None),
    ]
    if city_id is not None:
        filters.append(SafetyReport.city_id == city_id)
    if report_status is not None:
        filters.append(SafetyReport.status == report_status)
    if category is not None:
        filters.append(SafetyReport.category == category)
    if priority is not None:
        filters.append(SafetyReport.priority == priority)
    if assigned_to_user_id is not None:
        filters.append(SafetyReport.assigned_to_user_id == assigned_to_user_id)
    if overdue is not None:
        condition = _overdue_condition(datetime.now(UTC))
        filters.append(condition if overdue else ~condition)
    reports = list(
        await session.scalars(
            select(SafetyReport)
            .where(*filters)
            .order_by(SafetyReport.response_due_at.asc(), SafetyReport.id.asc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    total = await session.scalar(
        select(func.count()).select_from(SafetyReport).where(*filters)
    )
    return SafetyReportAdminListResponse(
        items=[safety_admin_summary(report) for report in reports],
        page=page,
        limit=limit,
        total=total or 0,
    )


@router.get("/reports/{report_id}", response_model=SafetyReportAdminDetailResponse)
async def get_scoped_safety_report(
    report_id: UUID,
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> SafetyReportAdminDetailResponse:
    report = await session.scalar(
        select(SafetyReport).where(
            SafetyReport.id == report_id,
            SafetyReport.city_id.in_(principal.city_ids_for(PERMISSION)),
            SafetyReport.retention_processed_at.is_(None),
        )
    )
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Safety report not found.",
        )
    return await safety_admin_detail(session, report)


@router.post("/reports/{report_id}/transition", response_model=SafetyReportAdminDetailResponse)
async def transition_scoped_safety_report(
    report_id: UUID,
    payload: SafetyTransitionRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> SafetyReportAdminDetailResponse:
    try:
        async with session.begin():
            report = await _locked_scoped_report_or_404(
                session,
                report_id=report_id,
                principal=principal,
            )
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="operations.safety.report.transition",
                key=idempotency_key,
                payload={"report_id": str(report_id), **payload.model_dump(mode="json")},
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            if (
                report.status != SafetyReportStatus.SUBMITTED
                and report.assigned_to_user_id != principal.user_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="The safety report must be assigned to the acting safety responder.",
                )
            assignee_id = (
                payload.assigned_to_user_id
                or report.assigned_to_user_id
                or principal.user_id
            )
            await _require_safety_assignee(
                session,
                user_id=assignee_id,
                city_id=report.city_id,
            )
            if payload.participant_message is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="A participant message is required for every safety transition.",
                )

            transitioned_at = datetime.now(UTC)
            previous_status = report.status
            transition_safety_report(
                report,
                target_status=payload.target_status,
                resolution_code=payload.resolution_code,
                assigned_to_user_id=assignee_id,
                transitioned_at=transitioned_at,
            )
            session.add(
                add_safety_note(
                    report,
                    author_user_id=principal.user_id,
                    visibility=CaseNoteVisibility.INTERNAL,
                    message=payload.internal_note,
                    created_at=transitioned_at,
                )
            )
            session.add(
                add_safety_note(
                    report,
                    author_user_id=principal.user_id,
                    visibility=CaseNoteVisibility.PARTICIPANT,
                    message=payload.participant_message,
                    created_at=transitioned_at,
                )
            )
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="SAFETY_REPORT_STATUS_CHANGED",
                resource_type="safety_report",
                resource_id=report.id,
                city_id=report.city_id,
                changes={
                    "previous_status": previous_status.value,
                    "current_status": report.status.value,
                    "priority": report.priority.value,
                    "assigned_to_user_id": str(assignee_id),
                    "resolution_code": (
                        report.resolution_code.value if report.resolution_code else None
                    ),
                    "participant_message_recorded": True,
                },
            )
            response = await safety_admin_detail(session, report)
            await finish_command(
                session,
                command,
                status_code=status.HTTP_200_OK,
                payload=response.model_dump(mode="json"),
            )
    except InvalidSafetyTransition as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except InvalidIdempotencyKey as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except IdempotencyKeyReuse as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return response
