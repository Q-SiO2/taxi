import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from taximobile_api.core.notification_policy import UnsupportedOutboxTopic
from taximobile_api.domains.drivers.models import (
    CredentialVerificationStatus,
    DriverCredential,
    DriverProfile,
)
from taximobile_api.domains.driver_applications.models import DriverCityAuthorization
from taximobile_api.domains.notifications.models import DeviceRegistrationKind, DeviceToken
from taximobile_api.domains.outbox.models import OutboxEvent
from taximobile_api.domains.ride_communications.models import (
    RideCoordinationCode,
    RideCoordinationMessage,
)
from taximobile_api.domains.outbox.processor import ClaimedOutboxEvent, failure_outcome, retry_delay_seconds
from taximobile_api.domains.rides.models import Ride, RideStatus
from taximobile_api.domains.scheduled_bookings.models import (
    ScheduledBooking,
    ScheduledBookingOffer,
    ScheduledBookingStatus,
    ScheduledOfferStatus,
)
from taximobile_api.workers.outbox import (
    NotificationTransportUnavailable,
    WebSocketOutboxDelivery,
)


def test_outbox_event_keeps_delivery_payload_as_non_authoritative_identifiers() -> None:
    event = OutboxEvent(topic="ride.offer.created", payload={"offer_id": "offer", "ride_id": "ride", "driver_id": "driver"})

    assert event.topic == "ride.offer.created"
    assert set(event.payload) == {"offer_id", "ride_id", "driver_id"}


def test_outbox_retry_delay_is_bounded_exponential_backoff() -> None:
    assert retry_delay_seconds(1) == 1
    assert retry_delay_seconds(4) == 8
    assert retry_delay_seconds(100) == 300


def test_outbox_failure_is_dead_lettered_at_configured_attempt_limit() -> None:
    assert failure_outcome(7, 8) == "DELIVERY_RETRY"
    assert failure_outcome(8, 8) == "DELIVERY_DEAD_LETTERED"
    assert failure_outcome(9, 8) == "DELIVERY_DEAD_LETTERED"


def test_driver_cancellation_refreshes_only_the_passenger() -> None:
    passenger_id = uuid4()
    driver_user_id = uuid4()
    driver_id = uuid4()
    ride = Ride(
        id=uuid4(),
        passenger_id=passenger_id,
        driver_id=driver_id,
        status=RideStatus.CANCELLED,
        cancelled_by_user_id=driver_user_id,
    )
    profile = DriverProfile(id=driver_id, user_id=driver_user_id, display_name="Driver")

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def get(self, model, identifier):
            if model is Ride and identifier == ride.id:
                return ride
            if model is DriverProfile and identifier == driver_id:
                return profile
            return None

    class Publisher:
        def __init__(self) -> None:
            self.hints = []

        async def publish_ride_refresh(self, user_id, ride_id, event_type):
            self.hints.append((user_id, ride_id, event_type))

    publisher = Publisher()
    delivery = WebSocketOutboxDelivery(lambda: Session(), publisher)
    event = ClaimedOutboxEvent(uuid4(), "ride.cancelled", {"ride_id": str(ride.id)})

    asyncio.run(delivery.deliver(event))

    assert publisher.hints == [(passenger_id, ride.id, "RIDE_CANCELLED")]


def test_matching_failure_refreshes_only_the_authoritative_passenger() -> None:
    passenger_id = uuid4()
    ride = Ride(id=uuid4(), passenger_id=passenger_id, status=RideStatus.UNMATCHED)

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def get(self, model, identifier):
            return ride if model is Ride and identifier == ride.id else None

    class Publisher:
        def __init__(self) -> None:
            self.hints = []

        async def publish_ride_refresh(self, user_id, ride_id, event_type):
            self.hints.append((user_id, ride_id, event_type))

    publisher = Publisher()
    delivery = WebSocketOutboxDelivery(lambda: Session(), publisher)
    event = ClaimedOutboxEvent(uuid4(), "ride.matching.failed", {"ride_id": str(ride.id)})

    asyncio.run(delivery.deliver(event))

    assert publisher.hints == [(passenger_id, ride.id, "RIDE_UNMATCHED")]


def test_passenger_coordination_refreshes_only_the_assigned_driver() -> None:
    passenger_id = uuid4()
    driver_user_id = uuid4()
    driver_id = uuid4()
    ride = Ride(
        id=uuid4(),
        passenger_id=passenger_id,
        driver_id=driver_id,
        status=RideStatus.DRIVER_EN_ROUTE,
    )
    profile = DriverProfile(id=driver_id, user_id=driver_user_id, display_name="Driver")
    message = RideCoordinationMessage(
        id=uuid4(),
        ride_id=ride.id,
        sender_user_id=passenger_id,
        code=RideCoordinationCode.PASSENGER_AT_PICKUP,
        created_at=datetime.now(UTC),
    )

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def get(self, model, identifier):
            if model is RideCoordinationMessage and identifier == message.id:
                return message
            if model is Ride and identifier == ride.id:
                return ride
            if model is DriverProfile and identifier == driver_id:
                return profile
            return None

    class Publisher:
        def __init__(self) -> None:
            self.hints = []

        async def publish_ride_refresh(self, user_id, ride_id, event_type):
            self.hints.append((user_id, ride_id, event_type))

    publisher = Publisher()
    delivery = WebSocketOutboxDelivery(lambda: Session(), publisher)
    event = ClaimedOutboxEvent(
        uuid4(),
        "ride.coordination.message",
        {"message_id": str(message.id)},
    )

    asyncio.run(delivery.deliver(event))

    assert publisher.hints == [
        (driver_user_id, ride.id, "RIDE_COORDINATION_MESSAGE")
    ]


def test_stale_coordination_hint_is_not_delivered() -> None:
    ride = Ride(
        id=uuid4(),
        passenger_id=uuid4(),
        driver_id=uuid4(),
        status=RideStatus.ACCEPTED,
    )
    message = RideCoordinationMessage(
        id=uuid4(),
        ride_id=ride.id,
        sender_user_id=ride.passenger_id,
        code=RideCoordinationCode.PASSENGER_NEEDS_MORE_TIME,
        created_at=datetime.now(UTC) - timedelta(minutes=6),
    )

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def get(self, model, identifier):
            if model is RideCoordinationMessage and identifier == message.id:
                return message
            if model is Ride and identifier == ride.id:
                return ride
            return None

    class Publisher:
        async def publish_ride_refresh(self, *_args):
            raise AssertionError("A stale coordination hint must not be delivered.")

    delivery = WebSocketOutboxDelivery(lambda: Session(), Publisher())
    event = ClaimedOutboxEvent(
        uuid4(),
        "ride.coordination.message",
        {"message_id": str(message.id)},
    )

    asyncio.run(delivery.deliver(event))


def test_credential_expiry_delivers_only_a_minimized_push_refresh_hint() -> None:
    profile = DriverProfile(id=uuid4(), user_id=uuid4(), display_name="Driver")
    credential = DriverCredential(
        id=uuid4(),
        driver_id=profile.id,
        credential_type="DRIVER_LICENSE",
        verification_status=CredentialVerificationStatus.EXPIRED,
    )
    device = DeviceToken(
        id=uuid4(),
        user_id=profile.user_id,
        registration_kind=DeviceRegistrationKind.FIREBASE_INSTALLATION_ID,
        token="installation-id",
    )

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def get(self, model, identifier):
            if model is DriverCredential and identifier == credential.id:
                return credential
            if model is DriverProfile and identifier == profile.id:
                return profile
            return None

        async def scalars(self, _statement):
            return [device]

    class Publisher:
        async def publish_ride_refresh(self, *_args):
            raise AssertionError("Credential events are not ride WebSocket events.")

    class PushProvider:
        def __init__(self) -> None:
            self.hints = []

        async def send_refresh(self, **payload):
            self.hints.append(payload)

    push = PushProvider()
    delivery = WebSocketOutboxDelivery(lambda: Session(), Publisher(), push)
    event = ClaimedOutboxEvent(
        uuid4(),
        "driver.credential.expired",
        {"credential_id": str(credential.id)},
    )

    asyncio.run(delivery.deliver(event))

    assert push.hints == [
        {
            "registration_id": "installation-id",
            "registration_kind": "FIREBASE_INSTALLATION_ID",
            "event_type": "DRIVER_CREDENTIAL_EXPIRED",
            "resource_id": str(credential.id),
            "expires_at": event.created_at + timedelta(days=7),
        }
    ]


def test_city_authorization_delivery_derives_recipient_and_sends_minimized_refresh() -> None:
    profile = DriverProfile(id=uuid4(), user_id=uuid4(), display_name="Driver")
    authorization = DriverCityAuthorization(
        id=uuid4(), driver_id=profile.id, city_id=uuid4(),
        application_id=uuid4(), valid_from=datetime.now(UTC),
    )
    device = DeviceToken(
        id=uuid4(), user_id=profile.user_id,
        registration_kind=DeviceRegistrationKind.FIREBASE_INSTALLATION_ID,
        token="installation-id",
    )

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def get(self, model, identifier):
            if model is DriverCityAuthorization and identifier == authorization.id:
                return authorization
            if model is DriverProfile and identifier == profile.id:
                return profile
            return None

        async def scalars(self, _statement):
            return [device]

    class Publisher:
        async def publish_ride_refresh(self, *_args):
            raise AssertionError("Authorization events are not ride WebSocket events.")

    class PushProvider:
        def __init__(self) -> None:
            self.hints = []

        async def send_refresh(self, **payload):
            self.hints.append(payload)

    push = PushProvider()
    delivery = WebSocketOutboxDelivery(lambda: Session(), Publisher(), push)
    event = ClaimedOutboxEvent(
        uuid4(), "driver.city_authorization.changed",
        {"authorization_id": str(authorization.id), "user_id": str(uuid4())},
    )

    asyncio.run(delivery.deliver(event))

    assert push.hints == [{
        "registration_id": "installation-id",
        "registration_kind": "FIREBASE_INSTALLATION_ID",
        "event_type": "DRIVER_CITY_AUTHORIZATION_CHANGED",
        "resource_id": str(authorization.id),
        "expires_at": event.created_at + timedelta(days=7),
    }]


def test_missing_city_authorization_is_consumed_without_push() -> None:
    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def get(self, *_):
            return None

    class PushProvider:
        async def send_refresh(self, **_payload):
            raise AssertionError("Missing source must not publish.")

    delivery = WebSocketOutboxDelivery(lambda: Session(), object(), PushProvider())
    asyncio.run(delivery.deliver(ClaimedOutboxEvent(
        uuid4(), "driver.city_authorization.changed",
        {"authorization_id": str(uuid4())},
    )))


def test_expired_event_is_consumed_without_contacting_any_delivery_boundary() -> None:
    class SessionFactory:
        def __call__(self):
            raise AssertionError("Expired event must not open a database session.")

    class Publisher:
        async def publish_ride_refresh(self, *_args):
            raise AssertionError("Expired event must not publish.")

    delivery = WebSocketOutboxDelivery(SessionFactory(), Publisher())
    event = ClaimedOutboxEvent(
        uuid4(),
        "ride.coordination.message",
        {"message_id": str(uuid4())},
        datetime.now(UTC) - timedelta(minutes=6),
    )

    asyncio.run(delivery.deliver(event))


def test_unclassified_event_fails_for_bounded_retry_and_dead_letter_visibility() -> None:
    delivery = WebSocketOutboxDelivery(lambda: None, object())
    event = ClaimedOutboxEvent(uuid4(), "future.unreviewed", {})

    with pytest.raises(UnsupportedOutboxTopic):
        asyncio.run(delivery.deliver(event))


@pytest.mark.parametrize(
    "booking_status",
    [ScheduledBookingStatus.OFFERING, ScheduledBookingStatus.CANCELLED, None],
)
def test_pending_scheduled_offer_pushes_only_for_an_offering_booking(booking_status) -> None:
    driver_user_id = uuid4()
    driver_id = uuid4()
    offer = ScheduledBookingOffer(
        id=uuid4(),
        booking_id=uuid4(),
        driver_id=driver_id,
        status=ScheduledOfferStatus.PENDING,
        offered_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        conflict_policy_snapshot={},
    )
    profile = DriverProfile(id=driver_id, user_id=driver_user_id, display_name="Driver")
    booking = (
        ScheduledBooking(id=offer.booking_id, status=booking_status)
        if booking_status is not None
        else None
    )

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def get(self, model, identifier):
            if model is ScheduledBookingOffer and identifier == offer.id:
                return offer
            if model is ScheduledBooking and identifier == offer.booking_id:
                return booking
            if model is DriverProfile and identifier == driver_id:
                return profile
            return None

    class Publisher:
        async def publish_ride_refresh(self, *_args):
            raise AssertionError("Scheduled push policy must not use ride WebSocket hints.")

    class Delivery(WebSocketOutboxDelivery):
        def __init__(self):
            super().__init__(lambda: Session(), Publisher())
            self.hints = []

        async def _push_refresh(self, user_id, resource_id, event_type, expires_at):
            assert expires_at == offer.expires_at
            self.hints.append((user_id, resource_id, event_type))

    delivery = Delivery()
    event = ClaimedOutboxEvent(
        uuid4(), "scheduled.offer.created", {"offer_id": str(offer.id)}
    )

    asyncio.run(delivery.deliver(event))

    assert delivery.hints == (
        [(driver_user_id, offer.id, "SCHEDULED_OFFER")]
        if booking_status == ScheduledBookingStatus.OFFERING
        else []
    )


@pytest.mark.parametrize("failed_channel", ["live", "push", "both"])
def test_channel_failure_still_attempts_both_transports_and_requests_retry(failed_channel) -> None:
    calls = []

    class Publisher:
        async def publish_ride_refresh(self, *_args):
            calls.append("live")
            if failed_channel in {"live", "both"}:
                raise RuntimeError("Private provider failure details")

    class Delivery(WebSocketOutboxDelivery):
        async def _push_refresh(self, *_args):
            calls.append("push")
            if failed_channel in {"push", "both"}:
                raise RuntimeError("Private push failure details")

    delivery = Delivery(lambda: None, Publisher())
    with pytest.raises(NotificationTransportUnavailable) as error:
        asyncio.run(delivery._publish_refresh(
            uuid4(), uuid4(), "RIDE_CANCELLED",
            ClaimedOutboxEvent(uuid4(), "ride.cancelled", {}),
        ))

    assert calls == ["live", "push"]
    assert str(error.value) == "Notification channel delivery failed."


def test_channel_delivery_preserves_worker_cancellation() -> None:
    class Publisher:
        async def publish_ride_refresh(self, *_args):
            raise asyncio.CancelledError()

    class Delivery(WebSocketOutboxDelivery):
        async def _push_refresh(self, *_args):
            raise AssertionError("Cancelled workers must not continue delivering.")

    delivery = Delivery(lambda: None, Publisher())
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(delivery._publish_refresh(
            uuid4(), uuid4(), "RIDE_CANCELLED",
            ClaimedOutboxEvent(uuid4(), "ride.cancelled", {}),
        ))


def test_unfulfilled_scheduled_booking_pushes_only_the_passenger() -> None:
    passenger_id = uuid4()
    booking = ScheduledBooking(
        id=uuid4(),
        passenger_id=passenger_id,
        status=ScheduledBookingStatus.UNFULFILLED,
    )

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def get(self, model, identifier):
            if model is ScheduledBooking and identifier == booking.id:
                return booking
            return None

    class Publisher:
        async def publish_ride_refresh(self, *_args):
            raise AssertionError("Scheduled push policy must not use ride WebSocket hints.")

    class Delivery(WebSocketOutboxDelivery):
        def __init__(self):
            super().__init__(lambda: Session(), Publisher())
            self.hints = []

        async def _push_refresh(self, user_id, resource_id, event_type, expires_at):
            self.hints.append((user_id, resource_id, event_type))

    delivery = Delivery()
    event = ClaimedOutboxEvent(
        uuid4(), "scheduled.unfulfilled", {"booking_id": str(booking.id)}
    )

    asyncio.run(delivery.deliver(event))

    assert delivery.hints == [
        (passenger_id, booking.id, "SCHEDULED_UNFULFILLED")
    ]
