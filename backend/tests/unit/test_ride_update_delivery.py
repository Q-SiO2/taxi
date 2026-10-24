"""Committed lifecycle catch-up uses minimal, current-owner-addressed hints."""
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from taximobile_api.domains.drivers.models import DriverProfile
from taximobile_api.domains.notifications.models import Notification
from taximobile_api.domains.outbox.models import OutboxEvent
from taximobile_api.domains.outbox.processor import ClaimedOutboxEvent
from taximobile_api.domains.rides.models import Ride, RideStatus
from taximobile_api.domains.rides import service
from taximobile_api.domains.payments import router as payments
from taximobile_api.domains.payments.models import Payment, PaymentMethod, PaymentStatus
from taximobile_api.domains.idempotency.service import IdempotentReplay
from taximobile_api.workers.outbox import WebSocketOutboxDelivery


@pytest.mark.asyncio
async def test_update_producer_records_only_generic_owner_inbox_and_ride_id():
    ride = Ride(id=uuid4(), passenger_id=uuid4(), driver_id=uuid4(), status=RideStatus.IN_PROGRESS)
    session = AsyncMock()
    session.add = MagicMock()
    await service.record_ride_update(session, ride)
    records = [call.args[0] for call in session.add.call_args_list]
    inbox = next(row for row in records if isinstance(row, Notification))
    event = next(row for row in records if isinstance(row, OutboxEvent))
    assert inbox.user_id == ride.passenger_id
    assert inbox.type == "RIDE_UPDATED"
    assert inbox.data == {"ride_id": str(ride.id)}
    assert event.topic == "ride.updated" and event.payload == inbox.data
    assert "status" not in event.payload and "latitude" not in event.payload


@pytest.mark.asyncio
@pytest.mark.parametrize("before,target", [
    (RideStatus.ACCEPTED, RideStatus.DRIVER_EN_ROUTE),
    (RideStatus.DRIVER_EN_ROUTE, RideStatus.DRIVER_ARRIVED),
    (RideStatus.DRIVER_ARRIVED, RideStatus.IN_PROGRESS),
])
async def test_each_valid_driver_transition_records_catchup(before, target):
    profile = DriverProfile(id=uuid4(), user_id=uuid4())
    ride = Ride(id=uuid4(), passenger_id=uuid4(), driver_id=profile.id, status=before)
    session = AsyncMock()
    session.add = MagicMock()
    with patch.object(service, "assigned_driver_ride", AsyncMock(return_value=ride)), \
         patch.object(service, "lock_driver", AsyncMock(return_value=profile)), \
         patch.object(service, "record_ride_update", AsyncMock()) as record:
        await service.transition_assigned_ride(session, ride, profile, target, profile.user_id)
        record.assert_awaited_once_with(session, ride)
    assert ride.status == target


@pytest.mark.asyncio
async def test_invalid_transition_does_not_record_update():
    profile = DriverProfile(id=uuid4(), user_id=uuid4())
    ride = Ride(id=uuid4(), passenger_id=uuid4(), driver_id=profile.id, status=RideStatus.COMPLETED)
    session = AsyncMock()
    with patch.object(service, "assigned_driver_ride", AsyncMock(return_value=ride)), \
         patch.object(service, "lock_driver", AsyncMock(return_value=profile)), \
         patch.object(service, "record_ride_update", AsyncMock()) as record:
        with pytest.raises(service.InvalidRideTransition):
            await service.transition_assigned_ride(session, ride, profile, RideStatus.DRIVER_ARRIVED, profile.user_id)
        record.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("current", [RideStatus.DRIVER_ARRIVED, RideStatus.IN_PROGRESS, RideStatus.COMPLETED, RideStatus.CANCELLED])
async def test_delayed_update_uses_current_owner_not_payload_recipient(current):
    ride = Ride(id=uuid4(), passenger_id=uuid4(), driver_id=uuid4(), status=current)
    session = AsyncMock()
    session.get.return_value = ride
    sessions = MagicMock()
    sessions.return_value.__aenter__ = AsyncMock(return_value=session)
    sessions.return_value.__aexit__ = AsyncMock(return_value=None)
    publisher = AsyncMock()
    event = ClaimedOutboxEvent(id=uuid4(), topic="ride.updated",
        payload={"ride_id": str(ride.id), "passenger_id": str(uuid4()), "status": "COMPLETED"},
        created_at=datetime.now(UTC))
    await WebSocketOutboxDelivery(sessions, publisher).deliver(event)
    publisher.publish_ride_refresh.assert_awaited_once_with(ride.passenger_id, ride.id, "RIDE_UPDATED")


@pytest.mark.asyncio
@pytest.mark.parametrize("current,assigned", [(RideStatus.MATCHING, True), (RideStatus.UNMATCHED, False), (RideStatus.COMPLETED, False)])
async def test_unassigned_or_unrelated_state_is_not_delivered(current, assigned):
    ride = Ride(id=uuid4(), passenger_id=uuid4(), driver_id=uuid4() if assigned else None, status=current)
    session = AsyncMock()
    session.get.return_value = ride
    sessions = MagicMock()
    sessions.return_value.__aenter__ = AsyncMock(return_value=session)
    sessions.return_value.__aexit__ = AsyncMock(return_value=None)
    publisher = AsyncMock()
    event = ClaimedOutboxEvent(id=uuid4(), topic="ride.updated", payload={"ride_id": str(ride.id)},
        created_at=datetime.now(UTC))
    await WebSocketOutboxDelivery(sessions, publisher).deliver(event)
    publisher.publish_ride_refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_expired_update_does_not_open_business_data_boundary():
    sessions = MagicMock()
    publisher = AsyncMock()
    event = ClaimedOutboxEvent(id=uuid4(), topic="ride.updated", payload={"ride_id": str(uuid4())},
        created_at=datetime.now(UTC)-timedelta(hours=3))
    await WebSocketOutboxDelivery(sessions, publisher).deliver(event)
    sessions.assert_not_called()
    publisher.publish_ride_refresh.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("payment_status", [PaymentStatus.PENDING, PaymentStatus.COMPLETED])
async def test_cash_only_notifies_on_first_actual_settlement(payment_status):
    profile = DriverProfile(id=uuid4(), user_id=uuid4())
    ride = Ride(id=uuid4(), passenger_id=uuid4(), driver_id=profile.id, status=RideStatus.COMPLETED)
    payment = Payment(id=uuid4(), ride_id=ride.id, amount=Decimal('35'), currency='MAD', method=PaymentMethod.CASH, status=payment_status)
    session = AsyncMock()
    session.begin = MagicMock()
    session.begin.return_value.__aenter__ = AsyncMock()
    session.begin.return_value.__aexit__ = AsyncMock(return_value=None)
    session.scalar.side_effect = [ride, payment, object()]
    with patch.object(payments, 'begin_command', AsyncMock(return_value=object())), \
         patch.object(payments, 'finish_command', AsyncMock()), \
         patch.object(payments, 'driver_for_user', AsyncMock(return_value=profile)), \
         patch.object(payments, 'record_ride_update', AsyncMock()) as record:
        response = await payments.settle_cash(ride.id, 'synthetic-idempotency-key', SimpleNamespace(user_id=profile.user_id), session)
        assert response.status == 'COMPLETED'
        if payment_status == PaymentStatus.PENDING:
            record.assert_awaited_once_with(session, ride)
        else:
            record.assert_not_awaited()


@pytest.mark.asyncio
async def test_same_key_cash_replay_does_not_notify_or_load_ride():
    session = AsyncMock()
    session.begin = MagicMock()
    session.begin.return_value.__aenter__ = AsyncMock()
    session.begin.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch.object(payments, 'begin_command', AsyncMock(return_value=IdempotentReplay(200, {'status':'COMPLETED'}))), \
         patch.object(payments, 'record_ride_update', AsyncMock()) as record:
        await payments.settle_cash(uuid4(), 'synthetic-idempotency-key', SimpleNamespace(user_id=uuid4()), session)
        session.scalar.assert_not_awaited()
        record.assert_not_awaited()


@pytest.mark.asyncio
async def test_completion_records_update_after_final_fare_and_pending_payment():
    profile = DriverProfile(id=uuid4(), user_id=uuid4())
    ride = Ride(id=uuid4(), passenger_id=uuid4(), driver_id=profile.id, status=RideStatus.IN_PROGRESS,
        quoted_pricing_rule_id=uuid4(), quoted_amount=Decimal('35'), quoted_currency='MAD', payment_method=PaymentMethod.CASH)
    session = AsyncMock()
    session.add = MagicMock()
    session.get.side_effect = [object(), None]
    fare = SimpleNamespace(total_amount=Decimal('35'), currency='MAD')
    with patch.object(service, 'assigned_driver_ride', AsyncMock(return_value=ride)), \
         patch.object(service, 'lock_driver', AsyncMock(return_value=profile)), \
         patch.object(service, 'finalize_fixed_fare_for_rule', AsyncMock(return_value=fare)), \
         patch.object(service, 'create_pending_payment', MagicMock()) as create_payment, \
         patch.object(service, 'record_ride_update', AsyncMock()) as record:
        await service.complete_assigned_ride(session, ride, profile, profile.user_id, 33.5899, -7.6039)
        create_payment.assert_called_once()
        record.assert_awaited_once_with(session, ride)
    assert ride.status == RideStatus.COMPLETED
