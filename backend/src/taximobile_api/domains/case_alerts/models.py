from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from taximobile_api.db.base import Base


class CaseAlertSeverity(StrEnum):
    HIGH = "HIGH"
    URGENT = "URGENT"


class CaseAlertStatus(StrEnum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class CaseOverdueAlert(Base):
    __tablename__ = "case_overdue_alerts"
    __table_args__ = (
        CheckConstraint(
            "(support_ticket_id IS NOT NULL)::integer + "
            "(safety_report_id IS NOT NULL)::integer = 1",
            name="case_overdue_alert_exactly_one_case",
        ),
        CheckConstraint("severity IN ('HIGH', 'URGENT')", name="case_overdue_alert_severity"),
        CheckConstraint(
            "status IN ('OPEN', 'ACKNOWLEDGED', 'RESOLVED')",
            name="case_overdue_alert_status",
        ),
        CheckConstraint("delivery_attempts >= 0", name="case_overdue_alert_delivery_attempts"),
        UniqueConstraint("support_ticket_id", name="uq_case_overdue_alert_support_ticket"),
        UniqueConstraint("safety_report_id", name="uq_case_overdue_alert_safety_report"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    city_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("cities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    support_ticket_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("support_tickets.id", ondelete="CASCADE"),
        nullable=True,
    )
    safety_report_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("safety_reports.id", ondelete="CASCADE"),
        nullable=True,
    )
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=CaseAlertStatus.OPEN.value)
    response_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    first_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivery_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_delivery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
