"""City-scoped operations reads for ordinary support cases."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
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
    _SOURCE_TICKET_CONSTRAINT,
    violated_constraint,
)
from taximobile_api.domains.safety.models import SafetyReport
from taximobile_api.domains.safety.router import safety_participants
from taximobile_api.domains.safety.schemas import (
    SupportSafetyEscalationRequest,
    SupportSafetyEscalationResponse,
)
from taximobile_api.domains.safety.service import create_safety_report_record
from taximobile_api.domains.support.admin_router import (
    support_admin_detail,
    support_admin_summary,
)
from taximobile_api.domains.support.models import (
    CaseNoteVisibility,
    SupportCategory,
    SupportPriority,
    SupportTicket,
    SupportTicketStatus,
)
from taximobile_api.domains.support.schemas import (
    SupportTicketAdminDetailResponse,
    SupportTicketAdminListResponse,
    SupportTransitionRequest,
    SupportTriageRequest,
)
from taximobile_api.domains.support.service import (
    InvalidSupportTransition,
    add_support_note,
    transition_support_ticket,
    triage_support_ticket,
)


router = APIRouter(prefix="/operations/support", tags=["operations-support"])
PERMISSION = OperationsPermission.MANAGE_SUPPORT_CASES


def _overdue_condition(now: datetime):
    terminal = (SupportTicketStatus.RESOLVED, SupportTicketStatus.CLOSED)
    return (
        SupportTicket.first_responded_at.is_(None)
        & (SupportTicket.response_due_at < now)
        & SupportTicket.status.not_in(terminal)
    )


async def _locked_scoped_ticket_or_404(
    session: AsyncSession,
    *,
    ticket_id: UUID,
    principal: OperationsPrincipal,
) -> SupportTicket:
    ticket = await session.scalar(
        select(SupportTicket)
        .where(
            SupportTicket.id == ticket_id,
            SupportTicket.city_id.in_(principal.city_ids_for(PERMISSION)),
            SupportTicket.retention_processed_at.is_(None),
        )
        .with_for_update()
    )
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found.",
        )
    return ticket


async def _require_support_assignee(
    session: AsyncSession,
    *,
    user_id: UUID,
    city_id: UUID,
) -> None:
    if not await has_active_city_case_grant(
        session,
        user_id=user_id,
        city_id=city_id,
        city_role=AdministrativeRoleTemplate.SUPPORT_AGENT,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The selected assignee does not have an active support grant for this city.",
        )


@router.get("/tickets", response_model=SupportTicketAdminListResponse)
async def list_scoped_support_tickets(
    city_id: UUID | None = Query(default=None),
    ticket_status: SupportTicketStatus | None = Query(default=None, alias="status"),
    priority: SupportPriority | None = Query(default=None),
    category: SupportCategory | None = Query(default=None),
    assigned_to_user_id: UUID | None = Query(default=None),
    overdue: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> SupportTicketAdminListResponse:
    allowed_city_ids = principal.city_ids_for(PERMISSION)
    if city_id is not None and city_id not in allowed_city_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="City not found.")
    filters = [
        SupportTicket.city_id.in_(allowed_city_ids),
        SupportTicket.retention_processed_at.is_(None),
    ]
    if city_id is not None:
        filters.append(SupportTicket.city_id == city_id)
    if ticket_status is not None:
        filters.append(SupportTicket.status == ticket_status)
    if priority is not None:
        filters.append(SupportTicket.priority == priority)
    if category is not None:
        filters.append(SupportTicket.category == category)
    if assigned_to_user_id is not None:
        filters.append(SupportTicket.assigned_to_user_id == assigned_to_user_id)
    if overdue is not None:
        condition = _overdue_condition(datetime.now(UTC))
        filters.append(condition if overdue else ~condition)
    tickets = list(
        await session.scalars(
            select(SupportTicket)
            .where(*filters)
            .order_by(SupportTicket.response_due_at.asc(), SupportTicket.id.asc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    total = await session.scalar(
        select(func.count()).select_from(SupportTicket).where(*filters)
    )
    return SupportTicketAdminListResponse(
        items=[support_admin_summary(ticket) for ticket in tickets],
        page=page,
        limit=limit,
        total=total or 0,
    )


@router.get("/tickets/{ticket_id}", response_model=SupportTicketAdminDetailResponse)
async def get_scoped_support_ticket(
    ticket_id: UUID,
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> SupportTicketAdminDetailResponse:
    ticket = await session.scalar(
        select(SupportTicket).where(
            SupportTicket.id == ticket_id,
            SupportTicket.city_id.in_(principal.city_ids_for(PERMISSION)),
            SupportTicket.retention_processed_at.is_(None),
        )
    )
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found.",
        )
    return await support_admin_detail(session, ticket)


@router.post("/tickets/{ticket_id}/triage", response_model=SupportTicketAdminDetailResponse)
async def triage_scoped_support_ticket(
    ticket_id: UUID,
    payload: SupportTriageRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> SupportTicketAdminDetailResponse:
    try:
        async with session.begin():
            ticket = await _locked_scoped_ticket_or_404(
                session,
                ticket_id=ticket_id,
                principal=principal,
            )
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="operations.support.ticket.triage",
                key=idempotency_key,
                payload={"ticket_id": str(ticket_id), **payload.model_dump(mode="json")},
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)

            assignee_id = payload.assigned_to_user_id or principal.user_id
            await _require_support_assignee(
                session,
                user_id=assignee_id,
                city_id=ticket.city_id,
            )
            previous = {
                "status": ticket.status.value,
                "priority": ticket.priority.value,
                "assigned_to_user_id": (
                    str(ticket.assigned_to_user_id) if ticket.assigned_to_user_id else None
                ),
            }
            triaged_at = datetime.now(UTC)
            triage_support_ticket(
                ticket,
                priority=payload.priority,
                assigned_to_user_id=assignee_id,
                triaged_at=triaged_at,
            )
            session.add(
                add_support_note(
                    ticket,
                    author_user_id=principal.user_id,
                    visibility=CaseNoteVisibility.INTERNAL,
                    message=payload.internal_note,
                    created_at=triaged_at,
                )
            )
            session.add(
                add_support_note(
                    ticket,
                    author_user_id=principal.user_id,
                    visibility=CaseNoteVisibility.PARTICIPANT,
                    message=payload.participant_message,
                    created_at=triaged_at,
                )
            )
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="SUPPORT_TICKET_TRIAGED",
                resource_type="support_ticket",
                resource_id=ticket.id,
                city_id=ticket.city_id,
                changes={
                    "previous": previous,
                    "current": {
                        "status": ticket.status.value,
                        "priority": ticket.priority.value,
                        "assigned_to_user_id": str(assignee_id),
                    },
                    "participant_message_recorded": True,
                },
            )
            response = await support_admin_detail(session, ticket)
            await finish_command(
                session,
                command,
                status_code=status.HTTP_200_OK,
                payload=response.model_dump(mode="json"),
            )
    except InvalidSupportTransition as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except InvalidIdempotencyKey as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except IdempotencyKeyReuse as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return response


@router.post("/tickets/{ticket_id}/transition", response_model=SupportTicketAdminDetailResponse)
async def transition_scoped_support_ticket(
    ticket_id: UUID,
    payload: SupportTransitionRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> SupportTicketAdminDetailResponse:
    try:
        async with session.begin():
            ticket = await _locked_scoped_ticket_or_404(
                session,
                ticket_id=ticket_id,
                principal=principal,
            )
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="operations.support.ticket.transition",
                key=idempotency_key,
                payload={"ticket_id": str(ticket_id), **payload.model_dump(mode="json")},
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            if ticket.assigned_to_user_id != principal.user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="The ticket must be assigned to the acting support agent.",
                )
            if payload.target_status in {SupportTicketStatus.RESOLVED, SupportTicketStatus.CLOSED}:
                if payload.participant_message is None:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="A participant message is required when resolving or closing.",
                    )

            transitioned_at = datetime.now(UTC)
            previous_status = ticket.status
            transition_support_ticket(
                ticket,
                target_status=payload.target_status,
                resolution_code=payload.resolution_code,
                transitioned_at=transitioned_at,
            )
            session.add(
                add_support_note(
                    ticket,
                    author_user_id=principal.user_id,
                    visibility=CaseNoteVisibility.INTERNAL,
                    message=payload.internal_note,
                    created_at=transitioned_at,
                )
            )
            if payload.participant_message is not None:
                session.add(
                    add_support_note(
                        ticket,
                        author_user_id=principal.user_id,
                        visibility=CaseNoteVisibility.PARTICIPANT,
                        message=payload.participant_message,
                        created_at=transitioned_at,
                    )
                )
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="SUPPORT_TICKET_STATUS_CHANGED",
                resource_type="support_ticket",
                resource_id=ticket.id,
                city_id=ticket.city_id,
                changes={
                    "previous_status": previous_status.value,
                    "current_status": ticket.status.value,
                    "resolution_code": (
                        ticket.resolution_code.value if ticket.resolution_code else None
                    ),
                    "participant_message_recorded": payload.participant_message is not None,
                },
            )
            response = await support_admin_detail(session, ticket)
            await finish_command(
                session,
                command,
                status_code=status.HTTP_200_OK,
                payload=response.model_dump(mode="json"),
            )
    except InvalidSupportTransition as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except InvalidIdempotencyKey as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except IdempotencyKeyReuse as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return response


@router.post(
    "/tickets/{ticket_id}/escalate-safety",
    response_model=SupportSafetyEscalationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def escalate_scoped_support_ticket_to_safety(
    ticket_id: UUID,
    payload: SupportSafetyEscalationRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> SupportSafetyEscalationResponse:
    try:
        async with session.begin():
            ticket = await _locked_scoped_ticket_or_404(
                session,
                ticket_id=ticket_id,
                principal=principal,
            )
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="operations.support.ticket.escalate_safety",
                key=idempotency_key,
                payload={"ticket_id": str(ticket_id), **payload.model_dump(mode="json")},
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
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
            await _require_support_assignee(
                session,
                user_id=principal.user_id,
                city_id=ticket.city_id,
            )
            ride, reported_user_id = await safety_participants(
                session,
                ride_id=ticket.ride_id,
                reporter_user_id=ticket.user_id,
            )
            if ride.city_id != ticket.city_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="The support ticket city does not match its ride.",
                )

            escalated_at = datetime.now(UTC)
            report = create_safety_report_record(
                city_id=ticket.city_id,
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
                city_id=ticket.city_id,
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
                city_id=ticket.city_id,
                changes={"source_support_ticket_id": str(ticket.id)},
            )
            response = SupportSafetyEscalationResponse(
                safety_report_id=report.id,
                source_support_ticket_id=ticket.id,
                city_id=ticket.city_id,
                status=report.status,
                created_at=report.created_at,
            )
            await finish_command(
                session,
                command,
                status_code=status.HTTP_201_CREATED,
                payload=response.model_dump(mode="json"),
            )
    except InvalidSupportTransition as error:
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
