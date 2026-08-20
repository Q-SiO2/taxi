from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Coordinate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    address: str | None = Field(default=None, max_length=500)


class RideCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pickup: Coordinate
    destination: Coordinate
    passenger_note: str | None = Field(default=None, max_length=2000)


class RideEstimateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pickup: Coordinate
    destination: Coordinate


class FareEstimate(BaseModel):
    amount: str
    currency: str
    pricing_rule_version: str


class RideEstimateResponse(BaseModel):
    estimate: FareEstimate


class RideResponse(BaseModel):
    id: UUID
    status: str
    pickup: Coordinate
    destination: Coordinate
    completed_at: datetime | None = None
    driver: "AssignedDriverResponse | None" = None
    last_known_driver_location: "LastKnownDriverLocationResponse | None" = None


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
    pickup: Coordinate
    estimated_pickup_distance_meters: int | None = None
    estimated_pickup_time_seconds: int | None = None
    estimated_fare: RideOfferFareResponse | None = None
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


class PaymentReceiptResponse(BaseModel):
    method: str
    status: str


class RideReceiptResponse(BaseModel):
    ride_id: UUID
    completed_at: datetime
    fare: FareBreakdownResponse
    payment: PaymentReceiptResponse


class RideCompletionResponse(BaseModel):
    ride_id: UUID
    status: str
    fare: FareResponse


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
