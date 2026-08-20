from uuid import uuid4

from fastapi.testclient import TestClient

from taximobile_api.domains.auth.dependencies import CurrentPrincipal, authenticated_principal
from taximobile_api.integrations.routing.models import Route, RouteCoordinate, RouteManeuver
from taximobile_api.integrations.routing.provider import RoutingUnavailable
from taximobile_api.main import create_app


class FakeRoutingProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[RouteCoordinate, RouteCoordinate, str]] = []

    async def route(
        self,
        origin: RouteCoordinate,
        destination: RouteCoordinate,
        language: str = "en",
    ) -> Route:
        self.calls.append((origin, destination, language))
        return Route(
            distance_meters=2500,
            duration_seconds=420,
            geometry=(origin, destination),
            maneuvers=(
                RouteManeuver(
                    instruction="Continue to the destination.",
                    distance_meters=2500,
                    duration_seconds=420,
                    begin_shape_index=0,
                    end_shape_index=1,
                ),
            ),
        )

    async def aclose(self) -> None:
        return None


class UnavailableRoutingProvider(FakeRoutingProvider):
    async def route(
        self,
        origin: RouteCoordinate,
        destination: RouteCoordinate,
        language: str = "en",
    ) -> Route:
        raise RoutingUnavailable("private upstream detail")


def test_authenticated_route_is_normalized_and_contains_no_provider_payload() -> None:
    provider = FakeRoutingProvider()
    app = create_app(routing_provider=provider)
    app.dependency_overrides[authenticated_principal] = lambda: CurrentPrincipal(uuid4(), uuid4())

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/routing/route",
            json={
                "origin": {"latitude": 33.5731, "longitude": -7.5898},
                "destination": {"latitude": 33.5800, "longitude": -7.5700},
                "language": "fr",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "distance_meters": 2500,
        "duration_seconds": 420,
        "geometry": [
            {"latitude": 33.5731, "longitude": -7.5898},
            {"latitude": 33.58, "longitude": -7.57},
        ],
        "maneuvers": [
            {
                "instruction": "Continue to the destination.",
                "distance_meters": 2500,
                "duration_seconds": 420,
                "begin_shape_index": 0,
                "end_shape_index": 1,
            }
        ],
    }
    assert provider.calls == [
        (RouteCoordinate(33.5731, -7.5898), RouteCoordinate(33.58, -7.57), "fr")
    ]


def test_route_language_is_closed_and_defaults_to_english() -> None:
    provider = FakeRoutingProvider()
    app = create_app(routing_provider=provider)
    app.dependency_overrides[authenticated_principal] = lambda: CurrentPrincipal(uuid4(), uuid4())

    with TestClient(app) as client:
        default_response = client.post(
            "/api/v1/routing/route",
            json={
                "origin": {"latitude": 33.5731, "longitude": -7.5898},
                "destination": {"latitude": 33.5800, "longitude": -7.5700},
            },
        )
        rejected_response = client.post(
            "/api/v1/routing/route",
            json={
                "origin": {"latitude": 33.5731, "longitude": -7.5898},
                "destination": {"latitude": 33.5800, "longitude": -7.5700},
                "language": "de",
            },
        )

    assert default_response.status_code == 200
    assert provider.calls[-1][-1] == "en"
    assert rejected_response.status_code == 422


def test_route_requires_authentication() -> None:
    app = create_app(routing_provider=FakeRoutingProvider())

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/routing/route",
            json={
                "origin": {"latitude": 33.5731, "longitude": -7.5898},
                "destination": {"latitude": 33.5800, "longitude": -7.5700},
            },
        )

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Authentication is required."


def test_route_provider_failure_returns_safe_service_unavailable_error() -> None:
    app = create_app(routing_provider=UnavailableRoutingProvider())
    app.dependency_overrides[authenticated_principal] = lambda: CurrentPrincipal(uuid4(), uuid4())

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/routing/route",
            json={
                "origin": {"latitude": 33.5731, "longitude": -7.5898},
                "destination": {"latitude": 33.5800, "longitude": -7.5700},
            },
        )

    assert response.status_code == 503
    assert response.json()["error"]["message"] == "Routing is temporarily unavailable."
    assert "private upstream detail" not in response.text
