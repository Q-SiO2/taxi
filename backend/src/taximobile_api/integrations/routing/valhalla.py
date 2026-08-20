"""Valhalla turn-by-turn routing adapter."""

from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import Any

import httpx

from taximobile_api.integrations.routing.models import Route, RouteCoordinate, RouteManeuver
from taximobile_api.integrations.routing.provider import RoutingUnavailable


class ValhallaRoutingProvider:
    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 5,
        client_id: str = "taximobile.q-sio2.github",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(base_url=base_url, timeout=timeout_seconds)
        self._client_id = client_id

    async def route(
        self,
        origin: RouteCoordinate,
        destination: RouteCoordinate,
        language: str = "en",
    ) -> Route:
        try:
            response = await self._client.post(
                "/route",
                headers={"X-Client-Id": self._client_id},
                json={
                    "locations": [
                        {"lat": origin.latitude, "lon": origin.longitude, "type": "break"},
                        {"lat": destination.latitude, "lon": destination.longitude, "type": "break"},
                    ],
                    "costing": "auto",
                    "units": "kilometers",
                    "directions_options": {
                        "units": "kilometers",
                        "language": _valhalla_language(language),
                    },
                    "shape_format": "polyline6",
                },
            )
            response.raise_for_status()
            payload = response.json()
            return _normalized_route(payload)
        except (httpx.HTTPError, TypeError, ValueError, KeyError, IndexError, OverflowError) as error:
            raise RoutingUnavailable("Routing is temporarily unavailable.") from error

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()


def _valhalla_language(language: str) -> str:
    # Valhalla currently supports French and English narration but not Arabic.
    # Keep the mapping closed so untrusted client values never become arbitrary
    # provider options. Arabic retains route geometry and receives en-US as the
    # provider fallback until a validated Arabic-capable adapter is deployed.
    return "fr-FR" if language == "fr" else "en-US"


def _normalized_route(payload: Mapping[str, Any]) -> Route:
    trip = payload["trip"]
    if not isinstance(trip, Mapping):
        raise ValueError("Valhalla response has no trip.")
    summary = trip["summary"]
    if not isinstance(summary, Mapping):
        raise ValueError("Valhalla response has no trip summary.")
    legs = trip["legs"]
    if not isinstance(legs, list) or not legs or not all(isinstance(leg, Mapping) for leg in legs):
        raise ValueError("Valhalla response has no route leg.")

    geometry: list[RouteCoordinate] = []
    maneuvers: list[RouteManeuver] = []
    geometry_offset = 0
    for leg in legs:
        leg_geometry = _decode_polyline6(leg["shape"])
        if geometry and leg_geometry and geometry[-1] == leg_geometry[0]:
            leg_geometry = leg_geometry[1:]
            geometry_offset -= 1
        geometry.extend(leg_geometry)
        raw_maneuvers = leg.get("maneuvers", [])
        if not isinstance(raw_maneuvers, list):
            raise ValueError("Valhalla response has invalid route maneuvers.")
        for maneuver in raw_maneuvers:
            maneuvers.append(_maneuver(maneuver, geometry_offset))
        geometry_offset = len(geometry)

    if len(geometry) < 2:
        raise ValueError("Valhalla response has invalid route geometry.")
    if any(
        maneuver.begin_shape_index < 0
        or maneuver.end_shape_index < maneuver.begin_shape_index
        or maneuver.end_shape_index >= len(geometry)
        for maneuver in maneuvers
    ):
        raise ValueError("Valhalla maneuver index is outside route geometry.")
    return Route(
        distance_meters=_kilometers_to_meters(summary["length"]),
        duration_seconds=_nonnegative_rounded(summary["time"]),
        geometry=tuple(geometry),
        maneuvers=tuple(maneuvers),
    )


def _decode_polyline6(encoded: str) -> list[RouteCoordinate]:
    """Decode Valhalla's signed-delta polyline6 into latitude/longitude pairs."""
    if not isinstance(encoded, str) or not encoded:
        raise ValueError("Valhalla route shape is invalid.")
    coordinates: list[RouteCoordinate] = []
    latitude = 0
    longitude = 0
    index = 0
    while index < len(encoded):
        latitude_delta, index = _decode_polyline_value(encoded, index)
        longitude_delta, index = _decode_polyline_value(encoded, index)
        latitude += latitude_delta
        longitude += longitude_delta
        decoded_latitude = latitude / 1_000_000
        decoded_longitude = longitude / 1_000_000
        if not -90 <= decoded_latitude <= 90 or not -180 <= decoded_longitude <= 180:
            raise ValueError("Valhalla route coordinate is outside valid bounds.")
        coordinates.append(RouteCoordinate(decoded_latitude, decoded_longitude))
    return coordinates


def _decode_polyline_value(encoded: str, index: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while True:
        if index >= len(encoded):
            raise ValueError("Truncated polyline.")
        value = ord(encoded[index]) - 63
        index += 1
        if value < 0 or value > 0x3F:
            raise ValueError("Invalid polyline character.")
        result |= (value & 0x1F) << shift
        shift += 5
        if value < 0x20:
            break
        if shift > 30:
            raise ValueError("Invalid polyline value.")
    return (~(result >> 1) if result & 1 else result >> 1), index


def _maneuver(raw: Any, geometry_offset: int) -> RouteManeuver:
    if not isinstance(raw, Mapping):
        raise ValueError("Valhalla route maneuver is invalid.")
    instruction = raw["instruction"]
    if not isinstance(instruction, str) or not instruction.strip():
        raise ValueError("Valhalla route instruction is empty.")
    begin = _shape_index(raw["begin_shape_index"])
    end = _shape_index(raw["end_shape_index"])
    if end < begin:
        raise ValueError("Valhalla maneuver shape range is invalid.")
    return RouteManeuver(
        instruction=instruction.strip(),
        distance_meters=_kilometers_to_meters(raw.get("length", 0)),
        duration_seconds=_nonnegative_rounded(raw.get("time", 0)),
        begin_shape_index=geometry_offset + begin,
        end_shape_index=geometry_offset + end,
    )


def _kilometers_to_meters(raw: Any) -> int:
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError("Valhalla route distance is invalid.")
    value = float(raw)
    if not isfinite(value) or value < 0:
        raise ValueError("Valhalla route distance is invalid.")
    return round(value * 1000)


def _nonnegative_rounded(raw: Any) -> int:
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError("Valhalla route duration is invalid.")
    value = float(raw)
    if not isfinite(value) or value < 0:
        raise ValueError("Valhalla route duration is invalid.")
    return round(value)


def _shape_index(raw: Any) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
        raise ValueError("Valhalla maneuver shape index is invalid.")
    return raw
