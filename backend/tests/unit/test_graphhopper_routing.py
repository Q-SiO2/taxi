import asyncio
import json

import httpx
import pytest

from taximobile_api.integrations.routing.graphhopper import GraphHopperRoutingProvider
from taximobile_api.integrations.routing.models import RouteCoordinate
from taximobile_api.integrations.routing.provider import RoutingUnavailable


def test_graphhopper_adapter_normalizes_route_geometry_and_maneuvers() -> None:
    captured_request: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/route"
        captured_request.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "paths": [
                    {
                        "distance": 2345.4,
                        "time": 321000,
                        "points": {
                            "type": "LineString",
                            "coordinates": [
                                [-7.5898, 33.5731],
                                [-7.5800, 33.5750],
                                [-7.5700, 33.5800],
                            ],
                        },
                        "instructions": [
                            {
                                "text": "Continue east",
                                "distance": 2345.4,
                                "time": 321000,
                                "interval": [0, 2],
                            }
                        ],
                    }
                ]
            },
        )

    client = httpx.AsyncClient(
        base_url="https://routing.example.test",
        transport=httpx.MockTransport(handler),
    )
    provider = GraphHopperRoutingProvider("https://ignored.example", client=client)
    route = asyncio.run(
        provider.route(
            RouteCoordinate(latitude=33.5731, longitude=-7.5898),
            RouteCoordinate(latitude=33.5800, longitude=-7.5700),
            "ar",
        )
    )
    asyncio.run(client.aclose())

    assert captured_request == {
        "profile": "car",
        "points": [[-7.5898, 33.5731], [-7.57, 33.58]],
        "locale": "ar",
        "instructions": True,
        "points_encoded": False,
        "elevation": False,
    }
    assert route.distance_meters == 2345
    assert route.duration_seconds == 321
    assert [(point.latitude, point.longitude) for point in route.geometry] == [
        (33.5731, -7.5898),
        (33.5750, -7.5800),
        (33.5800, -7.5700),
    ]
    assert route.maneuvers[0].instruction == "Continue east"
    assert route.maneuvers[0].distance_meters == 2345
    assert route.maneuvers[0].duration_seconds == 321
    assert route.maneuvers[0].begin_shape_index == 0
    assert route.maneuvers[0].end_shape_index == 2


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"paths": []},
        {
            "paths": [
                {
                    "distance": 1,
                    "time": 1000,
                    "points": {"type": "LineString", "coordinates": [[-7.6, 33.5]]},
                }
            ]
        },
        {
            "paths": [
                {
                    "distance": 1,
                    "time": 1000,
                    "points": {
                        "type": "LineString",
                        "coordinates": [[-7.6, 33.5], [-7.5, 91]],
                    },
                }
            ]
        },
        {
            "paths": [
                {
                    "distance": 1,
                    "time": 1000,
                    "points": {
                        "type": "LineString",
                        "coordinates": [[-7.6, 33.5], [-7.5, 33.6]],
                    },
                    "instructions": [
                        {"text": "Continue", "distance": 1, "time": 1000, "interval": [0, 2]}
                    ],
                }
            ]
        },
        {
            "paths": [
                {
                    "distance": float("inf"),
                    "time": 1000,
                    "points": {
                        "type": "LineString",
                        "coordinates": [[-7.6, 33.5], [-7.5, 33.6]],
                    },
                }
            ]
        },
        {
            "paths": [
                {
                    "distance": "1",
                    "time": 1000,
                    "points": {
                        "type": "LineString",
                        "coordinates": [[-7.6, 33.5], [-7.5, 33.6]],
                    },
                }
            ]
        },
        {
            "paths": [
                {
                    "distance": 1,
                    "time": 1000,
                    "points": {
                        "type": "Polygon",
                        "coordinates": [[-7.6, 33.5], [-7.5, 33.6]],
                    },
                }
            ]
        },
        {
            "paths": [
                {
                    "distance": 1,
                    "time": 1000,
                    "points": {
                        "type": "LineString",
                        "coordinates": [[-7.6, 33.5], [-7.5, 33.6]],
                    },
                    "instructions": [
                        {"text": "Continue", "distance": 1, "time": 1000, "interval": [0.0, 1]}
                    ],
                }
            ]
        },
    ],
)
def test_graphhopper_adapter_rejects_untrustworthy_response_shapes(payload: dict) -> None:
    client = httpx.AsyncClient(
        base_url="https://routing.example.test",
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload)),
    )
    provider = GraphHopperRoutingProvider("https://ignored.example", client=client)

    with pytest.raises(RoutingUnavailable, match="temporarily unavailable"):
        asyncio.run(provider.route(RouteCoordinate(33.5, -7.6), RouteCoordinate(33.6, -7.5)))
    asyncio.run(client.aclose())


def test_graphhopper_adapter_maps_upstream_failure_to_safe_error() -> None:
    client = httpx.AsyncClient(
        base_url="https://routing.example.test",
        transport=httpx.MockTransport(lambda _: httpx.Response(503, json={"message": "private detail"})),
    )
    provider = GraphHopperRoutingProvider("https://ignored.example", client=client)

    with pytest.raises(RoutingUnavailable, match="temporarily unavailable"):
        asyncio.run(provider.route(RouteCoordinate(33.5, -7.6), RouteCoordinate(33.6, -7.5)))
    asyncio.run(client.aclose())
