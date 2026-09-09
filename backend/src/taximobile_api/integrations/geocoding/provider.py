"""Narrow geocoding boundary; native provider payloads never leave this layer."""

from typing import Protocol

from taximobile_api.integrations.geocoding.models import (
    GeoCoordinate,
    PlaceSearchResult,
    ReversePlaceResult,
    SearchViewbox,
)


class GeocodingUnavailable(RuntimeError):
    """No trustworthy geocoding answer is available right now."""


class GeocodingProvider(Protocol):
    async def search(
        self,
        query: str,
        *,
        language: str,
        limit: int,
        viewbox: SearchViewbox,
    ) -> PlaceSearchResult: ...

    async def reverse(
        self,
        coordinate: GeoCoordinate,
        *,
        language: str,
    ) -> ReversePlaceResult: ...

    async def aclose(self) -> None: ...


class DisabledGeocodingProvider:
    """Fail-closed default used until an approved deployment is configured."""

    async def search(
        self,
        query: str,
        *,
        language: str,
        limit: int,
        viewbox: SearchViewbox,
    ) -> PlaceSearchResult:
        raise GeocodingUnavailable("Place search is not configured.")

    async def reverse(
        self,
        coordinate: GeoCoordinate,
        *,
        language: str,
    ) -> ReversePlaceResult:
        raise GeocodingUnavailable("Reverse geocoding is not configured.")

    async def aclose(self) -> None:
        return None
