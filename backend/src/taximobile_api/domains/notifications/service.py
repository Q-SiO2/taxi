"""Create only minimal notification records within the source transaction."""

from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.notifications.models import Notification


async def notify(
    session: AsyncSession,
    *,
    user_id,
    notification_type: str,
    title: str,
    body: str,
    data: dict[str, str],
) -> Notification:
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        body=body,
        data=data,
    )
    session.add(notification)
    await session.flush()
    return notification
