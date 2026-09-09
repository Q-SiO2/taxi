import asyncio

import pytest

from taximobile_api.integrations.geocoding.factory import create_geocoding_provider
from taximobile_api.integrations.geocoding.nominatim import NominatimGeocodingProvider
from taximobile_api.integrations.geocoding.provider import DisabledGeocodingProvider


@pytest.mark.parametrize(
    ("name", "base_url", "expected"),
    [
        ("disabled", None, DisabledGeocodingProvider),
        ("nominatim", "https://geo.example.test", NominatimGeocodingProvider),
    ],
)
def test_factory_is_closed(name: str, base_url: str | None, expected: type) -> None:
    provider = create_geocoding_provider(
        name,
        base_url,
        timeout_seconds=2,
        user_agent="TaxiMobile tests",
    )
    assert isinstance(provider, expected)
    asyncio.run(provider.aclose())


def test_factory_refuses_unknown_or_incomplete_provider() -> None:
    with pytest.raises(ValueError, match="Unsupported or incomplete"):
        create_geocoding_provider(
            "pelias",
            "https://geo.example.test",
            timeout_seconds=2,
            user_agent="TaxiMobile tests",
        )
    with pytest.raises(ValueError, match="Unsupported or incomplete"):
        create_geocoding_provider(
            "nominatim",
            None,
            timeout_seconds=2,
            user_agent="TaxiMobile tests",
        )
