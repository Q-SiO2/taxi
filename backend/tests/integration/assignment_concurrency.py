"""Bounded two-session lock-wait harness and mixed booking assignment proof."""

import asyncio
from datetime import UTC, datetime, timedelta

from geoalchemy2.elements import WKTElement
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from taximobile_api.domains.drivers.models import AvailabilityStatus, DriverLocation, DriverProfile
from taximobile_api.domains.rides.locking import lock_driver, lock_owned_offer
from taximobile_api.domains.rides.models import Ride, RideOffer, RideOfferStatus, RideStatus
from taximobile_api.domains.rides.service import accept_offer_atomically, RideOfferUnavailable
from taximobile_api.domains.scheduled_bookings.locking import lock_booking
from taximobile_api.domains.scheduled_bookings.models import ScheduledBooking, ScheduledBookingCommitment
from taximobile_api.domains.scheduled_bookings.service import booking_coordinates, handoff_booking
from taximobile_api.domains.outbox.models import OutboxEvent


async def contended_commands(sessions, *, acquire_first, prepare_second, first_command, second_command):
    """Prove contention before release, retain stale reads and commit both actors."""
    locked, cached, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
    pids, tasks = {}, []

    async def configure(session, actor):
        await session.execute(text("SET LOCAL lock_timeout = '10s'"))
        await session.execute(text("SET LOCAL statement_timeout = '15s'"))
        pids[actor] = await session.scalar(text("SELECT pg_backend_pid()"))

    async def first():
        async with sessions() as session, session.begin():
            await configure(session, "first")
            await acquire_first(session)
            locked.set()
            await asyncio.wait_for(release.wait(), 8)
            return await first_command(session)

    async def second():
        await asyncio.wait_for(locked.wait(), 8)
        async with sessions() as session, session.begin():
            await configure(session, "second")
            old_state = await prepare_second(session)
            cached.set()
            return await second_command(session, old_state)

    try:
        tasks = [asyncio.create_task(first()), asyncio.create_task(second())]
        await asyncio.wait_for(cached.wait(), 8)
        async with sessions() as observer:
            deadline = asyncio.get_running_loop().time() + 5
            while True:
                blockers = await observer.scalar(text("SELECT pg_blocking_pids(:pid)"), {"pid": pids["second"]})
                if pids["first"] in blockers:
                    break
                assert not tasks[1].done(), "Second command bypassed the expected lock"
                assert asyncio.get_running_loop().time() < deadline, "Expected lock wait not observed"
                await asyncio.sleep(0.01)
        release.set()
        return await asyncio.wait_for(asyncio.gather(*tasks), 15)
    finally:
        release.set()
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


async def prove_mixed_assignment(settings, booking_id, *, immediate_first):
    engine = create_async_engine(settings.database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session, session.begin():
            booking = await session.get(ScheduledBooking, booking_id)
            commitment = await session.get(ScheduledBookingCommitment, booking.current_commitment_id)
            driver_id = commitment.driver_id
            now = booking.scheduled_for
            location = await session.scalar(select(DriverLocation).where(DriverLocation.driver_id == driver_id)
                .order_by(DriverLocation.observed_at.desc(), DriverLocation.id.desc()).limit(1))
            location.observed_at = now
            pickup, destination = await booking_coordinates(session, booking)
            immediate = Ride(city_id=booking.city_id, operator_id=booking.operator_id,
                service_type=booking.service_type, fixed_route_direction_id=booking.fixed_route_direction_id,
                passenger_id=booking.passenger_id, status=RideStatus.MATCHING,
                pickup_point=WKTElement(f"POINT({pickup.longitude} {pickup.latitude})", srid=4326),
                destination_point=WKTElement(f"POINT({destination.longitude} {destination.latitude})", srid=4326))
            session.add(immediate)
            await session.flush()
            offer = RideOffer(ride_id=immediate.id, driver_id=driver_id,
                expires_at=datetime.now(UTC) + timedelta(minutes=3))
            session.add(offer)
            await session.flush()
            immediate_id, offer_id = immediate.id, offer.id
            # Deliberately retain an outstanding offer while AVAILABLE: an old
            # offer may survive an offline/online cycle. This adversarial state
            # must not let two independently valid commands assign the driver.
            assert (await session.get(DriverProfile, driver_id)).availability_status == AvailabilityStatus.AVAILABLE

        async def acquire(session):
            if immediate_first:
                await lock_owned_offer(session, offer_id, driver_id)
            else:
                await lock_booking(session, booking_id)
            await lock_driver(session, driver_id)

        async def prepare(session):
            return (await session.get(ScheduledBooking, booking_id),
                    await session.get(DriverProfile, driver_id),
                    await session.get(Ride, immediate_id))

        async def execute(session, immediate_command):
            if immediate_command:
                try:
                    ride = await accept_offer_atomically(session, offer_id, driver_id)
                    return "assigned", ride.id
                except RideOfferUnavailable:
                    return "conflict", None
            result = await handoff_booking(session, await session.get(ScheduledBooking, booking_id),
                now=now, matching_settings=settings)
            return ("assigned", result.id) if isinstance(result, Ride) else ("booking", result.status.value)

        async def first(session):
            return await execute(session, immediate_first)

        async def second(session, old_state):
            result = await execute(session, not immediate_first)
            assert old_state[1].availability_status == AvailabilityStatus.EN_ROUTE
            return result

        first_result, second_result = await contended_commands(sessions, acquire_first=acquire,
            prepare_second=prepare, first_command=first, second_command=second)
        async with sessions() as session:
            assigned = list(await session.scalars(select(Ride).where(Ride.driver_id == driver_id,
                Ride.status.in_([RideStatus.ACCEPTED, RideStatus.DRIVER_EN_ROUTE, RideStatus.DRIVER_ARRIVED, RideStatus.IN_PROGRESS]))))
            assert len(assigned) == 1 and first_result == ("assigned", assigned[0].id)
            booking = await session.get(ScheduledBooking, booking_id)
            offer = await session.get(RideOffer, offer_id)
            if immediate_first:
                assert assigned[0].id == immediate_id and assigned[0].scheduled_booking_id is None
                assert booking.status.value == "UNFULFILLED" and booking.live_ride_id is None
                assert second_result == ("booking", "UNFULFILLED")
                assert offer.status == RideOfferStatus.ACCEPTED
                topic = "scheduled.unfulfilled"
            else:
                assert assigned[0].scheduled_booking_id == booking_id and booking.live_ride_id == assigned[0].id
                assert second_result == ("conflict", None)
                assert offer.status == RideOfferStatus.PENDING
                topic = "scheduled.dispatch.started"
            events = list(await session.scalars(select(OutboxEvent).where(
                OutboxEvent.payload["booking_id"].astext == str(booking_id), OutboxEvent.topic == topic)))
            assert len(events) == 1
    finally:
        await engine.dispose()
