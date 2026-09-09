"""Adapter for an approved, preferably self-hosted Nominatim deployment."""

from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import Any

import httpx

from taximobile_api.integrations.geocoding.models import (
    GeoCoordinate,
    PlaceAttribution,
    PlaceCandidate,
    PlaceSearchResult,
    ReversePlaceResult,
    SearchViewbox,
)
from taximobile_api.integrations.geocoding.provider import GeocodingUnavailable


_ATTRIBUTION = PlaceAttribution(
    text="© OpenStreetMap contributors",
    url="https://www.openstreetmap.org/copyright",
)
_LANGUAGES = {
    "ar": "ar,fr;q=0.8,en;q=0.6",
    "fr": "fr,ar;q=0.8,en;q=0.6",
    "en": "en,fr;q=0.8,ar;q=0.6",
}
_PRIMARY_ADDRESS_KEYS = (
    "amenity",
    "shop",
    "tourism",
    "historic",
    "railway",
    "aeroway",
    "office",
    "building",
    "house_name",
    "road",
    "pedestrian",
    "neighbourhood",
    "suburb",
    "city_district",
    "city",
    "town",
    "village",
)


class NominatimGeocodingProvider:
    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 5,
        user_agent: str = "TaxiMobile/0.1",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout_seconds,
            headers={"User-Agent": user_agent},
        )

    async def search(
        self,
        query: str,
        *,
        language: str,
        limit: int,
        viewbox: SearchViewbox,
    ) -> PlaceSearchResult:
        try:
            response = await self._client.get(
                "search",
                params={
                    "q": query,
                    "format": "jsonv2",
                    "addressdetails": 1,
                    "namedetails": 0,
                    "extratags": 0,
                    "polygon_geojson": 0,
                    "countrycodes": "ma",
                    "accept-language": _provider_language(language),
                    # A viewbox boosts the selected city but does not hide valid
                    # nearby destinations. PostGIS remains the exact service-area authority.
                    "viewbox": (
                        f"{viewbox.west},{viewbox.south},"
                        f"{viewbox.east},{viewbox.north}"
                    ),
                    "bounded": 0,
                    "limit": min(max(limit * 2, limit), 20),
                },
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise ValueError("Nominatim search response is not a list.")
            candidates: list[PlaceCandidate] = []
            seen: set[tuple[float, float, str]] = set()
            malformed_count = 0
            for raw in payload:
                try:
                    candidate = _candidate(raw)
                except (TypeError, ValueError, KeyError, OverflowError):
                    # One malformed upstream item must not discard trustworthy
                    # siblings, but a wholly malformed non-empty response is an
                    # outage rather than a misleading "no results" answer.
                    malformed_count += 1
                    continue
                key = (
                    round(candidate.coordinate.latitude, 7),
                    round(candidate.coordinate.longitude, 7),
                    candidate.primary_text.casefold(),
                )
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(candidate)
                if len(candidates) >= limit:
                    break
            if payload and malformed_count and not candidates:
                raise ValueError("Nominatim search response has no usable candidates.")
            return PlaceSearchResult(tuple(candidates), _ATTRIBUTION)
        except (
            httpx.HTTPError,
            TypeError,
            ValueError,
            KeyError,
            OverflowError,
        ) as error:
            raise GeocodingUnavailable("Place search is temporarily unavailable.") from error

    async def reverse(
        self,
        coordinate: GeoCoordinate,
        *,
        language: str,
    ) -> ReversePlaceResult:
        try:
            response = await self._client.get(
                "reverse",
                params={
                    "lat": coordinate.latitude,
                    "lon": coordinate.longitude,
                    "format": "jsonv2",
                    "addressdetails": 1,
                    "namedetails": 0,
                    "extratags": 0,
                    "zoom": 18,
                    "layer": "address,poi",
                    "accept-language": _provider_language(language),
                },
            )
            if response.status_code == httpx.codes.NOT_FOUND:
                return ReversePlaceResult(None, _ATTRIBUTION)
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, Mapping) and payload.get("error"):
                return ReversePlaceResult(None, _ATTRIBUTION)
            return ReversePlaceResult(_candidate(payload), _ATTRIBUTION)
        except (
            httpx.HTTPError,
            TypeError,
            ValueError,
            KeyError,
            OverflowError,
        ) as error:
            raise GeocodingUnavailable("Reverse geocoding is temporarily unavailable.") from error

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()


def _provider_language(language: str) -> str:
    return _LANGUAGES.get(language, _LANGUAGES["en"])


def _candidate(raw: Any) -> PlaceCandidate:
    if not isinstance(raw, Mapping):
        raise ValueError("Nominatim place is not an object.")
    latitude = _coordinate_value(raw.get("lat"), -90, 90)
    longitude = _coordinate_value(raw.get("lon"), -180, 180)
    display_name = _safe_text(raw.get("display_name"), maximum=500)
    if display_name is None:
        raise ValueError("Nominatim place has no display name.")
    address = raw.get("address")
    address_mapping = address if isinstance(address, Mapping) else {}
    explicit_name = _safe_text(raw.get("name"), maximum=200)
    primary = explicit_name or next(
        (
            value
            for key in _PRIMARY_ADDRESS_KEYS
            if (value := _safe_text(address_mapping.get(key), maximum=200)) is not None
        ),
        None,
    )
    if primary is None:
        primary = _safe_text(display_name.split(",", 1)[0], maximum=200)
    if primary is None:
        raise ValueError("Nominatim place has no usable label.")
    secondary = display_name
    if secondary.casefold() == primary.casefold():
        secondary = None
    elif secondary.casefold().startswith(primary.casefold() + ","):
        secondary = secondary[len(primary) + 1 :].strip() or None
    category = _safe_text(raw.get("category"), maximum=64) or "unknown"
    place_type = _safe_text(raw.get("addresstype"), maximum=64) or _safe_text(
        raw.get("type"), maximum=64
    )
    reference = _safe_text(raw.get("place_id"), maximum=80) or (
        f"{latitude:.7f}:{longitude:.7f}:{primary.casefold()}"
    )
    return PlaceCandidate(
        provider_reference=reference,
        primary_text=primary,
        secondary_text=secondary,
        coordinate=GeoCoordinate(latitude, longitude),
        kind=_normalized_kind(category, place_type),
    )


def _coordinate_value(raw: Any, minimum: float, maximum: float) -> float:
    if isinstance(raw, bool):
        raise ValueError("Invalid coordinate.")
    value = float(raw)
    if not isfinite(value) or not minimum <= value <= maximum:
        raise ValueError("Coordinate outside bounds.")
    return value


def _safe_text(raw: Any, *, maximum: int) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, (str, int)) or isinstance(raw, bool):
        raise ValueError("Invalid provider text.")
    value = " ".join(str(raw).split()).strip()
    if not value or len(value) > maximum or any(ord(character) < 32 for character in value):
        return None
    return value


def _normalized_kind(category: str, place_type: str | None) -> str:
    value = (place_type or category).lower()
    if value in {"house", "building", "residential", "postcode"}:
        return "ADDRESS"
    if value in {"road", "street", "pedestrian", "path"}:
        return "STREET"
    if value in {
        "city",
        "town",
        "village",
        "suburb",
        "neighbourhood",
        "quarter",
        "city_district",
    }:
        return "LOCALITY"
    if category in {
        "amenity",
        "shop",
        "tourism",
        "historic",
        "railway",
        "aeroway",
        "leisure",
        "office",
    }:
        return "POI"
    return "OTHER"
