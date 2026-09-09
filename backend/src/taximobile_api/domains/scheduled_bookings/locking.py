"""Scheduling aggregate locks must precede offer, commitment and driver locks."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.scheduled_bookings.models import ScheduledBooking


async def lock_booking(session: AsyncSession, booking_id: UUID) -> ScheduledBooking | None:
    """Acquire current authority even when this session cached an older row.

    Call within the command transaction before mutating the aggregate. PostgreSQL
    may wait for another command; populate_existing prevents an identity-map copy
    from concealing that command's newly committed terminal state.
    """
    return await session.scalar(
        select(ScheduledBooking).where(ScheduledBooking.id == booking_id)
        .with_for_update().execution_options(populate_existing=True)
    )
