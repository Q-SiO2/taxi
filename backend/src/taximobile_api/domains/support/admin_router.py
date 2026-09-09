"""Restricted support triage; participant routes never expose these fields."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
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
from taximobile_api.domains.support.models import (
    CaseNoteVisibility,
    SupportCategory,
    SupportPriority,
    SupportTicket,
    SupportTicketNote,
    SupportTicketStatus,
)
from taximobile_api.domains.support.schemas import (
    SupportTicketAdminDetailResponse,
    SupportTicketAdminListResponse,
    SupportTicketAdminSummaryResponse,
    SupportTicketNoteAdminResponse,
    SupportTransitionRequest,
    SupportTriageRequest,
)
from taximobile_api.domains.support.service import (
    InvalidSupportTransition,
    add_support_note,
    transition_support_ticket,
    triage_support_ticket,
)


router = APIRouter(prefix="/admin/support", tags=["administration"])


def support_admin_summary(ticket: SupportTicket) -> SupportTicketAdminSummaryResponse:
    return SupportTicketAdminSummaryResponse(
        id=ticket.id,
        city_id=ticket.city_id,
        user_id=ticket.user_id,
        ride_id=ticket.ride_id,
        category=ticket.category,
        subject=ticket.subject,
        status=ticket.status,
        priority=ticket.priority,
        assigned_to_user_id=ticket.assigned_to_user_id,
        response_due_at=ticket.response_due_at,
        first_responded_at=ticket.first_responded_at,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


async def support_admin_detail(
    session: AsyncSession,
    ticket: SupportTicket,
) -> SupportTicketAdminDetailResponse:
    notes = list(
        await session.scalars(
            select(SupportTicketNote)
            .where(SupportTicketNote.ticket_id == ticket.id)
            .order_by(SupportTicketNote.created_at.asc(), SupportTicketNote.id.asc())
            .limit(100)
        )
    )
    return SupportTicketAdminDetailResponse(
        **support_admin_summary(ticket).model_dump(),
        description=ticket.description,
        resolution_code=ticket.resolution_code,
        resolved_at=ticket.resolved_at,
        closed_at=ticket.closed_at,
        retention_policy_version=ticket.retention_policy_version,
        retention_until=ticket.retention_until,
        notes=[
            SupportTicketNoteAdminResponse(
                id=note.id,
                author_user_id=note.author_user_id,
                visibility=note.visibility,
                message=note.message,
                created_at=note.created_at,
            )
            for note in notes
        ],
    )


async def locked_ticket_or_404(session: AsyncSession, ticket_id: UUID) -> SupportTicket:
    ticket = await session.scalar(
        select(SupportTicket).where(
            SupportTicket.id == ticket_id,
            SupportTicket.retention_processed_at.is_(None),
        ).with_for_update()
    )
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support ticket not found.")
    return ticket


async def active_admin_or_409(session: AsyncSession, user_id: UUID) -> User:
    user = await session.scalar(
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .where(
            User.id == user_id,
            User.status == UserStatus.ACTIVE,
            UserRole.role == Role.ADMIN,
        )
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The selected assignee is not an active support administrator.",
        )
    return user


@router.get("/tickets", response_model=SupportTicketAdminListResponse)
async def list_support_tickets_for_triage(
    ticket_status: SupportTicketStatus | None = Query(default=None, alias="status"),
    priority: SupportPriority | None = Query(default=None),
    category: SupportCategory | None = Query(default=None),
    assigned_to_user_id: UUID | None = Query(default=None),
    overdue: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    _: CurrentPrincipal = Depends(administrator),
    session: AsyncSession = Depends(database_session),
) -> SupportTicketAdminListResponse:
    filters = [SupportTicket.retention_processed_at.is_(None)]
    if ticket_status is not None:
        filters.append(SupportTicket.status == ticket_status)
    if priority is not None:
        filters.append(SupportTicket.priority == priority)
    if category is not None:
        filters.append(SupportTicket.category == category)
    if assigned_to_user_id is not None:
        filters.append(SupportTicket.assigned_to_user_id == assigned_to_user_id)
    if overdue is not None:
        terminal = [SupportTicketStatus.RESOLVED, SupportTicketStatus.CLOSED]
        if overdue:
            filters.extend(
                [
                    SupportTicket.first_responded_at.is_(None),
                    SupportTicket.response_due_at < datetime.now(UTC),
                    SupportTicket.status.not_in(terminal),
                ]
            )
        else:
            filters.append(
                SupportTicket.first_responded_at.is_not(None)
                | (SupportTicket.response_due_at >= datetime.now(UTC))
                | SupportTicket.status.in_(terminal)
            )
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
async def get_support_ticket_for_triage(
    ticket_id: UUID,
    _: CurrentPrincipal = Depends(administrator),
    session: AsyncSession = Depends(database_session),
) -> SupportTicketAdminDetailResponse:
    ticket = await session.scalar(
        select(SupportTicket).where(
            SupportTicket.id == ticket_id,
            SupportTicket.retention_processed_at.is_(None),
        )
    )
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support ticket not found.")
    return await support_admin_detail(session, ticket)


@router.post("/tickets/{ticket_id}/triage", response_model=SupportTicketAdminDetailResponse)
async def triage_ticket(
    ticket_id: UUID,
    payload: SupportTriageRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(administrator),
    session: AsyncSession = Depends(database_session),
) -> SupportTicketAdminDetailResponse:
    try:
        async with session.begin():
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="support.ticket.triage",
                key=idempotency_key,
                payload={"ticket_id": str(ticket_id), **payload.model_dump(mode="json")},
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            ticket = await locked_ticket_or_404(session, ticket_id)
            assignee_id = payload.assigned_to_user_id or principal.user_id
            await active_admin_or_409(session, assignee_id)
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
            await session.flush()
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
async def transition_ticket(
    ticket_id: UUID,
    payload: SupportTransitionRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(administrator),
    session: AsyncSession = Depends(database_session),
) -> SupportTicketAdminDetailResponse:
    try:
        async with session.begin():
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="support.ticket.transition",
                key=idempotency_key,
                payload={"ticket_id": str(ticket_id), **payload.model_dump(mode="json")},
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            ticket = await locked_ticket_or_404(session, ticket_id)
            if ticket.assigned_to_user_id != principal.user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="The ticket must be assigned to the acting administrator.",
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
                changes={
                    "previous_status": previous_status.value,
                    "current_status": ticket.status.value,
                    "resolution_code": (
                        ticket.resolution_code.value if ticket.resolution_code else None
                    ),
                    "participant_message_recorded": payload.participant_message is not None,
                },
            )
            await session.flush()
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
