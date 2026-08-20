"""Normalized routing values that do not expose a provider response shape."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RouteCoordinate:
    latitude: float
    longitude: float


@dataclass(frozen=True, slots=True)
class RouteManeuver:
    instruction: str
    distance_meters: int
    duration_seconds: int
    begin_shape_index: int
    end_shape_index: int


@dataclass(frozen=True, slots=True)
class Route:
    distance_meters: int
    duration_seconds: int
    geometry: tuple[RouteCoordinate, ...]
    maneuvers: tuple[RouteManeuver, ...]
