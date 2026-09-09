"""RACE-07 account suspension versus immediate and scheduled assignment.

These tests use independent PostgreSQL sessions and ``pg_blocking_pids`` through
the shared contention harness.  The fixture account and journeys are synthetic;
the results prove transaction ordering, not hosted incident-response readiness.
"""

import asyncio
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from assignment_concurrency import contended_commands
from scheduled_handoff_fixtures import prepare_handoff_fixture
from scheduled_acceptance_fixtures import seed_acceptance
from test_live_ride_concurrency import seed as seed_live_assignment
from test_mvp_lifecycle import require_integration_settings
from test_scheduled_acceptance_concurrency import accept as accept_scheduled_offer
from test_scheduled_live_protection import (
    assert_no_live_acceptance,
    live_work,
)
from taximobile_api.domains.administration.service import suspend_locked_user_access
from taximobile_api.domains.auth.authority import lock_user_for_status_change
from taximobile_api.domains.auth.models import User, UserStatus
from taximobile_api.domains.drivers.models import (
    AvailabilityStatus,
    DriverProfile,
)
from taximobile_api.domains.matching.service import dispatch_ride
from taximobile_api.domains.notifications.models import Notification
from taximobile_api.domains.outbox.models import OutboxEvent
from taximobile_api.domains.rides.models import Ride, RideOffer, RideOfferStatus, RideStatus
from taximobile_api.domains.rides.service import RideOfferUnavailable, accept_offer_atomically
from taximobile_api.domains.scheduled_bookings import service as scheduling
from taximobile_api.domains.scheduled_bookings.models import (
    ScheduledBooking,
    ScheduledBookingCommitment,
    ScheduledBookingOffer,
)


pytestmark = pytest.mark.integration


async def suspend_account(session, user_id):
    """Exercise the same lock and access revocation used by both admin surfaces."""
    user = await lock_user_for_status_change(session, user_id)
    assert user is not None and user.status == UserStatus.ACTIVE
    return await suspend_locked_user_access(
        session,
        user=user,
        changed_at=datetime.now(UTC),
    )


def test_dispatch_excludes_suspended_user_even_when_driver_profile_is_active():
    async def prove():
        settings = require_integration_settings()
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            fixture = await seed_acceptance(sessions, offsets=(0,))
            driver_id = fixture.driver_ids[0]
            ride_id, _ = await live_work(sessions, fixture, driver_id=driver_id)
            async with sessions.begin() as session:
                profile = await session.get(DriverProfile, driver_id)
                for other_id in fixture.driver_ids[1:]:
                    (await session.get(DriverProfile, other_id)).availability_status = (
                        AvailabilityStatus.OFFLINE
                    )
                await suspend_account(session, profile.user_id)

            async with sessions.begin() as session:
                assert await dispatch_ride(session, ride_id, settings) is None

            async with sessions() as session:
                profile = await session.get(DriverProfile, driver_id)
                ride = await session.get(Ride, ride_id)
                # Global containment does not rewrite independent driver history;
                # dispatch must nevertheless treat the profile as no supply.
                assert profile.account_status.value == "ACTIVE"
                assert profile.availability_status == AvailabilityStatus.AVAILABLE
                assert ride.status == RideStatus.UNMATCHED and ride.driver_id is None
                assert await session.scalar(
                    select(RideOffer.id).where(RideOffer.ride_id == ride_id)
                ) is None
        finally:
            await engine.dispose()

    asyncio.run(prove())


def test_suspended_user_cannot_accept_an_existing_scheduled_offer():
    async def prove():
        engine = create_async_engine(require_integration_settings().database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            fixture = await seed_acceptance(sessions, offsets=(0,))
            booking_id, driver_id = fixture.booking_ids[0], fixture.driver_ids[0]
            async with sessions.begin() as session:
                profile = await session.get(DriverProfile, driver_id)
                await suspend_account(session, profile.user_id)
            async with sessions.begin() as session:
                with pytest.raises(
                    scheduling.ScheduledOfferUnavailable,
                    match="Driver account is not active",
                ):
                    await accept_scheduled_offer(session, fixture, booking_id, driver_id)

            async with sessions() as session:
                booking = await session.get(ScheduledBooking, booking_id)
                offer = await session.get(
                    ScheduledBookingOffer,
                    fixture.offer_ids[booking_id, driver_id],
                )
                assert booking.status.value == "OFFERING"
                assert booking.current_commitment_id is None
                assert offer.status.value == "PENDING" and offer.responded_at is None
                assert await session.scalar(
                    select(ScheduledBookingCommitment.id).where(
                        ScheduledBookingCommitment.booking_id == booking_id,
                    )
                ) is None
        finally:
            await engine.dispose()

    asyncio.run(prove())


@pytest.mark.parametrize("winner", ["suspension", "live"])
def test_live_acceptance_and_account_suspension_share_authority_lock(winner):
    async def prove():
        settings = require_integration_settings()
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            ride_id, offer_id, driver_id, user_id, _ = await seed_live_assignment(sessions)

            async def acquire(session):
                if winner == "suspension":
                    await suspend_account(session, user_id)
                else:
                    await accept_offer_atomically(session, offer_id, driver_id)

            async def prepare(session):
                state = (
                    await session.get(User, user_id),
                    await session.get(Ride, ride_id),
                    await session.get(RideOffer, offer_id),
                    await session.get(DriverProfile, driver_id),
                )
                assert state[0].status == UserStatus.ACTIVE
                return state

            async def first(_session):
                return winner

            async def second(session, cached_state):
                assert cached_state[0].status == UserStatus.ACTIVE
                if winner == "suspension":
                    with pytest.raises(
                        RideOfferUnavailable,
                        match="Driver account is no longer active",
                    ):
                        await accept_offer_atomically(session, offer_id, driver_id)
                    return "conflict"
                await suspend_account(session, user_id)
                return "suspension"

            results = await contended_commands(
                sessions,
                acquire_first=acquire,
                prepare_second=prepare,
                first_command=first,
                second_command=second,
            )
            assert results == [
                winner,
                "conflict" if winner == "suspension" else "suspension",
            ]

            async with sessions() as session:
                user = await session.get(User, user_id)
                ride = await session.get(Ride, ride_id)
                offer = await session.get(RideOffer, offer_id)
                assert user.status == UserStatus.SUSPENDED
                if winner == "suspension":
                    await assert_no_live_acceptance(session, ride_id, offer_id)
                else:
                    assert ride.status == RideStatus.ACCEPTED and ride.driver_id == driver_id
                    assert offer.status == RideOfferStatus.ACCEPTED
                    assert await session.scalar(
                        select(func.count(Notification.id)).where(
                            Notification.user_id == ride.passenger_id,
                            Notification.type == "DRIVER_ASSIGNED",
                        )
                    ) == 1
                    assert await session.scalar(
                        select(func.count(OutboxEvent.id)).where(
                            OutboxEvent.topic == "ride.accepted",
                            OutboxEvent.payload["ride_id"].astext == str(ride_id),
                        )
                    ) == 1
        finally:
            await engine.dispose()

    asyncio.run(prove())


@pytest.mark.parametrize("winner", ["suspension", "handoff"])
def test_scheduled_handoff_and_account_suspension_share_authority_lock(winner):
    async def prove():
        settings = require_integration_settings()
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            ready = await prepare_handoff_fixture(sessions)
            fixture = ready.acceptance
            booking_id, driver_id, user_id = ready.booking_id, ready.driver_id, ready.user_id
            first_result = {}

            async def acquire(session):
                if winner == "suspension":
                    await suspend_account(session, user_id)
                else:
                    result = await scheduling.handoff_booking(
                        session,
                        await session.get(ScheduledBooking, booking_id),
                        now=fixture.now,
                        matching_settings=settings,
                    )
                    assert isinstance(result, Ride)
                    first_result["ride_id"] = result.id

            async def prepare(session):
                booking = await session.get(ScheduledBooking, booking_id)
                state = (
                    await session.get(User, user_id),
                    booking,
                    await session.get(
                        ScheduledBookingCommitment,
                        booking.current_commitment_id,
                    ),
                    await session.get(DriverProfile, driver_id),
                )
                assert state[0].status == UserStatus.ACTIVE
                return state

            async def first(_session):
                return winner

            async def second(session, cached_state):
                assert cached_state[0].status == UserStatus.ACTIVE
                if winner == "suspension":
                    result = await scheduling.handoff_booking(
                        session,
                        cached_state[1],
                        now=fixture.now,
                        matching_settings=settings,
                    )
                    assert isinstance(result, ScheduledBooking)
                    return result.status.value
                await suspend_account(session, user_id)
                return "suspension"

            results = await contended_commands(
                sessions,
                acquire_first=acquire,
                prepare_second=prepare,
                first_command=first,
                second_command=second,
            )
            assert results == [
                winner,
                "UNFULFILLED" if winner == "suspension" else "suspension",
            ]

            async with sessions() as session:
                assert (await session.get(User, user_id)).status == UserStatus.SUSPENDED
                booking = await session.get(ScheduledBooking, booking_id)
                commitment = await session.scalar(
                    select(ScheduledBookingCommitment).where(
                        ScheduledBookingCommitment.booking_id == booking_id,
                    )
                )
                rides = list(
                    await session.scalars(
                        select(Ride).where(Ride.scheduled_booking_id == booking_id)
                    )
                )
                if winner == "suspension":
                    assert booking.status.value == "UNFULFILLED"
                    assert booking.current_commitment_id is None
                    assert commitment.status.value == "RELEASED"
                    assert rides == []
                    expected_topic = "scheduled.unfulfilled"
                else:
                    assert booking.status.value == "LIVE_RIDE_CREATED"
                    assert len(rides) == 1
                    assert rides[0].id == first_result["ride_id"]
                    assert rides[0].driver_id == driver_id
                    assert commitment.status.value == "FULFILLED"
                    expected_topic = "scheduled.dispatch.started"
                assert await session.scalar(
                    select(func.count(OutboxEvent.id)).where(
                        OutboxEvent.topic == expected_topic,
                        OutboxEvent.payload["booking_id"].astext == str(booking_id),
                    )
                ) == 1
        finally:
            await engine.dispose()

    asyncio.run(prove())
