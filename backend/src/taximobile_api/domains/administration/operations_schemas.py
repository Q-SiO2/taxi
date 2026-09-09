"""Scoped grant and audit contracts for the operations console."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from taximobile_api.domains.administration.models import (
    AdministrativeGrantRequestAction,
    AdministrativeGrantRequestStatus,
    AdministrativeRoleTemplate,
)


class AdministrativeGrantCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    role_template: AdministrativeRoleTemplate
    market_id: UUID | None = None
    operator_id: UUID | None = None
    city_id: UUID | None = None
    expires_at: datetime | None = None
    reason: str = Field(min_length=3, max_length=240)

    @model_validator(mode="after")
    def valid_template_scope(self):
        if self.expires_at is not None and self.expires_at.tzinfo is None:
            raise ValueError("expires_at must include a timezone.")
        if self.role_template == AdministrativeRoleTemplate.PLATFORM_ADMIN:
            valid = self.market_id is not None and self.operator_id is None and self.city_id is None
        elif self.role_template == AdministrativeRoleTemplate.OPERATOR_ADMIN:
            valid = self.market_id is None and self.operator_id is not None and self.city_id is None
        else:
            valid = self.market_id is None and self.operator_id is None and self.city_id is not None
        if not valid:
            raise ValueError("Role template and administrative scope do not match.")
        return self


class AdministrativeGrantResponse(BaseModel):
    id: UUID
    user_id: UUID
    role_template: str
    market_id: UUID | None
    operator_id: UUID | None
    city_id: UUID | None
    granted_by_user_id: UUID
    grant_reason: str
    granted_at: datetime
    expires_at: datetime | None
    revoked_at: datetime | None
    revoked_by_user_id: UUID | None
    revocation_reason: str | None


class AdministrativeGrantListResponse(BaseModel):
    items: list[AdministrativeGrantResponse]
    page: int
    limit: int
    total: int


class AdministrativeGrantRevocationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grant_id: UUID
    reason: str = Field(min_length=3, max_length=240)


class AdministrativeGrantDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=240)


class AdministrativeGrantChangeRequestResponse(BaseModel):
    id: UUID
    action: AdministrativeGrantRequestAction
    status: AdministrativeGrantRequestStatus
    requester_user_id: UUID
    decided_by_user_id: UUID | None
    target_user_id: UUID
    role_template: AdministrativeRoleTemplate
    market_id: UUID | None
    operator_id: UUID | None
    city_id: UUID | None
    source_grant_id: UUID | None
    resulting_grant_id: UUID | None
    reason: str
    decision_reason: str | None
    requested_grant_expires_at: datetime | None
    requested_at: datetime
    decided_at: datetime | None
    optimistic_version: int


class AdministrativeGrantChangeRequestListResponse(BaseModel):
    items: list[AdministrativeGrantChangeRequestResponse]
    page: int
    limit: int
    total: int


class OperationsAuditLogResponse(BaseModel):
    id: UUID
    actor_user_id: UUID
    action: str
    resource_type: str
    resource_id: UUID
    market_id: UUID | None
    operator_id: UUID | None
    city_id: UUID | None
    changes: dict
    created_at: datetime


class OperationsAuditLogListResponse(BaseModel):
    items: list[OperationsAuditLogResponse]
    page: int
    limit: int
    total: int


class OperationsAccountSecurityReason(StrEnum):
    ACCOUNT_COMPROMISE = "ACCOUNT_COMPROMISE"
    VERIFIED_USER_REQUEST = "VERIFIED_USER_REQUEST"
    SAFETY_CONTAINMENT = "SAFETY_CONTAINMENT"
    LEGAL_REQUIREMENT = "LEGAL_REQUIREMENT"
    SECURITY_INCIDENT = "SECURITY_INCIDENT"


class OperationsAccountSecurityActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason_code: OperationsAccountSecurityReason
    case_reference: str = Field(
        min_length=7,
        max_length=72,
        pattern=r"^(?:SUP|SAF|SEC)-[A-Z0-9][A-Z0-9-]{2,67}$",
    )

    @field_validator("case_reference", mode="before")
    @classmethod
    def normalize_case_reference(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value
