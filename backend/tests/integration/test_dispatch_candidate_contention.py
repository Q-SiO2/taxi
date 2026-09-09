"""Deterministic transaction proofs for the defect found by concurrent HTTP load."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from geoalchemy2.elements import WKTElement
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from taximobile_api.domains.auth.models import User
from taximobile_api.domains.drivers.models import DriverProfile
from taximobile_api.domains.markets.constants import LEGACY_CITY_ID, LEGACY_OPERATOR_ID
from taximobile_api.domains.matching.service import dispatch_ride
from taximobile_api.domains.notifications.models import Notification
from taximobile_api.domains.rides.models import Ride, RideOffer, RideStatus
from taximobile_api.workers.matching import MatchingProcessor

from test_mvp_lifecycle import require_integration_settings
from workload_fixtures import seed_workload_supply


pytestmark = pytest.mark.integration


async def seed_ride(sessions):
    async with sessions.begin() as session:
        passenger = User(email=f"load-{uuid4().hex}@taximobile.invalid", password_hash="!inert-workload")
        session.add(passenger)
        await session.flush()
        ride = Ride(city_id=LEGACY_CITY_ID, operator_id=LEGACY_OPERATOR_ID,
                    passenger_id=passenger.id, status=RideStatus.REQUESTED,
                    pickup_point=WKTElement("POINT(-7.5898 33.5731)", srid=4326),
                    destination_point=WKTElement("POINT(-7.61 33.58)", srid=4326))
        session.add(ride)
        await session.flush()
        return ride.id


def test_first_dispatch_does_not_reserve_the_entire_ranked_supply():
    async def scenario():
        settings = require_integration_settings()
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            await seed_workload_supply(sessions, 2)
            first_ride, second_ride = await seed_ride(sessions), await seed_ride(sessions)
            async with sessions.begin() as first:
                first_offer = await dispatch_ride(first, first_ride, settings)
                assert first_offer is not None
                # Keep the first transaction uncommitted. Discovery in the other
                # session sees old AVAILABLE data; candidate locking must choose
                # the other free driver without waiting or reporting no supply.
                async with sessions.begin() as second:
                    second_offer = await asyncio.wait_for(dispatch_ride(second, second_ride, settings), 3)
                    assert second_offer is not None
                    assert second_offer.driver_id != first_offer.driver_id
            async with sessions() as observer:
                offers = list(await observer.scalars(select(RideOffer)))
                assert len(offers) == len({offer.driver_id for offer in offers}) == 2
                assert all(ride.status == RideStatus.MATCHING for ride in await observer.scalars(select(Ride)))
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.parametrize("expire", [False, True])
def test_all_candidates_locked_defer_to_worker_retry_or_matching_deadline(expire):
    async def scenario():
        settings = require_integration_settings()
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            await seed_workload_supply(sessions, 1)
            ride_id = await seed_ride(sessions)
            processor = MatchingProcessor(sessions, settings)
            async with sessions.begin() as holder:
                await holder.scalar(select(DriverProfile).with_for_update())
                async with sessions.begin() as requester:
                    assert await asyncio.wait_for(dispatch_ride(requester, ride_id, settings), 3) is None
                    assert (await requester.get(Ride, ride_id)).status == RideStatus.MATCHING
                # A worker pass while the driver remains locked is not exhaustion.
                assert await asyncio.wait_for(processor.process_once(), 3) == 1
                async with sessions() as observer:
                    assert (await observer.get(Ride, ride_id)).status == RideStatus.MATCHING
                    assert list(await observer.scalars(select(RideOffer))) == []
                    assert list(await observer.scalars(select(Notification))) == []
            if expire:
                async with sessions.begin() as session:
                    ride = await session.get(Ride, ride_id)
                    ride.created_at = datetime.now(UTC) - timedelta(seconds=settings.matching_timeout_seconds + 1)
            assert await processor.process_once() == 1
            assert await processor.process_once() == 0
            async with sessions() as observer:
                ride = await observer.get(Ride, ride_id)
                offers = list(await observer.scalars(select(RideOffer)))
                notifications = list(await observer.scalars(select(Notification)))
                assert ride.status == (RideStatus.UNMATCHED if expire else RideStatus.MATCHING)
                assert len(offers) == (0 if expire else 1)
                assert len(notifications) == 1
        finally:
            await engine.dispose()

    asyncio.run(scenario())
