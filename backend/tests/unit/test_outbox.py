import asyncio
from uuid import uuid4

from taximobile_api.domains.drivers.models import (
    CredentialVerificationStatus,
    DriverCredential,
    DriverProfile,
)
from taximobile_api.domains.notifications.models import DeviceRegistrationKind, DeviceToken
from taximobile_api.domains.outbox.models import OutboxEvent
from taximobile_api.domains.outbox.processor import ClaimedOutboxEvent, failure_outcome, retry_delay_seconds
from taximobile_api.domains.rides.models import Ride, RideStatus
from taximobile_api.workers.outbox import WebSocketOutboxDelivery


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
        }
    ]
