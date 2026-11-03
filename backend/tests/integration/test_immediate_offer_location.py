"""Migrated PostGIS assignment-time GPS proofs, not physical GNSS evidence."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from geoalchemy2.elements import WKTElement
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from assignment_concurrency import contended_commands
from test_live_ride_concurrency import seed
from test_mvp_lifecycle import require_integration_settings
from test_scheduled_live_protection import assert_no_live_acceptance
from taximobile_api.domains.drivers.models import AvailabilityStatus, DriverLocation, DriverProfile
from taximobile_api.domains.drivers.schemas import LocationUpdateRequest
from taximobile_api.domains.drivers.service import record_location
from taximobile_api.domains.markets.models import City, CityConfigurationVersion, CityServiceAreaVersion, ServiceAreaStatus
from taximobile_api.domains.notifications.models import Notification
from taximobile_api.domains.outbox.models import OutboxEvent
from taximobile_api.domains.rides.locking import lock_driver
from taximobile_api.domains.rides.models import Ride, RideOffer, RideOfferStatus, RideStatus
from taximobile_api.domains.rides.service import RideOfferUnavailable, accept_offer_atomically


pytestmark = pytest.mark.integration
AREA = 'MULTIPOLYGON(((-7.63 33.58,-7.61 33.58,-7.61 33.60,-7.63 33.60,-7.63 33.58)))'


async def prepare_area(session, ride_id):
    ride = await session.get(Ride, ride_id)
    city = await session.get(City, ride.city_id)
    configuration = await session.get(CityConfigurationVersion, city.active_configuration_version_id)
    area = await session.get(CityServiceAreaVersion, configuration.service_area_version_id)
    area.boundary = WKTElement(AREA, srid=4326)
    await session.flush()
    return city, area


@pytest.mark.parametrize('case,threshold,expected', [
    ('fresh', 30, None), ('missing', 30, 'DRIVER_LOCATION_MISSING'),
    ('stale', 30, 'DRIVER_LOCATION_STALE'), ('future', 30, 'DRIVER_LOCATION_FUTURE'),
    ('latest-outside', 30, 'DRIVER_OUTSIDE_SERVICE_AREA'),
    ('tie-outside', 30, 'DRIVER_OUTSIDE_SERVICE_AREA'),
    ('inactive-area', 30, 'DRIVER_OUTSIDE_SERVICE_AREA'),
    ('no-active-configuration', 30, 'DRIVER_OUTSIDE_SERVICE_AREA'),
    ('configured-fresh', 60, None), ('configured-stale', 10, 'DRIVER_LOCATION_STALE'),
    ('boundary', 30, None),
])
def test_acceptance_reloads_actual_latest_location_and_active_service_area(case, threshold, expected):
    async def prove():
        settings = require_integration_settings()
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            ride_id, offer_id, driver_id, _, _ = await seed(sessions)
            async with sessions.begin() as session:
                city, area = await prepare_area(session, ride_id)
                location = await session.scalar(select(DriverLocation).where(DriverLocation.driver_id == driver_id))
                now = datetime.now(UTC)
                if case == 'missing':
                    await session.execute(delete(DriverLocation).where(DriverLocation.driver_id == driver_id))
                elif case in {'stale', 'configured-fresh', 'configured-stale'}:
                    location.observed_at = now - timedelta(seconds={'stale': 90, 'configured-fresh': 45, 'configured-stale': 20}[case])
                elif case == 'future':
                    # A fresh older observation must not mask a newer future row.
                    session.add(DriverLocation(driver_id=driver_id,
                        point=WKTElement('POINT(-7.62 33.59)', srid=4326),
                        observed_at=now + timedelta(seconds=120), accuracy_meters=5))
                elif case in {'latest-outside', 'tie-outside'}:
                    if case == 'tie-outside':
                        location.id = UUID(int=1)
                        location.observed_at = now
                    session.add(DriverLocation(id=UUID(int=(1 << 128) - 1), driver_id=driver_id,
                        point=WKTElement('POINT(-7.6099 33.59)', srid=4326),
                        observed_at=now if case == 'tie-outside' else now + timedelta(seconds=1), accuracy_meters=5))
                elif case == 'inactive-area':
                    area.status = ServiceAreaStatus.REPLACED
                elif case == 'no-active-configuration':
                    city.active_configuration_version_id = None
                elif case == 'boundary':
                    location.point = WKTElement('POINT(-7.61 33.59)', srid=4326)
            async with sessions.begin() as session:
                if expected:
                    with pytest.raises(RideOfferUnavailable, match=expected):
                        await accept_offer_atomically(session, offer_id, driver_id, location_freshness_seconds=threshold)
                else:
                    accepted = await accept_offer_atomically(session, offer_id, driver_id, location_freshness_seconds=threshold)
                    assert accepted.status == RideStatus.ACCEPTED and accepted.driver_id == driver_id
            async with sessions() as session:
                if expected:
                    await assert_no_live_acceptance(session, ride_id, offer_id)
                    assert (await session.get(DriverProfile, driver_id)).availability_status == AvailabilityStatus.OFFERED_RIDE
                    assert (await session.get(RideOffer, offer_id)).responded_at is None
                else:
                    assert (await session.get(RideOffer, offer_id)).status == RideOfferStatus.ACCEPTED
                    assert (await session.get(DriverProfile, driver_id)).availability_status == AvailabilityStatus.EN_ROUTE
                    events = list(await session.scalars(select(OutboxEvent).where(OutboxEvent.topic == 'ride.accepted')))
                    notices = list(await session.scalars(select(Notification).where(Notification.type == 'DRIVER_ASSIGNED')))
                    assert len(events) == len(notices) == 1
        finally:
            await engine.dispose()
    asyncio.run(prove())


@pytest.mark.parametrize('winner', ['location', 'accept'])
def test_location_ingestion_and_immediate_acceptance_serialize_on_driver(winner):
    async def prove():
        settings = require_integration_settings()
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            ride_id, offer_id, driver_id, _, _ = await seed(sessions)
            async with sessions.begin() as session:
                await prepare_area(session, ride_id)
                location = await session.scalar(select(DriverLocation).where(DriverLocation.driver_id == driver_id))
                location.point = WKTElement('POINT(-7.6101 33.59)', srid=4326)
                location.observed_at = datetime.now(UTC) - timedelta(seconds=10)
                before_location_id = location.id

            async def update(session):
                profile = await lock_driver(session, driver_id)
                return await record_location(session, profile, LocationUpdateRequest(
                    latitude=33.59, longitude=-7.6099, observed_at=datetime.now(UTC), accuracy=5))

            async def acquire(session):
                if winner == 'location':
                    await update(session)
                else:
                    await accept_offer_atomically(session, offer_id, driver_id)

            async def prepare(session):
                profile = await session.get(DriverProfile, driver_id)
                previous = await session.get(DriverLocation, before_location_id)
                assert profile.availability_status == AvailabilityStatus.OFFERED_RIDE
                return profile, previous

            async def first(_session):
                return winner

            async def second(session, cached):
                assert cached[0].availability_status == AvailabilityStatus.OFFERED_RIDE
                if winner == 'location':
                    with pytest.raises(RideOfferUnavailable, match='DRIVER_OUTSIDE_SERVICE_AREA'):
                        await accept_offer_atomically(session, offer_id, driver_id)
                else:
                    await update(session)
                    assert cached[0].availability_status == AvailabilityStatus.EN_ROUTE
                return 'refused' if winner == 'location' else 'updated'

            assert await contended_commands(sessions, acquire_first=acquire, prepare_second=prepare,
                first_command=first, second_command=second) == [winner, 'refused' if winner == 'location' else 'updated']
            async with sessions() as session:
                assert len(list(await session.scalars(select(DriverLocation).where(DriverLocation.driver_id == driver_id)))) == 2
                if winner == 'location':
                    await assert_no_live_acceptance(session, ride_id, offer_id)
                else:
                    ride = await session.get(Ride, ride_id)
                    assert ride.status == RideStatus.ACCEPTED and ride.driver_id == driver_id
                    assert (await session.get(RideOffer, offer_id)).status == RideOfferStatus.ACCEPTED
        finally:
            await engine.dispose()
    asyncio.run(prove())
