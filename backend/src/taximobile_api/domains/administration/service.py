from datetime import datetime
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.administration.models import AuditLog
from taximobile_api.domains.auth.models import Session
from taximobile_api.domains.notifications.models import DeviceToken


async def audit(database_session: AsyncSession, *, actor_user_id, action: str, resource_type: str, resource_id, changes: dict) -> None:
    database_session.add(AuditLog(actor_user_id=actor_user_id, action=action, resource_type=resource_type, resource_id=resource_id, changes=changes))
    await database_session.flush()


async def revoke_user_access(
    database_session: AsyncSession,
    *,
    user_id: UUID,
    revoked_at: datetime,
) -> tuple[int, int]:
    """Revoke every active session and push registration owned by one user."""

    session_result = await database_session.execute(
        update(Session)
        .where(Session.user_id == user_id, Session.revoked_at.is_(None))
        .values(revoked_at=revoked_at)
    )
    device_result = await database_session.execute(
        update(DeviceToken)
        .where(DeviceToken.user_id == user_id, DeviceToken.revoked_at.is_(None))
        .values(revoked_at=revoked_at)
    )
    return max(session_result.rowcount or 0, 0), max(device_result.rowcount or 0, 0)
