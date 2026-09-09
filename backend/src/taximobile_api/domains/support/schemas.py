"""The user-facing support contract. Extra fields are rejected deliberately."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from taximobile_api.domains.support.models import (
    CaseNoteVisibility,
    SupportCategory,
    SupportPriority,
    SupportResolutionCode,
    SupportTicketStatus,
)


class SupportTicketCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: SupportCategory
    subject: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=4000)
    ride_id: UUID | None = None
    city_id: UUID | None = None

    @field_validator("subject", "description", mode="before")
    @classmethod
    def normalize_participant_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class SupportTicketResponse(BaseModel):
    id: UUID
    city_id: UUID
    category: SupportCategory
    subject: str
    description: str
    ride_id: UUID | None
    status: str
    latest_public_message: str | None = None
    latest_public_message_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SupportTicketListResponse(BaseModel):
    items: list[SupportTicketResponse]
    page: int
    limit: int
    total: int


class SupportTriageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority: SupportPriority
    assigned_to_user_id: UUID | None = None
    participant_message: str = Field(min_length=3, max_length=1000)
    internal_note: str = Field(min_length=3, max_length=1000)

    @field_validator("participant_message", "internal_note", mode="before")
    @classmethod
    def normalize_triage_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class SupportTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_status: SupportTicketStatus
    resolution_code: SupportResolutionCode | None = None
    participant_message: str | None = Field(default=None, min_length=3, max_length=1000)
    internal_note: str = Field(min_length=3, max_length=1000)

    @field_validator("participant_message", "internal_note", mode="before")
    @classmethod
    def normalize_transition_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class SupportTicketNoteAdminResponse(BaseModel):
    id: UUID
    author_user_id: UUID
    visibility: CaseNoteVisibility
    message: str
    created_at: datetime


class SupportTicketAdminSummaryResponse(BaseModel):
    id: UUID
    city_id: UUID
    user_id: UUID
    ride_id: UUID | None
    category: SupportCategory
    subject: str
    status: SupportTicketStatus
    priority: SupportPriority
    assigned_to_user_id: UUID | None
    response_due_at: datetime
    first_responded_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SupportTicketAdminDetailResponse(SupportTicketAdminSummaryResponse):
    description: str
    resolution_code: SupportResolutionCode | None
    resolved_at: datetime | None
    closed_at: datetime | None
    retention_policy_version: str
    retention_until: datetime | None
    notes: list[SupportTicketNoteAdminResponse]


class SupportTicketAdminListResponse(BaseModel):
    items: list[SupportTicketAdminSummaryResponse]
    page: int
    limit: int
    total: int
