"""Scoped driver-register maintenance; no account or license authority."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from taximobile_api.domains.cooperatives.models import CooperativeMembershipStatus


class MembershipFields(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: CooperativeMembershipStatus
    membership_number: str | None = Field(default=None, min_length=1, max_length=120)
    joined_at: AwareDatetime | None = None
    ended_at: AwareDatetime | None = None
    reason: str = Field(min_length=3, max_length=240)

    @model_validator(mode="after")
    def dates_are_ordered(self):
        if self.joined_at is not None and self.ended_at is not None and self.ended_at < self.joined_at:
            raise ValueError("The membership end must not precede its join date.")
        return self


class OperatorMembershipCreateRequest(MembershipFields):
    driver_id: UUID
    status: Literal[CooperativeMembershipStatus.PENDING, CooperativeMembershipStatus.ACTIVE] = (
        CooperativeMembershipStatus.PENDING
    )


class OperatorMembershipUpdateRequest(MembershipFields):
    expected_updated_at: AwareDatetime
    # PATCH is a complete member-record edit, so omission cannot silently clear
    # a field that the staff member never inspected.
    membership_number: str | None = Field(min_length=1, max_length=120)
    joined_at: AwareDatetime | None
    ended_at: AwareDatetime | None


class OperatorMembershipResponse(BaseModel):
    id: UUID
    cooperative_id: UUID
    driver_id: UUID | None
    status: str
    membership_number: str | None
    joined_at: datetime | None
    ended_at: datetime | None
    updated_at: datetime


class OperatorMembershipListResponse(BaseModel):
    operator_id: UUID
    cooperative_id: UUID
    cooperative_status: str
    items: list[OperatorMembershipResponse]
    page: int
    limit: int
    total: int
