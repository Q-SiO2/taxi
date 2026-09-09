from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from taximobile_api.db.base import Base


class LegalHoldStatus(StrEnum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"


class LegalHoldReasonCode(StrEnum):
    LITIGATION = "LITIGATION"
    REGULATORY_REQUEST = "REGULATORY_REQUEST"
    LAW_ENFORCEMENT_REQUEST = "LAW_ENFORCEMENT_REQUEST"
    DISPUTE_PRESERVATION = "DISPUTE_PRESERVATION"
    OTHER_LEGAL_OBLIGATION = "OTHER_LEGAL_OBLIGATION"


class CaseRetentionActionCode(StrEnum):
    PERSONAL_DATA_ERASED = "PERSONAL_DATA_ERASED"


class LegalHoldReleaseReasonCode(StrEnum):
    OBLIGATION_ENDED = "OBLIGATION_ENDED"
    REQUEST_WITHDRAWN = "REQUEST_WITHDRAWN"
    SUPERSEDED = "SUPERSEDED"
    PLACED_IN_ERROR = "PLACED_IN_ERROR"


class CaseLegalHold(Base):
    __tablename__ = "case_legal_holds"
    __table_args__ = (
        CheckConstraint(
            "(support_ticket_id IS NOT NULL)::integer + (safety_report_id IS NOT NULL)::integer = 1",
            name="case_legal_hold_exactly_one_case",
        ),
        CheckConstraint("status IN ('ACTIVE', 'RELEASED')", name="case_legal_hold_status"),
        CheckConstraint(
            "reason_code IN ('LITIGATION', 'REGULATORY_REQUEST', 'LAW_ENFORCEMENT_REQUEST', "
            "'DISPUTE_PRESERVATION', 'OTHER_LEGAL_OBLIGATION')",
            name="case_legal_hold_reason_code",
        ),
        CheckConstraint("review_due_at > placed_at", name="case_legal_hold_review_after_placement"),
        CheckConstraint(
            "(status = 'ACTIVE' AND released_by_user_id IS NULL AND released_at IS NULL AND release_reason_code IS NULL) OR "
            "(status = 'RELEASED' AND released_by_user_id IS NOT NULL AND released_at IS NOT NULL AND "
            "release_reason_code IN ('OBLIGATION_ENDED', 'REQUEST_WITHDRAWN', 'SUPERSEDED', 'PLACED_IN_ERROR'))",
            name="case_legal_hold_release_state",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    city_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False, index=True)
    support_ticket_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=True)
    safety_report_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("safety_reports.id", ondelete="CASCADE"), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=LegalHoldStatus.ACTIVE.value)
    reason_code: Mapped[str] = mapped_column(String(40), nullable=False)
    authority_reference: Mapped[str] = mapped_column(String(240), nullable=False)
    placed_by_user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    placed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    review_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    released_by_user_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    release_reason_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class CaseRetentionAction(Base):
    __tablename__ = "case_retention_actions"
    __table_args__ = (
        CheckConstraint(
            "(support_ticket_id IS NOT NULL)::integer + (safety_report_id IS NOT NULL)::integer = 1",
            name="case_retention_action_exactly_one_case",
        ),
        CheckConstraint("action = 'PERSONAL_DATA_ERASED'", name="case_retention_action_code"),
        CheckConstraint("erased_note_count >= 0", name="case_retention_action_note_count"),
        UniqueConstraint("support_ticket_id", name="uq_case_retention_actions_support_ticket"),
        UniqueConstraint("safety_report_id", name="uq_case_retention_actions_safety_report"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    city_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False, index=True)
    support_ticket_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("support_tickets.id", ondelete="RESTRICT"), nullable=True)
    safety_report_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("safety_reports.id", ondelete="RESTRICT"), nullable=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    retention_policy_version: Mapped[str] = mapped_column(String(40), nullable=False)
    retention_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    erased_note_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
