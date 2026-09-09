from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from taximobile_api.db.base import Base
from taximobile_api.domains.markets.models import bounded_enum


class RideCoordinationCode(StrEnum):
    """The complete launch vocabulary; arbitrary participant text is forbidden."""

    PASSENGER_AT_PICKUP = "PASSENGER_AT_PICKUP"
    PASSENGER_NEEDS_MORE_TIME = "PASSENGER_NEEDS_MORE_TIME"
    PASSENGER_CANNOT_FIND_DRIVER = "PASSENGER_CANNOT_FIND_DRIVER"
    DRIVER_ON_MY_WAY = "DRIVER_ON_MY_WAY"
    DRIVER_AT_PICKUP = "DRIVER_AT_PICKUP"
    DRIVER_CANNOT_FIND_PASSENGER = "DRIVER_CANNOT_FIND_PASSENGER"


class RideCoordinationMessage(Base):
    """One closed-code coordination fact for an assigned, non-terminal ride."""

    __tablename__ = "ride_coordination_messages"
    __table_args__ = (
        Index(
            "ix_ride_coordination_messages_ride_created",
            "ride_id",
            "created_at",
        ),
        Index(
            "ix_ride_coordination_messages_sender_ride",
            "sender_user_id",
            "ride_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    ride_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("rides.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    code: Mapped[RideCoordinationCode] = mapped_column(
        bounded_enum(RideCoordinationCode, "ride_coordination_code", 40),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
