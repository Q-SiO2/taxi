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


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
