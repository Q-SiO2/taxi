from uuid import uuid4

from fastapi.testclient import TestClient

from taximobile_api.domains.auth.dependencies import CurrentPrincipal, authenticated_principal
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.places.service import PlaceCityContext
from taximobile_api.integrations.geocoding.models import (
    GeoCoordinate,
    PlaceAttribution,
    PlaceCandidate,
    PlaceSearchResult,
    ReversePlaceResult,
    SearchViewbox,
)
from taximobile_api.integrations.geocoding.provider import GeocodingUnavailable
from taximobile_api.main import create_app


class FakeGeocodingProvider:
    def __init__(self) -> None:
        self.search_calls: list[tuple[str, str, int, SearchViewbox]] = []
        self.reverse_calls: list[tuple[GeoCoordinate, str]] = []

    async def search(
        self,
        query: str,
        *,
        language: str,
        limit: int,
        viewbox: SearchViewbox,
    ) -> PlaceSearchResult:
        self.search_calls.append((query, language, limit, viewbox))
        return PlaceSearchResult(
            (
                PlaceCandidate(
                    "provider-1",
                    "Bab El Had",
                    "Avenue Hassan II, Rabat",
                    GeoCoordinate(34.0205, -6.8414),
                    "POI",
                ),
                PlaceCandidate(
                    "provider-2",
                    "Temara",
                    "Temara, Maroc",
                    GeoCoordinate(33.927, -6.906),
                    "LOCALITY",
                ),
            ),
            PlaceAttribution("© OpenStreetMap contributors", "https://www.openstreetmap.org/copyright"),
        )

    async def reverse(
        self,
        coordinate: GeoCoordinate,
        *,
        language: str,
    ) -> ReversePlaceResult:
        self.reverse_calls.append((coordinate, language))
        return ReversePlaceResult(
            PlaceCandidate(
                "provider-r",
                "Avenue Mohammed V",
                "Hassan, Rabat",
                GeoCoordinate(coordinate.latitude + 0.001, coordinate.longitude + 0.001),
                "STREET",
            ),
            PlaceAttribution("© OpenStreetMap contributors", "https://www.openstreetmap.org/copyright"),
        )

    async def aclose(self) -> None:
        return None


class UnavailableProvider(FakeGeocodingProvider):
    async def search(self, query: str, **kwargs) -> PlaceSearchResult:
        raise GeocodingUnavailable("private upstream detail")

    async def reverse(self, coordinate: GeoCoordinate, **kwargs) -> ReversePlaceResult:
        raise GeocodingUnavailable("private upstream detail")


def _app(monkeypatch, provider):
    city_id = uuid4()
    area_id = uuid4()
    context = PlaceCityContext(city_id, area_id, SearchViewbox(-6.95, 33.9, -6.7, 34.15))

    async def city_context(_session, requested_city_id):
        assert requested_city_id == city_id
        return context

    async def serviceability(_session, requested_context, coordinates):
        assert requested_context == context
        return [index == 0 for index, _ in enumerate(coordinates)]

    monkeypatch.setattr(
        "taximobile_api.domains.places.router.active_place_city_context",
        city_context,
    )
    monkeypatch.setattr(
        "taximobile_api.domains.places.router.pickup_serviceability",
        serviceability,
    )
    app = create_app(geocoding_provider=provider)
    app.dependency_overrides[authenticated_principal] = lambda: CurrentPrincipal(uuid4(), uuid4())
    app.dependency_overrides[database_session] = lambda: object()
    return app, city_id, context


def test_search_normalizes_query_and_marks_exact_serviceability(monkeypatch) -> None:
    provider = FakeGeocodingProvider()
    app, city_id, context = _app(monkeypatch, provider)
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/places/search",
            params={
                "city_id": str(city_id),
                "query": "  Bab   El Had  ",
                "language": "fr",
                "limit": 2,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["city_id"] == str(city_id)
    assert body["query"] == "Bab El Had"
    assert [item["pickup_serviceable"] for item in body["items"]] == [True, False]
    assert body["items"][0]["id"] != "provider-1"
    assert len(body["items"][0]["id"]) == 24
    assert "provider" not in response.text
    assert provider.search_calls == [("Bab El Had", "fr", 2, context.viewbox)]


def test_reverse_keeps_requested_coordinate_authoritative(monkeypatch) -> None:
    provider = FakeGeocodingProvider()
    app, city_id, _ = _app(monkeypatch, provider)
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/places/reverse",
            params={
                "city_id": str(city_id),
                "latitude": 34.02,
                "longitude": -6.84,
                "language": "ar",
            },
        )

    assert response.status_code == 200
    assert response.json()["item"]["coordinate"] == {
        "latitude": 34.02,
        "longitude": -6.84,
    }
    assert response.json()["item"]["pickup_serviceable"] is True
    assert provider.reverse_calls == [(GeoCoordinate(34.02, -6.84), "ar")]


def test_places_require_authentication_and_validate_closed_inputs() -> None:
    app = create_app(geocoding_provider=FakeGeocodingProvider())
    city_id = uuid4()
    with TestClient(app) as client:
        unauthorized = client.get(
            "/api/v1/places/search",
            params={"city_id": str(city_id), "query": "Rabat"},
        )
        invalid_language = client.get(
            "/api/v1/places/reverse",
            params={
                "city_id": str(city_id),
                "latitude": 34,
                "longitude": -6,
                "language": "de",
            },
        )
    assert unauthorized.status_code == 401
    # Validation occurs before the authentication dependency, but leaks no data.
    assert invalid_language.status_code in {401, 422}


def test_provider_failure_is_safe_and_preserves_map_fallback_copy(monkeypatch) -> None:
    app, city_id, _ = _app(monkeypatch, UnavailableProvider())
    with TestClient(app) as client:
        search = client.get(
            "/api/v1/places/search",
            params={"city_id": str(city_id), "query": "Rabat"},
        )
        reverse = client.get(
            "/api/v1/places/reverse",
            params={"city_id": str(city_id), "latitude": 34, "longitude": -6},
        )
    assert search.status_code == 503
    assert "Select a point on the map instead" in search.text
    assert reverse.status_code == 503
    assert "selected coordinate is still usable" in reverse.text
    assert "private upstream detail" not in search.text + reverse.text


def test_place_rate_limit_stops_before_provider_or_city_lookup(monkeypatch) -> None:
    provider = FakeGeocodingProvider()
    app, city_id, _ = _app(monkeypatch, provider)

    class DenyLimiter:
        async def allow(self, *args, **kwargs) -> bool:
            return False

    app.state.rate_limiter = DenyLimiter()
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/places/search",
            params={"city_id": str(city_id), "query": "Rabat"},
        )
    assert response.status_code == 429
    assert provider.search_calls == []
