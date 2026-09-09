"""Migrated-database defenses against conflicting assignment writers."""

import asyncio
import importlib

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from assignment_concurrency import contended_commands
from test_live_ride_concurrency import seed
from test_mvp_lifecycle import require_integration_settings
from taximobile_api.domains.drivers.models import AvailabilityStatus, DriverProfile
from taximobile_api.domains.notifications.models import Notification
from taximobile_api.domains.outbox.models import OutboxEvent
from taximobile_api.domains.rides.locking import lock_driver, lock_owned_offer
from taximobile_api.domains.rides.models import Ride, RideOffer, RideOfferStatus, RideStatus
from taximobile_api.domains.rides.service import accept_offer_atomically, RideOfferUnavailable


pytestmark = pytest.mark.integration
ACTIVE = [RideStatus.ACCEPTED, RideStatus.DRIVER_EN_ROUTE, RideStatus.DRIVER_ARRIVED, RideStatus.IN_PROGRESS]


@pytest.mark.parametrize("same_driver", [True, False], ids=["one-driver-two-rides", "two-drivers-one-ride"])
def test_competing_assignments_have_one_winner(same_driver):
    async def prove():
        settings = require_integration_settings()
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            ride_a, offer_a, driver_a, _, _ = await seed(sessions)
            ride_b, offer_b, driver_b, _, _ = await seed(sessions)
            async with sessions() as session, session.begin():
                offer = await session.get(RideOffer, offer_b)
                if same_driver:
                    offer.driver_id = driver_a
                    driver_b = driver_a
                else:
                    offer.ride_id = ride_a
                    ride_b = ride_a

            async def acquire(session):
                await lock_owned_offer(session, offer_a, driver_a)
                await lock_driver(session, driver_a)

            async def prepare(session):
                return (await session.get(Ride, ride_b), await session.get(RideOffer, offer_b),
                        await session.get(DriverProfile, driver_b))

            async def first(session):
                return (await accept_offer_atomically(session, offer_a, driver_a)).id

            async def second(session, old_state):
                with pytest.raises(RideOfferUnavailable):
                    await accept_offer_atomically(session, offer_b, driver_b)
                if same_driver:
                    assert old_state[2].availability_status == AvailabilityStatus.EN_ROUTE
                else:
                    assert old_state[0].driver_id == driver_a
                return "conflict"

            assert await contended_commands(sessions, acquire_first=acquire, prepare_second=prepare,
                first_command=first, second_command=second) == [ride_a, "conflict"]
            async with sessions() as session:
                active = list(await session.scalars(select(Ride).where(Ride.status.in_(ACTIVE))))
                assert len(active) == 1 and active[0].id == ride_a and active[0].driver_id == driver_a
                assert (await session.get(RideOffer, offer_a)).status == RideOfferStatus.ACCEPTED
                assert (await session.get(RideOffer, offer_b)).status == RideOfferStatus.PENDING
                events = list(await session.scalars(select(OutboxEvent).where(OutboxEvent.topic == "ride.accepted")))
                notices = list(await session.scalars(select(Notification).where(Notification.type == "DRIVER_ASSIGNED")))
                assert len(events) == len(notices) == 1
                assert notices[0].user_id == active[0].passenger_id
        finally:
            await engine.dispose()
    asyncio.run(prove())


@pytest.mark.parametrize("active_status", ACTIVE)
def test_database_rejects_second_active_ride_and_releases_terminal_slot(active_status):
    async def prove():
        settings = require_integration_settings()
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            ride_a, _, driver_a, _, _ = await seed(sessions, arrived=True)
            ride_b, _, _, _, _ = await seed(sessions)
            async with sessions() as session, session.begin():
                # Deliberately bypass services: the DB must guard every writer.
                with pytest.raises(IntegrityError, match="uq_rides_one_active_per_driver"):
                    async with session.begin_nested():
                        await session.execute(text("UPDATE rides SET driver_id=:driver, status=:state WHERE id=:ride"),
                            {"driver": driver_a, "state": active_status.value, "ride": ride_b})
                assert (await session.get(Ride, ride_b)).driver_id is None
                await session.execute(text("UPDATE rides SET status='CANCELLED' WHERE id=:ride"), {"ride": ride_a})
                await session.execute(text("UPDATE rides SET driver_id=:driver, status=:state WHERE id=:ride"),
                    {"driver": driver_a, "state": active_status.value, "ride": ride_b})
            async with sessions() as session:
                assert (await session.get(Ride, ride_a)).status == RideStatus.CANCELLED
                assert (await session.get(Ride, ride_b)).driver_id == driver_a
        finally:
            await engine.dispose()
    asyncio.run(prove())


def test_migration_refuses_conflicts_without_mutating_history_and_can_be_reapplied():
    async def prove():
        settings = require_integration_settings()
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        migration = importlib.import_module("migrations.versions.20260903_0048_one_active_ride_per_driver")

        def migrate(connection, direction):
            with Operations.context(MigrationContext.configure(connection)):
                getattr(migration, direction)()

        try:
            ride_a, _, driver_a, _, _ = await seed(sessions, arrived=True)
            ride_b, _, _, _, _ = await seed(sessions)
            async with engine.begin() as connection:
                await connection.run_sync(migrate, "downgrade")
                await connection.execute(text("UPDATE rides SET driver_id=:driver, status='ACCEPTED' WHERE id=:ride"),
                    {"driver": driver_a, "ride": ride_b})
                before = (await connection.execute(text("SELECT id, driver_id, status FROM rides ORDER BY id"))).all()
                with pytest.raises(DBAPIError, match="Active ride conflicts require operator investigation"):
                    async with connection.begin_nested():
                        await connection.run_sync(migrate, "upgrade")
                assert (await connection.execute(text("SELECT id, driver_id, status FROM rides ORDER BY id"))).all() == before
                # Only the synthetic fixture is resolved here. Production
                # conflicts need the documented independent operator review.
                await connection.execute(text("UPDATE rides SET status='CANCELLED' WHERE id=:ride"), {"ride": ride_b})
                await connection.run_sync(migrate, "upgrade")
                definition = await connection.scalar(text("SELECT indexdef FROM pg_indexes WHERE indexname='uq_rides_one_active_per_driver'"))
                assert "UNIQUE INDEX" in definition and "IN_PROGRESS" in definition
                assert await connection.scalar(text("SELECT status FROM rides WHERE id=:ride"), {"ride": ride_a}) == "DRIVER_ARRIVED"
        finally:
            await engine.dispose()
    asyncio.run(prove())
