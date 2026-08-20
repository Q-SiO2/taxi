"""Deliver transactional-outbox refresh hints through live and push transports."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taximobile_api.core.live_events import LiveEventPublisher
from taximobile_api.core.metrics import MetricsRegistry
from taximobile_api.domains.drivers.models import (
    CredentialVerificationStatus,
    DriverCredential,
    DriverProfile,
)
from taximobile_api.domains.notifications.models import DeviceToken
from taximobile_api.domains.outbox.processor import ClaimedOutboxEvent, OutboxProcessor
from taximobile_api.domains.rides.models import Ride, RideOffer, RideOfferStatus, RideStatus
from taximobile_api.integrations.push import InvalidPushRegistration, PushProvider
from taximobile_api.workers.runtime import run_polling_processor


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
        if event.topic == "ride.offer.created":
            await self._deliver_offer(event)
        elif event.topic == "ride.accepted":
            await self._deliver_acceptance(event)
        elif event.topic == "ride.cancelled":
            await self._deliver_cancellation(event)
        elif event.topic == "ride.matching.failed":
            await self._deliver_matching_failure(event)
        elif event.topic == "driver.credential.expiring":
            await self._deliver_credential_refresh(
                event,
                CredentialVerificationStatus.VERIFIED,
                "DRIVER_CREDENTIAL_EXPIRING",
            )
        elif event.topic == "driver.credential.expired":
            await self._deliver_credential_refresh(
                event,
                CredentialVerificationStatus.EXPIRED,
                "DRIVER_CREDENTIAL_EXPIRED",
            )
        # Unknown topics are safely consumed. They remain durable audit records,
        # but cannot turn into an unbounded retry storm after a future rollout.

    async def _deliver_offer(self, event: ClaimedOutboxEvent) -> None:
        offer_id = UUID(str(event.payload["offer_id"]))
        async with self._sessions() as session:
            offer = await session.get(RideOffer, offer_id)
            if offer is None or offer.status != RideOfferStatus.PENDING or offer.expires_at <= datetime.now(UTC):
                return
            ride = await session.get(Ride, offer.ride_id)
            profile = await session.get(DriverProfile, offer.driver_id)
            if ride is None or ride.status != RideStatus.MATCHING or profile is None:
                return
            await self._live_events.publish_ride_refresh(profile.user_id, ride.id, "RIDE_OFFER_AVAILABLE")
            await self._push_refresh(profile.user_id, ride.id, "RIDE_OFFER_AVAILABLE")

    async def _deliver_acceptance(self, event: ClaimedOutboxEvent) -> None:
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
            await self._live_events.publish_ride_refresh(ride.passenger_id, ride.id, "DRIVER_ASSIGNED")
            await self._push_refresh(ride.passenger_id, ride.id, "DRIVER_ASSIGNED")

    async def _deliver_cancellation(self, event: ClaimedOutboxEvent) -> None:
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
                await self._live_events.publish_ride_refresh(user_id, ride.id, "RIDE_CANCELLED")
                await self._push_refresh(user_id, ride.id, "RIDE_CANCELLED")

    async def _deliver_matching_failure(self, event: ClaimedOutboxEvent) -> None:
        ride_id = UUID(str(event.payload["ride_id"]))
        async with self._sessions() as session:
            ride = await session.get(Ride, ride_id)
            if ride is None or ride.status != RideStatus.UNMATCHED:
                return
            await self._live_events.publish_ride_refresh(ride.passenger_id, ride.id, "RIDE_UNMATCHED")
            await self._push_refresh(ride.passenger_id, ride.id, "RIDE_UNMATCHED")

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
            await self._push_refresh(profile.user_id, credential.id, event_type)

    async def _push_refresh(self, user_id: UUID, resource_id: UUID, event_type: str) -> None:
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
        for device in devices:
            try:
                await self._push_provider.send_refresh(
                    registration_id=device.token,
                    registration_kind=device.registration_kind.value,
                    event_type=event_type,
                    resource_id=str(resource_id),
                )
            except InvalidPushRegistration:
                await self._revoke_device(device.id)

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
