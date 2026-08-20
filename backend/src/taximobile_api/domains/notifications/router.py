from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.auth.dependencies import CurrentPrincipal, authenticated_principal
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.notifications.models import DeviceToken, Notification
from taximobile_api.domains.notifications.schemas import (
    DeviceRegistrationRequest,
    DeviceRegistrationResponse,
    DeviceRevocationRequest,
    NotificationListResponse,
    NotificationResponse,
)


router = APIRouter(tags=["notifications"])


def notification_response(notification: Notification) -> NotificationResponse:
    # Payloads are server-created IDs only; do not return arbitrary provider data.
    return NotificationResponse(
        id=notification.id,
        type=notification.type,
        title=notification.title,
        body=notification.body,
        data={str(key): str(value) for key, value in notification.data.items()},
        read_at=notification.read_at,
        created_at=notification.created_at,
    )


@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications(
    unread: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> NotificationListResponse:
    filters = [Notification.user_id == principal.user_id]
    if unread:
        filters.append(Notification.read_at.is_(None))
    notifications = list(
        await session.scalars(
            select(Notification)
            .where(*filters)
            .order_by(Notification.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    total = await session.scalar(select(func.count()).select_from(Notification).where(*filters))
    return NotificationListResponse(
        items=[notification_response(item) for item in notifications], page=page, limit=limit, total=total or 0
    )


@router.post("/notifications/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> NotificationResponse:
    async with session.begin():
        notification = await session.scalar(
            select(Notification)
            .where(Notification.id == notification_id, Notification.user_id == principal.user_id)
            .with_for_update()
        )
        if notification is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")
        if notification.read_at is None:
            notification.read_at = datetime.now(UTC)
            await session.flush()
    return notification_response(notification)


@router.post("/devices", response_model=DeviceRegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register_device(
    payload: DeviceRegistrationRequest,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> DeviceRegistrationResponse:
    now = datetime.now(UTC)
    async with session.begin():
        # PostgreSQL arbitrates concurrent callbacks and account switches. One
        # provider token has exactly one current TaxiMobile owner.
        statement = (
            insert(DeviceToken)
            .values(
                user_id=principal.user_id,
                session_id=principal.session_id,
                platform=payload.platform,
                registration_kind=payload.registration_kind,
                token=payload.registration_id,
                last_seen_at=now,
                revoked_at=None,
            )
            .on_conflict_do_update(
                index_elements=[DeviceToken.registration_kind, DeviceToken.token],
                set_={
                    "user_id": principal.user_id,
                    "session_id": principal.session_id,
                    "platform": payload.platform,
                    "registration_kind": payload.registration_kind,
                    "last_seen_at": now,
                    "revoked_at": None,
                },
            )
            .returning(DeviceToken.id, DeviceToken.platform, DeviceToken.registration_kind)
        )
        device_id, platform, registration_kind = (await session.execute(statement)).one()
    return DeviceRegistrationResponse(
        id=device_id,
        platform=platform,
        registration_kind=registration_kind,
    )


@router.delete("/devices", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_device(
    payload: DeviceRevocationRequest,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> Response:
    async with session.begin():
        await session.execute(
            update(DeviceToken)
            .where(
                DeviceToken.user_id == principal.user_id,
                DeviceToken.session_id == principal.session_id,
                DeviceToken.platform == payload.platform,
                DeviceToken.registration_kind == payload.registration_kind,
                DeviceToken.token == payload.registration_id,
                DeviceToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
    # Idempotent and ownership-safe: callers cannot probe another account's
    # device registration through response differences.
    return Response(status_code=status.HTTP_204_NO_CONTENT)
