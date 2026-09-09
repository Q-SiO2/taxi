import asyncio

import httpx
import pytest

from taximobile_api.integrations.geocoding.models import GeoCoordinate, SearchViewbox
from taximobile_api.integrations.geocoding.nominatim import NominatimGeocodingProvider
from taximobile_api.integrations.geocoding.provider import GeocodingUnavailable


def test_search_sends_minimized_bounded_contract_and_normalizes_candidates() -> None:
    seen_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_request
        seen_request = request
        return httpx.Response(
            200,
            json=[
                {
                    "place_id": 41,
                    "lat": "34.0209000",
                    "lon": "-6.8416000",
                    "name": "Gare de Rabat-Ville",
                    "display_name": "Gare de Rabat-Ville, Hassan, Rabat, Maroc",
                    "category": "railway",
                    "type": "station",
                    "address": {"railway": "Gare de Rabat-Ville", "city": "Rabat"},
                    "importance": 0.9,
                    "licence": "upstream value is not exposed",
                },
                # A duplicate must not crowd a distinct result out of the limit.
                {
                    "place_id": 42,
                    "lat": "34.02090001",
                    "lon": "-6.84160001",
                    "name": "Gare de Rabat-Ville",
                    "display_name": "Gare de Rabat-Ville, Hassan, Rabat, Maroc",
                    "category": "railway",
                    "type": "station",
                    "address": {},
                },
                {
                    "place_id": 43,
                    "lat": "34.0132",
                    "lon": "-6.8326",
                    "display_name": "Avenue Mohammed V, Rabat, Maroc",
                    "category": "highway",
                    "type": "road",
                    "address": {"road": "Avenue Mohammed V", "city": "Rabat"},
                },
            ],
        )

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://geo.internal")
    provider = NominatimGeocodingProvider(
        "https://ignored.example",
        client=client,
        user_agent="TaxiMobile test",
    )
    result = asyncio.run(
        provider.search(
            "محطة الرباط",
            language="ar",
            limit=2,
            viewbox=SearchViewbox(-6.9, 33.9, -6.7, 34.1),
        )
    )
    asyncio.run(client.aclose())

    assert [item.kind for item in result.candidates] == ["POI", "STREET"]
    assert result.candidates[0].primary_text == "Gare de Rabat-Ville"
    assert result.candidates[0].secondary_text == "Hassan, Rabat, Maroc"
    assert result.candidates[1].coordinate == GeoCoordinate(34.0132, -6.8326)
    assert result.attribution.url == "https://www.openstreetmap.org/copyright"
    assert seen_request is not None
    params = seen_request.url.params
    assert params["q"] == "محطة الرباط"
    assert params["countrycodes"] == "ma"
    assert params["accept-language"] == "ar,fr;q=0.8,en;q=0.6"
    assert params["viewbox"] == "-6.9,33.9,-6.7,34.1"
    assert params["bounded"] == "0"
    assert params["addressdetails"] == "1"
    assert "email" not in params
    assert "user_id" not in params


def test_reverse_returns_none_for_no_match_and_rejects_malformed_upstream() -> None:
    responses = iter(
        [
            httpx.Response(404, json={"error": "Unable to geocode"}),
            httpx.Response(200, json={"place_id": 1, "lat": "NaN", "lon": "1"}),
        ]
    )
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: next(responses)),
        base_url="https://geo.internal",
    )
    provider = NominatimGeocodingProvider("https://ignored.example", client=client)

    missing = asyncio.run(provider.reverse(GeoCoordinate(34.02, -6.84), language="fr"))
    assert missing.candidate is None
    with pytest.raises(GeocodingUnavailable):
        asyncio.run(provider.reverse(GeoCoordinate(34.02, -6.84), language="fr"))
    asyncio.run(client.aclose())


def test_search_converts_http_and_shape_failures_to_safe_unavailability() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"unexpected": True})),
        base_url="https://geo.internal",
    )
    provider = NominatimGeocodingProvider("https://ignored.example", client=client)
    with pytest.raises(GeocodingUnavailable):
        asyncio.run(
            provider.search(
                "Rabat",
                language="en",
                limit=8,
                viewbox=SearchViewbox(-7, 33, -6, 35),
            )
        )
    asyncio.run(client.aclose())


def test_search_keeps_valid_siblings_but_rejects_a_wholly_malformed_result() -> None:
    seen_paths: list[str] = []
    responses = iter(
        [
            httpx.Response(
                200,
                json=[
                    {"place_id": 1, "lat": "NaN", "lon": "-6.8"},
                    {
                        "place_id": 2,
                        "lat": "34.0209",
                        "lon": "-6.8416",
                        "display_name": "Gare de Rabat-Ville, Rabat",
                        "category": "railway",
                        "type": "station",
                        "address": {"railway": "Gare de Rabat-Ville"},
                    },
                ],
            ),
            httpx.Response(200, json=[{"place_id": 3, "lat": "NaN", "lon": "-6.8"}]),
        ]
    )
    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        return next(responses)

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://geo.internal/nominatim/",
    )
    provider = NominatimGeocodingProvider("https://ignored.example", client=client)

    result = asyncio.run(
        provider.search(
            "Gare",
            language="fr",
            limit=8,
            viewbox=SearchViewbox(-7, 33, -6, 35),
        )
    )
    assert [candidate.primary_text for candidate in result.candidates] == [
        "Gare de Rabat-Ville"
    ]
    assert seen_paths == ["/nominatim/search"]
    with pytest.raises(GeocodingUnavailable):
        asyncio.run(
            provider.search(
                "Gare",
                language="fr",
                limit=8,
                viewbox=SearchViewbox(-7, 33, -6, 35),
            )
        )
    assert seen_paths == ["/nominatim/search", "/nominatim/search"]
    asyncio.run(client.aclose())
