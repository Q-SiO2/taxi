import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from taximobile_api.domains.rides.models import Ride, RideStatus
from taximobile_api.domains.rides.service import (
    DRIVER_CANCELLABLE,
    PASSENGER_CANCELLABLE,
    cancel_passenger_ride,
    is_valid_transition,
)


def test_only_documented_state_transitions_are_allowed() -> None:
    assert is_valid_transition(RideStatus.REQUESTED, RideStatus.MATCHING)
    assert is_valid_transition(RideStatus.DRIVER_ARRIVED, RideStatus.IN_PROGRESS)
    assert is_valid_transition(RideStatus.IN_PROGRESS, RideStatus.COMPLETED)
    assert not is_valid_transition(RideStatus.REQUESTED, RideStatus.COMPLETED)
    assert not is_valid_transition(RideStatus.COMPLETED, RideStatus.CANCELLED)
    assert not is_valid_transition(RideStatus.UNMATCHED, RideStatus.ACCEPTED)


def test_passenger_cannot_cancel_in_progress_or_completed_rides() -> None:
    assert RideStatus.DRIVER_ARRIVED in PASSENGER_CANCELLABLE
    assert RideStatus.IN_PROGRESS not in PASSENGER_CANCELLABLE
    assert RideStatus.COMPLETED not in PASSENGER_CANCELLABLE
    assert RideStatus.UNMATCHED not in PASSENGER_CANCELLABLE


def test_driver_must_move_through_every_operational_state() -> None:
    assert is_valid_transition(RideStatus.ACCEPTED, RideStatus.DRIVER_EN_ROUTE)
    assert is_valid_transition(RideStatus.DRIVER_EN_ROUTE, RideStatus.DRIVER_ARRIVED)
    assert not is_valid_transition(RideStatus.ACCEPTED, RideStatus.DRIVER_ARRIVED)
    assert is_valid_transition(RideStatus.IN_PROGRESS, RideStatus.COMPLETED)


def test_driver_cancellation_is_limited_to_an_assigned_pre_start_ride() -> None:
    assert RideStatus.ACCEPTED in DRIVER_CANCELLABLE
    assert RideStatus.DRIVER_EN_ROUTE in DRIVER_CANCELLABLE
    assert RideStatus.DRIVER_ARRIVED in DRIVER_CANCELLABLE
    assert RideStatus.REQUESTED not in DRIVER_CANCELLABLE
    assert RideStatus.IN_PROGRESS not in DRIVER_CANCELLABLE


def test_cancellation_hint_is_enqueued_in_the_business_transaction() -> None:
    user_id = uuid4()
    ride = Ride(id=uuid4(), passenger_id=user_id, status=RideStatus.MATCHING)
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    enqueue = AsyncMock()

    with patch("taximobile_api.domains.rides.service.enqueue", new=enqueue):
        asyncio.run(cancel_passenger_ride(session, ride, user_id, "Plans changed"))

    assert ride.status == RideStatus.CANCELLED
    enqueue.assert_awaited_once_with(
        session,
        topic="ride.cancelled",
        payload={"ride_id": str(ride.id)},
    )
