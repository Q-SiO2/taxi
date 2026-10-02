"""Shared read authority for mobile REST and live subscriptions."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Session, User, UserStatus


async def mobile_session_is_active(
    database_session: AsyncSession, user_id: UUID, session_id: UUID,
    *, now: datetime | None = None,
) -> bool:
    """Re-read ownership, account status, revocation and session expiry.

    This is not a lock held across socket IO or a substitute for a business
    transaction's commit-time authority. Every call uses a fresh statement.
    """
    return await database_session.scalar(
        select(Session.id).join(User, User.id == Session.user_id).where(
            Session.id == session_id,
            Session.user_id == user_id,
            Session.revoked_at.is_(None),
            Session.expires_at > (now or datetime.now(UTC)),
            User.status == UserStatus.ACTIVE,
        )
    ) is not None
