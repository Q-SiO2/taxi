from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DriverApplicationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str = Field(min_length=1, max_length=120)


class DriverProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    display_name: str
    verification_status: str
    account_status: str
    availability_status: str


class VerificationResponse(BaseModel):
    status: str
    submitted_at: datetime | None = None


class DriverCredentialResponse(BaseModel):
    id: UUID
    type: str
    status: str
    issued_at: datetime | None
    expires_at: datetime | None


class DriverCredentialListResponse(BaseModel):
    credentials: list[DriverCredentialResponse]


class VehicleCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    make: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=80)
    year: int = Field(ge=1900, le=2100)
    color: str = Field(min_length=1, max_length=60)
    registration_number: str = Field(min_length=1, max_length=64)
    taxi_identifier: str | None = Field(default=None, max_length=64)
    passenger_capacity: int | None = Field(default=None, ge=1, le=12)

    @field_validator("registration_number", "taxi_identifier")
    @classmethod
    def normalize_identifiers(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else None


class VehicleResponse(BaseModel):
    id: UUID
    make: str
    model: str
    color: str
    status: str
    verification_status: str


class VehicleListResponse(BaseModel):
    vehicles: list[VehicleResponse]


class VehicleUpdateRequest(BaseModel):
    """Owner-controlled details; any material edit requires re-verification."""

    model_config = ConfigDict(extra="forbid")
    make: str | None = Field(default=None, min_length=1, max_length=80)
    model: str | None = Field(default=None, min_length=1, max_length=80)
    year: int | None = Field(default=None, ge=1900, le=2100)
    color: str | None = Field(default=None, min_length=1, max_length=60)
    registration_number: str | None = Field(default=None, min_length=1, max_length=64)
    taxi_identifier: str | None = Field(default=None, max_length=64)
    passenger_capacity: int | None = Field(default=None, ge=1, le=12)

    @field_validator("registration_number", "taxi_identifier")
    @classmethod
    def normalize_identifiers(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else None

    @model_validator(mode="after")
    def require_a_change(self) -> "VehicleUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("At least one vehicle field must be supplied.")
        for required_field in ("make", "model", "year", "color", "registration_number"):
            if required_field in self.model_fields_set and getattr(self, required_field) is None:
                raise ValueError(f"{required_field} cannot be null.")
        return self


class ActiveVehicleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vehicle_id: UUID


class AvailabilityResponse(BaseModel):
    status: str
    vehicle_id: UUID | None


class LocationUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    observed_at: datetime
    accuracy: float | None = Field(default=None, ge=0, le=10_000)
    heading: float | None = Field(default=None, ge=0, lt=360)
    speed: float | None = Field(default=None, ge=0, le=100)


class LocationUpdateResponse(BaseModel):
    accepted: bool = True
    server_time: datetime


class DriverRideResponse(BaseModel):
    id: UUID
    status: str
    completed_at: datetime | None


class DriverRideListResponse(BaseModel):
    items: list[DriverRideResponse]
    page: int
    limit: int
    total: int
