"""Real PostgreSQL lock-wait proofs using the public-route lifecycle's coherent fixture.

The barrier is pg_blocking_pids, not an assumed sleep or task launch order.
Each invocation owns its isolated integration database and commits both actors.
"""

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from taximobile_api.domains.drivers.models import AvailabilityStatus, DriverLocation, DriverProfile
from taximobile_api.domains.drivers.service import driver_for_user
from taximobile_api.domains.notifications.models import Notification
from taximobile_api.domains.outbox.models import OutboxEvent
from taximobile_api.domains.rides.models import Ride
from taximobile_api.domains.scheduled_bookings import service
from taximobile_api.domains.scheduled_bookings.locking import lock_booking
from taximobile_api.domains.scheduled_bookings.models import (
    ScheduledBooking, ScheduledBookingCommitment, ScheduledBookingOffer,
)


async def prove_scheduling_race(settings, booking_id: UUID, mode: str):
    engine = create_async_engine(settings.database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    winner_locked = asyncio.Event()
    loser_cached = asyncio.Event()
    release_winner = asyncio.Event()
    pids = {}
    tasks = []
    try:
        async with sessions() as session, session.begin():
            booking = await session.get(ScheduledBooking, booking_id)
            offer = await session.scalar(select(ScheduledBookingOffer).where(
                ScheduledBookingOffer.booking_id == booking_id,
            ))
            driver_id = offer.driver_id
            offer_id = offer.id
            profile = await session.get(DriverProfile, driver_id)
            user_id = profile.user_id
            passenger_id = booking.passenger_id
            now = booking.scheduled_for if mode != "accept-cancel" else datetime.now(UTC)
            location = await session.scalar(select(DriverLocation).where(
                DriverLocation.driver_id == driver_id,
            ).order_by(DriverLocation.observed_at.desc(), DriverLocation.id.desc()).limit(1))
            assert location is not None
            # Advance the observation with the simulated handoff clock.
            location.observed_at = now

        async def configure(session, actor):
            await session.execute(text("SET LOCAL lock_timeout = '10s'"))
            await session.execute(text("SET LOCAL statement_timeout = '15s'"))
            pids[actor] = await session.scalar(text("SELECT pg_backend_pid()"))

        async def act(session, action, cached_booking):
            try:
                if action == "handoff":
                    result = await service.handoff_booking(
                        session, cached_booking, now=now, matching_settings=settings,
                    )
                    return ("ride", result.id) if isinstance(result, Ride) else ("booking", result.status.value)
                if action == "cancel":
                    result = await service.cancel_booking(
                        session, cached_booking, passenger_id=passenger_id,
                        reason="Synthetic lock-order proof", now=now,
                    )
                    return ("booking", result.status.value)
                if action == "accept":
                    offer, booking = await service.driver_offer(session, offer_id, driver_id, lock=True)
                    profile = await session.get(DriverProfile, driver_id)
                    result = await service.accept_offer(
                        session, offer=offer, booking=booking, profile=profile, now=now,
                    )
                    return ("commitment", result.id)
                raise AssertionError("Unknown race action")
            except (service.SchedulingConflict, service.ScheduledOfferUnavailable):
                return ("conflict", None)

        async def winner():
            async with sessions() as session, session.begin():
                await configure(session, "winner")
                if mode == "offline-handoff":
                    profile = await driver_for_user(session, user_id, lock=True)
                    cached_booking = None
                else:
                    cached_booking = await lock_booking(session, booking_id)
                winner_locked.set()
                await asyncio.wait_for(release_winner.wait(), timeout=8)
                if mode == "offline-handoff":
                    profile.availability_status = AvailabilityStatus.OFFLINE
                    profile.available_since = None
                    profile.online_city_id = None
                    profile.online_service_type = None
                    return ("offline", None)
                action = "cancel" if mode in {"cancel-handoff", "accept-cancel"} else "handoff"
                return await act(session, action, cached_booking)

        async def loser():
            await asyncio.wait_for(winner_locked.wait(), timeout=8)
            async with sessions() as session, session.begin():
                await configure(session, "loser")
                cached_booking = await session.get(ScheduledBooking, booking_id)
                cached_profile = await session.get(DriverProfile, driver_id)
                assert cached_profile.availability_status == AvailabilityStatus.AVAILABLE
                # Hold references so SQLAlchemy's weak identity map really keeps
                # the old rows across the wait; this catches missing refreshes.
                loser_cached.set()
                action = "accept" if mode == "accept-cancel" else "cancel" if mode == "handoff-cancel" else "handoff"
                result = await act(session, action, cached_booking)
                if mode == "offline-handoff":
                    assert cached_profile.availability_status == AvailabilityStatus.OFFLINE
                return result

        tasks = [asyncio.create_task(winner()), asyncio.create_task(loser())]
        await asyncio.wait_for(loser_cached.wait(), timeout=8)
        async with sessions() as observer:
            deadline = asyncio.get_running_loop().time() + 5
            while True:
                blockers = await observer.scalar(text("SELECT pg_blocking_pids(:pid)"), {"pid": pids["loser"]})
                if pids["winner"] in blockers:
                    break
                assert not tasks[1].done(), "Loser bypassed the required database lock"
                assert asyncio.get_running_loop().time() < deadline, "Expected lock wait was not observed"
                await asyncio.sleep(0.01)
        release_winner.set()
        first, second = await asyncio.wait_for(asyncio.gather(*tasks), timeout=15)

        async with sessions() as session:
            booking = await session.get(ScheduledBooking, booking_id)
            rides = list(await session.scalars(select(Ride).where(Ride.scheduled_booking_id == booking_id)))
            events = list(await session.scalars(select(OutboxEvent).where(
                OutboxEvent.payload["booking_id"].astext == str(booking_id),
            )))
            notifications = list(await session.scalars(select(Notification).where(
                Notification.data["booking_id"].astext == str(booking_id),
            )))
            if mode in {"handoff-handoff", "handoff-cancel"}:
                assert booking.status.value == "LIVE_RIDE_CREATED"
                assert len(rides) == 1 and booking.live_ride_id == rides[0].id
                assert first == ("ride", rides[0].id)
                assert second == (first if mode == "handoff-handoff" else ("conflict", None))
                topic, hint = "scheduled.dispatch.started", "SCHEDULED_DISPATCH_STARTED"
            elif mode == "offline-handoff":
                assert booking.status.value == "UNFULFILLED"
                assert rides == [] and booking.live_ride_id is None
                assert first == ("offline", None) and second == ("booking", "UNFULFILLED")
                topic, hint = "scheduled.unfulfilled", "SCHEDULED_UNFULFILLED"
            else:
                assert booking.status.value == "CANCELLED"
                assert rides == [] and booking.live_ride_id is None
                assert first == ("booking", "CANCELLED") and second == ("conflict", None)
                assert not any(row.topic in {"scheduled.dispatch.started", "scheduled.unfulfilled"} for row in events)
                if mode == "accept-cancel":
                    assert await session.scalar(select(ScheduledBookingCommitment.id).where(
                        ScheduledBookingCommitment.booking_id == booking_id,
                    )) is None
                return
            assert len([row for row in events if row.topic == topic]) == 1
            notices = [row for row in notifications if row.type == hint]
            assert len(notices) == 1 and notices[0].user_id == passenger_id
    finally:
        release_winner.set()
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await engine.dispose()
