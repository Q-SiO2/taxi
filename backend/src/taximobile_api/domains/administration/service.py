from datetime import datetime
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.administration.models import AuditLog, OperationsSession
from taximobile_api.domains.auth.models import Session, User, UserStatus
from taximobile_api.domains.notifications.models import DeviceToken


async def audit(
    database_session: AsyncSession,
    *,
    actor_user_id,
    action: str,
    resource_type: str,
    resource_id,
    changes: dict,
    market_id: UUID | None = None,
    operator_id: UUID | None = None,
    city_id: UUID | None = None,
) -> None:
    """Append a bounded audit event, including control-plane scope when known.

    Existing single-city administrative calls remain valid with an unscoped
    event.  Every new operations command supplies scope so filtering happens in
    SQL before pagination and cannot leak another city's count.
    """

    database_session.add(
        AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            market_id=market_id,
            operator_id=operator_id,
            city_id=city_id,
            changes=changes,
        )
    )
    await database_session.flush()


async def revoke_user_access(
    database_session: AsyncSession,
    *,
    user_id: UUID,
    revoked_at: datetime,
) -> tuple[int, int]:
    """Revoke mobile/operations sessions and push registrations for one user."""

    session_result = await database_session.execute(
        update(Session)
        .where(Session.user_id == user_id, Session.revoked_at.is_(None))
        .values(revoked_at=revoked_at)
    )
    operations_session_result = await database_session.execute(
        update(OperationsSession)
        .where(
            OperationsSession.user_id == user_id,
            OperationsSession.revoked_at.is_(None),
        )
        .values(revoked_at=revoked_at)
    )
    device_result = await database_session.execute(
        update(DeviceToken)
        .where(DeviceToken.user_id == user_id, DeviceToken.revoked_at.is_(None))
        .values(revoked_at=revoked_at)
    )
    session_count = max(session_result.rowcount or 0, 0) + max(
        operations_session_result.rowcount or 0,
        0,
    )
    return session_count, max(device_result.rowcount or 0, 0)


async def suspend_locked_user_access(
    database_session: AsyncSession,
    *,
    user: User,
    changed_at: datetime,
) -> tuple[UserStatus, int, int]:
    """Suspend a caller-locked account and revoke every server-side access path.

    Both administration surfaces acquire ``lock_user_for_status_change`` before
    calling this function. Assignment commit points take the complementary shared
    lock, making the winning order explicit without coupling account containment
    to ride, booking, or driver-profile mutation.
    """
    previous_status = user.status
    user.status = UserStatus.SUSPENDED
    user.updated_at = changed_at
    sessions_revoked, devices_revoked = await revoke_user_access(
        database_session,
        user_id=user.id,
        revoked_at=changed_at,
    )
    return previous_status, sessions_revoked, devices_revoked
