from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from taximobile_api.db.base import Base


class DevicePlatform(StrEnum):
    ANDROID = "ANDROID"
    IOS = "IOS"


class DeviceRegistrationKind(StrEnum):
    FIREBASE_INSTALLATION_ID = "FIREBASE_INSTALLATION_ID"
    LEGACY_FCM_TOKEN = "LEGACY_FCM_TOKEN"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(String(500), nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class DeviceToken(Base):
    __tablename__ = "device_tokens"
    # A provider registration identifies one app installation and must have one
    # current owner. Re-registering a kind/ID pair after an account switch
    # atomically transfers the row instead of leaving the former account able to
    # address the same phone.
    __table_args__ = (
        UniqueConstraint(
            "registration_kind",
            "token",
            name="one_owner_per_push_registration",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    platform: Mapped[DevicePlatform] = mapped_column(Enum(DevicePlatform, name="device_platform"), nullable=False)
    registration_kind: Mapped[DeviceRegistrationKind] = mapped_column(
        Enum(DeviceRegistrationKind, name="device_registration_kind"),
        nullable=False,
        default=DeviceRegistrationKind.FIREBASE_INSTALLATION_ID,
    )
    token: Mapped[str] = mapped_column(String(512), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
