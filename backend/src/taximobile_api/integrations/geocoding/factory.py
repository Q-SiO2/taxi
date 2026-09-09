"""Select one geocoder from deployment-owned, validated configuration."""

from taximobile_api.integrations.geocoding.nominatim import NominatimGeocodingProvider
from taximobile_api.integrations.geocoding.provider import (
    DisabledGeocodingProvider,
    GeocodingProvider,
)


def create_geocoding_provider(
    provider_name: str,
    base_url: str | None,
    *,
    timeout_seconds: float,
    user_agent: str,
) -> GeocodingProvider:
    if provider_name == "disabled":
        return DisabledGeocodingProvider()
    if provider_name == "nominatim" and base_url is not None:
        return NominatimGeocodingProvider(
            base_url,
            timeout_seconds=timeout_seconds,
            user_agent=user_agent,
        )
    raise ValueError("Unsupported or incomplete geocoding provider configuration")
