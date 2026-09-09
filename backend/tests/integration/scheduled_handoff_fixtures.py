"""Synthetic, migrated fixture for scheduled-booking handoff races.

The helper prepares a real accepted commitment at its handoff instant.  Tests
may place the driver's latest location close to a service-area boundary so a
small, credible update can change live readiness without bypassing production
domain commands.
"""

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.dialects.postgresql.ranges import Range

from scheduled_acceptance_fixtures import AcceptanceFixture, seed_acceptance
from taximobile_api.domains.drivers.models import (
    AvailabilityStatus,
    DriverLocation,
    DriverProfile,
)
from taximobile_api.domains.scheduled_bookings.models import (
    ScheduledBooking,
    ScheduledBookingOffer,
)
from taximobile_api.domains.scheduled_bookings import service as scheduling


@dataclass(frozen=True)
class ReadyHandoffFixture:
    """Identifiers and clock for one committed booking ready for handoff."""

    acceptance: AcceptanceFixture
    booking_id: UUID
    driver_id: UUID
    user_id: UUID

    @property
    def now(self):
        return self.acceptance.now


async def prepare_handoff_fixture(
    sessions,
    *,
    latitude: float | None = None,
    longitude: float | None = None,
    location_age: timedelta = timedelta(0),
) -> ReadyHandoffFixture:
    """Create one current commitment with only its driver in live supply.

    ``latitude`` and ``longitude`` must be supplied together. ``location_age``
    is relative to the fixture's stable handoff clock, which makes boundary
    and freshness races deterministic without inventing future timestamps.
    """

    if (latitude is None) != (longitude is None):
        raise ValueError("Handoff fixture latitude and longitude must be supplied together.")
    if location_age < timedelta(0):
        raise ValueError("Handoff fixture location age cannot be negative.")

    fixture = await seed_acceptance(sessions, offsets=(0,))
    booking_id, driver_id = fixture.booking_ids[0], fixture.driver_ids[0]
    async with sessions.begin() as session:
        booking = await session.get(ScheduledBooking, booking_id)
        profile = await session.get(DriverProfile, driver_id)
        offer = await session.get(
            ScheduledBookingOffer,
            fixture.offer_ids[booking_id, driver_id],
        )
        assert booking is not None and profile is not None and offer is not None
        commitment = await scheduling.accept_offer(
            session,
            offer=offer,
            booking=booking,
            profile=profile,
            now=fixture.now,
        )
        booking.scheduled_for = fixture.now
        commitment.protected_window = Range(
            fixture.now - timedelta(minutes=30),
            fixture.now + timedelta(minutes=120),
            bounds="[)",
        )
        profile.availability_status = AvailabilityStatus.AVAILABLE
        profile.available_since = fixture.now
        location = await session.scalar(
            select(DriverLocation)
            .where(DriverLocation.driver_id == driver_id)
            .order_by(DriverLocation.observed_at.desc(), DriverLocation.id.desc())
            .limit(1)
        )
        assert location is not None
        if latitude is not None and longitude is not None:
            location.point = WKTElement(f"POINT({longitude} {latitude})", srid=4326)
        location.observed_at = fixture.now - location_age
        for other_id in fixture.driver_ids[1:]:
            other = await session.get(DriverProfile, other_id)
            assert other is not None
            other.availability_status = AvailabilityStatus.OFFLINE
        await session.flush()
        return ReadyHandoffFixture(
            acceptance=fixture,
            booking_id=booking_id,
            driver_id=driver_id,
            user_id=profile.user_id,
        )
