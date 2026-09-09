"""Scoped, privacy-bounded operations review for scheduled booking exceptions."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.administration.operations_dependencies import (
    require_operations_permission,
)
from taximobile_api.domains.administration.permissions import (
    OperationsPermission,
    OperationsPrincipal,
)
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.scheduled_bookings.models import (
    ScheduledBooking,
    ScheduledBookingStatus,
)
from taximobile_api.domains.scheduled_bookings.router import booking_response
from taximobile_api.domains.scheduled_bookings.schemas import (
    ScheduledBookingListResponse,
    ScheduledBookingResponse,
)


router = APIRouter(prefix="/operations", tags=["operations-scheduling"])
MANAGE_SCHEDULING = OperationsPermission.MANAGE_SCHEDULING_POLICY


def scoped_filters(principal: OperationsPrincipal):
    return (
        ScheduledBooking.city_id.in_(principal.city_ids_for(MANAGE_SCHEDULING)),
        ScheduledBooking.operator_id.in_(
            principal.operator_ids_for(MANAGE_SCHEDULING)
        ),
    )


@router.get("/scheduled-bookings", response_model=ScheduledBookingListResponse)
async def list_scheduled_booking_exceptions(
    city_id: UUID | None = Query(default=None),
    booking_status: ScheduledBookingStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: OperationsPrincipal = Depends(
        require_operations_permission(MANAGE_SCHEDULING)
    ),
    session: AsyncSession = Depends(database_session),
) -> ScheduledBookingListResponse:
    filters = list(scoped_filters(principal))
    if city_id is not None:
        if city_id not in principal.city_ids_for(MANAGE_SCHEDULING):
            raise HTTPException(status_code=404, detail="City scope not found.")
        filters.append(ScheduledBooking.city_id == city_id)
    if booking_status is not None:
        filters.append(ScheduledBooking.status == booking_status)
    else:
        filters.append(
            ScheduledBooking.status.in_(
                {
                    ScheduledBookingStatus.OFFERING,
                    ScheduledBookingStatus.DISPATCH_HANDOFF,
                    ScheduledBookingStatus.UNFULFILLED,
                    ScheduledBookingStatus.CANCELLED,
                }
            )
        )
    items = list(
        await session.scalars(
            select(ScheduledBooking)
            .where(*filters)
            .order_by(ScheduledBooking.scheduled_for, ScheduledBooking.id)
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    total = await session.scalar(
        select(func.count()).select_from(ScheduledBooking).where(*filters)
    )
    return ScheduledBookingListResponse(
        items=[await booking_response(session, item) for item in items],
        page=page,
        limit=limit,
        total=total or 0,
    )


@router.get(
    "/scheduled-bookings/{booking_id}", response_model=ScheduledBookingResponse
)
async def get_scheduled_booking_exception(
    booking_id: UUID,
    principal: OperationsPrincipal = Depends(
        require_operations_permission(MANAGE_SCHEDULING)
    ),
    session: AsyncSession = Depends(database_session),
) -> ScheduledBookingResponse:
    booking = await session.scalar(
        select(ScheduledBooking).where(
            ScheduledBooking.id == booking_id,
            *scoped_filters(principal),
        )
    )
    if booking is None:
        raise HTTPException(status_code=404, detail="Scheduled booking not found.")
    return await booking_response(session, booking)
