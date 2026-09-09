"""RACE-06: real lock waits, buffered exclusion and transactional side effects."""

import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.dialects.postgresql.ranges import Range
from sqlalchemy.exc import IntegrityError
from datetime import timedelta
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from taximobile_api.domains.drivers.models import DriverProfile
from taximobile_api.domains.notifications.models import Notification
from taximobile_api.domains.outbox.models import OutboxEvent
from taximobile_api.domains.rides.locking import lock_driver
from taximobile_api.domains.rides.models import Ride
from taximobile_api.domains.scheduled_bookings import service
from taximobile_api.domains.scheduled_bookings.models import (
    ScheduledBooking, ScheduledBookingCommitment, ScheduledBookingEvent, ScheduledBookingOffer,
)

from assignment_concurrency import contended_commands
from scheduled_acceptance_fixtures import seed_acceptance
from test_mvp_lifecycle import require_integration_settings


pytestmark = pytest.mark.integration


async def accept(session, fixture, booking_id, driver_id):
    offer = await session.get(ScheduledBookingOffer, fixture.offer_ids[booking_id, driver_id])
    booking = await session.get(ScheduledBooking, booking_id)
    profile = await session.get(DriverProfile, driver_id)
    return await service.accept_offer(session, offer=offer, booking=booking, profile=profile, now=fixture.now)


async def assert_durable(sessions, fixture, winners):
    """Every winner has exactly one booking pointer/event/recipient/outbox result."""
    async with sessions() as session:
        commitments = list(await session.scalars(select(ScheduledBookingCommitment)))
        assert {(c.booking_id, c.driver_id) for c in commitments} == set(winners)
        assert all(c.status.value == "ACTIVE" for c in commitments)
        assert await session.scalar(select(Ride.id)) is None  # Future work is not live assignment.
        events = list(await session.scalars(select(ScheduledBookingEvent).where(
            ScheduledBookingEvent.event_type == "DRIVER_COMMITTED")))
        notices = list(await session.scalars(select(Notification).where(Notification.type == "SCHEDULED_DRIVER_COMMITTED")))
        outbox = list(await session.scalars(select(OutboxEvent).where(OutboxEvent.topic == "scheduled.driver.committed")))
        assert len(events) == len(notices) == len(outbox) == len(winners)
        for commitment in commitments:
            booking = await session.get(ScheduledBooking, commitment.booking_id)
            assert booking.status.value == "DRIVER_COMMITTED" and booking.current_commitment_id == commitment.id
            assert booking.live_ride_id is None
            matching_events = [e for e in events if e.booking_id == booking.id]
            assert len(matching_events) == 1 and matching_events[0].controlled_metadata == {"commitment_id": str(commitment.id)}
            assert len([n for n in notices if n.user_id == booking.passenger_id and n.data == {"booking_id": str(booking.id)}]) == 1
            assert len([e for e in outbox if e.payload == {"booking_id": str(booking.id)}]) == 1
            offers = list(await session.scalars(select(ScheduledBookingOffer).where(ScheduledBookingOffer.booking_id == booking.id)))
            assert all(o.status.value == ("ACCEPTED" if o.id == commitment.offer_id else "CANCELLED") for o in offers)
        for booking_id in set(fixture.booking_ids) - {b for b, _ in winners}:
            booking = await session.get(ScheduledBooking, booking_id)
            assert booking.status.value == "OFFERING" and booking.current_commitment_id is None
            offers = list(await session.scalars(select(ScheduledBookingOffer).where(ScheduledBookingOffer.booking_id == booking_id)))
            assert all(o.status.value == "PENDING" and o.responded_at is None for o in offers)


@pytest.mark.parametrize("mode", ["two-drivers-one-booking", "one-driver-buffer-overlap", "one-driver-adjacent-windows"])
def test_concurrent_acceptance_reloads_authority_and_honors_buffered_windows(mode):
    async def prove():
        engine = create_async_engine(require_integration_settings().database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            fixture = await seed_acceptance(sessions, offsets=(0, 150 if mode == "one-driver-adjacent-windows" else 90))
            booking_a, booking_b = fixture.booking_ids
            driver_a, driver_b = fixture.driver_ids
            if mode == "two-drivers-one-booking":
                booking_b = booking_a
            else:
                driver_b = driver_a

            async def acquire(session):
                await service.driver_offer(session, fixture.offer_ids[booking_a, driver_a], driver_a, lock=True)
                await lock_driver(session, driver_a)

            async def prepare(session):
                return (await session.get(ScheduledBooking, booking_b),
                        await session.get(ScheduledBookingOffer, fixture.offer_ids[booking_b, driver_b]),
                        await session.get(DriverProfile, driver_b))

            async def first(session):
                return (await accept(session, fixture, booking_a, driver_a)).id

            async def second(session, old_state):
                if mode == "one-driver-adjacent-windows":
                    return (await accept(session, fixture, booking_b, driver_b)).id
                # The HTTP boundary rolls back on conflict. A savepoint here
                # models that transaction boundary without masking DB errors.
                with pytest.raises(service.ScheduledOfferUnavailable):
                    async with session.begin_nested():
                        await accept(session, fixture, booking_b, driver_b)
                if mode == "two-drivers-one-booking":
                    assert old_state[0].status.value == "DRIVER_COMMITTED"
                    assert old_state[1].status.value == "CANCELLED"
                return "conflict"

            results = await contended_commands(sessions, acquire_first=acquire, prepare_second=prepare,
                first_command=first, second_command=second)
            winners = [(booking_a, driver_a)]
            if mode == "one-driver-adjacent-windows":
                assert results[0] != results[1]
                winners.append((booking_b, driver_b))
            else:
                assert results[1] == "conflict"
            await assert_durable(sessions, fixture, winners)
        finally:
            await engine.dispose()
    asyncio.run(prove())


def test_cancelled_commitment_releases_window_only_after_commit():
    async def prove():
        engine = create_async_engine(require_integration_settings().database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            fixture = await seed_acceptance(sessions)
            booking_a, booking_b = fixture.booking_ids
            driver_id = fixture.driver_ids[0]
            async with sessions.begin() as session:
                original_id = (await accept(session, fixture, booking_a, driver_id)).id

            async def acquire(session):
                await service.cancel_booking(session, await session.get(ScheduledBooking, booking_a),
                    passenger_id=fixture.passenger_ids[0], reason="Synthetic release test", now=fixture.now)

            async def prepare(session):
                return await session.get(ScheduledBookingCommitment, original_id)

            async def first(session):
                return "cancelled"

            async def second(session, old_commitment):
                assert old_commitment.status.value == "ACTIVE"
                return (await accept(session, fixture, booking_b, driver_id)).id

            result = await contended_commands(sessions, acquire_first=acquire, prepare_second=prepare,
                first_command=first, second_command=second)
            assert result[0] == "cancelled" and result[1] != original_id
            async with sessions() as session:
                rows = list(await session.scalars(select(ScheduledBookingCommitment)))
                assert len(rows) == 2
                original = await session.get(ScheduledBookingCommitment, original_id)
                replacement = await session.get(ScheduledBookingCommitment, result[1])
                assert original.status.value == "CANCELLED" and original.release_reason == "PASSENGER_CANCELLED"
                assert original.released_at == fixture.now
                assert replacement.status.value == "ACTIVE" and replacement.driver_id == driver_id
                old_booking = await session.get(ScheduledBooking, booking_a)
                new_booking = await session.get(ScheduledBooking, booking_b)
                assert old_booking.status.value == "CANCELLED" and old_booking.current_commitment_id == original_id
                assert new_booking.status.value == "DRIVER_COMMITTED" and new_booking.current_commitment_id == result[1]
                assert await session.scalar(select(Ride.id)) is None
                notices = list(await session.scalars(select(Notification).where(Notification.type == "SCHEDULED_DRIVER_COMMITTED")))
                outbox = list(await session.scalars(select(OutboxEvent).where(OutboxEvent.topic == "scheduled.driver.committed")))
                assert len(notices) == len(outbox) == 2  # Retained history, not erased on cancellation.
                assert {n.user_id for n in notices} == set(fixture.passenger_ids)
                assert {e.payload["booking_id"] for e in outbox} == {str(b) for b in fixture.booking_ids}
        finally:
            await engine.dispose()
    asyncio.run(prove())


def test_exclusion_constraint_stops_a_concurrent_writer_without_application_locks():
    async def prove():
        engine = create_async_engine(require_integration_settings().database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            fixture = await seed_acceptance(sessions)
            booking_a, booking_b = fixture.booking_ids
            driver_id = fixture.driver_ids[0]

            async def acquire(session):
                await accept(session, fixture, booking_a, driver_id)

            async def prepare(session):
                return (await session.get(ScheduledBooking, booking_b), await session.get(DriverProfile, driver_id))

            async def first(session):
                return "accepted"

            async def second(session, old_state):
                booking, profile = old_state
                with pytest.raises(IntegrityError) as failure:
                    async with session.begin_nested():
                        session.add(ScheduledBookingCommitment(
                            booking_id=booking_b, offer_id=fixture.offer_ids[booking_b, driver_id],
                            driver_id=driver_id, vehicle_id=profile.active_vehicle_id,
                            protected_window=Range(booking.scheduled_for - timedelta(minutes=30),
                                                   booking.scheduled_for + timedelta(minutes=120), bounds="[)"),
                            status="ACTIVE", committed_at=fixture.now,
                        ))
                        await session.flush()
                assert getattr(failure.value.orig, "sqlstate", None) == "23P01"
                return "excluded"

            assert await contended_commands(sessions, acquire_first=acquire, prepare_second=prepare,
                first_command=first, second_command=second) == ["accepted", "excluded"]
            await assert_durable(sessions, fixture, [(booking_a, driver_id)])
        finally:
            await engine.dispose()
    asyncio.run(prove())
