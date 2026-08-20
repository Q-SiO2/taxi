import asyncio
import json

import httpx
import pytest

from taximobile_api.integrations.routing.models import RouteCoordinate
from taximobile_api.integrations.routing.provider import RoutingUnavailable
from taximobile_api.integrations.routing.valhalla import ValhallaRoutingProvider


def _encode_polyline6(coordinates: list[tuple[float, float]]) -> str:
    encoded: list[str] = []
    previous_latitude = 0
    previous_longitude = 0
    for latitude, longitude in coordinates:
        latitude_value = round(latitude * 1_000_000)
        longitude_value = round(longitude * 1_000_000)
        for delta in (
            latitude_value - previous_latitude,
            longitude_value - previous_longitude,
        ):
            value = ~(delta << 1) if delta < 0 else delta << 1
            while value >= 0x20:
                encoded.append(chr((0x20 | (value & 0x1F)) + 63))
                value >>= 5
            encoded.append(chr(value + 63))
        previous_latitude = latitude_value
        previous_longitude = longitude_value
    return "".join(encoded)


def test_valhalla_adapter_normalizes_route_geometry_and_maneuvers() -> None:
    coordinates = [(33.5731, -7.5898), (33.5750, -7.5800), (33.5800, -7.5700)]
    captured_request: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "trip": {
                    "summary": {"length": 2.345, "time": 321},
                    "legs": [
                        {
                            "shape": _encode_polyline6(coordinates),
                            "maneuvers": [
                                {
                                    "instruction": "Drive east.",
                                    "length": 2.345,
                                    "time": 321,
                                    "begin_shape_index": 0,
                                    "end_shape_index": 2,
                                }
                            ],
                        }
                    ],
                }
            },
        )

    client = httpx.AsyncClient(
        base_url="https://routing.example.test",
        transport=httpx.MockTransport(handler),
    )
    provider = ValhallaRoutingProvider("https://ignored.example", client=client)
    route = asyncio.run(
        provider.route(
            RouteCoordinate(*coordinates[0]),
            RouteCoordinate(*coordinates[-1]),
            "fr",
        )
    )
    asyncio.run(client.aclose())

    assert captured_request["costing"] == "auto"
    assert captured_request["shape_format"] == "polyline6"
    assert captured_request["directions_options"] == {
        "units": "kilometers",
        "language": "fr-FR",
    }
    assert captured_request["locations"] == [
        {"lat": coordinates[0][0], "lon": coordinates[0][1], "type": "break"},
        {"lat": coordinates[-1][0], "lon": coordinates[-1][1], "type": "break"},
    ]
    assert route.distance_meters == 2345
    assert route.duration_seconds == 321
    assert [(point.latitude, point.longitude) for point in route.geometry] == coordinates
    assert route.maneuvers[0].distance_meters == 2345
    assert route.maneuvers[0].begin_shape_index == 0
    assert route.maneuvers[0].end_shape_index == 2


def test_valhalla_adapter_uses_safe_english_fallback_for_arabic_narration() -> None:
    captured_request: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "trip": {
                    "summary": {"length": 1, "time": 60},
                    "legs": [
                        {
                            "shape": _encode_polyline6([(33.5, -7.6), (33.6, -7.5)]),
                            "maneuvers": [],
                        }
                    ],
                }
            },
        )

    client = httpx.AsyncClient(
        base_url="https://routing.example.test",
        transport=httpx.MockTransport(handler),
    )
    provider = ValhallaRoutingProvider("https://ignored.example", client=client)
    asyncio.run(provider.route(RouteCoordinate(33.5, -7.6), RouteCoordinate(33.6, -7.5), "ar"))
    asyncio.run(client.aclose())

    assert captured_request["directions_options"]["language"] == "en-US"


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(503, json={"error": "unavailable"}),
        httpx.Response(200, json={"trip": {"summary": {"length": 1, "time": 1}, "legs": []}}),
        httpx.Response(
            200,
            json={
                "trip": {
                    "summary": {"length": 1, "time": 1},
                    "legs": [{"shape": "truncated~", "maneuvers": []}],
                }
            },
        ),
    ],
)
def test_valhalla_adapter_maps_upstream_failures_to_safe_error(response: httpx.Response) -> None:
    client = httpx.AsyncClient(
        base_url="https://routing.example.test",
        transport=httpx.MockTransport(lambda _: response),
    )
    provider = ValhallaRoutingProvider("https://ignored.example", client=client)

    with pytest.raises(RoutingUnavailable, match="temporarily unavailable"):
        asyncio.run(provider.route(RouteCoordinate(33.5, -7.6), RouteCoordinate(33.6, -7.5)))
    asyncio.run(client.aclose())


@pytest.mark.parametrize(
    "summary,coordinates,maneuvers",
    [
        ({"length": -1, "time": 60}, [(33.5, -7.6), (33.6, -7.5)], []),
        ({"length": 1, "time": -1}, [(33.5, -7.6), (33.6, -7.5)], []),
        ({"length": 1, "time": 60}, [(95.0, -7.6), (33.6, -7.5)], []),
        (
            {"length": 1, "time": 60},
            [(33.5, -7.6), (33.6, -7.5)],
            [
                {
                    "instruction": " ",
                    "length": 1,
                    "time": 60,
                    "begin_shape_index": 0,
                    "end_shape_index": 1,
                }
            ],
        ),
        (
            {"length": 1, "time": 60},
            [(33.5, -7.6), (33.6, -7.5)],
            [
                {
                    "instruction": "Continue.",
                    "length": 1,
                    "time": 60,
                    "begin_shape_index": 0,
                    "end_shape_index": 9,
                }
            ],
        ),
        (
            {"length": 1, "time": 60},
            [(33.5, -7.6), (33.6, -7.5)],
            [
                {
                    "instruction": "Continue.",
                    "length": -1,
                    "time": 60,
                    "begin_shape_index": 0,
                    "end_shape_index": 1,
                }
            ],
        ),
    ],
)
def test_valhalla_adapter_rejects_invalid_normalized_values(
    summary: dict,
    coordinates: list[tuple[float, float]],
    maneuvers: list[dict],
) -> None:
    response = httpx.Response(
        200,
        json={
            "trip": {
                "summary": summary,
                "legs": [{"shape": _encode_polyline6(coordinates), "maneuvers": maneuvers}],
            }
        },
    )
    client = httpx.AsyncClient(
        base_url="https://routing.example.test",
        transport=httpx.MockTransport(lambda _: response),
    )
    provider = ValhallaRoutingProvider("https://ignored.example", client=client)

    with pytest.raises(RoutingUnavailable, match="temporarily unavailable"):
        asyncio.run(provider.route(RouteCoordinate(33.5, -7.6), RouteCoordinate(33.6, -7.5)))
    asyncio.run(client.aclose())
