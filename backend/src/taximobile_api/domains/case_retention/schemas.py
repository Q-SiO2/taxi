from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from taximobile_api.domains.case_retention.models import (
    CaseRetentionActionCode,
    LegalHoldReasonCode,
    LegalHoldReleaseReasonCode,
    LegalHoldStatus,
)


class CaseKind(StrEnum):
    SUPPORT = "SUPPORT"
    SAFETY = "SAFETY"


class LegalHoldCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_kind: CaseKind
    case_id: UUID
    reason_code: LegalHoldReasonCode
    authority_reference: str = Field(min_length=3, max_length=240, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]+$")
    review_due_at: datetime

    @field_validator("authority_reference", mode="before")
    @classmethod
    def normalize_reference(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class LegalHoldReleaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason_code: LegalHoldReleaseReasonCode


class LegalHoldResponse(BaseModel):
    id: UUID
    city_id: UUID
    case_kind: CaseKind
    case_id: UUID
    status: LegalHoldStatus
    reason_code: LegalHoldReasonCode
    authority_reference: str
    placed_by_user_id: UUID
    placed_at: datetime
    review_due_at: datetime
    released_by_user_id: UUID | None
    released_at: datetime | None
    release_reason_code: LegalHoldReleaseReasonCode | None


class LegalHoldListResponse(BaseModel):
    items: list[LegalHoldResponse]
    page: int
    limit: int
    total: int


class CaseRetentionActionResponse(BaseModel):
    id: UUID
    city_id: UUID
    case_kind: CaseKind
    case_id: UUID
    action: CaseRetentionActionCode
    retention_policy_version: str
    retention_due_at: datetime
    executed_at: datetime
    erased_note_count: int


class CaseRetentionActionListResponse(BaseModel):
    items: list[CaseRetentionActionResponse]
    page: int
    limit: int
    total: int
