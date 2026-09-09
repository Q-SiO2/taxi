"""PostGIS proof that place discovery uses the active versioned city polygon."""

from __future__ import annotations

import asyncio
from os import getenv

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from taximobile_api.core.config import Settings
from taximobile_api.domains.markets.constants import LEGACY_CITY_ID
from taximobile_api.domains.markets.models import CityConfigurationService
from taximobile_api.domains.places.service import (
    PlaceCityUnavailable,
    active_place_city_context,
    pickup_serviceability,
)
from taximobile_api.integrations.geocoding.models import GeoCoordinate


pytestmark = pytest.mark.integration


def integration_settings() -> Settings:
    if getenv("TAXIMOBILE_RUN_INTEGRATION") != "1":
        pytest.skip("Set TAXIMOBILE_RUN_INTEGRATION=1 with an isolated migrated PostGIS database.")
    settings = Settings.from_environment()
    if settings.environment != "test" or "taximobile_ci" not in settings.database_url:
        pytest.fail("Integration tests require an isolated taximobile_ci PostGIS database.")
    return settings


def test_active_city_viewbox_and_exact_polygon_serviceability() -> None:
    settings = integration_settings()

    async def scenario() -> None:
        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with sessions() as session:
                context = await active_place_city_context(session, LEGACY_CITY_ID)
                assert context.city_id == LEGACY_CITY_ID
                assert context.viewbox.west == pytest.approx(-7.9)
                assert context.viewbox.south == pytest.approx(33.3)
                assert context.viewbox.east == pytest.approx(-7.2)
                assert context.viewbox.north == pytest.approx(33.9)
                serviceable = await pickup_serviceability(
                    session,
                    context,
                    [
                        GeoCoordinate(33.5731, -7.5898),
                        GeoCoordinate(34.0209, -6.8416),
                    ],
                )
                assert serviceable == [True, False]

                await session.execute(
                    update(CityConfigurationService).values(enabled=False)
                )
                await session.flush()
                with pytest.raises(PlaceCityUnavailable):
                    await active_place_city_context(session, LEGACY_CITY_ID)
        finally:
            await engine.dispose()

    asyncio.run(scenario())
