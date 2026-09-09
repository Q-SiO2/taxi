from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from taximobile_api.domains.case_alerts.models import CaseAlertSeverity, CaseAlertStatus


class CaseAlertAcknowledgeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=3, max_length=240)

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class CaseAlertResponse(BaseModel):
    id: UUID
    city_id: UUID
    case_type: str
    case_id: UUID
    severity: CaseAlertSeverity
    status: CaseAlertStatus
    response_due_at: datetime
    first_detected_at: datetime
    last_evaluated_at: datetime
    delivery_attempts: int
    next_delivery_at: datetime | None
    last_delivered_at: datetime | None
    acknowledged_at: datetime | None
    acknowledged_by_user_id: UUID | None
    resolved_at: datetime | None


class CaseAlertListResponse(BaseModel):
    items: list[CaseAlertResponse]
    page: int
    limit: int
    total: int
