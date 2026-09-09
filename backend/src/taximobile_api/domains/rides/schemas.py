from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from taximobile_api.domains.fixed_routes.schemas import FixedRouteRideSummary
from taximobile_api.domains.payments.models import PaymentMethod
from taximobile_api.domains.payments.schemas import PassengerRefundSummaryResponse
from taximobile_api.domains.ride_communications.schemas import (
    RideCoordinationMessageResponse,
)


class Coordinate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    address: str | None = Field(default=None, max_length=500)


class RideCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pickup: Coordinate | None = None
    destination: Coordinate | None = None
    fixed_route_direction_version_id: UUID | None = None
    city_id: UUID | None = None
    passenger_note: str | None = Field(default=None, max_length=2000)
    payment_method: PaymentMethod = PaymentMethod.CASH

    @model_validator(mode="after")
    def one_service_source(self):
        if self.fixed_route_direction_version_id is None:
            if self.pickup is None or self.destination is None:
                raise ValueError("Point-to-point rides require pickup and destination.")
        elif self.pickup is not None or self.destination is not None:
            raise ValueError(
                "A fixed-route ride derives pickup and destination from its published direction."
            )
        return self


class RideEstimateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pickup: Coordinate | None = None
    destination: Coordinate | None = None
    fixed_route_direction_version_id: UUID | None = None
    city_id: UUID | None = None

    @model_validator(mode="after")
    def one_service_source(self):
        if self.fixed_route_direction_version_id is None:
            if self.pickup is None or self.destination is None:
                raise ValueError("Point-to-point estimates require pickup and destination.")
        elif self.pickup is not None or self.destination is not None:
            raise ValueError(
                "A fixed-route estimate derives endpoints from its published direction."
            )
        return self


class FareEstimate(BaseModel):
    amount: str
    currency: str
    pricing_rule_version: str
    city_id: UUID
    operator_id: UUID
    service_type: str = "ON_DEMAND"
    fixed_route: FixedRouteRideSummary | None = None
    economics: "FareEconomicsResponse"


class FareEconomicsResponse(BaseModel):
    transport_fare: str
    scheduling_surcharge: str
    operator_service_fee: str
    passenger_total: str
    expected_driver_net: str
    operator_allocation: str
    operator_fee_policy_version: str
    operator_fee_calculation_mode: str
    operator_fee_funding_mode: str
    scheduling_policy_version: str | None = None


class RideEstimateResponse(BaseModel):
    estimate: FareEstimate
    payment_methods: list[str]


class RideResponse(BaseModel):
    id: UUID
    city_id: UUID
    operator_id: UUID
    service_type: str = "ON_DEMAND"
    fixed_route: FixedRouteRideSummary | None = None
    status: str
    pickup: Coordinate
    destination: Coordinate
    completed_at: datetime | None = None
    driver: "AssignedDriverResponse | None" = None
    last_known_driver_location: "LastKnownDriverLocationResponse | None" = None
    latest_coordination_message: RideCoordinationMessageResponse | None = None
    payment_method: str


class AssignedVehicleResponse(BaseModel):
    make: str
    model: str
    color: str
    taxi_identifier: str | None = None


class AssignedDriverResponse(BaseModel):
    display_name: str
    vehicle: AssignedVehicleResponse


class LastKnownDriverLocationResponse(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    observed_at: datetime
    accuracy_meters: float | None = Field(default=None, ge=0)


class RideListResponse(BaseModel):
    items: list[RideResponse]
    page: int
    limit: int
    total: int


class CancellationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=1, max_length=120)


class RideOfferFareResponse(BaseModel):
    amount: str
    currency: str


class RideOfferResponse(BaseModel):
    id: UUID
    ride_id: UUID
    service_type: str = "ON_DEMAND"
    fixed_route: FixedRouteRideSummary | None = None
    pickup: Coordinate
    estimated_pickup_distance_meters: int | None = None
    estimated_pickup_time_seconds: int | None = None
    estimated_fare: RideOfferFareResponse | None = None
    economics: FareEconomicsResponse | None = None
    matching_algorithm_version: str | None = None
    issued_at: datetime
    expires_at: datetime


class RideOfferListResponse(BaseModel):
    server_time: datetime
    offers: list[RideOfferResponse]


class RideOfferAcceptResponse(BaseModel):
    ride_id: UUID
    status: str


class RideOfferDeclineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=1, max_length=120)


class RideOfferDeclineResponse(BaseModel):
    success: bool = True


class RideTransitionResponse(BaseModel):
    ride_id: UUID
    status: str
    occurred_at: datetime


class RideCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class FareResponse(BaseModel):
    amount: str
    currency: str


class FareComponentResponse(BaseModel):
    code: str
    label: str
    amount: str


class FareBreakdownResponse(FareResponse):
    pricing_rule_version: str | None = None
    components: list[FareComponentResponse] = []
    economics: FareEconomicsResponse | None = None


class PaymentReceiptResponse(BaseModel):
    method: str
    status: str
    manual_transfer: "ManualTransferInstructionsResponse | None" = None
    refunds: PassengerRefundSummaryResponse | None = None


class ManualTransferInstructionsResponse(BaseModel):
    recipient_name: str
    bank_account: str | None = None
    wallet_id: str | None = None
    payment_reference: str
    latest_claim_status: str | None = None


class RideReceiptResponse(BaseModel):
    ride_id: UUID
    completed_at: datetime
    fare: FareBreakdownResponse
    payment: PaymentReceiptResponse


class RideCompletionResponse(BaseModel):
    ride_id: UUID
    status: str
    fare: FareResponse
    payment_method: str


class RideRatingCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    score: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class RideRatingResponse(BaseModel):
    id: UUID
    score: int
    comment: str | None
    created_at: datetime


class RideRatingListResponse(BaseModel):
    items: list[RideRatingResponse]
