"""Database authority for account status at security-sensitive commit points.

Authentication rejects suspended users before a request enters a domain route.
Longer-running assignment commands must also serialize their final decision with
an account status change, because authentication and business commit use separate
transactions.  PostgreSQL ``FOR SHARE`` conflicts with the ``FOR UPDATE`` lock
used by suspension without granting the assignment path permission to mutate the
account row.
"""

from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import User, UserStatus


def active_user_exists(user_id):
    """Return a correlated-capable predicate for an active global account."""
    return exists(
        select(User.id)
        .where(User.id == user_id, User.status == UserStatus.ACTIVE)
        .correlate_except(User)
    )


async def user_account_is_active(
    session: AsyncSession,
    user_id: UUID,
    *,
    serialize_with_status_change: bool = False,
) -> bool:
    """Read global account authority, optionally holding it through commit.

    Assignment callers enable serialization only after acquiring their normal
    aggregate and driver locks.  If suspension owns the user row first, this read
    waits and observes ``SUSPENDED``.  If assignment owns the shared row lock
    first, suspension waits until that already-authorized command commits.
    """
    statement = select(User.status).where(User.id == user_id)
    if serialize_with_status_change:
        statement = statement.with_for_update(read=True)
    return await session.scalar(statement) == UserStatus.ACTIVE


async def lock_user_for_status_change(
    session: AsyncSession, user_id: UUID,
) -> User | None:
    """Acquire and refresh the exclusive row lock used by account containment."""
    return await session.scalar(
        select(User)
        .where(User.id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
