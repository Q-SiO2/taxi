"""Provider-neutral place discovery values used by the application layer."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GeoCoordinate:
    latitude: float
    longitude: float


@dataclass(frozen=True, slots=True)
class SearchViewbox:
    west: float
    south: float
    east: float
    north: float


@dataclass(frozen=True, slots=True)
class PlaceCandidate:
    """One normalized candidate; the provider's native identifier stays private."""

    provider_reference: str
    primary_text: str
    secondary_text: str | None
    coordinate: GeoCoordinate
    kind: str


@dataclass(frozen=True, slots=True)
class PlaceAttribution:
    text: str
    url: str


@dataclass(frozen=True, slots=True)
class PlaceSearchResult:
    candidates: tuple[PlaceCandidate, ...]
    attribution: PlaceAttribution


@dataclass(frozen=True, slots=True)
class ReversePlaceResult:
    candidate: PlaceCandidate | None
    attribution: PlaceAttribution
