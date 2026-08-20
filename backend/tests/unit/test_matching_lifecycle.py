from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from taximobile_api.core.config import Settings
from taximobile_api.domains.drivers.models import (
    AvailabilityStatus,
    DriverAccountStatus,
    DriverProfile,
    VerificationStatus,
)
from taximobile_api.domains.matching.service import mark_ride_unmatched
from taximobile_api.domains.notifications.models import Notification
from taximobile_api.domains.outbox.models import OutboxEvent
from taximobile_api.domains.rides.models import Ride, RideEvent, RideEventType, RideOffer, RideOfferStatus, RideStatus
from taximobile_api.domains.rides.service import decline_offer
from taximobile_api.workers.matching import MatchingProcessor


class ScalarSequenceSession:
    def __init__(self, *, scalar_values=(), scalar_list=()) -> None:
        self.scalar_values = list(scalar_values)
        self.scalar_list = list(scalar_list)
        self.added = []
        self.flushes = 0

    async def scalar(self, _statement):
        return self.scalar_values.pop(0)

    async def get(self, _model, _identifier):
        return self.scalar_values.pop(0)

    async def scalars(self, _statement):
        return self.scalar_list

    def add(self, value) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        self.flushes += 1

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    @asynccontextmanager
    async def begin(self):
        yield


def available_driver() -> DriverProfile:
    return DriverProfile(
        id=uuid4(),
        user_id=uuid4(),
        display_name="Driver",
        verification_status=VerificationStatus.APPROVED,
        account_status=DriverAccountStatus.ACTIVE,
        availability_status=AvailabilityStatus.OFFERED_RIDE,
        available_since=datetime.now(UTC) - timedelta(minutes=12),
    )


@pytest.mark.asyncio
async def test_decline_releases_driver_without_erasing_wait_and_records_event() -> None:
    profile = available_driver()
    ride = Ride(id=uuid4(), passenger_id=uuid4(), status=RideStatus.MATCHING)
    offer = RideOffer(
        id=uuid4(),
        ride_id=ride.id,
        driver_id=profile.id,
        status=RideOfferStatus.PENDING,
        expires_at=datetime.now(UTC) + timedelta(minutes=1),
    )
    original_wait = profile.available_since
    session = ScalarSequenceSession(scalar_values=(offer, profile, ride))

    ride_id = await decline_offer(session, offer.id, profile.id, "Pickup is unsuitable")

    assert ride_id == ride.id
    assert offer.status == RideOfferStatus.DECLINED
    assert profile.availability_status == AvailabilityStatus.AVAILABLE
    assert profile.available_since == original_wait
    event = next(value for value in session.added if isinstance(value, RideEvent))
    assert event.event_type == RideEventType.OFFER_DECLINED
    assert event.actor_user_id == profile.user_id


@pytest.mark.asyncio
async def test_expiration_processor_releases_driver_and_advances_same_ride(monkeypatch) -> None:
    profile = available_driver()
    ride = Ride(id=uuid4(), passenger_id=uuid4(), status=RideStatus.MATCHING)
    offer = RideOffer(
        id=uuid4(),
        ride_id=ride.id,
        driver_id=profile.id,
        status=RideOfferStatus.PENDING,
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    original_wait = profile.available_since
    session = ScalarSequenceSession(scalar_values=(profile, ride), scalar_list=(offer,))

    class Factory:
        def __call__(self):
            return session

    dispatched = []

    async def record_dispatch(_session, ride_id, _settings):
        dispatched.append(ride_id)

    monkeypatch.setattr("taximobile_api.workers.matching.dispatch_ride", record_dispatch)
    processed = await MatchingProcessor(Factory(), Settings.from_environment()).process_once()

    assert processed == 1
    assert offer.status == RideOfferStatus.EXPIRED
    assert profile.availability_status == AvailabilityStatus.AVAILABLE
    assert profile.available_since == original_wait
    assert dispatched == [ride.id]
    assert any(
        isinstance(value, RideEvent) and value.event_type == RideEventType.OFFER_EXPIRED
        for value in session.added
    )


@pytest.mark.asyncio
async def test_candidate_exhaustion_is_terminal_audited_and_minimally_notified() -> None:
    ride = Ride(id=uuid4(), passenger_id=uuid4(), status=RideStatus.MATCHING)
    session = ScalarSequenceSession()

    await mark_ride_unmatched(session, ride)

    assert ride.status == RideStatus.UNMATCHED
    event = next(value for value in session.added if isinstance(value, RideEvent))
    outbox = next(value for value in session.added if isinstance(value, OutboxEvent))
    notification = next(value for value in session.added if isinstance(value, Notification))
    assert event.event_type == RideEventType.MATCHING_FAILED
    assert outbox.topic == "ride.matching.failed"
    assert outbox.payload == {"ride_id": str(ride.id)}
    assert notification.user_id == ride.passenger_id
    assert notification.data == {"ride_id": str(ride.id)}
