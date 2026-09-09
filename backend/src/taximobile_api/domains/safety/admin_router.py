"""Highly restricted safety queues and support-to-safety escalation."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.administration.service import audit
from taximobile_api.domains.auth.dependencies import CurrentPrincipal, administrator
from taximobile_api.domains.auth.models import Role, User, UserRole, UserStatus
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.idempotency.service import (
    IdempotencyKeyReuse,
    IdempotentReplay,
    InvalidIdempotencyKey,
    begin_command,
    finish_command,
)
from taximobile_api.domains.safety.models import (
    SafetyReport,
    SafetyReportCategory,
    SafetyReportNote,
    SafetyReportStatus,
)
from taximobile_api.domains.safety.router import safety_participants
from taximobile_api.domains.safety.schemas import (
    SafetyReportAdminDetailResponse,
    SafetyReportAdminListResponse,
    SafetyReportAdminSummaryResponse,
    SafetyReportNoteAdminResponse,
    SafetyTransitionRequest,
    SupportSafetyEscalationRequest,
)
from taximobile_api.domains.safety.service import (
    InvalidSafetyTransition,
    add_safety_note,
    create_safety_report_record,
    transition_safety_report,
)
from taximobile_api.domains.support.models import (
    CaseNoteVisibility,
    SupportPriority,
    SupportTicket,
    SupportTicketStatus,
)
from taximobile_api.domains.support.service import (
    InvalidSupportTransition,
    add_support_note,
    triage_support_ticket,
)


router = APIRouter(prefix="/admin", tags=["administration"])
_SOURCE_TICKET_CONSTRAINT = "uq_safety_reports_source_support_ticket_id"


def violated_constraint(error: IntegrityError) -> str | None:
    direct = getattr(error.orig, "constraint_name", None)
    cause = getattr(error.orig, "__cause__", None)
    return direct or getattr(cause, "constraint_name", None)


def safety_admin_summary(report: SafetyReport) -> SafetyReportAdminSummaryResponse:
    return SafetyReportAdminSummaryResponse(
        id=report.id,
        city_id=report.city_id,
        ride_id=report.ride_id,
        reporter_user_id=report.reporter_user_id,
        category=report.category,
        status=report.status,
        priority=report.priority,
        assigned_to_user_id=report.assigned_to_user_id,
        response_due_at=report.response_due_at,
        first_acknowledged_at=report.first_acknowledged_at,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


async def safety_admin_detail(
    session: AsyncSession,
    report: SafetyReport,
) -> SafetyReportAdminDetailResponse:
    notes = list(
        await session.scalars(
            select(SafetyReportNote)
            .where(SafetyReportNote.report_id == report.id)
            .order_by(SafetyReportNote.created_at.asc(), SafetyReportNote.id.asc())
            .limit(100)
        )
    )
    return SafetyReportAdminDetailResponse(
        **safety_admin_summary(report).model_dump(),
        reported_user_id=report.reported_user_id,
        source_support_ticket_id=report.source_support_ticket_id,
        description=report.description,
        escalated_at=report.escalated_at,
        resolved_at=report.resolved_at,
        closed_at=report.closed_at,
        resolution_code=report.resolution_code,
        retention_policy_version=report.retention_policy_version,
        retention_until=report.retention_until,
        notes=[
            SafetyReportNoteAdminResponse(
                id=note.id,
                author_user_id=note.author_user_id,
                visibility=note.visibility,
                message=note.message,
                created_at=note.created_at,
            )
            for note in notes
        ],
    )


async def active_safety_admin_or_409(session: AsyncSession, user_id: UUID) -> None:
    active = await session.scalar(
        select(User.id)
        .join(UserRole, UserRole.user_id == User.id)
        .where(
            User.id == user_id,
            User.status == UserStatus.ACTIVE,
            UserRole.role == Role.ADMIN,
        )
    )
    if active is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The selected assignee is not an active safety administrator.",
        )


async def locked_safety_report_or_404(
    session: AsyncSession,
    report_id: UUID,
) -> SafetyReport:
    report = await session.scalar(
        select(SafetyReport).where(
            SafetyReport.id == report_id,
            SafetyReport.retention_processed_at.is_(None),
        ).with_for_update()
    )
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Safety report not found.")
    return report


@router.get("/safety/reports", response_model=SafetyReportAdminListResponse)
async def list_safety_reports_for_triage(
    report_status: SafetyReportStatus | None = Query(default=None, alias="status"),
    category: SafetyReportCategory | None = Query(default=None),
    priority: SupportPriority | None = Query(default=None),
    assigned_to_user_id: UUID | None = Query(default=None),
    overdue: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    _: CurrentPrincipal = Depends(administrator),
    session: AsyncSession = Depends(database_session),
) -> SafetyReportAdminListResponse:
    filters = [SafetyReport.retention_processed_at.is_(None)]
    if report_status is not None:
        filters.append(SafetyReport.status == report_status)
    if category is not None:
        filters.append(SafetyReport.category == category)
    if priority is not None:
        filters.append(SafetyReport.priority == priority)
    if assigned_to_user_id is not None:
        filters.append(SafetyReport.assigned_to_user_id == assigned_to_user_id)
    if overdue is not None:
        terminal = [SafetyReportStatus.RESOLVED, SafetyReportStatus.CLOSED]
        if overdue:
            filters.extend(
                [
                    SafetyReport.first_acknowledged_at.is_(None),
                    SafetyReport.response_due_at < datetime.now(UTC),
                    SafetyReport.status.not_in(terminal),
                ]
            )
        else:
            filters.append(
                SafetyReport.first_acknowledged_at.is_not(None)
                | (SafetyReport.response_due_at >= datetime.now(UTC))
                | SafetyReport.status.in_(terminal)
            )
    reports = list(
        await session.scalars(
            select(SafetyReport)
            .where(*filters)
            .order_by(SafetyReport.response_due_at.asc(), SafetyReport.id.asc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    total = await session.scalar(select(func.count()).select_from(SafetyReport).where(*filters))
    return SafetyReportAdminListResponse(
        items=[safety_admin_summary(report) for report in reports],
        page=page,
        limit=limit,
        total=total or 0,
    )


@router.get("/safety/reports/{report_id}", response_model=SafetyReportAdminDetailResponse)
async def get_safety_report_for_triage(
    report_id: UUID,
    _: CurrentPrincipal = Depends(administrator),
    session: AsyncSession = Depends(database_session),
) -> SafetyReportAdminDetailResponse:
    report = await session.scalar(
        select(SafetyReport).where(
            SafetyReport.id == report_id,
            SafetyReport.retention_processed_at.is_(None),
        )
    )
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Safety report not found.")
    return await safety_admin_detail(session, report)


@router.post(
    "/safety/reports/{report_id}/transition",
    response_model=SafetyReportAdminDetailResponse,
)
async def transition_safety_case(
    report_id: UUID,
    payload: SafetyTransitionRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(administrator),
    session: AsyncSession = Depends(database_session),
) -> SafetyReportAdminDetailResponse:
    try:
        async with session.begin():
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="safety.report.transition",
                key=idempotency_key,
                payload={"report_id": str(report_id), **payload.model_dump(mode="json")},
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            report = await locked_safety_report_or_404(session, report_id)
            if (
                report.status != SafetyReportStatus.SUBMITTED
                and report.assigned_to_user_id != principal.user_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="The safety report must be assigned to the acting administrator.",
                )
            assignee_id = payload.assigned_to_user_id or report.assigned_to_user_id or principal.user_id
            await active_safety_admin_or_409(session, assignee_id)
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
            await session.flush()
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


@router.post(
    "/support/tickets/{ticket_id}/escalate-safety",
    response_model=SafetyReportAdminDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def escalate_support_ticket_to_safety(
    ticket_id: UUID,
    payload: SupportSafetyEscalationRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(administrator),
    session: AsyncSession = Depends(database_session),
) -> SafetyReportAdminDetailResponse:
    try:
        async with session.begin():
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="support.ticket.escalate_safety",
                key=idempotency_key,
                payload={"ticket_id": str(ticket_id), **payload.model_dump(mode="json")},
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            ticket = await session.scalar(
                select(SupportTicket).where(SupportTicket.id == ticket_id).with_for_update()
            )
            if ticket is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support ticket not found.")
            if ticket.ride_id is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Only a ride-linked support ticket can become a safety report.",
                )
            existing = await session.scalar(
                select(SafetyReport.id).where(SafetyReport.source_support_ticket_id == ticket.id)
            )
            if existing is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This support ticket already has a safety report.",
                )
            ride, reported_user_id = await safety_participants(
                session,
                ride_id=ticket.ride_id,
                reporter_user_id=ticket.user_id,
            )
            escalated_at = datetime.now(UTC)
            report = create_safety_report_record(
                city_id=ride.city_id,
                ride_id=ticket.ride_id,
                reporter_user_id=ticket.user_id,
                reported_user_id=reported_user_id,
                category=payload.category,
                description=ticket.description,
                source_support_ticket_id=ticket.id,
                created_at=escalated_at,
            )
            session.add(report)
            await session.flush()
            triage_support_ticket(
                ticket,
                priority=SupportPriority.URGENT,
                assigned_to_user_id=principal.user_id,
                triaged_at=escalated_at,
            )
            session.add(
                add_support_note(
                    ticket,
                    author_user_id=principal.user_id,
                    visibility=CaseNoteVisibility.INTERNAL,
                    message=payload.internal_note,
                    created_at=escalated_at,
                )
            )
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="SUPPORT_TICKET_ESCALATED_TO_SAFETY",
                resource_type="support_ticket",
                resource_id=ticket.id,
                changes={
                    "safety_report_id": str(report.id),
                    "category": report.category.value,
                    "support_status": ticket.status.value,
                },
            )
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="SAFETY_REPORT_CREATED_FROM_SUPPORT",
                resource_type="safety_report",
                resource_id=report.id,
                changes={"source_support_ticket_id": str(ticket.id)},
            )
            response = await safety_admin_detail(session, report)
            await finish_command(
                session,
                command,
                status_code=status.HTTP_201_CREATED,
                payload=response.model_dump(mode="json"),
            )
    except (InvalidSupportTransition, InvalidSafetyTransition) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except IntegrityError as error:
        if violated_constraint(error) != _SOURCE_TICKET_CONSTRAINT:
            raise
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This support ticket already has a safety report.",
        ) from error
    except InvalidIdempotencyKey as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except IdempotencyKeyReuse as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return response
