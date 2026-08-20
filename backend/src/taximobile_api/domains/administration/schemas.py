from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from taximobile_api.domains.drivers.schemas import DriverProfileResponse


class AccountSecurityActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("A reason is required.")
        return value


class AccountSecurityActionResponse(BaseModel):
    user_id: UUID
    status: str
    sessions_revoked: int = Field(ge=0)
    device_registrations_revoked: int = Field(ge=0)
    changed_at: datetime


class AuditLogResponse(BaseModel):
    id: UUID
    actor_user_id: UUID
    action: str
    resource_type: str
    resource_id: UUID
    changes: dict[str, Any]
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    page: int
    limit: int
    total: int


class PricingRuleCreateRequest(BaseModel):
    """A deliberately small tariff contract for the supported MVP fixed-fare engine."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    fixed_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="MAD", min_length=3, max_length=3)
    effective_from: datetime
    effective_until: datetime | None = None

    @field_validator("name", "version", mode="before")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field must not be blank.")
        return value

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        value = value.strip().upper()
        if not value.isalpha():
            raise ValueError("Currency must use a three-letter ISO-style code.")
        return value

    @model_validator(mode="after")
    def validate_effective_range(self) -> "PricingRuleCreateRequest":
        if self.effective_from.tzinfo is None:
            raise ValueError("effective_from must include a timezone.")
        if self.effective_until is not None:
            if self.effective_until.tzinfo is None:
                raise ValueError("effective_until must include a timezone.")
            if self.effective_until <= self.effective_from:
                raise ValueError("effective_until must be after effective_from.")
        return self


class PricingRuleResponse(BaseModel):
    id: UUID
    name: str
    version: str
    model: str
    fixed_amount: Decimal | None
    currency: str
    effective_from: datetime
    effective_until: datetime | None
    status: str


class DriverApprovalResponse(BaseModel):
    driver: DriverProfileResponse
    approved_at: datetime
