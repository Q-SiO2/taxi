from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from taximobile_api.domains.safety.models import (
    SafetyReportCategory,
    SafetyReportStatus,
    SafetyResolutionCode,
)
from taximobile_api.domains.support.models import CaseNoteVisibility, SupportPriority


class SafetyReportCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ride_id: UUID
    category: SafetyReportCategory
    description: str = Field(min_length=3, max_length=4000)

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class SafetyReportResponse(BaseModel):
    id: UUID
    city_id: UUID
    ride_id: UUID
    category: SafetyReportCategory
    status: SafetyReportStatus
    latest_public_message: str | None = None
    latest_public_message_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SafetyReportListResponse(BaseModel):
    items: list[SafetyReportResponse]
    page: int
    limit: int
    total: int


class SafetyTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_status: SafetyReportStatus
    assigned_to_user_id: UUID | None = None
    resolution_code: SafetyResolutionCode | None = None
    participant_message: str | None = Field(default=None, min_length=3, max_length=1000)
    internal_note: str = Field(min_length=3, max_length=1000)

    @field_validator("participant_message", "internal_note", mode="before")
    @classmethod
    def normalize_transition_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class SupportSafetyEscalationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: SafetyReportCategory
    internal_note: str = Field(min_length=3, max_length=1000)

    @field_validator("internal_note", mode="before")
    @classmethod
    def normalize_internal_note(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class SupportSafetyEscalationResponse(BaseModel):
    """Minimal handoff receipt safe for an ordinary support agent."""

    safety_report_id: UUID
    source_support_ticket_id: UUID
    city_id: UUID
    status: SafetyReportStatus
    created_at: datetime


class SafetyReportNoteAdminResponse(BaseModel):
    id: UUID
    author_user_id: UUID
    visibility: CaseNoteVisibility
    message: str
    created_at: datetime


class SafetyReportAdminSummaryResponse(BaseModel):
    id: UUID
    city_id: UUID
    ride_id: UUID
    reporter_user_id: UUID
    category: SafetyReportCategory
    status: SafetyReportStatus
    priority: SupportPriority
    assigned_to_user_id: UUID | None
    response_due_at: datetime
    first_acknowledged_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SafetyReportAdminDetailResponse(SafetyReportAdminSummaryResponse):
    reported_user_id: UUID | None
    source_support_ticket_id: UUID | None
    description: str
    escalated_at: datetime | None
    resolved_at: datetime | None
    closed_at: datetime | None
    resolution_code: SafetyResolutionCode | None
    retention_policy_version: str
    retention_until: datetime | None
    notes: list[SafetyReportNoteAdminResponse]


class SafetyReportAdminListResponse(BaseModel):
    items: list[SafetyReportAdminSummaryResponse]
    page: int
    limit: int
    total: int
