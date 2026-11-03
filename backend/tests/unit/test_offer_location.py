"""Immediate-assignment readiness boundaries without an OS or database claim."""

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from taximobile_api.domains.drivers.offer_location import observation_age_failure, offer_location_failure


@pytest.mark.parametrize('age,expected', [
    (None, 'DRIVER_LOCATION_MISSING'), (-60.001, 'DRIVER_LOCATION_FUTURE'),
    (-60, None), (0, None), (30, None), (30.001, 'DRIVER_LOCATION_STALE'),
])
def test_observation_age_has_exact_existing_dispatch_boundaries(age, expected):
    now = datetime(2026, 10, 11, 12, tzinfo=UTC)
    observed = None if age is None else now - timedelta(seconds=age)
    assert observation_age_failure(observed, now=now, freshness_seconds=30) == expected


def test_observation_age_uses_configured_threshold_and_refuses_naive_time():
    now = datetime(2026, 10, 11, 12, tzinfo=UTC)
    observed = now - timedelta(seconds=45)
    assert observation_age_failure(observed, now=now, freshness_seconds=30) == 'DRIVER_LOCATION_STALE'
    assert observation_age_failure(observed, now=now, freshness_seconds=60) is None
    assert observation_age_failure(now.replace(tzinfo=None), now=now, freshness_seconds=30) == 'DRIVER_LOCATION_INVALID_TIME'


@pytest.mark.parametrize('age,inside,city_exists,expected', [
    (None, True, True, 'DRIVER_LOCATION_MISSING'),
    (31, True, True, 'DRIVER_LOCATION_STALE'),
    (-61, True, True, 'DRIVER_LOCATION_FUTURE'),
    (0, False, True, 'DRIVER_OUTSIDE_SERVICE_AREA'),
    (0, True, False, 'DRIVER_OUTSIDE_SERVICE_AREA'),
    (0, True, True, None),
])
def test_latest_scalar_observation_and_current_active_area(monkeypatch, age, inside, city_exists, expected):
    now = datetime(2026, 10, 11, 12, tzinfo=UTC)
    driver_id, city_id, location_id = uuid4(), uuid4(), uuid4()
    location = None if age is None else SimpleNamespace(id=location_id, observed_at=now - timedelta(seconds=age))
    city = SimpleNamespace(id=city_id)
    calls = []

    class Session:
        async def execute(self, statement):
            compiled = statement.compile()
            assert driver_id in compiled.params.values()
            sql = str(compiled)
            assert 'driver_locations.observed_at DESC, driver_locations.id DESC' in sql
            assert 'LIMIT' in sql
            assert [column.name for column in statement.selected_columns] == ['id', 'observed_at']
            return SimpleNamespace(first=lambda: location)

        async def get(self, model, identity, **kwargs):
            assert model.__name__ == 'City' and identity == city_id
            assert kwargs == {'populate_existing': True}
            calls.append('city')
            return city if city_exists else None

    async def area(session, **kwargs):
        assert kwargs == {'city': city, 'location_id': location_id, 'now': now}
        calls.append('area')
        return inside

    monkeypatch.setattr('taximobile_api.domains.drivers.offer_location.location_is_inside_active_service_area', area)
    assert asyncio.run(offer_location_failure(Session(), driver_id=driver_id, city_id=city_id, now=now, freshness_seconds=30)) == expected
    assert calls == ([] if age is None or age > 30 or age < -60 else ['city'] + (['area'] if city_exists else []))
