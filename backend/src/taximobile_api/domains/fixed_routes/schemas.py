"""Strict public and operations contracts for published fixed routes."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from taximobile_api.domains.fixed_routes.models import FixedRouteDirectionCode
from taximobile_api.domains.markets.schemas import LocalizedName


VERSION_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
CODE_PATTERN = r"^[A-Z0-9][A-Z0-9_-]{0,63}$"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RouteCoordinate(StrictModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class LineStringGeometry(StrictModel):
    type: Literal["LineString"] = "LineString"
    coordinates: list[list[float]] = Field(min_length=2, max_length=500)

    @field_validator("coordinates")
    @classmethod
    def valid_coordinates(cls, value: list[list[float]]) -> list[list[float]]:
        normalized: list[list[float]] = []
        for point in value:
            if len(point) != 2:
                raise ValueError("Every route point must contain longitude and latitude.")
            longitude, latitude = point
            if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
                raise ValueError("Route coordinates are outside WGS84 bounds.")
            normalized.append([longitude, latitude])
        if len({(point[0], point[1]) for point in normalized}) < 2:
            raise ValueError("A route geometry must contain at least two distinct points.")
        return normalized

    def to_wkt(self) -> str:
        return "LINESTRING(" + ",".join(
            f"{longitude} {latitude}" for longitude, latitude in self.coordinates
        ) + ")"


class FixedRouteStopDraft(StrictModel):
    localized_name: LocalizedName
    location: RouteCoordinate


class FixedRouteDirectionDraft(StrictModel):
    direction_code: FixedRouteDirectionCode
    start_location_name: LocalizedName
    finish_location_name: LocalizedName
    start: RouteCoordinate
    finish: RouteCoordinate
    geometry: LineStringGeometry
    flat_fare_policy_version_id: UUID | None = None
    stops: list[FixedRouteStopDraft] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def meaningful_direction(self):
        if self.start == self.finish:
            raise ValueError("A fixed-route direction must have different start and finish points.")
        return self


class FixedRouteCreateRequest(StrictModel):
    operator_id: UUID
    code: str = Field(pattern=CODE_PATTERN)

    @field_validator("code", mode="before")
    @classmethod
    def clean_code(cls, value: str) -> str:
        return value.strip().upper()


class FixedRouteUpdateRequest(StrictModel):
    code: str = Field(pattern=CODE_PATTERN)
    reason: str = Field(min_length=3, max_length=240)

    @field_validator("code", mode="before")
    @classmethod
    def clean_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, value: str) -> str:
        return value.strip()


class FixedRouteVersionCreateRequest(StrictModel):
    version: str = Field(pattern=VERSION_PATTERN)
    localized_name: LocalizedName
    localized_description: LocalizedName | None = None
    effective_from: datetime
    effective_until: datetime | None = None
    directions: list[FixedRouteDirectionDraft] = Field(min_length=1, max_length=2)

    @model_validator(mode="after")
    def valid_version(self):
        if self.effective_from.tzinfo is None:
            raise ValueError("effective_from must include a timezone.")
        if self.effective_until is not None:
            if self.effective_until.tzinfo is None:
                raise ValueError("effective_until must include a timezone.")
            if self.effective_until <= self.effective_from:
                raise ValueError("effective_until must be after effective_from.")
        codes = [direction.direction_code for direction in self.directions]
        if len(codes) != len(set(codes)):
            raise ValueError("A route version cannot duplicate a direction code.")
        return self


class FixedRouteVersionUpdateRequest(StrictModel):
    expected_version: int = Field(ge=1)
    localized_name: LocalizedName | None = None
    localized_description: LocalizedName | None = None
    clear_localized_description: bool = False
    effective_from: datetime | None = None
    effective_until: datetime | None = None
    clear_effective_until: bool = False
    directions: list[FixedRouteDirectionDraft] | None = Field(
        default=None, min_length=1, max_length=2
    )

    @model_validator(mode="after")
    def valid_update(self):
        changed = self.model_fields_set - {"expected_version"}
        if not changed:
            raise ValueError("At least one route-version field must be supplied.")
        if self.localized_description is not None and self.clear_localized_description:
            raise ValueError(
                "localized_description and clear_localized_description cannot be combined."
            )
        if self.effective_until is not None and self.clear_effective_until:
            raise ValueError("effective_until and clear_effective_until cannot be combined.")
        if self.effective_from is not None and self.effective_from.tzinfo is None:
            raise ValueError("effective_from must include a timezone.")
        if self.effective_until is not None and self.effective_until.tzinfo is None:
            raise ValueError("effective_until must include a timezone.")
        if self.directions is not None:
            codes = [direction.direction_code for direction in self.directions]
            if len(codes) != len(set(codes)):
                raise ValueError("A route version cannot duplicate a direction code.")
        return self


class FixedRouteCommandRequest(StrictModel):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=240)

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, value: str) -> str:
        return value.strip()


class FixedRouteRetireRequest(StrictModel):
    reason: str = Field(min_length=3, max_length=240)

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, value: str) -> str:
        return value.strip()


class FixedRouteStopResponse(BaseModel):
    id: UUID
    sequence: int
    localized_name: dict[str, str]
    location: RouteCoordinate


class FixedRouteDirectionResponse(BaseModel):
    id: UUID
    direction_code: str
    start_location_name: dict[str, str]
    finish_location_name: dict[str, str]
    start: RouteCoordinate
    finish: RouteCoordinate
    geometry: LineStringGeometry
    flat_fare_policy_version_id: UUID | None
    flat_fare: str | None
    currency: str | None
    immediate_booking_enabled: bool
    scheduled_booking_enabled: bool
    stops: list[FixedRouteStopResponse]


class FixedRouteRideSummary(BaseModel):
    direction_version_id: UUID
    route_version_id: UUID
    route_code: str
    localized_route_name: dict[str, str]
    direction_code: str
    start_location_name: dict[str, str]
    finish_location_name: dict[str, str]


class FixedRouteVersionResponse(BaseModel):
    id: UUID
    fixed_route_id: UUID
    route_code: str
    city_id: UUID
    operator_id: UUID
    version: str
    localized_name: dict[str, str]
    localized_description: dict[str, str]
    status: str
    effective_from: datetime
    effective_until: datetime | None
    optimistic_version: int
    directions: list[FixedRouteDirectionResponse]
    created_by_user_id: UUID | None = None
    submitted_by_user_id: UUID | None = None
    submitted_at: datetime | None = None
    published_by_user_id: UUID | None = None
    published_at: datetime | None = None
    retired_by_user_id: UUID | None = None
    retired_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class FixedRouteResponse(BaseModel):
    id: UUID
    city_id: UUID
    operator_id: UUID
    code: str
    status: str
    versions: list[FixedRouteVersionResponse] = Field(default_factory=list)


class FixedRouteListResponse(BaseModel):
    items: list[FixedRouteResponse]
    page: int
    limit: int
    total: int


class FixedRouteFareOptionResponse(BaseModel):
    id: UUID
    version: str
    name: str
    status: str
    fixed_amount: str
    currency: str
    effective_from: datetime
    effective_until: datetime | None


class FixedRouteFareOptionListResponse(BaseModel):
    items: list[FixedRouteFareOptionResponse]


class PublicCityResponse(BaseModel):
    id: UUID
    code: str
    localized_name: dict[str, str]
    timezone: str
    lifecycle_status: str
    booking_available: bool


class PublicCityListResponse(BaseModel):
    items: list[PublicCityResponse]


class PublicFixedRouteListResponse(BaseModel):
    city: PublicCityResponse
    routes: list[FixedRouteResponse]
