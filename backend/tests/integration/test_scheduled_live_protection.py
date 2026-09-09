"""Cross-domain protection between future commitments and immediate rides."""

import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest
from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.dialects.postgresql.ranges import Range
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from assignment_concurrency import contended_commands
from scheduled_acceptance_fixtures import seed_acceptance
from test_mvp_lifecycle import require_integration_settings
from test_scheduled_acceptance_concurrency import accept
from taximobile_api.domains.auth.models import User
from taximobile_api.domains.drivers.models import AvailabilityStatus, DriverProfile
from taximobile_api.domains.matching.service import dispatch_ride
from taximobile_api.domains.notifications.models import Notification
from taximobile_api.domains.outbox.models import OutboxEvent
from taximobile_api.domains.rides.models import Ride, RideEvent, RideEventType, RideOffer, RideOfferStatus, RideStatus
from taximobile_api.domains.rides.service import RideOfferUnavailable, accept_offer_atomically
from taximobile_api.domains.scheduled_bookings import service as scheduling
from taximobile_api.domains.scheduled_bookings.models import (
    ScheduledBooking,
    ScheduledBookingCommitment,
    ScheduledBookingOffer,
)
from taximobile_api.domains.scheduled_bookings.protection import driver_has_protected_commitment


pytestmark = pytest.mark.integration


async def live_work(sessions, fixture, *, driver_id, offer=False):
    async with sessions.begin() as session:
        passenger = User(email=f"immediate-{uuid4().hex}@taximobile.invalid",
                         password_hash="!inert-synthetic-passenger")
        session.add(passenger)
        await session.flush()
        ride = Ride(
            city_id=(await session.get(ScheduledBooking, fixture.booking_ids[0])).city_id,
            operator_id=(await session.get(ScheduledBooking, fixture.booking_ids[0])).operator_id,
            passenger_id=passenger.id, status=RideStatus.MATCHING,
            pickup_point=WKTElement("POINT(-7.5898 33.5731)", srid=4326),
            destination_point=WKTElement("POINT(-7.61 33.58)", srid=4326),
        )
        session.add(ride)
        profile = await session.get(DriverProfile, driver_id)
        profile.availability_status = AvailabilityStatus.OFFERED_RIDE if offer else AvailabilityStatus.AVAILABLE
        profile.available_since = fixture.now - timedelta(minutes=10)
        await session.flush()
        if not offer:
            return ride.id, None
        row = RideOffer(ride_id=ride.id, driver_id=driver_id,
                        status=RideOfferStatus.PENDING, expires_at=fixture.now + timedelta(minutes=5))
        session.add(row)
        await session.flush()
        return ride.id, row.id


async def make_current(session, fixture, booking_id, driver_id):
    booking = await session.get(ScheduledBooking, booking_id)
    booking.scheduled_for = fixture.now
    commitment = await session.scalar(select(ScheduledBookingCommitment).where(
        ScheduledBookingCommitment.booking_id == booking_id,
        ScheduledBookingCommitment.driver_id == driver_id,
    ))
    commitment.protected_window = Range(
        fixture.now - timedelta(minutes=30), fixture.now + timedelta(minutes=120), bounds="[)"
    )
    await session.flush()
    return commitment


async def assert_no_live_acceptance(session, ride_id, offer_id):
    ride = await session.get(Ride, ride_id)
    offer = await session.get(RideOffer, offer_id)
    assert ride.status == RideStatus.MATCHING and ride.driver_id is None and ride.vehicle_id is None
    assert offer.status == RideOfferStatus.PENDING and offer.responded_at is None
    assert await session.scalar(select(RideEvent.id).where(
        RideEvent.ride_id == ride_id, RideEvent.event_type == RideEventType.STATUS_CHANGED,
        RideEvent.new_status == RideStatus.ACCEPTED,
    )) is None
    assert await session.scalar(select(Notification.id).where(
        Notification.user_id == ride.passenger_id, Notification.type == "DRIVER_ASSIGNED",
    )) is None
    assert await session.scalar(select(OutboxEvent.id).where(
        OutboxEvent.topic == "ride.accepted", OutboxEvent.payload["ride_id"].astext == str(ride_id),
    )) is None


def test_active_half_open_window_predicate_has_exact_boundaries_and_status():
    async def prove():
        engine = create_async_engine(require_integration_settings().database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            fixture = await seed_acceptance(sessions, offsets=(0,))
            driver_id = fixture.driver_ids[0]
            async with sessions.begin() as session:
                commitment = await accept(session, fixture, fixture.booking_ids[0], driver_id)
                lower = fixture.now
                upper = fixture.now + timedelta(hours=1)
                commitment.protected_window = Range(lower, upper, bounds="[)")
            async with sessions.begin() as session:
                assert await driver_has_protected_commitment(session, driver_id, at=lower)
                assert await driver_has_protected_commitment(session, driver_id, at=upper - timedelta(microseconds=1))
                assert not await driver_has_protected_commitment(session, driver_id, at=upper)
                commitment = await session.get(ScheduledBookingCommitment, commitment.id)
                commitment.status = "CANCELLED"
            async with sessions() as session:
                assert not await driver_has_protected_commitment(session, driver_id, at=lower)
        finally:
            await engine.dispose()
    asyncio.run(prove())


def test_dispatch_excludes_current_commitment_and_cancellation_restores_supply():
    async def prove():
        settings = require_integration_settings()
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            fixture = await seed_acceptance(sessions, offsets=(0,))
            booking_id, driver_id = fixture.booking_ids[0], fixture.driver_ids[0]
            async with sessions.begin() as session:
                await accept(session, fixture, booking_id, driver_id)
                await make_current(session, fixture, booking_id, driver_id)
                # Keep the second fixture driver out of immediate supply.
                for other in fixture.driver_ids[1:]:
                    (await session.get(DriverProfile, other)).availability_status = AvailabilityStatus.OFFLINE
            first_ride, _ = await live_work(sessions, fixture, driver_id=driver_id)
            async with sessions.begin() as session:
                assert await dispatch_ride(session, first_ride, settings) is None
            async with sessions() as session:
                assert (await session.get(Ride, first_ride)).status == RideStatus.UNMATCHED
                assert await session.scalar(select(RideOffer.id).where(RideOffer.ride_id == first_ride)) is None
            async with sessions.begin() as session:
                booking = await session.get(ScheduledBooking, booking_id)
                await scheduling.cancel_booking(session, booking, passenger_id=fixture.passenger_ids[0],
                                                reason="Synthetic release", now=fixture.now)
            second_ride, _ = await live_work(sessions, fixture, driver_id=driver_id)
            async with sessions.begin() as session:
                offer = await dispatch_ride(session, second_ride, settings)
                assert offer is not None and offer.driver_id == driver_id
        finally:
            await engine.dispose()
    asyncio.run(prove())


def test_dispatch_allows_active_commitment_outside_current_window():
    async def prove():
        settings = require_integration_settings()
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            fixture = await seed_acceptance(sessions, offsets=(0,))
            booking_id, driver_id = fixture.booking_ids[0], fixture.driver_ids[0]
            async with sessions.begin() as session:
                await accept(session, fixture, booking_id, driver_id)
                for other in fixture.driver_ids[1:]:
                    (await session.get(DriverProfile, other)).availability_status = AvailabilityStatus.OFFLINE
            ride_id, _ = await live_work(sessions, fixture, driver_id=driver_id)
            async with sessions.begin() as session:
                offer = await dispatch_ride(session, ride_id, settings)
                assert offer is not None and offer.driver_id == driver_id
        finally:
            await engine.dispose()
    asyncio.run(prove())


def test_offer_crossing_window_is_rejected_then_allowed_after_cancellation():
    async def prove():
        engine = create_async_engine(require_integration_settings().database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            fixture = await seed_acceptance(sessions, offsets=(0,))
            booking_id, driver_id = fixture.booking_ids[0], fixture.driver_ids[0]
            async with sessions.begin() as session:
                await accept(session, fixture, booking_id, driver_id)
                await make_current(session, fixture, booking_id, driver_id)
            ride_id, offer_id = await live_work(sessions, fixture, driver_id=driver_id, offer=True)
            async with sessions.begin() as session:
                with pytest.raises(RideOfferUnavailable, match="reserved for a scheduled booking"):
                    await accept_offer_atomically(session, offer_id, driver_id)
            async with sessions() as session:
                await assert_no_live_acceptance(session, ride_id, offer_id)
            async with sessions.begin() as session:
                await scheduling.cancel_booking(
                    session, await session.get(ScheduledBooking, booking_id),
                    passenger_id=fixture.passenger_ids[0], reason="Synthetic release", now=fixture.now,
                )
            async with sessions.begin() as session:
                accepted = await accept_offer_atomically(session, offer_id, driver_id)
                assert accepted.id == ride_id and accepted.status == RideStatus.ACCEPTED
        finally:
            await engine.dispose()
    asyncio.run(prove())


@pytest.mark.parametrize("winner", ["live", "scheduled"])
def test_live_and_scheduled_acceptance_serialize_on_the_driver(winner):
    async def prove():
        engine = create_async_engine(require_integration_settings().database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            fixture = await seed_acceptance(sessions, offsets=(0,))
            booking_id, driver_id = fixture.booking_ids[0], fixture.driver_ids[0]
            async with sessions.begin() as session:
                (await session.get(ScheduledBooking, booking_id)).scheduled_for = fixture.now
            ride_id, offer_id = await live_work(sessions, fixture, driver_id=driver_id, offer=True)

            async def acquire(session):
                if winner == "live":
                    return await accept_offer_atomically(session, offer_id, driver_id)
                return await accept(session, fixture, booking_id, driver_id)

            async def prepare(session):
                return (await session.get(ScheduledBooking, booking_id),
                        await session.get(ScheduledBookingOffer, fixture.offer_ids[booking_id, driver_id]),
                        await session.get(DriverProfile, driver_id))

            async def first(session):
                return winner

            async def second(session, old_state):
                with pytest.raises((scheduling.ScheduledOfferUnavailable, RideOfferUnavailable)):
                    async with session.begin_nested():
                        if winner == "live":
                            await accept(session, fixture, booking_id, driver_id)
                        else:
                            await accept_offer_atomically(session, offer_id, driver_id)
                assert old_state[2].availability_status == (
                    AvailabilityStatus.EN_ROUTE if winner == "live" else AvailabilityStatus.OFFERED_RIDE
                )
                return "conflict"

            assert await contended_commands(sessions, acquire_first=acquire, prepare_second=prepare,
                first_command=first, second_command=second) == [winner, "conflict"]
            async with sessions() as session:
                booking = await session.get(ScheduledBooking, booking_id)
                if winner == "live":
                    assert (await session.get(Ride, ride_id)).status == RideStatus.ACCEPTED
                    assert booking.status.value == "OFFERING" and booking.current_commitment_id is None
                else:
                    assert booking.status.value == "DRIVER_COMMITTED"
                    await assert_no_live_acceptance(session, ride_id, offer_id)
        finally:
            await engine.dispose()
    asyncio.run(prove())


def test_dispatch_skips_schedule_locked_driver_then_excludes_committed_window():
    async def prove():
        settings = require_integration_settings()
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            fixture = await seed_acceptance(sessions, offsets=(0,))
            booking_id, driver_id = fixture.booking_ids[0], fixture.driver_ids[0]
            async with sessions.begin() as session:
                (await session.get(ScheduledBooking, booking_id)).scheduled_for = fixture.now
            ride_id, _ = await live_work(sessions, fixture, driver_id=driver_id)

            schedule_ready = asyncio.Event()
            release_schedule = asyncio.Event()

            async def schedule_first():
                async with sessions.begin() as session:
                    await accept(session, fixture, booking_id, driver_id)
                    schedule_ready.set()
                    await asyncio.wait_for(release_schedule.wait(), 5)

            task = asyncio.create_task(schedule_first())
            try:
                await asyncio.wait_for(schedule_ready.wait(), 5)
                async with sessions.begin() as session:
                    # Candidate locking is deliberately SKIP LOCKED: it must
                    # return promptly, leave MATCHING and create no stale offer.
                    assert await asyncio.wait_for(dispatch_ride(session, ride_id, settings), 2) is None
                async with sessions() as session:
                    ride = await session.get(Ride, ride_id)
                    assert ride.status == RideStatus.MATCHING
                    assert await session.scalar(select(RideOffer.id).where(RideOffer.ride_id == ride_id)) is None
            finally:
                release_schedule.set()
                await asyncio.wait_for(task, 5)
            # Once committed, the correlated eligibility predicate sees a true
            # absence of supply and closes the bounded matching attempt.
            async with sessions.begin() as session:
                assert await dispatch_ride(session, ride_id, settings) is None
            async with sessions() as session:
                ride = await session.get(Ride, ride_id)
                assert ride.status == RideStatus.UNMATCHED and ride.driver_id is None
                assert await session.scalar(select(RideOffer.id).where(RideOffer.ride_id == ride_id)) is None
        finally:
            await engine.dispose()
    asyncio.run(prove())
