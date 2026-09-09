from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from taximobile_api.db.base import Base
from taximobile_api.domains.support.models import CaseNoteVisibility, SupportPriority


class SafetyReportCategory(StrEnum):
    IMMEDIATE_DANGER = "IMMEDIATE_DANGER"
    HARASSMENT = "HARASSMENT"
    ASSAULT = "ASSAULT"
    UNSAFE_DRIVING = "UNSAFE_DRIVING"
    DISCRIMINATION = "DISCRIMINATION"
    VEHICLE_SAFETY = "VEHICLE_SAFETY"
    OTHER_SAFETY = "OTHER_SAFETY"


class SafetyReportStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class SafetyResolutionCode(StrEnum):
    SAFETY_ACTION_TAKEN = "SAFETY_ACTION_TAKEN"
    REFERRED_TO_AUTHORITIES = "REFERRED_TO_AUTHORITIES"
    INFORMATION_PROVIDED = "INFORMATION_PROVIDED"
    DUPLICATE = "DUPLICATE"
    NO_PLATFORM_ACTION = "NO_PLATFORM_ACTION"


class SafetyReport(Base):
    __tablename__ = "safety_reports"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    city_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("cities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    ride_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("rides.id"), nullable=True, index=True
    )
    reporter_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    reported_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    source_support_ticket_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("support_tickets.id"),
        nullable=True,
        unique=True,
    )
    category: Mapped[SafetyReportCategory] = mapped_column(
        Enum(SafetyReportCategory, name="safety_report_category"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SafetyReportStatus] = mapped_column(
        Enum(SafetyReportStatus, name="safety_report_status"),
        nullable=False,
        default=SafetyReportStatus.SUBMITTED,
    )
    priority: Mapped[SupportPriority] = mapped_column(
        Enum(SupportPriority, name="support_priority"), nullable=False, index=True
    )
    assigned_to_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    response_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    first_acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_code: Mapped[SafetyResolutionCode | None] = mapped_column(
        Enum(SafetyResolutionCode, name="safety_resolution_code"), nullable=True
    )
    latest_public_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    latest_public_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retention_policy_version: Mapped[str] = mapped_column(
        String(40), nullable=False, default="safety-launch-v1"
    )
    retention_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retention_action: Mapped[str | None] = mapped_column(String(32), nullable=True)
    retention_processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class SafetyReportNote(Base):
    __tablename__ = "safety_report_notes"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    report_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("safety_reports.id", ondelete="CASCADE"),
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
