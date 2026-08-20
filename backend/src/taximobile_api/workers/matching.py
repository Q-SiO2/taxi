"""Lease expired offers and continue deterministic sequential matching."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taximobile_api.core.config import Settings
from taximobile_api.core.metrics import MetricsRegistry
from taximobile_api.domains.drivers.models import AvailabilityStatus, DriverProfile
from taximobile_api.domains.matching.service import dispatch_ride
from taximobile_api.domains.rides.models import Ride, RideEvent, RideEventType, RideOffer, RideOfferStatus, RideStatus
from taximobile_api.workers.runtime import run_polling_processor


class MatchingProcessor:
    """Atomically expires due offers and advances each still-matching ride.

    `SKIP LOCKED` lets multiple API replicas run this processor without both
    handling the same offer. Ride and driver locks in the matching services are
    still the authority for the resulting state transitions.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
        *,
        batch_size: int = 20,
    ) -> None:
        self._sessions = session_factory
        self._settings = settings
        self._batch_size = batch_size

    async def process_once(self) -> int:
        now = datetime.now(UTC)
        async with self._sessions() as session:
            async with session.begin():
                offers = list(
                    await session.scalars(
                        select(RideOffer)
                        .where(
                            RideOffer.status == RideOfferStatus.PENDING,
                            RideOffer.expires_at <= now,
                        )
                        .order_by(RideOffer.expires_at, RideOffer.id)
                        .limit(self._batch_size)
                        .with_for_update(skip_locked=True)
                    )
                )
                ride_ids = []
                for offer in offers:
                    offer.status = RideOfferStatus.EXPIRED
                    offer.responded_at = now
                    profile = await session.scalar(
                        select(DriverProfile)
                        .where(DriverProfile.id == offer.driver_id)
                        .with_for_update()
                    )
                    if profile is not None and profile.availability_status == AvailabilityStatus.OFFERED_RIDE:
                        # Expiry is not a new waiting period and must not erase
                        # the driver's accumulated idle-time consideration.
                        profile.availability_status = AvailabilityStatus.AVAILABLE
                        if profile.available_since is None:
                            profile.available_since = now
                    ride = await session.scalar(select(Ride).where(Ride.id == offer.ride_id).with_for_update())
                    if ride is not None and ride.status == RideStatus.MATCHING:
                        session.add(
                            RideEvent(
                                ride_id=ride.id,
                                event_type=RideEventType.OFFER_EXPIRED,
                                previous_status=RideStatus.MATCHING,
                                new_status=RideStatus.MATCHING,
                            )
                        )
                        ride_ids.append(ride.id)
                await session.flush()
                for ride_id in dict.fromkeys(ride_ids):
                    await dispatch_ride(session, ride_id, self._settings)
                return len(offers)


async def run_matching_processor(
    processor: MatchingProcessor,
    poll_seconds: float,
    metrics: MetricsRegistry,
) -> None:
    """Expire offers continuously with bounded failure telemetry."""
    await run_polling_processor(
        worker="matching",
        processor=processor,
        poll_seconds=poll_seconds,
        metrics=metrics,
    )
