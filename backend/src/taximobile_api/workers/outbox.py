"""Deliver transactional-outbox refresh hints through live and push transports."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taximobile_api.core.live_events import LiveEventPublisher
from taximobile_api.core.metrics import MetricsRegistry
from taximobile_api.core.notification_policy import (
    DeliveryChannel,
    notification_policy_for_topic,
)
from taximobile_api.domains.drivers.models import (
    CredentialVerificationStatus,
    DriverCredential,
    DriverProfile,
)
from taximobile_api.domains.driver_applications.models import DriverCityAuthorization
from taximobile_api.domains.notifications.models import DeviceToken
from taximobile_api.domains.outbox.processor import ClaimedOutboxEvent, OutboxProcessor
from taximobile_api.domains.rides.models import Ride, RideOffer, RideOfferStatus, RideStatus
from taximobile_api.domains.ride_communications.models import (
    RideCoordinationMessage,
)
from taximobile_api.domains.ride_communications.policy import (
    ACTIVE_COORDINATION_STATUSES,
    sender_role_for_code,
)
from taximobile_api.domains.ride_communications.schemas import (
    RideCoordinationSenderRole,
)
from taximobile_api.domains.scheduled_bookings.models import (
    ScheduledBooking,
    ScheduledBookingOffer,
    ScheduledBookingStatus,
    ScheduledOfferStatus,
)
from taximobile_api.integrations.push import InvalidPushRegistration, PushProvider
from taximobile_api.workers.runtime import run_polling_processor


class NotificationTransportUnavailable(RuntimeError):
    """At least one configured channel failed; retry the minimized hint safely."""


class WebSocketOutboxDelivery:
    """Reload current records before emitting a non-authoritative refresh hint."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        live_events: LiveEventPublisher,
        push_provider: PushProvider | None = None,
    ) -> None:
        self._sessions = session_factory
        self._live_events = live_events
        self._push_provider = push_provider

    async def deliver(self, event: ClaimedOutboxEvent) -> None:
        policy = notification_policy_for_topic(event.topic)
        if event.created_at <= datetime.now(UTC) - timedelta(
            seconds=policy.max_delivery_age_seconds
        ):
            return
        if event.topic == "ride.offer.created":
            await self._deliver_offer(event, policy.hint_type)
        elif event.topic == "ride.accepted":
            await self._deliver_acceptance(event, policy.hint_type)
        elif event.topic == "ride.cancelled":
            await self._deliver_cancellation(event, policy.hint_type)
        elif event.topic == "ride.matching.failed":
            await self._deliver_matching_failure(event, policy.hint_type)
        elif event.topic == "ride.coordination.message":
            await self._deliver_coordination_message(event, policy.hint_type)
        elif event.topic == "scheduled.offer.created":
            await self._deliver_scheduled_offer(event, policy.hint_type)
        elif event.topic == "scheduled.driver.committed":
            await self._deliver_scheduled_booking_status(
                event,
                policy.hint_type,
                {
                    ScheduledBookingStatus.DRIVER_COMMITTED,
                    ScheduledBookingStatus.DISPATCH_HANDOFF,
                    ScheduledBookingStatus.LIVE_RIDE_CREATED,
                },
            )
        elif event.topic == "scheduled.dispatch.started":
            await self._deliver_scheduled_booking_status(
                event,
                policy.hint_type,
                {
                    ScheduledBookingStatus.DISPATCH_HANDOFF,
                    ScheduledBookingStatus.LIVE_RIDE_CREATED,
                },
            )
        elif event.topic == "scheduled.fallback.matching":
            await self._deliver_scheduled_booking_status(
                event,
                policy.hint_type,
                {ScheduledBookingStatus.LIVE_RIDE_CREATED},
            )
        elif event.topic == "scheduled.unfulfilled":
            await self._deliver_scheduled_booking_status(
                event,
                policy.hint_type,
                {ScheduledBookingStatus.UNFULFILLED},
            )
        elif event.topic == "driver.credential.expiring":
            await self._deliver_credential_refresh(
                event,
                CredentialVerificationStatus.VERIFIED,
                policy.hint_type,
            )
        elif event.topic == "driver.city_authorization.changed":
            await self._deliver_city_authorization_refresh(event, policy.hint_type)
        elif event.topic == "driver.credential.expired":
            await self._deliver_credential_refresh(
                event,
                CredentialVerificationStatus.EXPIRED,
                policy.hint_type,
            )
        else:  # pragma: no cover - the closed registry and branches must evolve together.
            raise RuntimeError("Approved outbox policy has no delivery implementation.")

    async def _deliver_offer(self, event: ClaimedOutboxEvent, hint_type: str) -> None:
        offer_id = UUID(str(event.payload["offer_id"]))
        async with self._sessions() as session:
            offer = await session.get(RideOffer, offer_id)
            if offer is None or offer.status != RideOfferStatus.PENDING or offer.expires_at <= datetime.now(UTC):
                return
            ride = await session.get(Ride, offer.ride_id)
            profile = await session.get(DriverProfile, offer.driver_id)
            if ride is None or ride.status != RideStatus.MATCHING or profile is None:
                return
            await self._publish_refresh(
                profile.user_id, ride.id, hint_type, event,
                source_expires_at=offer.expires_at,
            )

    async def _deliver_acceptance(self, event: ClaimedOutboxEvent, hint_type: str) -> None:
        ride_id = UUID(str(event.payload["ride_id"]))
        async with self._sessions() as session:
            ride = await session.get(Ride, ride_id)
            if ride is None or ride.status not in {
                RideStatus.ACCEPTED,
                RideStatus.DRIVER_EN_ROUTE,
                RideStatus.DRIVER_ARRIVED,
                RideStatus.IN_PROGRESS,
            }:
                return
            await self._publish_refresh(ride.passenger_id, ride.id, hint_type, event)

    async def _deliver_cancellation(self, event: ClaimedOutboxEvent, hint_type: str) -> None:
        ride_id = UUID(str(event.payload["ride_id"]))
        async with self._sessions() as session:
            ride = await session.get(Ride, ride_id)
            if ride is None or ride.status != RideStatus.CANCELLED:
                return
            recipients: set[UUID] = set()
            if ride.cancelled_by_user_id != ride.passenger_id:
                recipients.add(ride.passenger_id)
            if ride.driver_id is not None:
                profile = await session.get(DriverProfile, ride.driver_id)
                if profile is not None and ride.cancelled_by_user_id != profile.user_id:
                    recipients.add(profile.user_id)
            for user_id in recipients:
                await self._publish_refresh(user_id, ride.id, hint_type, event)

    async def _deliver_matching_failure(self, event: ClaimedOutboxEvent, hint_type: str) -> None:
        ride_id = UUID(str(event.payload["ride_id"]))
        async with self._sessions() as session:
            ride = await session.get(Ride, ride_id)
            if ride is None or ride.status != RideStatus.UNMATCHED:
                return
            await self._publish_refresh(ride.passenger_id, ride.id, hint_type, event)

    async def _deliver_coordination_message(self, event: ClaimedOutboxEvent, hint_type: str) -> None:
        message_id = UUID(str(event.payload["message_id"]))
        async with self._sessions() as session:
            message = await session.get(RideCoordinationMessage, message_id)
            if message is None:
                return
            ride = await session.get(Ride, message.ride_id)
            now = datetime.now(UTC)
            if (
                ride is None
                or ride.status not in ACTIVE_COORDINATION_STATUSES
                or message.created_at < now - timedelta(minutes=5)
            ):
                return
            sender_role = sender_role_for_code(message.code)
            if sender_role == RideCoordinationSenderRole.DRIVER:
                recipient_user_id = ride.passenger_id
            else:
                if ride.driver_id is None:
                    return
                driver = await session.get(DriverProfile, ride.driver_id)
                if driver is None:
                    return
                recipient_user_id = driver.user_id
            await self._publish_refresh(
                recipient_user_id, ride.id, hint_type, event,
                source_expires_at=message.created_at + timedelta(minutes=5),
            )

    async def _deliver_scheduled_offer(
        self, event: ClaimedOutboxEvent, hint_type: str
    ) -> None:
        offer_id = UUID(str(event.payload["offer_id"]))
        async with self._sessions() as session:
            offer = await session.get(ScheduledBookingOffer, offer_id)
            if (
                offer is None
                or offer.status != ScheduledOfferStatus.PENDING
                or offer.expires_at <= datetime.now(UTC)
            ):
                return
            booking = await session.get(ScheduledBooking, offer.booking_id)
            if booking is None or booking.status != ScheduledBookingStatus.OFFERING:
                return
            profile = await session.get(DriverProfile, offer.driver_id)
            if profile is None:
                return
            await self._publish_refresh(
                profile.user_id, offer.id, hint_type, event,
                source_expires_at=offer.expires_at,
            )

    async def _deliver_scheduled_booking_status(
        self,
        event: ClaimedOutboxEvent,
        hint_type: str,
        allowed_statuses: set[ScheduledBookingStatus],
    ) -> None:
        booking_id = UUID(str(event.payload["booking_id"]))
        async with self._sessions() as session:
            booking = await session.get(ScheduledBooking, booking_id)
            if booking is None or booking.status not in allowed_statuses:
                return
            await self._publish_refresh(
                booking.passenger_id, booking.id, hint_type, event
            )

    async def _deliver_credential_refresh(
        self,
        event: ClaimedOutboxEvent,
        expected_status: CredentialVerificationStatus,
        event_type: str,
    ) -> None:
        credential_id = UUID(str(event.payload["credential_id"]))
        async with self._sessions() as session:
            credential = await session.get(DriverCredential, credential_id)
            if credential is None or credential.verification_status != expected_status:
                return
            profile = await session.get(DriverProfile, credential.driver_id)
            if profile is None:
                return
            # Persistent notification history is authoritative. FCM carries
            # only a minimized refresh hint for a background installation.
            await self._publish_refresh(
                profile.user_id, credential.id, event_type, event
            )

    async def _deliver_city_authorization_refresh(
        self, event: ClaimedOutboxEvent, event_type: str,
    ) -> None:
        authorization_id = UUID(str(event.payload["authorization_id"]))
        async with self._sessions() as session:
            authorization = await session.get(DriverCityAuthorization, authorization_id)
            if authorization is None:
                return
            profile = await session.get(DriverProfile, authorization.driver_id)
            if profile is None:
                return
            # The source record determines the recipient. The event contains no
            # user ID, status or reason and can only prompt an authoritative reload.
            await self._publish_refresh(
                profile.user_id, authorization.id, event_type, event
            )

    async def _publish_refresh(
        self,
        user_id: UUID,
        resource_id: UUID,
        event_type: str,
        event: ClaimedOutboxEvent,
        *,
        source_expires_at: datetime | None = None,
    ) -> None:
        policy = notification_policy_for_topic(event.topic)
        expires_at = event.created_at + timedelta(seconds=policy.max_delivery_age_seconds)
        if source_expires_at is not None:
            expires_at = min(expires_at, source_expires_at)
        if expires_at <= datetime.now(UTC):
            return
        channel_failed = False
        if DeliveryChannel.LIVE in policy.channels:
            try:
                await self._live_events.publish_ride_refresh(
                    user_id, resource_id, event_type
                )
            except Exception:
                # A live transport outage must not prevent the push fallback.
                # Cancellation still propagates (it is not an Exception).
                channel_failed = True
        if DeliveryChannel.PUSH in policy.channels:
            try:
                await self._push_refresh(user_id, resource_id, event_type, expires_at)
            except Exception:
                channel_failed = True
        if channel_failed:
            # The processor owns bounded retries/dead letters. Successful
            # channels may receive duplicates; hints never mutate domain state.
            raise NotificationTransportUnavailable("Notification channel delivery failed.")

    async def _push_refresh(
        self, user_id: UUID, resource_id: UUID, event_type: str, expires_at: datetime
    ) -> None:
        if self._push_provider is None:
            return
        async with self._sessions() as session:
            devices = list(
                await session.scalars(
                    select(DeviceToken).where(
                        DeviceToken.user_id == user_id,
                        DeviceToken.revoked_at.is_(None),
                    )
                )
            )
        device_failed = False
        for device in devices:
            if expires_at <= datetime.now(UTC):
                break
            try:
                await self._push_provider.send_refresh(
                    registration_id=device.token,
                    registration_kind=device.registration_kind.value,
                    event_type=event_type,
                    resource_id=str(resource_id),
                    expires_at=expires_at,
                )
            except InvalidPushRegistration:
                try:
                    await self._revoke_device(device.id)
                except Exception:
                    device_failed = True
            except Exception:
                # One broken registration must not starve healthy devices.
                # Preserve cancellation; report aggregate failure for retry.
                device_failed = True
        if device_failed:
            raise NotificationTransportUnavailable("Notification device delivery failed.")

    async def _revoke_device(self, device_id: UUID) -> None:
        async with self._sessions() as session:
            async with session.begin():
                await session.execute(
                    update(DeviceToken)
                    .where(DeviceToken.id == device_id, DeviceToken.revoked_at.is_(None))
                    .values(revoked_at=datetime.now(UTC))
                )


async def run_outbox_processor(
    processor: OutboxProcessor,
    poll_seconds: float,
    metrics: MetricsRegistry,
) -> None:
    """Deliver outbox events continuously with bounded failure telemetry."""
    await run_polling_processor(
        worker="outbox",
        processor=processor,
        poll_seconds=poll_seconds,
        metrics=metrics,
    )
