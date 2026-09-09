"""Shared authority for active scheduled commitment windows."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ScheduledBookingCommitment, ScheduledCommitmentStatus


def protected_commitment_exists(driver_id, at: datetime):
    """Return a correlated-capable SQL predicate for an active `[start,end)` window."""
    return exists(
        select(ScheduledBookingCommitment.id).where(
            ScheduledBookingCommitment.driver_id == driver_id,
            ScheduledBookingCommitment.status == ScheduledCommitmentStatus.ACTIVE,
            ScheduledBookingCommitment.protected_window.op("@>")(at),
        )
    )


async def driver_has_protected_commitment(
    session: AsyncSession, driver_id: UUID, *, at: datetime
) -> bool:
    """Read current commitment authority after the caller locks the driver."""
    return bool(await session.scalar(select(protected_commitment_exists(driver_id, at))))
