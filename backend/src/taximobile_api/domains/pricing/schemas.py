"""Strict operations contracts for versioned city pricing economics."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from taximobile_api.domains.markets.models import ServiceType
from taximobile_api.domains.pricing.models import (
    BookingType,
    OperatorFeeCalculationMode,
    OperatorFeeFundingMode,
    PricingModel,
    PricingRoundingRule,
    SchedulingRefundMode,
    SchedulingSurchargeBeneficiary,
)


VERSION_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
CURRENCY_PATTERN = r"^[A-Z]{3}$"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _validate_effective_range(
    effective_from: datetime,
    effective_until: datetime | None,
) -> None:
    if effective_from.tzinfo is None:
        raise ValueError("effective_from must include a timezone.")
    if effective_until is not None:
        if effective_until.tzinfo is None:
            raise ValueError("effective_until must include a timezone.")
        if effective_until <= effective_from:
            raise ValueError("effective_until must be after effective_from.")


def _clean_currency(value: str) -> str:
    cleaned = value.strip().upper()
    if len(cleaned) != 3 or not cleaned.isalpha() or not cleaned.isascii():
        raise ValueError("currency must be a three-letter ISO-style code.")
    return cleaned


class PricingRuleCreateRequest(StrictModel):
    operator_id: UUID
    service_type: ServiceType = ServiceType.ON_DEMAND
    booking_type: BookingType = BookingType.IMMEDIATE
    fixed_route_direction_id: UUID | None = None
    name: str = Field(min_length=1, max_length=120)
    version: str = Field(pattern=VERSION_PATTERN)
    model: PricingModel = PricingModel.FIXED
    fixed_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(pattern=CURRENCY_PATTERN)
    effective_from: datetime
    effective_until: datetime | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("currency", mode="before")
    @classmethod
    def clean_currency(cls, value: str) -> str:
        return _clean_currency(value)

    @model_validator(mode="after")
    def supported_tariff(self):
        _validate_effective_range(self.effective_from, self.effective_until)
        if self.model != PricingModel.FIXED:
            raise ValueError("Phase 14 supports fixed city tariffs only.")
        if self.service_type not in {
            ServiceType.ON_DEMAND,
            ServiceType.FIXED_ROUTE,
        } or self.booking_type != BookingType.IMMEDIATE:
            raise ValueError(
                "Phase 15 tariff activation supports immediate on-demand or fixed-route service only."
            )
        if (
            self.service_type == ServiceType.ON_DEMAND
            and self.fixed_route_direction_id is not None
        ):
            raise ValueError("Only a fixed-route tariff can reference a route direction.")
        return self


class PricingRuleUpdateRequest(StrictModel):
    expected_version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    fixed_amount: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )
    currency: str | None = Field(default=None, pattern=CURRENCY_PATTERN)
    effective_from: datetime | None = None
    effective_until: datetime | None = None
    clear_effective_until: bool = False

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("currency", mode="before")
    @classmethod
    def clean_currency(cls, value: str | None) -> str | None:
        return _clean_currency(value) if value is not None else None

    @model_validator(mode="after")
    def valid_update(self):
        if not (
            self.name is not None
            or self.fixed_amount is not None
            or self.currency is not None
            or self.effective_from is not None
            or self.effective_until is not None
            or self.clear_effective_until
        ):
            raise ValueError("At least one tariff field must be supplied.")
        if self.effective_from is not None and self.effective_from.tzinfo is None:
            raise ValueError("effective_from must include a timezone.")
        if self.effective_until is not None and self.effective_until.tzinfo is None:
            raise ValueError("effective_until must include a timezone.")
        if self.effective_until is not None and self.clear_effective_until:
            raise ValueError("effective_until and clear_effective_until cannot be combined.")
        return self


class PricingPolicyCommandRequest(StrictModel):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=240)

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, value: str) -> str:
        return value.strip()


class PricingRuleResponse(BaseModel):
    id: UUID
    city_id: UUID
    operator_id: UUID
    service_type: str
    booking_type: str
    fixed_route_direction_id: UUID | None
    name: str
    version: str
    model: str
    fixed_amount: Decimal | None
    currency: str
    effective_from: datetime
    effective_until: datetime | None
    status: str
    optimistic_version: int
    created_by_user_id: UUID | None
    submitted_by_user_id: UUID | None
    submitted_at: datetime | None
    activated_by_user_id: UUID | None
    activated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PricingRuleListResponse(BaseModel):
    items: list[PricingRuleResponse]
    page: int
    limit: int
    total: int


class OperatorFeePolicyCreateRequest(StrictModel):
    operator_id: UUID
    service_type: ServiceType = ServiceType.ON_DEMAND
    version: str = Field(pattern=VERSION_PATTERN)
    calculation_mode: OperatorFeeCalculationMode
    funding_mode: OperatorFeeFundingMode
    eligible_base_code: str = Field(default="TRANSPORT_FARE", pattern=r"^TRANSPORT_FARE$")
    percentage_rate: Decimal | None = Field(
        default=None,
        ge=0,
        lt=100,
        max_digits=7,
        decimal_places=4,
    )
    flat_amount: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    currency: str = Field(pattern=CURRENCY_PATTERN)
    rounding_rule: PricingRoundingRule = PricingRoundingRule.HALF_UP_0_01
    minimum_driver_net: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    effective_from: datetime
    effective_until: datetime | None = None

    @field_validator("currency", mode="before")
    @classmethod
    def clean_currency(cls, value: str) -> str:
        return _clean_currency(value)

    @model_validator(mode="after")
    def valid_policy(self):
        _validate_effective_range(self.effective_from, self.effective_until)
        if self.service_type not in {
            ServiceType.ON_DEMAND,
            ServiceType.FIXED_ROUTE,
        }:
            raise ValueError(
                "Phase 15 fee policies support on-demand or fixed-route service only."
            )
        if self.calculation_mode == OperatorFeeCalculationMode.PERCENTAGE_OF_TRANSPORT_FARE:
            if self.percentage_rate is None or self.flat_amount is not None:
                raise ValueError("A percentage policy requires only percentage_rate.")
        elif self.flat_amount is None or self.percentage_rate is not None:
            raise ValueError("A flat policy requires only flat_amount.")
        return self


class OperatorFeePolicyUpdateRequest(StrictModel):
    expected_version: int = Field(ge=1)
    calculation_mode: OperatorFeeCalculationMode | None = None
    funding_mode: OperatorFeeFundingMode | None = None
    percentage_rate: Decimal | None = Field(
        default=None,
        ge=0,
        lt=100,
        max_digits=7,
        decimal_places=4,
    )
    flat_amount: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    currency: str | None = Field(default=None, pattern=CURRENCY_PATTERN)
    minimum_driver_net: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    effective_from: datetime | None = None
    effective_until: datetime | None = None
    clear_effective_until: bool = False

    @field_validator("currency", mode="before")
    @classmethod
    def clean_currency(cls, value: str | None) -> str | None:
        return _clean_currency(value) if value is not None else None

    @model_validator(mode="after")
    def valid_update(self):
        mutable_fields = self.model_fields_set - {"expected_version"}
        if not mutable_fields:
            raise ValueError("At least one operator-fee field must be supplied.")
        if self.effective_from is not None and self.effective_from.tzinfo is None:
            raise ValueError("effective_from must include a timezone.")
        if self.effective_until is not None and self.effective_until.tzinfo is None:
            raise ValueError("effective_until must include a timezone.")
        if self.effective_until is not None and self.clear_effective_until:
            raise ValueError("effective_until and clear_effective_until cannot be combined.")
        if self.percentage_rate is not None and self.flat_amount is not None:
            raise ValueError("percentage_rate and flat_amount cannot be combined.")
        return self


class OperatorFeePolicyResponse(BaseModel):
    id: UUID
    city_id: UUID
    operator_id: UUID
    service_type: str
    version: str
    status: str
    calculation_mode: str
    funding_mode: str
    eligible_base_code: str
    percentage_rate: Decimal | None
    flat_amount: Decimal | None
    currency: str
    rounding_rule: str
    minimum_driver_net: Decimal
    effective_from: datetime
    effective_until: datetime | None
    optimistic_version: int
    created_by_user_id: UUID | None
    submitted_by_user_id: UUID | None
    submitted_at: datetime | None
    activated_by_user_id: UUID | None
    activated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class OperatorFeePolicyListResponse(BaseModel):
    items: list[OperatorFeePolicyResponse]
    page: int
    limit: int
    total: int


class SchedulingPolicyCreateRequest(StrictModel):
    operator_id: UUID
    service_type: ServiceType = ServiceType.ON_DEMAND
    version: str = Field(pattern=VERSION_PATTERN)
    surcharge_amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    currency: str = Field(pattern=CURRENCY_PATTERN)
    beneficiary: SchedulingSurchargeBeneficiary
    collection_timing_code: str = Field(
        default="AT_RIDE_SETTLEMENT",
        pattern=r"^AT_RIDE_SETTLEMENT$",
    )
    minimum_lead_minutes: int = Field(default=60, ge=15, le=10080)
    maximum_horizon_days: int = Field(default=30, ge=1, le=365)
    offer_open_minutes_before: int = Field(default=1440, ge=30, le=43200)
    offer_response_seconds: int = Field(default=120, ge=15, le=3600)
    commitment_deadline_minutes_before: int = Field(default=180, ge=10, le=10080)
    handoff_minutes_before: int = Field(default=30, ge=5, le=1440)
    protected_duration_minutes: int = Field(default=90, ge=15, le=1440)
    conflict_buffer_before_minutes: int = Field(default=30, ge=0, le=1440)
    conflict_buffer_after_minutes: int = Field(default=30, ge=0, le=1440)
    passenger_cancel_cutoff_minutes: int = Field(default=60, ge=0, le=10080)
    driver_cancel_cutoff_minutes: int = Field(default=120, ge=0, le=10080)
    surcharge_refund_mode: SchedulingRefundMode = SchedulingRefundMode.FULL_BEFORE_CUTOFF
    fallback_matching_enabled: bool = True
    effective_from: datetime
    effective_until: datetime | None = None

    @field_validator("currency", mode="before")
    @classmethod
    def clean_currency(cls, value: str) -> str:
        return _clean_currency(value)

    @model_validator(mode="after")
    def valid_policy(self):
        _validate_effective_range(self.effective_from, self.effective_until)
        if self.service_type not in {ServiceType.ON_DEMAND, ServiceType.FIXED_ROUTE}:
            raise ValueError("Scheduling supports on-demand or fixed-route service only.")
        if not (
            self.offer_open_minutes_before > self.commitment_deadline_minutes_before
            >= self.handoff_minutes_before
        ):
            raise ValueError("Offer, commitment, and handoff windows must be in descending order.")
        return self


class SchedulingPolicyUpdateRequest(StrictModel):
    expected_version: int = Field(ge=1)
    surcharge_amount: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    currency: str | None = Field(default=None, pattern=CURRENCY_PATTERN)
    beneficiary: SchedulingSurchargeBeneficiary | None = None
    minimum_lead_minutes: int | None = Field(default=None, ge=15, le=10080)
    maximum_horizon_days: int | None = Field(default=None, ge=1, le=365)
    offer_open_minutes_before: int | None = Field(default=None, ge=30, le=43200)
    offer_response_seconds: int | None = Field(default=None, ge=15, le=3600)
    commitment_deadline_minutes_before: int | None = Field(default=None, ge=10, le=10080)
    handoff_minutes_before: int | None = Field(default=None, ge=5, le=1440)
    protected_duration_minutes: int | None = Field(default=None, ge=15, le=1440)
    conflict_buffer_before_minutes: int | None = Field(default=None, ge=0, le=1440)
    conflict_buffer_after_minutes: int | None = Field(default=None, ge=0, le=1440)
    passenger_cancel_cutoff_minutes: int | None = Field(default=None, ge=0, le=10080)
    driver_cancel_cutoff_minutes: int | None = Field(default=None, ge=0, le=10080)
    surcharge_refund_mode: SchedulingRefundMode | None = None
    fallback_matching_enabled: bool | None = None
    effective_from: datetime | None = None
    effective_until: datetime | None = None
    clear_effective_until: bool = False

    @field_validator("currency", mode="before")
    @classmethod
    def clean_currency(cls, value: str | None) -> str | None:
        return _clean_currency(value) if value is not None else None

    @model_validator(mode="after")
    def valid_update(self):
        if not (self.model_fields_set - {"expected_version"}):
            raise ValueError("At least one scheduling-policy field must be supplied.")
        if self.effective_from is not None and self.effective_from.tzinfo is None:
            raise ValueError("effective_from must include a timezone.")
        if self.effective_until is not None and self.effective_until.tzinfo is None:
            raise ValueError("effective_until must include a timezone.")
        if self.effective_until is not None and self.clear_effective_until:
            raise ValueError("effective_until and clear_effective_until cannot be combined.")
        return self


class SchedulingPolicyResponse(BaseModel):
    id: UUID
    city_id: UUID
    operator_id: UUID
    service_type: str
    version: str
    status: str
    surcharge_amount: Decimal
    currency: str
    beneficiary: str
    collection_timing_code: str
    minimum_lead_minutes: int
    maximum_horizon_days: int
    offer_open_minutes_before: int
    offer_response_seconds: int
    commitment_deadline_minutes_before: int
    handoff_minutes_before: int
    protected_duration_minutes: int
    conflict_buffer_before_minutes: int
    conflict_buffer_after_minutes: int
    passenger_cancel_cutoff_minutes: int
    driver_cancel_cutoff_minutes: int
    surcharge_refund_mode: str
    fallback_matching_enabled: bool
    effective_from: datetime
    effective_until: datetime | None
    optimistic_version: int
    created_by_user_id: UUID | None
    submitted_by_user_id: UUID | None
    submitted_at: datetime | None
    activated_by_user_id: UUID | None
    activated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SchedulingPolicyListResponse(BaseModel):
    items: list[SchedulingPolicyResponse]
    page: int
    limit: int
    total: int
