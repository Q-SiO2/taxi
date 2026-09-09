"""Persistent support case metadata, intentionally separate from safety reports."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from taximobile_api.db.base import Base


class SupportCategory(StrEnum):
    RIDE_PROBLEM = "RIDE_PROBLEM"
    FARE_DISPUTE = "FARE_DISPUTE"
    ACCOUNT_ACCESS = "ACCOUNT_ACCESS"
    OTHER = "OTHER"


class SupportTicketStatus(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class SupportPriority(StrEnum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class SupportResolutionCode(StrEnum):
    INFORMATION_PROVIDED = "INFORMATION_PROVIDED"
    ACTION_TAKEN = "ACTION_TAKEN"
    REFUND_RECORDED = "REFUND_RECORDED"
    DUPLICATE = "DUPLICATE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    NO_ACTION = "NO_ACTION"


class CaseNoteVisibility(StrEnum):
    INTERNAL = "INTERNAL"
    PARTICIPANT = "PARTICIPANT"


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    city_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("cities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    ride_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("rides.id"), nullable=True, index=True
    )
    category: Mapped[SupportCategory] = mapped_column(
        Enum(SupportCategory, name="support_ticket_category"), nullable=False
    )
    subject: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SupportTicketStatus] = mapped_column(
        Enum(SupportTicketStatus, name="support_ticket_status"), nullable=False, default=SupportTicketStatus.OPEN
    )
    priority: Mapped[SupportPriority] = mapped_column(
        Enum(SupportPriority, name="support_priority"),
        nullable=False,
        default=SupportPriority.NORMAL,
        index=True,
    )
    assigned_to_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    response_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    first_responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_code: Mapped[SupportResolutionCode | None] = mapped_column(
        Enum(SupportResolutionCode, name="support_resolution_code"), nullable=True
    )
    latest_public_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    latest_public_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retention_policy_version: Mapped[str] = mapped_column(
        String(40), nullable=False, default="support-launch-v1"
    )
    retention_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retention_action: Mapped[str | None] = mapped_column(String(32), nullable=True)
    retention_processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class SupportTicketNote(Base):
    """Append-only case communication; internal text never enters participant responses."""

    __tablename__ = "support_ticket_notes"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    ticket_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("support_tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    visibility: Mapped[CaseNoteVisibility] = mapped_column(
        Enum(CaseNoteVisibility, name="case_note_visibility"), nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
