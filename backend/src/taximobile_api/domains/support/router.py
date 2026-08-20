"""Authenticated, participant-owned support ticket endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.auth.dependencies import CurrentPrincipal, authenticated_principal
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.drivers.service import DriverMissing, driver_for_user
from taximobile_api.domains.rides.models import Ride
from taximobile_api.domains.support.models import SupportTicket
from taximobile_api.domains.support.schemas import (
    SupportTicketCreateRequest,
    SupportTicketListResponse,
    SupportTicketResponse,
)


router = APIRouter(prefix="/support", tags=["support"])


def ticket_response(ticket: SupportTicket) -> SupportTicketResponse:
    return SupportTicketResponse(
        id=ticket.id,
        category=ticket.category,
        subject=ticket.subject,
        description=ticket.description,
        ride_id=ticket.ride_id,
        status=ticket.status.value,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


async def user_can_reference_ride(session: AsyncSession, user_id: UUID, ride_id: UUID) -> bool:
    """Allow a ticket reference only for the passenger or assigned driver."""
    ride = await session.get(Ride, ride_id)
    if ride is None:
        return False
    if ride.passenger_id == user_id:
        return True
    try:
        profile = await driver_for_user(session, user_id)
    except DriverMissing:
        return False
    return ride.driver_id == profile.id


@router.post("/tickets", response_model=SupportTicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: SupportTicketCreateRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> SupportTicketResponse:
    if not await request.app.state.rate_limiter.allow(
        f"support-create:{principal.user_id}",
        limit=request.app.state.settings.support_ticket_rate_limit_per_minute,
        window_seconds=60,
    ):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many support requests. Try again shortly.")
    async with session.begin():
        if payload.ride_id is not None and not await user_can_reference_ride(session, principal.user_id, payload.ride_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot reference this ride.")
        ticket = SupportTicket(
            user_id=principal.user_id,
            ride_id=payload.ride_id,
            category=payload.category,
            subject=payload.subject.strip(),
            description=payload.description.strip(),
        )
        session.add(ticket)
        await session.flush()
    return ticket_response(ticket)


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
