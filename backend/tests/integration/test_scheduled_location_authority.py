"""RACE-07 driver location updates versus scheduled handoff.

Both actors exercise production domain commands in independent PostgreSQL
sessions.  The shared contention harness proves an actual row-lock wait with
``pg_blocking_pids`` before either transaction is released.
"""

import asyncio
from datetime import timedelta

import pytest
from geoalchemy2 import Geometry
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from assignment_concurrency import contended_commands
from scheduled_handoff_fixtures import prepare_handoff_fixture
from test_mvp_lifecycle import require_integration_settings
from taximobile_api.domains.auth.models import User, UserStatus
from taximobile_api.domains.drivers.models import (
    AvailabilityStatus,
    DriverLocation,
    DriverProfile,
)
from taximobile_api.domains.drivers.schemas import LocationUpdateRequest
from taximobile_api.domains.drivers.service import record_location
from taximobile_api.domains.notifications.models import Notification
from taximobile_api.domains.outbox.models import OutboxEvent
from taximobile_api.domains.rides.locking import lock_driver
from taximobile_api.domains.rides.models import Ride, RideStatus
from taximobile_api.domains.scheduled_bookings import service as scheduling
from taximobile_api.domains.scheduled_bookings.models import (
    ScheduledBooking,
    ScheduledBookingCommitment,
    ScheduledBookingEvent,
    ScheduledBookingEventType,
)


pytestmark = pytest.mark.integration

BOUNDARY_LATITUDE = 33.5731
INSIDE_LONGITUDE = -7.201
OUTSIDE_LONGITUDE = -7.199
LOCATION_STEP = timedelta(seconds=10)


async def record_outside_location(session, *, ready):
    """Follow the authenticated location route's lock-then-write sequence."""

    profile = await lock_driver(session, ready.driver_id)
    assert profile is not None
    return await record_location(
        session,
        profile,
        LocationUpdateRequest(
            latitude=BOUNDARY_LATITUDE,
            longitude=OUTSIDE_LONGITUDE,
            observed_at=ready.now,
            accuracy=5,
        ),
    )


@pytest.mark.parametrize("winner", ["location", "handoff"])
def test_location_update_and_scheduled_handoff_serialize_on_driver(winner):
    async def prove():
        settings = require_integration_settings()
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            ready = await prepare_handoff_fixture(
                sessions,
                latitude=BOUNDARY_LATITUDE,
                longitude=INSIDE_LONGITUDE,
                location_age=LOCATION_STEP,
            )
            first_ids = {}

            async def acquire(session):
                if winner == "location":
                    location = await record_outside_location(session, ready=ready)
                    first_ids["location"] = location.id
                    return
                result = await scheduling.handoff_booking(
                    session,
                    await session.get(ScheduledBooking, ready.booking_id),
                    now=ready.now,
                    matching_settings=settings,
                )
                assert isinstance(result, Ride)
                first_ids["ride"] = result.id

            async def prepare(session):
                booking = await session.get(ScheduledBooking, ready.booking_id)
                profile = await session.get(DriverProfile, ready.driver_id)
                location = await session.scalar(
                    select(DriverLocation)
                    .where(DriverLocation.driver_id == ready.driver_id)
                    .order_by(DriverLocation.observed_at.desc(), DriverLocation.id.desc())
                    .limit(1)
                )
                assert booking is not None and profile is not None and location is not None
                assert profile.availability_status == AvailabilityStatus.AVAILABLE
                assert location.observed_at == ready.now - LOCATION_STEP
                return booking, profile, location

            async def first(_session):
                return winner

            async def second(session, cached_state):
                assert cached_state[1].availability_status == AvailabilityStatus.AVAILABLE
                if winner == "location":
                    result = await scheduling.handoff_booking(
                        session,
                        cached_state[0],
                        now=ready.now,
                        matching_settings=settings,
                    )
                    assert isinstance(result, ScheduledBooking)
                    return result.status.value
                location = await record_outside_location(session, ready=ready)
                assert location.id != cached_state[2].id
                return "location"

            assert await contended_commands(
                sessions,
                acquire_first=acquire,
                prepare_second=prepare,
                first_command=first,
                second_command=second,
            ) == [
                winner,
                "UNFULFILLED" if winner == "location" else "location",
            ]

            async with sessions() as session:
                user = await session.get(User, ready.user_id)
                profile = await session.get(DriverProfile, ready.driver_id)
                booking = await session.get(ScheduledBooking, ready.booking_id)
                commitment = await session.scalar(
                    select(ScheduledBookingCommitment).where(
                        ScheduledBookingCommitment.booking_id == ready.booking_id,
                    )
                )
                rides = list(
                    await session.scalars(
                        select(Ride).where(Ride.scheduled_booking_id == ready.booking_id)
                    )
                )
                latest_location = (
                    await session.execute(
                        select(
                            DriverLocation.id,
                            DriverLocation.observed_at,
                            func.ST_X(
                                DriverLocation.point.cast(
                                    Geometry(geometry_type="POINT", srid=4326)
                                )
                            ),
                        )
                        .where(DriverLocation.driver_id == ready.driver_id)
                        .order_by(
                            DriverLocation.observed_at.desc(),
                            DriverLocation.id.desc(),
                        )
                        .limit(1)
                    )
                ).one()

                assert user is not None and user.status == UserStatus.ACTIVE
                assert profile is not None and booking is not None and commitment is not None
                assert latest_location.observed_at == ready.now
                assert latest_location[2] == pytest.approx(OUTSIDE_LONGITUDE)
                if winner == "location":
                    assert latest_location.id == first_ids["location"]
                    assert booking.status.value == "UNFULFILLED"
                    assert booking.current_commitment_id is None
                    assert profile.availability_status == AvailabilityStatus.AVAILABLE
                    assert commitment.status.value == "RELEASED"
                    assert commitment.release_reason == "DRIVER_OUTSIDE_SERVICE_AREA"
                    assert rides == []
                    event = await session.scalar(
                        select(ScheduledBookingEvent).where(
                            ScheduledBookingEvent.booking_id == ready.booking_id,
                            ScheduledBookingEvent.event_type
                            == ScheduledBookingEventType.UNFULFILLED,
                        )
                    )
                    assert event is not None
                    assert event.controlled_metadata == {
                        "reason": "DRIVER_OUTSIDE_SERVICE_AREA_FALLBACK_NO_SUPPLY"
                    }
                    expected_topic = "scheduled.unfulfilled"
                    expected_notification = "SCHEDULED_UNFULFILLED"
                else:
                    assert booking.status.value == "LIVE_RIDE_CREATED"
                    assert booking.live_ride_id == first_ids["ride"]
                    assert len(rides) == 1
                    assert rides[0].id == first_ids["ride"]
                    assert rides[0].driver_id == ready.driver_id
                    assert rides[0].status == RideStatus.ACCEPTED
                    assert profile.availability_status == AvailabilityStatus.EN_ROUTE
                    assert commitment.status.value == "FULFILLED"
                    expected_topic = "scheduled.dispatch.started"
                    expected_notification = "SCHEDULED_DISPATCH_STARTED"

                assert await session.scalar(
                    select(func.count(OutboxEvent.id)).where(
                        OutboxEvent.topic == expected_topic,
                        OutboxEvent.payload["booking_id"].astext == str(ready.booking_id),
                    )
                ) == 1
                assert await session.scalar(
                    select(func.count(Notification.id)).where(
                        Notification.user_id == ready.acceptance.passenger_ids[0],
                        Notification.type == expected_notification,
                    )
                ) == 1
        finally:
            await engine.dispose()

    asyncio.run(prove())
