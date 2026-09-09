"""Boundary proofs for live scheduled-handoff admission without device or provider I/O."""

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from taximobile_api.domains.drivers.models import AvailabilityStatus
from taximobile_api.domains.markets.models import ServiceType
from taximobile_api.domains.scheduled_bookings.readiness import handoff_readiness_failure


def context():
    city = SimpleNamespace(id=uuid4())
    profile = SimpleNamespace(
        id=uuid4(), availability_status=AvailabilityStatus.AVAILABLE,
        online_city_id=city.id, online_service_type=ServiceType.FIXED_ROUTE,
    )
    return profile, city


@pytest.mark.parametrize("availability", [state for state in AvailabilityStatus if state != AvailabilityStatus.AVAILABLE])
def test_non_available_driver_never_reaches_location_lookup(availability):
    profile, city = context()
    profile.availability_status = availability

    class Session:
        async def scalar(self, _statement):
            raise AssertionError("Availability must fail before location lookup.")

    assert asyncio.run(handoff_readiness_failure(
        Session(), profile, city, ServiceType.FIXED_ROUTE,
        now=datetime.now(UTC), location_freshness_seconds=30,
    )) == "DRIVER_NOT_AVAILABLE"


@pytest.mark.parametrize("scope", ["missing-city", "wrong-city", "missing-service", "wrong-service"])
def test_live_city_and_service_must_match(scope):
    profile, city = context()
    if scope == "missing-city":
        profile.online_city_id = None
    elif scope == "wrong-city":
        profile.online_city_id = uuid4()
    elif scope == "missing-service":
        profile.online_service_type = None
    else:
        profile.online_service_type = ServiceType.ON_DEMAND

    class Session:
        async def scalar(self, _statement):
            raise AssertionError("Scope must fail before location lookup.")

    assert asyncio.run(handoff_readiness_failure(
        Session(), profile, city, ServiceType.FIXED_ROUTE,
        now=datetime.now(UTC), location_freshness_seconds=30,
    )) == "DRIVER_LIVE_SCOPE_MISMATCH"


@pytest.mark.parametrize("age,expected", [
    (None, "DRIVER_LOCATION_MISSING"), (-60.001, "DRIVER_LOCATION_FUTURE"),
    (-60, None), (0, None), (30, None), (30.001, "DRIVER_LOCATION_STALE"),
])
def test_location_age_boundaries_and_authoritative_area_check(monkeypatch, age, expected):
    profile, city = context()
    now = datetime(2026, 9, 3, 12, tzinfo=UTC)
    location = None if age is None else SimpleNamespace(id=uuid4(), observed_at=now - timedelta(seconds=age))
    area_calls = []

    class Session:
        async def scalar(self, statement):
            assert profile.id in statement.compile().params.values()
            return location

    async def area(_session, **kwargs):
        area_calls.append(kwargs)
        return True

    monkeypatch.setattr("taximobile_api.domains.scheduled_bookings.readiness.location_is_inside_active_service_area", area)
    assert asyncio.run(handoff_readiness_failure(
        Session(), profile, city, ServiceType.FIXED_ROUTE,
        now=now, location_freshness_seconds=30,
    )) == expected
    assert len(area_calls) == (1 if expected is None else 0)
    if area_calls:
        assert area_calls[0] == {"city": city, "location_id": location.id, "now": now}


def test_fresh_location_outside_authoritative_area_is_rejected(monkeypatch):
    profile, city = context()
    now = datetime.now(UTC)

    class Session:
        async def scalar(self, _statement):
            return SimpleNamespace(id=uuid4(), observed_at=now)

    async def area(*_args, **_kwargs):
        return False

    monkeypatch.setattr("taximobile_api.domains.scheduled_bookings.readiness.location_is_inside_active_service_area", area)
    assert asyncio.run(handoff_readiness_failure(
        Session(), profile, city, ServiceType.FIXED_ROUTE,
        now=now, location_freshness_seconds=30,
    )) == "DRIVER_OUTSIDE_SERVICE_AREA"
