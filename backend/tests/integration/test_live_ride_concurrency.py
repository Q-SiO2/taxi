"""Synthetic, migrated PostgreSQL proofs; no provider or physical-device claims.

Fixture rows use the migration's compatibility city and real constraints. No
login is possible for these inert password hashes. Independent sessions retain
stale objects, and pg_blocking_pids (not a sleep) proves the contested lock.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from geoalchemy2.elements import WKTElement
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from taximobile_api.domains.auth.models import User
from taximobile_api.domains.drivers.models import (
    AvailabilityStatus, DriverAccountStatus, DriverProfile, Vehicle,
    VehicleVerificationStatus, VerificationStatus,
)
from taximobile_api.domains.driver_applications.models import (
    DriverCityApplication, DriverCityAuthorization, DriverCityAuthorizationService,
)
from taximobile_api.domains.markets.constants import (
    LEGACY_CITY_ID, LEGACY_OPERATOR_ID, LEGACY_DRIVER_REQUIREMENT_VERSION_ID,
)
from taximobile_api.domains.markets.models import ServiceType
from taximobile_api.domains.notifications.models import Notification
from taximobile_api.domains.outbox.models import OutboxEvent
from taximobile_api.domains.rides import service
from taximobile_api.domains.rides.locking import lock_driver, lock_ride
from taximobile_api.domains.rides.models import Ride, RideOffer, RideStatus, RideOfferStatus
from taximobile_api.domains.matching.service import dispatch_ride
from taximobile_api.workers.matching import MatchingProcessor
from test_mvp_lifecycle import require_integration_settings


pytestmark = pytest.mark.integration


async def seed(sessions, *, arrived=False, expired=False):
    async with sessions() as session, session.begin():
        driver_user = User(email=f"driver-{uuid4().hex}@example.test", password_hash="!inert-synthetic-account")
        passenger = User(email=f"passenger-{uuid4().hex}@example.test", password_hash="!inert-synthetic-account")
        session.add_all([driver_user, passenger])
        await session.flush()
        profile = DriverProfile(user_id=driver_user.id, display_name="Synthetic driver",
            account_status=DriverAccountStatus.ACTIVE, verification_status=VerificationStatus.APPROVED,
            availability_status=AvailabilityStatus.AT_PICKUP if arrived else AvailabilityStatus.OFFERED_RIDE,
            online_city_id=LEGACY_CITY_ID, online_service_type=ServiceType.ON_DEMAND)
        session.add(profile)
        await session.flush()
        vehicle = Vehicle(driver_id=profile.id, make="Synthetic", model="Fixture", year=2025,
            color="grey", registration_number=f"TEST-{uuid4().hex}",
            verification_status=VehicleVerificationStatus.VERIFIED)
        session.add(vehicle)
        await session.flush()
        profile.active_vehicle_id = vehicle.id
        application = DriverCityApplication(driver_id=profile.id, city_id=LEGACY_CITY_ID,
            requirement_version_id=LEGACY_DRIVER_REQUIREMENT_VERSION_ID)
        session.add(application)
        await session.flush()
        authorization = DriverCityAuthorization(driver_id=profile.id, city_id=LEGACY_CITY_ID,
            application_id=application.id, vehicle_id=vehicle.id,
            valid_from=datetime.now(UTC) - timedelta(days=1))
        session.add(authorization)
        await session.flush()
        session.add(DriverCityAuthorizationService(authorization_id=authorization.id,
            service_type=ServiceType.ON_DEMAND))
        ride = Ride(city_id=LEGACY_CITY_ID, operator_id=LEGACY_OPERATOR_ID,
            passenger_id=passenger.id,
            status=RideStatus.DRIVER_ARRIVED if arrived else RideStatus.MATCHING,
            driver_id=profile.id if arrived else None, vehicle_id=vehicle.id if arrived else None,
            pickup_point=WKTElement("POINT(-7.62 33.59)", srid=4326),
            destination_point=WKTElement("POINT(-7.61 33.58)", srid=4326))
        session.add(ride)
        await session.flush()
        offer = RideOffer(ride_id=ride.id, driver_id=profile.id,
            status=RideOfferStatus.ACCEPTED if arrived else RideOfferStatus.PENDING,
            expires_at=datetime.now(UTC) + timedelta(seconds=-1 if expired else 180))
        session.add(offer)
        await session.flush()
        return ride.id, offer.id, profile.id, driver_user.id, passenger.id


@pytest.mark.parametrize("mode", [
    "cancel-accept", "accept-cancel", "accept-accept", "decline-accept",
    "offline-accept", "start-cancel", "cancel-start",
])
def test_live_commands_observe_winning_transaction(mode):
    asyncio.run(prove_race(require_integration_settings(), mode))


async def prove_race(settings, mode):
    engine = create_async_engine(settings.database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    first_locked, cached, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
    pids, tasks = {}, []
    try:
        ride_id, offer_id, driver_id, user_id, passenger_id = await seed(sessions, arrived="start" in mode)

        async def configure(session, name):
            await session.execute(text("SET LOCAL lock_timeout = '10s'"))
            await session.execute(text("SET LOCAL statement_timeout = '15s'"))
            pids[name] = await session.scalar(text("SELECT pg_backend_pid()"))

        async def command(session, name, ride, profile):
            try:
                if name == "accept":
                    await service.accept_offer_atomically(session, offer_id, driver_id)
                elif name == "cancel":
                    await service.cancel_passenger_ride(session, ride, passenger_id, "Synthetic race")
                elif name == "decline":
                    await service.decline_offer(session, offer_id, driver_id, "Synthetic decline")
                elif name == "start":
                    await service.transition_assigned_ride(session, ride, profile, RideStatus.IN_PROGRESS, user_id)
                elif name == "offline":
                    profile.availability_status = AvailabilityStatus.OFFLINE
                    profile.online_city_id = profile.online_service_type = profile.available_since = None
                else:
                    raise AssertionError(name)
                return "ok"
            except (service.RideOfferUnavailable, service.InvalidRideTransition):
                return "conflict"

        first_action, second_action = mode.split("-")

        async def first():
            async with sessions() as session, session.begin():
                await configure(session, "first")
                if first_action == "offline":
                    profile = await lock_driver(session, driver_id)
                    ride = await session.get(Ride, ride_id)
                else:
                    ride = await lock_ride(session, ride_id)
                    profile = await session.get(DriverProfile, driver_id)
                first_locked.set()
                await asyncio.wait_for(release.wait(), 8)
                return await command(session, first_action, ride, profile)

        async def second():
            await asyncio.wait_for(first_locked.wait(), 8)
            async with sessions() as session, session.begin():
                await configure(session, "second")
                ride = await session.get(Ride, ride_id)
                profile = await session.get(DriverProfile, driver_id)
                offer = await session.get(RideOffer, offer_id)
                cached.set()
                result = await command(session, second_action, ride, profile)
                if mode == "offline-accept":
                    assert profile.availability_status == AvailabilityStatus.OFFLINE
                assert offer.id == offer_id  # keep strong cached references across lock wait
                return result

        tasks = [asyncio.create_task(first()), asyncio.create_task(second())]
        await asyncio.wait_for(cached.wait(), 8)
        async with sessions() as observer:
            deadline = asyncio.get_running_loop().time() + 5
            while True:
                blockers = await observer.scalar(text("SELECT pg_blocking_pids(:pid)"), {"pid": pids["second"]})
                if pids["first"] in blockers:
                    break
                assert not tasks[1].done(), "Command bypassed the required lock"
                assert asyncio.get_running_loop().time() < deadline, "No expected lock wait"
                await asyncio.sleep(0.01)
        release.set()
        results = await asyncio.wait_for(asyncio.gather(*tasks), 15)
        assert results == ["ok", "ok" if mode == "accept-cancel" else "conflict"]
        async with sessions() as session:
            ride = await session.get(Ride, ride_id)
            profile = await session.get(DriverProfile, driver_id)
            offer = await session.get(RideOffer, offer_id)
            expected = {
                "cancel-accept": (RideStatus.CANCELLED, AvailabilityStatus.AVAILABLE, RideOfferStatus.CANCELLED),
                "accept-cancel": (RideStatus.CANCELLED, AvailabilityStatus.AVAILABLE, RideOfferStatus.ACCEPTED),
                "accept-accept": (RideStatus.ACCEPTED, AvailabilityStatus.EN_ROUTE, RideOfferStatus.ACCEPTED),
                "decline-accept": (RideStatus.MATCHING, AvailabilityStatus.AVAILABLE, RideOfferStatus.DECLINED),
                "offline-accept": (RideStatus.MATCHING, AvailabilityStatus.OFFLINE, RideOfferStatus.PENDING),
                "start-cancel": (RideStatus.IN_PROGRESS, AvailabilityStatus.ON_RIDE, RideOfferStatus.ACCEPTED),
                "cancel-start": (RideStatus.CANCELLED, AvailabilityStatus.AVAILABLE, RideOfferStatus.ACCEPTED),
            }[mode]
            assert (ride.status, profile.availability_status, offer.status) == expected
            events = list(await session.scalars(select(OutboxEvent).where(
                OutboxEvent.payload["ride_id"].astext == str(ride_id))))
            assert sum(e.topic == "ride.accepted" for e in events) == int(first_action == "accept")
            assert sum(e.topic == "ride.cancelled" for e in events) == int(ride.status == RideStatus.CANCELLED)
            notifications = list(await session.scalars(select(Notification).where(
                Notification.data["ride_id"].astext == str(ride_id))))
            assert len(notifications) == int(first_action == "accept")
            assert all(n.user_id == passenger_id for n in notifications)
    finally:
        release.set()
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await engine.dispose()


def test_expiry_worker_skips_locked_ride_then_expires_once():
    async def prove():
        settings = require_integration_settings()
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            ride_id, offer_id, driver_id, _, _ = await seed(sessions, expired=True)
            processor = MatchingProcessor(sessions, settings)
            async with sessions() as holder, holder.begin():
                await lock_ride(holder, ride_id)
                assert await asyncio.wait_for(processor.process_once(), 3) == 0
                assert (await holder.get(RideOffer, offer_id)).status == RideOfferStatus.PENDING
            assert await asyncio.wait_for(processor.process_once(), 8) == 1
            assert await processor.process_once() == 0
            async with sessions() as session:
                assert (await session.get(RideOffer, offer_id)).status == RideOfferStatus.EXPIRED
                assert (await session.get(Ride, ride_id)).status == RideStatus.UNMATCHED
                assert (await session.get(DriverProfile, driver_id)).availability_status == AvailabilityStatus.AVAILABLE
                events = list(await session.scalars(select(OutboxEvent).where(
                    OutboxEvent.payload["ride_id"].astext == str(ride_id))))
                assert len(events) == 1 and events[0].topic == "ride.matching.failed"
        finally:
            await engine.dispose()
    asyncio.run(prove())


@pytest.mark.parametrize("ride_status", [RideStatus.DRIVER_EN_ROUTE, RideStatus.DRIVER_ARRIVED, RideStatus.IN_PROGRESS])
def test_dispatch_never_reopens_an_operational_ride(ride_status):
    async def prove():
        settings = require_integration_settings()
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            ride_id, _, _, _, _ = await seed(sessions, arrived=True)
            async with sessions() as session, session.begin():
                ride = await session.get(Ride, ride_id)
                ride.status = ride_status
            async with sessions() as session, session.begin():
                assert await dispatch_ride(session, ride_id, settings) is None
                assert (await session.get(Ride, ride_id)).status == ride_status
        finally:
            await engine.dispose()
    asyncio.run(prove())
