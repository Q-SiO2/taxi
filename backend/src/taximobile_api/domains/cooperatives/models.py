"""Persistent cooperative and membership facts."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from taximobile_api.db.base import Base


class CooperativeStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class CooperativeMembershipStatus(StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    ENDED = "ENDED"


class Cooperative(Base):
    __tablename__ = "cooperatives"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    legal_identifier: Mapped[str | None] = mapped_column(String(120), unique=True, nullable=True)
    status: Mapped[CooperativeStatus] = mapped_column(
        Enum(CooperativeStatus, name="cooperative_status"),
        nullable=False,
        default=CooperativeStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class CooperativeMembership(Base):
    __tablename__ = "cooperative_memberships"
    __table_args__ = (
        UniqueConstraint("cooperative_id", "user_id", name="uq_cooperative_memberships_cooperative_user"),
        UniqueConstraint(
            "cooperative_id",
            "membership_number",
            name="uq_cooperative_memberships_cooperative_membership_number",
        ),
        CheckConstraint(
            "ended_at IS NULL OR joined_at IS NULL OR ended_at >= joined_at",
            name="membership_dates_ordered",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    cooperative_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("cooperatives.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    membership_status: Mapped[CooperativeMembershipStatus] = mapped_column(
        Enum(CooperativeMembershipStatus, name="cooperative_membership_status"),
        nullable=False,
        default=CooperativeMembershipStatus.PENDING,
        index=True,
    )
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    membership_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
