"""Strict operations contracts for market/city foundation resources."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from taximobile_api.domains.markets.constants import ALL_CITY_READINESS_GATES
from taximobile_api.domains.markets.models import (
    CityLifecycleStatus,
    ConfigurationStatus,
    OperatorStatus,
    OperatorType,
    ReadinessStatus,
    ServiceAreaStatus,
    ServiceType,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LocalizedName(StrictModel):
    en: str = Field(min_length=1, max_length=120)
    fr: str = Field(min_length=1, max_length=120)
    ar: str = Field(min_length=1, max_length=120)

    @field_validator("en", "fr", "ar")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Localized names cannot be blank.")
        return cleaned


class Coordinate(StrictModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class MultiPolygonGeometry(StrictModel):
    type: Literal["MultiPolygon"] = "MultiPolygon"
    coordinates: list[list[list[list[float]]]]

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(
        cls,
        value: list[list[list[list[float]]]],
    ) -> list[list[list[list[float]]]]:
        if not value:
            raise ValueError("A service area must contain at least one polygon.")
        vertices = 0
        for polygon in value:
            if not polygon:
                raise ValueError("Every polygon must contain an exterior ring.")
            for ring in polygon:
                if len(ring) < 4:
                    raise ValueError("Every polygon ring must contain at least four points.")
                normalized_ring: list[tuple[float, float]] = []
                for point in ring:
                    if len(point) != 2:
                        raise ValueError("Every point must contain longitude and latitude.")
                    longitude, latitude = point
                    if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
                        raise ValueError("Service-area coordinates are outside WGS84 bounds.")
                    normalized_ring.append((longitude, latitude))
                    vertices += 1
                if normalized_ring[0] != normalized_ring[-1]:
                    raise ValueError("Every polygon ring must be closed.")
        if vertices > 5_000:
            raise ValueError("A service-area version cannot exceed 5,000 vertices.")
        return value

    def to_wkt(self) -> str:
        polygons = []
        for polygon in self.coordinates:
            rings = []
            for ring in polygon:
                rings.append(
                    "(" + ",".join(f"{point[0]} {point[1]}" for point in ring) + ")"
                )
            polygons.append("(" + ",".join(rings) + ")")
        return "MULTIPOLYGON(" + ",".join(polygons) + ")"


class MarketResponse(BaseModel):
    id: UUID
    code: str
    name: str
    default_currency: str
    status: str


class MarketListResponse(BaseModel):
    items: list[MarketResponse]
    page: int
    limit: int
    total: int


class OperatorCreateRequest(StrictModel):
    market_id: UUID
    cooperative_id: UUID | None = None
    name: str = Field(min_length=1, max_length=200)
    operator_type: OperatorType

    @field_validator("name")
    @classmethod
    def clean_operator_name(cls, value: str) -> str:
        return value.strip()


class OperatorUpdateRequest(StrictModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    status: OperatorStatus | None = None

    @field_validator("name")
    @classmethod
    def clean_operator_update_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def has_change(self):
        if self.name is None and self.status is None:
            raise ValueError("At least one operator field is required.")
        return self


class OperatorResponse(BaseModel):
    id: UUID
    market_id: UUID
    cooperative_id: UUID | None
    name: str
    operator_type: str
    status: str
    created_at: datetime
    updated_at: datetime


class OperatorListResponse(BaseModel):
    items: list[OperatorResponse]
    page: int
    limit: int
    total: int


class CityCreateRequest(StrictModel):
    market_id: UUID
    code: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", min_length=2, max_length=64)
    localized_name: LocalizedName
    timezone: str = Field(pattern=r"^[A-Za-z_]+(?:/[A-Za-z0-9_+\-]+)+$", max_length=64)
    presentation_centroid: Coordinate


class CityUpdateRequest(StrictModel):
    expected_version: int = Field(ge=1)
    localized_name: LocalizedName | None = None
    timezone: str | None = Field(
        default=None,
        pattern=r"^[A-Za-z_]+(?:/[A-Za-z0-9_+\-]+)+$",
        max_length=64,
    )
    presentation_centroid: Coordinate | None = None

    @model_validator(mode="after")
    def has_change(self):
        if (
            self.localized_name is None
            and self.timezone is None
            and self.presentation_centroid is None
        ):
            raise ValueError("At least one city field is required.")
        return self


class CityLifecycleTransitionRequest(StrictModel):
    target_status: CityLifecycleStatus
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=240)


class CityResponse(BaseModel):
    id: UUID
    market_id: UUID
    code: str
    localized_name: LocalizedName
    timezone: str
    presentation_centroid: Coordinate
    lifecycle_status: str
    active_configuration_version_id: UUID | None
    optimistic_version: int
    is_legacy_compatibility: bool
    created_at: datetime
    updated_at: datetime


class CityListResponse(BaseModel):
    items: list[CityResponse]
    page: int
    limit: int
    total: int


class OperatorCityAssignmentCreateRequest(StrictModel):
    operator_id: UUID
    city_id: UUID
    service_type: ServiceType
    effective_from: datetime
    effective_until: datetime | None = None

    @model_validator(mode="after")
    def valid_range(self):
        if self.effective_from.tzinfo is None:
            raise ValueError("effective_from must include a timezone.")
        if self.effective_until is not None:
            if self.effective_until.tzinfo is None:
                raise ValueError("effective_until must include a timezone.")
            if self.effective_until <= self.effective_from:
                raise ValueError("effective_until must be after effective_from.")
        return self


class OperatorCityAssignmentRetireRequest(StrictModel):
    reason: str = Field(min_length=3, max_length=240)


class OperatorCityAssignmentResponse(BaseModel):
    id: UUID
    operator_id: UUID
    city_id: UUID
    service_type: str
    effective_from: datetime
    effective_until: datetime | None
    status: str
    created_at: datetime
    retired_at: datetime | None


class OperatorCityAssignmentListResponse(BaseModel):
    items: list[OperatorCityAssignmentResponse]
    page: int
    limit: int
    total: int


class ServiceAreaVersionCreateRequest(StrictModel):
    version: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
    boundary: MultiPolygonGeometry
    effective_from: datetime
    effective_until: datetime | None = None

    @model_validator(mode="after")
    def valid_range(self):
        if self.effective_from.tzinfo is None:
            raise ValueError("effective_from must include a timezone.")
        if self.effective_until is not None and self.effective_until <= self.effective_from:
            raise ValueError("effective_until must be after effective_from.")
        return self


class ServiceAreaVersionUpdateRequest(StrictModel):
    expected_version: int = Field(ge=1)
    boundary: MultiPolygonGeometry | None = None
    effective_from: datetime | None = None
    effective_until: datetime | None = None

    @model_validator(mode="after")
    def valid_update(self):
        if self.boundary is None and self.effective_from is None and self.effective_until is None:
            raise ValueError("At least one service-area field is required.")
        if self.effective_from is not None and self.effective_from.tzinfo is None:
            raise ValueError("effective_from must include a timezone.")
        return self


class ServiceAreaTransitionRequest(StrictModel):
    target_status: ServiceAreaStatus
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=240)


class ServiceAreaVersionResponse(BaseModel):
    id: UUID
    city_id: UUID
    version: str
    boundary: MultiPolygonGeometry
    status: str
    effective_from: datetime
    effective_until: datetime | None
    optimistic_version: int
    created_at: datetime
    updated_at: datetime


class ServiceAreaVersionListResponse(BaseModel):
    items: list[ServiceAreaVersionResponse]
    page: int
    limit: int
    total: int


class ConfigurationServiceInput(StrictModel):
    service_type: ServiceType
    operator_city_assignment_id: UUID
    tariff_version_id: UUID | None = None
    operator_fee_policy_version_id: UUID | None = None
    scheduling_policy_version_id: UUID | None = None
    payment_capability_version_id: UUID | None = None
    enabled: bool = True


class ConfigurationRouteInput(StrictModel):
    fixed_route_version_id: UUID
    immediate_booking_enabled: bool = True
    scheduled_booking_enabled: bool = False

    @model_validator(mode="after")
    def supported_booking_modes(self):
        if not self.immediate_booking_enabled and not self.scheduled_booking_enabled:
            raise ValueError("A configured route must enable at least one booking mode.")
        return self


class CityConfigurationCreateRequest(StrictModel):
    version: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
    service_area_version_id: UUID
    driver_requirement_version_id: UUID | None = None
    services: list[ConfigurationServiceInput] = Field(min_length=1, max_length=8)
    routes: list[ConfigurationRouteInput] = Field(default_factory=list, max_length=100)

    @field_validator("services")
    @classmethod
    def unique_services(cls, value: list[ConfigurationServiceInput]):
        service_types = [service.service_type for service in value]
        if len(service_types) != len(set(service_types)):
            raise ValueError("A configuration can contain each service type only once.")
        return value

    @field_validator("routes")
    @classmethod
    def unique_routes(cls, value: list[ConfigurationRouteInput]):
        ids = [route.fixed_route_version_id for route in value]
        if len(ids) != len(set(ids)):
            raise ValueError("A configuration cannot duplicate a fixed-route version.")
        return value


class CityConfigurationUpdateRequest(StrictModel):
    expected_version: int = Field(ge=1)
    service_area_version_id: UUID | None = None
    driver_requirement_version_id: UUID | None = None
    services: list[ConfigurationServiceInput] | None = Field(default=None, min_length=1, max_length=8)
    routes: list[ConfigurationRouteInput] | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def has_change(self):
        if (
            self.service_area_version_id is None
            and self.driver_requirement_version_id is None
            and self.services is None
            and self.routes is None
        ):
            raise ValueError("At least one configuration field is required.")
        if self.services is not None:
            service_types = [service.service_type for service in self.services]
            if len(service_types) != len(set(service_types)):
                raise ValueError("A configuration can contain each service type only once.")
        if self.routes is not None:
            ids = [route.fixed_route_version_id for route in self.routes]
            if len(ids) != len(set(ids)):
                raise ValueError("A configuration cannot duplicate a fixed-route version.")
        return self


class ConfigurationCommandRequest(StrictModel):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=240)


class ConfigurationServiceResponse(BaseModel):
    service_type: str
    operator_city_assignment_id: UUID
    tariff_version_id: UUID | None
    operator_fee_policy_version_id: UUID | None
    scheduling_policy_version_id: UUID | None
    payment_capability_version_id: UUID | None
    enabled: bool


class ConfigurationRouteResponse(BaseModel):
    fixed_route_version_id: UUID
    immediate_booking_enabled: bool
    scheduled_booking_enabled: bool


class ReadinessCheckResponse(BaseModel):
    id: UUID
    gate_code: str
    status: str
    non_secret_evidence_reference: str | None
    decided_at: datetime | None


class CityConfigurationResponse(BaseModel):
    id: UUID
    city_id: UUID
    version: str
    status: str
    service_area_version_id: UUID
    driver_requirement_version_id: UUID | None
    optimistic_version: int
    services: list[ConfigurationServiceResponse]
    routes: list[ConfigurationRouteResponse] = Field(default_factory=list)
    readiness_checks: list[ReadinessCheckResponse]
    missing_readiness_gates: list[str]
    missing_pilot_entry_gates: list[str]
    missing_public_activation_gates: list[str]
    post_launch_review_status: str
    submitted_at: datetime | None
    approved_at: datetime | None
    activated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CityConfigurationListResponse(BaseModel):
    items: list[CityConfigurationResponse]
    page: int
    limit: int
    total: int


class ReadinessDecisionRequest(StrictModel):
    gate_code: str = Field(max_length=64)
    status: ReadinessStatus
    non_secret_evidence_reference: str = Field(min_length=3, max_length=240)
    expected_configuration_version: int = Field(ge=1)

    @field_validator("gate_code")
    @classmethod
    def gate_is_allowlisted(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in ALL_CITY_READINESS_GATES:
            raise ValueError("Readiness gate is not allowlisted.")
        return normalized

    @field_validator("non_secret_evidence_reference")
    @classmethod
    def clean_evidence(cls, value: str) -> str:
        return value.strip()


class RolloutCitySummary(BaseModel):
    city_id: UUID
    code: str
    localized_name: LocalizedName
    lifecycle_status: str
    active_configuration_version_id: UUID | None
    readiness_passed: int
    readiness_required: int
    missing_readiness_gates: list[str]
    pilot_entry_passed: int
    pilot_entry_required: int
    missing_pilot_entry_gates: list[str]
    public_activation_passed: int
    public_activation_required: int
    missing_public_activation_gates: list[str]
    post_launch_review_status: str


class RolloutOverviewResponse(BaseModel):
    visible_market_count: int
    visible_operator_count: int
    visible_city_count: int
    cities: list[RolloutCitySummary]
