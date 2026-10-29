"""Packaged rules and authenticated, read-only city-clock planning contract."""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
import httpx
from pydantic import ValidationError
import pytest

from taximobile_api.domains.auth.dependencies import authenticated_principal
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.fixed_routes import router as city_router
from taximobile_api.domains.markets.models import CityLifecycleStatus
from taximobile_api.domains.scheduled_bookings import local_time as clock
from taximobile_api.domains.scheduled_bookings.schemas import ScheduledLocalTimeRequest


@pytest.mark.parametrize("zone,local,expected", [
    ("Africa/Casablanca", "2026-11-01T09:30", [("2026-11-01T08:30:00+00:00", 3600)]),
    ("Africa/Casablanca", "2026-02-15T02:30", [("2026-02-15T01:30:00+00:00", 3600), ("2026-02-15T02:30:00+00:00", 0)]),
    ("Africa/Casablanca", "2026-03-22T02:30", []),
    ("Australia/Lord_Howe", "2026-04-05T01:45", [("2026-04-04T14:45:00+00:00", 39600), ("2026-04-04T15:15:00+00:00", 37800)]),
    ("Pacific/Apia", "2011-12-30T12:00", []),
    ("UTC", "2026-11-01T09:30", [("2026-11-01T09:30:00+00:00", 0)]),
])
def test_real_rules_return_only_distinct_roundtripped_instants(zone, local, expected):
    result = clock.local_pickup_time_options(datetime.fromisoformat(local), zone)
    assert [(instant.isoformat(), offset) for instant, offset in result] == expected
    assert clock.packaged_rules_version() == "2026b"


@pytest.mark.parametrize("changes", [
    {"local_date": "2026-02-30"}, {"local_date": "2026-2-03"}, {"local_date": 0},
    {"local_time": "2:30"}, {"local_time": "24:00"}, {"local_time": "02:30:00"},
    {"local_time": "02:30+01:00"}, {"local_time": "02:30Z"}, {"offset": 3600},
])
def test_request_rejects_invalid_dates_offsets_precision_and_unknown_fields(changes):
    with pytest.raises(ValidationError):
        ScheduledLocalTimeRequest(**({"local_date": "2026-11-01", "local_time": "09:30"} | changes))


@pytest.mark.parametrize("zone", ["../../private", "Africa/PRIVATE-invalid", "/UTC", "", "Etc/../UTC"])
def test_unknown_or_path_like_configured_zones_are_unavailable(zone):
    with pytest.raises(clock.TimeZoneRulesUnavailable):
        clock.local_pickup_time_options(datetime(2026, 11, 1, 9, 30), zone)


def test_missing_packaged_data_never_uses_os_rules(monkeypatch):
    clock._packaged_zone.cache_clear()
    def missing(*args):
        raise ModuleNotFoundError("private local path")
    monkeypatch.setattr(clock.resources, "files", missing)
    with pytest.raises(clock.TimeZoneRulesUnavailable):
        clock.local_pickup_time_options(datetime(2026, 11, 1, 9, 30), "Africa/Casablanca")
    clock._packaged_zone.cache_clear()


@pytest.mark.parametrize("local", [datetime(2026, 11, 1, tzinfo=UTC), datetime(2026, 11, 1, second=1), datetime(2026, 11, 1, microsecond=1)])
def test_conversion_requires_a_naive_minute_selection(local):
    with pytest.raises(ValueError):
        clock.local_pickup_time_options(local, "UTC")


class ReadOnlyCitySession:
    def __init__(self, city):
        self.city = city
        self.reads = 0

    async def scalar(self, query):
        self.reads += 1
        assert "cities.lifecycle_status IN" in str(query)
        assert query.compile().params['lifecycle_status_1'] == list(city_router.PUBLIC_CITY_STATUSES)
        return self.city


def app_and_session(city, authenticated=True):
    app = FastAPI()
    app.include_router(city_router.router, prefix="/api/v1")
    session = ReadOnlyCitySession(city)
    app.dependency_overrides[database_session] = lambda: session
    if authenticated:
        app.dependency_overrides[authenticated_principal] = lambda: SimpleNamespace(user_id=uuid4())
    return app, session


@pytest.mark.parametrize("lifecycle,configured", [(CityLifecycleStatus.ACTIVE, True), (CityLifecycleStatus.ACTIVE, False), (CityLifecycleStatus.PAUSED, True)])
def test_http_returns_context_options_no_store_and_current_booking_flag(lifecycle, configured):
    async def prove():
        city = SimpleNamespace(id=uuid4(), timezone="Africa/Casablanca", lifecycle_status=lifecycle,
                               active_configuration_version_id=uuid4() if configured else None)
        app, session = app_and_session(city)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://testserver") as client:
            response = await client.post(f"/api/v1/cities/{city.id}/scheduled-time-options", json={"local_date": "2026-02-15", "local_time": "02:30"})
        assert response.status_code == 200
        assert response.headers['cache-control'] == 'no-store'
        result = response.json()
        assert result['city_id'] == str(city.id)
        assert result['city_timezone'] == city.timezone and result['rules_version'] == '2026b'
        assert result['booking_available'] == (lifecycle == CityLifecycleStatus.ACTIVE and configured)
        assert result['local_date'] == '2026-02-15' and result['local_time'] == '02:30'
        assert [item['utc_offset_seconds'] for item in result['options']] == [3600, 0]
        assert session.reads == 1  # The session supplies no write/commit methods.
    asyncio.run(prove())


def test_http_requires_authentication_before_city_access():
    async def prove():
        app, session = app_and_session(None, authenticated=False)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://testserver') as client:
            response = await client.post(f'/api/v1/cities/{uuid4()}/scheduled-time-options', json={'local_date': '2026-11-01', 'local_time': '09:30'})
        assert response.status_code == 401 and session.reads == 0
    asyncio.run(prove())


def test_http_hidden_city_uses_existing_not_found_boundary():
    async def prove():
        app, session = app_and_session(None)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://testserver') as client:
            response = await client.post(f'/api/v1/cities/{uuid4()}/scheduled-time-options', json={'local_date': '2026-11-01', 'local_time': '09:30'})
        assert response.status_code == 404 and session.reads == 1
    asyncio.run(prove())


def test_http_rule_failure_is_sanitized_and_never_becomes_empty_options(monkeypatch):
    def fail(*args):
        raise clock.TimeZoneRulesUnavailable('private path and configuration')
    monkeypatch.setattr(city_router, 'local_pickup_time_options', fail)
    async def prove():
        city = SimpleNamespace(id=uuid4(), timezone='Africa/Casablanca', lifecycle_status=CityLifecycleStatus.ACTIVE)
        app, _ = app_and_session(city)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://testserver') as client:
            response = await client.post(f'/api/v1/cities/{city.id}/scheduled-time-options', json={'local_date': '2026-11-01', 'local_time': '09:30'})
        assert response.status_code == 503
        assert response.json() == {'detail': 'City time rules are unavailable. Try again later.'}
    asyncio.run(prove())
