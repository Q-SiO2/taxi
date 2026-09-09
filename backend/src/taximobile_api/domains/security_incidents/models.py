"""Durable, market-scoped security incidents and append-only timeline facts."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from taximobile_api.db.base import Base
from taximobile_api.domains.markets.models import bounded_enum


class SecurityIncidentSeverity(StrEnum):
    SEV1 = "SEV1"
    SEV2 = "SEV2"
    SEV3 = "SEV3"
    SEV4 = "SEV4"


class SecurityIncidentCategory(StrEnum):
    ACCOUNT_COMPROMISE = "ACCOUNT_COMPROMISE"
    PROVIDER_CREDENTIAL_EXPOSURE = "PROVIDER_CREDENTIAL_EXPOSURE"
    DATA_EXPOSURE = "DATA_EXPOSURE"
    MALICIOUS_ACCESS = "MALICIOUS_ACCESS"
    SERVICE_ABUSE = "SERVICE_ABUSE"
    OTHER = "OTHER"


class SecurityIncidentStatus(StrEnum):
    OPEN = "OPEN"
    CONTAINING = "CONTAINING"
    CONTAINED = "CONTAINED"
    RECOVERING = "RECOVERING"
    RECOVERED = "RECOVERED"
    CLOSED = "CLOSED"


class SecurityIncidentTimelineKind(StrEnum):
    INCIDENT_OPENED = "INCIDENT_OPENED"
    EVIDENCE_LINKED = "EVIDENCE_LINKED"
    CONTAINMENT_ACTION = "CONTAINMENT_ACTION"
    COMMUNICATION_DECISION = "COMMUNICATION_DECISION"
    RECOVERY_ACTION = "RECOVERY_ACTION"
    POSTMORTEM_ACTION = "POSTMORTEM_ACTION"
    RESPONSIBILITY_CHANGED = "RESPONSIBILITY_CHANGED"
    STATUS_TRANSITION = "STATUS_TRANSITION"


class SecurityIncidentPostmortemOutcome(StrEnum):
    CONTROL_CHANGED = "CONTROL_CHANGED"
    FOLLOW_UP_REQUIRED = "FOLLOW_UP_REQUIRED"
    NO_FURTHER_ACTION = "NO_FURTHER_ACTION"


class SecurityIncidentResponsibility(StrEnum):
    SECURITY_RESPONSE_LEAD = "SECURITY_RESPONSE_LEAD"
    COMMUNICATIONS_LEAD = "COMMUNICATIONS_LEAD"
    OPERATIONS_LIAISON = "OPERATIONS_LIAISON"
    POSTMORTEM_OWNER = "POSTMORTEM_OWNER"


class SecurityIncident(Base):
    __tablename__ = "security_incidents"
    __table_args__ = (
        CheckConstraint(
            "containment_due_at > opened_at",
            name="security_incident_containment_due_after_open",
        ),
        CheckConstraint(
            "detected_at <= opened_at",
            name="security_incident_detected_before_open",
        ),
        CheckConstraint(
            "optimistic_version > 0",
            name="security_incident_version_positive",
        ),
        CheckConstraint(
            "(status IN ('OPEN', 'CONTAINING') AND contained_at IS NULL "
            "AND recovered_at IS NULL AND closed_at IS NULL "
            "AND postmortem_due_at IS NULL) OR "
            "(status IN ('CONTAINED', 'RECOVERING') AND contained_at IS NOT NULL "
            "AND recovered_at IS NULL AND closed_at IS NULL "
            "AND postmortem_due_at IS NULL) OR "
            "(status = 'RECOVERED' AND contained_at IS NOT NULL "
            "AND recovered_at IS NOT NULL AND closed_at IS NULL "
            "AND postmortem_due_at IS NULL) OR "
            "(status = 'CLOSED' AND contained_at IS NOT NULL "
            "AND recovered_at IS NOT NULL AND closed_at IS NOT NULL "
            "AND postmortem_due_at IS NOT NULL)",
            name="security_incident_lifecycle_timestamps",
        ),
        CheckConstraint(
            "contained_at IS NULL OR contained_at >= opened_at",
            name="security_incident_contained_after_open",
        ),
        CheckConstraint(
            "recovered_at IS NULL OR recovered_at >= contained_at",
            name="security_incident_recovered_after_contained",
        ),
        CheckConstraint(
            "closed_at IS NULL OR closed_at >= recovered_at",
            name="security_incident_closed_after_recovered",
        ),
        CheckConstraint(
            "postmortem_due_at IS NULL OR postmortem_due_at > closed_at",
            name="security_incident_postmortem_after_close",
        ),
        CheckConstraint(
            "(postmortem_completed_at IS NULL "
            "AND postmortem_completed_by_user_id IS NULL "
            "AND postmortem_outcome IS NULL) OR "
            "(status = 'CLOSED' AND postmortem_completed_at IS NOT NULL "
            "AND postmortem_completed_by_user_id IS NOT NULL "
            "AND postmortem_outcome IS NOT NULL)",
            name="security_incident_postmortem_completion_shape",
        ),
        CheckConstraint(
            "postmortem_completed_at IS NULL OR postmortem_completed_at >= closed_at",
            name="security_incident_postmortem_completed_after_close",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    reference: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    market_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("markets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    city_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("cities.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    severity: Mapped[SecurityIncidentSeverity] = mapped_column(
        bounded_enum(SecurityIncidentSeverity, "security_incident_severity", 8),
        nullable=False,
        index=True,
    )
    category: Mapped[SecurityIncidentCategory] = mapped_column(
        bounded_enum(SecurityIncidentCategory, "security_incident_category", 40),
        nullable=False,
        index=True,
    )
    status: Mapped[SecurityIncidentStatus] = mapped_column(
        bounded_enum(SecurityIncidentStatus, "security_incident_status", 16),
        nullable=False,
        default=SecurityIncidentStatus.OPEN,
        index=True,
    )
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    reported_by_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    lead_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    containment_due_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    contained_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    recovered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    postmortem_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    postmortem_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    postmortem_completed_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    postmortem_outcome: Mapped[SecurityIncidentPostmortemOutcome | None] = mapped_column(
        bounded_enum(
            SecurityIncidentPostmortemOutcome,
            "security_incident_postmortem_outcome",
            32,
        ),
        nullable=True,
    )
    optimistic_version: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=1
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class SecurityIncidentTimelineEntry(Base):
    __tablename__ = "security_incident_timeline_entries"
    __table_args__ = (
        UniqueConstraint(
            "incident_id",
            "sequence",
            name="uq_security_incident_timeline_incident_sequence",
        ),
        CheckConstraint(
            "sequence > 0",
            name="security_incident_timeline_sequence_positive",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    incident_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("security_incidents.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[SecurityIncidentTimelineKind] = mapped_column(
        bounded_enum(
            SecurityIncidentTimelineKind,
            "security_incident_timeline_kind",
            32,
        ),
        nullable=False,
        index=True,
    )
    actor_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    audit_log_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("audit_logs.id", ondelete="RESTRICT"),
        nullable=True,
    )
    external_reference: Mapped[str | None] = mapped_column(String(160), nullable=True)


class SecurityIncidentResponsibilityAssignment(Base):
    """Append-visible responsibility tenure with a one-time release transition."""

    __tablename__ = "security_incident_responsibility_assignments"
    __table_args__ = (
        Index(
            "ix_security_incident_responsibilities_incident",
            "incident_id",
            "assigned_at",
        ),
        Index(
            "ix_security_incident_responsibilities_assignee",
            "assigned_user_id",
            "released_at",
        ),
        Index(
            "uq_security_incident_responsibilities_active_role",
            "incident_id",
            "responsibility",
            unique=True,
            postgresql_where=text("released_at IS NULL"),
        ),
        CheckConstraint(
            "(released_at IS NULL AND released_by_user_id IS NULL "
            "AND release_reference IS NULL) OR "
            "(released_at IS NOT NULL AND released_by_user_id IS NOT NULL "
            "AND release_reference IS NOT NULL)",
            name="security_incident_responsibility_release_shape",
        ),
        CheckConstraint(
            "released_at IS NULL OR released_at >= assigned_at",
            name="security_incident_responsibility_release_after_assign",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    incident_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("security_incidents.id", ondelete="RESTRICT"),
        nullable=False,
    )
    responsibility: Mapped[SecurityIncidentResponsibility] = mapped_column(
        bounded_enum(
            SecurityIncidentResponsibility,
            "security_incident_responsibility",
            32,
        ),
        nullable=False,
    )
    assigned_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    assigned_by_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    assignment_reference: Mapped[str] = mapped_column(String(160), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    released_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    released_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    release_reference: Mapped[str | None] = mapped_column(
        String(160), nullable=True
    )
