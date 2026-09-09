"""Strict API contracts for security-incident operations."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from taximobile_api.domains.security_incidents.models import (
    SecurityIncidentCategory,
    SecurityIncidentPostmortemOutcome,
    SecurityIncidentResponsibility,
    SecurityIncidentSeverity,
    SecurityIncidentStatus,
    SecurityIncidentTimelineKind,
)
from taximobile_api.domains.security_incidents.service import SecurityIncidentTransition


REFERENCE_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:/-]{2,159}$"
MANUAL_TIMELINE_KINDS = frozenset(
    {
        SecurityIncidentTimelineKind.EVIDENCE_LINKED,
        SecurityIncidentTimelineKind.CONTAINMENT_ACTION,
        SecurityIncidentTimelineKind.COMMUNICATION_DECISION,
        SecurityIncidentTimelineKind.RECOVERY_ACTION,
        SecurityIncidentTimelineKind.POSTMORTEM_ACTION,
    }
)


class SecurityIncidentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    market_id: UUID
    city_id: UUID | None = None
    severity: SecurityIncidentSeverity
    category: SecurityIncidentCategory
    summary: str = Field(min_length=10, max_length=500)
    detected_at: datetime
    containment_due_at: datetime

    @field_validator("summary", mode="before")
    @classmethod
    def normalize_summary(cls, value: object) -> object:
        return " ".join(value.split()) if isinstance(value, str) else value


class SecurityIncidentTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transition: SecurityIncidentTransition
    expected_version: int = Field(ge=1)
    summary: str = Field(min_length=10, max_length=500)
    occurred_at: datetime
    postmortem_due_at: datetime | None = None

    @field_validator("summary", mode="before")
    @classmethod
    def normalize_summary(cls, value: object) -> object:
        return " ".join(value.split()) if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_close_fields(self) -> "SecurityIncidentTransitionRequest":
        if self.transition == SecurityIncidentTransition.CLOSE:
            if self.postmortem_due_at is None:
                raise ValueError("postmortem_due_at is required when closing an incident")
        elif self.postmortem_due_at is not None:
            raise ValueError("postmortem_due_at is only accepted when closing an incident")
        return self


class SecurityIncidentTimelineCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: SecurityIncidentTimelineKind
    summary: str = Field(min_length=10, max_length=500)
    occurred_at: datetime
    audit_log_id: UUID | None = None
    external_reference: str | None = Field(
        default=None,
        min_length=3,
        max_length=160,
        pattern=REFERENCE_PATTERN,
    )

    @field_validator("summary", mode="before")
    @classmethod
    def normalize_summary(cls, value: object) -> object:
        return " ".join(value.split()) if isinstance(value, str) else value

    @field_validator("external_reference", mode="before")
    @classmethod
    def normalize_reference(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_manual_entry(self) -> "SecurityIncidentTimelineCreateRequest":
        if self.kind not in MANUAL_TIMELINE_KINDS:
            raise ValueError("this timeline kind is generated only by the incident lifecycle")
        if self.audit_log_id is None and self.external_reference is None:
            raise ValueError("audit_log_id or external_reference is required")
        return self


class SecurityIncidentPostmortemCompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=1)
    outcome: SecurityIncidentPostmortemOutcome
    summary: str = Field(min_length=10, max_length=500)
    occurred_at: datetime
    audit_log_id: UUID | None = None
    external_reference: str | None = Field(
        default=None,
        min_length=3,
        max_length=160,
        pattern=REFERENCE_PATTERN,
    )

    @field_validator("summary", mode="before")
    @classmethod
    def normalize_summary(cls, value: object) -> object:
        return " ".join(value.split()) if isinstance(value, str) else value

    @field_validator("external_reference", mode="before")
    @classmethod
    def normalize_reference(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_reference(self) -> "SecurityIncidentPostmortemCompleteRequest":
        if self.audit_log_id is None and self.external_reference is None:
            raise ValueError("audit_log_id or external_reference is required")
        if (
            self.outcome == SecurityIncidentPostmortemOutcome.FOLLOW_UP_REQUIRED
            and self.external_reference is None
        ):
            raise ValueError(
                "external_reference is required when follow-up work remains"
            )
        return self


class SecurityIncidentResponsibilityAssignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=1)
    assigned_user_id: UUID
    occurred_at: datetime
    external_reference: str = Field(
        min_length=3,
        max_length=160,
        pattern=REFERENCE_PATTERN,
    )

    @field_validator("external_reference", mode="before")
    @classmethod
    def normalize_reference(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class SecurityIncidentResponse(BaseModel):
    id: UUID
    reference: str
    market_id: UUID
    city_id: UUID | None
    severity: SecurityIncidentSeverity
    category: SecurityIncidentCategory
    status: SecurityIncidentStatus
    summary: str
    reported_by_user_id: UUID
    lead_user_id: UUID
    detected_at: datetime
    opened_at: datetime
    containment_due_at: datetime
    contained_at: datetime | None
    recovered_at: datetime | None
    closed_at: datetime | None
    postmortem_due_at: datetime | None
    postmortem_completed_at: datetime | None
    postmortem_completed_by_user_id: UUID | None
    postmortem_outcome: SecurityIncidentPostmortemOutcome | None
    optimistic_version: int


class SecurityIncidentListResponse(BaseModel):
    items: list[SecurityIncidentResponse]
    page: int
    limit: int
    total: int


class SecurityIncidentTimelineResponse(BaseModel):
    id: UUID
    incident_id: UUID
    sequence: int
    kind: SecurityIncidentTimelineKind
    actor_user_id: UUID
    occurred_at: datetime
    recorded_at: datetime
    summary: str
    audit_log_id: UUID | None
    external_reference: str | None


class SecurityIncidentTimelineListResponse(BaseModel):
    items: list[SecurityIncidentTimelineResponse]
    page: int
    limit: int
    total: int


class SecurityIncidentResponsibilityResponse(BaseModel):
    id: UUID
    incident_id: UUID
    responsibility: SecurityIncidentResponsibility
    assigned_user_id: UUID
    assigned_by_user_id: UUID
    assignment_reference: str
    assigned_at: datetime
    released_at: datetime | None
    released_by_user_id: UUID | None
    release_reference: str | None
    incident_version: int


class SecurityIncidentResponsibilityListResponse(BaseModel):
    items: list[SecurityIncidentResponsibilityResponse]
    page: int
    limit: int
    total: int
