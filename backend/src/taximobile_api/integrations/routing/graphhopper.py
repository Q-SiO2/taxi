"""GraphHopper adapter for the provider-neutral TaxiMobile route contract."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import isfinite
from typing import Any

import httpx

from taximobile_api.integrations.routing.models import Route, RouteCoordinate, RouteManeuver
from taximobile_api.integrations.routing.provider import RoutingUnavailable


class GraphHopperRoutingProvider:
    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 5,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(base_url=base_url, timeout=timeout_seconds)

    async def route(
        self,
        origin: RouteCoordinate,
        destination: RouteCoordinate,
        language: str = "en",
    ) -> Route:
        try:
            response = await self._client.post(
                "/route",
                json={
                    "profile": "car",
                    "points": [
                        [origin.longitude, origin.latitude],
                        [destination.longitude, destination.latitude],
                    ],
                    "locale": _graphhopper_locale(language),
                    "instructions": True,
                    "points_encoded": False,
                    "elevation": False,
                },
            )
            response.raise_for_status()
            return _normalized_route(response.json())
        except (
            httpx.HTTPError,
            TypeError,
            ValueError,
            KeyError,
            IndexError,
            OverflowError,
        ) as error:
            raise RoutingUnavailable("Routing is temporarily unavailable.") from error

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()


def _graphhopper_locale(language: str) -> str:
    return language if language in {"ar", "en", "fr"} else "en"


def _normalized_route(payload: Mapping[str, Any]) -> Route:
    paths = payload["paths"]
    if not isinstance(paths, list) or not paths or not isinstance(paths[0], Mapping):
        raise ValueError("GraphHopper response has no route path.")
    path = paths[0]
    distance_meters = _nonnegative_rounded(path["distance"])
    duration_seconds = _milliseconds_to_seconds(path["time"])

    points = path["points"]
    if not isinstance(points, Mapping) or points.get("type") != "LineString":
        raise ValueError("GraphHopper response has no GeoJSON geometry.")
    raw_coordinates = points["coordinates"]
    if not isinstance(raw_coordinates, list) or len(raw_coordinates) < 2:
        raise ValueError("GraphHopper response has invalid route geometry.")
    geometry = tuple(_coordinate(item) for item in raw_coordinates)

    raw_instructions = path.get("instructions", [])
    if not isinstance(raw_instructions, list):
        raise ValueError("GraphHopper response has invalid route instructions.")
    maneuvers = tuple(_maneuver(item, len(geometry)) for item in raw_instructions)
    return Route(
        distance_meters=distance_meters,
        duration_seconds=duration_seconds,
        geometry=geometry,
        maneuvers=maneuvers,
    )


def _coordinate(raw: Any) -> RouteCoordinate:
    if (
        not isinstance(raw, Sequence)
        or isinstance(raw, (str, bytes))
        or len(raw) != 2
    ):
        raise ValueError("GraphHopper route coordinate is invalid.")
    longitude = float(raw[0])
    latitude = float(raw[1])
    if (
        not isfinite(latitude)
        or not isfinite(longitude)
        or latitude < -90
        or latitude > 90
        or longitude < -180
        or longitude > 180
    ):
        raise ValueError("GraphHopper route coordinate is outside valid bounds.")
    return RouteCoordinate(latitude=latitude, longitude=longitude)


def _maneuver(raw: Any, geometry_size: int) -> RouteManeuver:
    if not isinstance(raw, Mapping):
        raise ValueError("GraphHopper route instruction is invalid.")
    interval = raw["interval"]
    if (
        not isinstance(interval, Sequence)
        or isinstance(interval, (str, bytes))
        or len(interval) != 2
    ):
        raise ValueError("GraphHopper instruction interval is invalid.")
    begin = _shape_index(interval[0])
    end = _shape_index(interval[1])
    if begin < 0 or end < begin or end >= geometry_size:
        raise ValueError("GraphHopper instruction interval is outside route geometry.")
    raw_instruction = raw["text"]
    if not isinstance(raw_instruction, str) or not raw_instruction.strip():
        raise ValueError("GraphHopper instruction text is empty.")
    return RouteManeuver(
        instruction=raw_instruction.strip(),
        distance_meters=_nonnegative_rounded(raw.get("distance", 0)),
        duration_seconds=_milliseconds_to_seconds(raw.get("time", 0)),
        begin_shape_index=begin,
        end_shape_index=end,
    )


def _nonnegative_rounded(raw: Any) -> int:
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError("GraphHopper route metric is invalid.")
    value = float(raw)
    if not isfinite(value) or value < 0:
        raise ValueError("GraphHopper route metric is invalid.")
    return round(value)


def _milliseconds_to_seconds(raw: Any) -> int:
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError("GraphHopper route duration is invalid.")
    return _nonnegative_rounded(raw / 1000)


def _shape_index(raw: Any) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise ValueError("GraphHopper instruction interval index is invalid.")
    return raw
