from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from taximobile_api.domains.payments.models import PaymentMethod
from taximobile_api.domains.rides.schemas import Coordinate


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ScheduledBookingCreateRequest(StrictModel):
    scheduled_for: datetime
    city_id: UUID | None = None
    pickup: Coordinate | None = None
    destination: Coordinate | None = None
    fixed_route_direction_version_id: UUID | None = None
    passenger_note: str | None = Field(default=None, max_length=1000)
    payment_method: PaymentMethod = PaymentMethod.CASH
    expected_pricing_rule_version: str | None = Field(default=None, min_length=1, max_length=64)
    expected_operator_fee_policy_version: str | None = Field(default=None, min_length=1, max_length=64)
    expected_scheduling_policy_version: str | None = Field(default=None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def valid_service_shape(self):
        if self.scheduled_for.tzinfo is None:
            raise ValueError("scheduled_for must include a timezone.")
        fixed = self.fixed_route_direction_version_id is not None
        points = self.pickup is not None or self.destination is not None
        if fixed == points:
            raise ValueError(
                "Supply either one fixed-route direction or both pickup and destination."
            )
        if not fixed and (self.pickup is None or self.destination is None):
            raise ValueError("Both pickup and destination are required.")
        return self


class BookingEconomicsResponse(BaseModel):
    transport_fare: Decimal
    scheduling_surcharge: Decimal
    operator_service_fee: Decimal
    passenger_total: Decimal
    expected_driver_net: Decimal
    operator_allocation: Decimal
    currency: str
    pricing_rule_version: str
    operator_fee_policy_version: str
    scheduling_policy_version: str


class CancellationTermsResponse(BaseModel):
    passenger_cancel_cutoff_minutes: int
    surcharge_refund_mode: str
    summary: str


class ScheduledBookingEstimateResponse(BaseModel):
    city_id: UUID
    operator_id: UUID
    service_type: str
    fixed_route_direction_version_id: UUID | None
    scheduled_for: datetime
    city_timezone: str
    pickup: Coordinate
    destination: Coordinate
    economics: BookingEconomicsResponse
    cancellation_terms: CancellationTermsResponse
    payment_method: PaymentMethod


class ScheduledBookingResponse(BaseModel):
    id: UUID
    city_id: UUID
    operator_id: UUID
    service_type: str
    fixed_route_direction_version_id: UUID | None
    scheduled_for: datetime
    city_timezone: str
    status: str
    pickup: Coordinate
    destination: Coordinate
    economics: BookingEconomicsResponse
    cancellation_terms: CancellationTermsResponse
    driver_committed: bool
    live_ride_id: UUID | None
    cancellation_financial_outcome: str | None
    created_at: datetime


class ScheduledBookingListResponse(BaseModel):
    items: list[ScheduledBookingResponse]
    page: int
    limit: int
    total: int


class ScheduledBookingCancelRequest(StrictModel):
    reason: str = Field(min_length=1, max_length=120)


class ScheduledOfferPreferenceRequest(StrictModel):
    city_id: UUID
    enabled: bool


class ScheduledOfferPreferenceResponse(BaseModel):
    city_id: UUID
    enabled: bool
    updated_at: datetime


class ScheduledOfferPreferenceListResponse(BaseModel):
    items: list[ScheduledOfferPreferenceResponse]


class ScheduledOfferResponse(BaseModel):
    id: UUID
    booking_id: UUID
    status: str
    city_id: UUID
    service_type: str
    scheduled_for: datetime
    city_timezone: str
    expires_at: datetime
    pickup: Coordinate
    destination: Coordinate
    economics: BookingEconomicsResponse
    cancellation_terms: CancellationTermsResponse
    server_time: datetime


class ScheduledOfferListResponse(BaseModel):
    items: list[ScheduledOfferResponse]


class ScheduledOfferDeclineRequest(StrictModel):
    reason: str | None = Field(default=None, max_length=120)


class ScheduledCommitmentResponse(BaseModel):
    id: UUID
    booking_id: UUID
    city_id: UUID
    service_type: str
    scheduled_for: datetime
    city_timezone: str
    status: str
    protected_from: datetime
    protected_until: datetime
    pickup: Coordinate
    destination: Coordinate
    economics: BookingEconomicsResponse


class ScheduledCommitmentListResponse(BaseModel):
    items: list[ScheduledCommitmentResponse]
