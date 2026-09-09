"""Lease expired offers and continue deterministic sequential matching."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taximobile_api.core.config import Settings
from taximobile_api.core.metrics import MetricsRegistry
from taximobile_api.domains.drivers.models import AvailabilityStatus
from taximobile_api.domains.matching.service import dispatch_ride
from taximobile_api.domains.rides.models import Ride, RideEvent, RideEventType, RideOffer, RideOfferStatus, RideStatus
from taximobile_api.domains.rides.locking import lock_driver
from taximobile_api.workers.runtime import run_polling_processor


class MatchingProcessor:
    """Atomically expires due offers and advances each still-matching ride.

    `SKIP LOCKED` lets multiple worker replicas run this processor without both
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
                rides = list(
                    await session.scalars(
                        select(Ride)
                        .where(or_(
                            select(RideOffer.id).where(
                                RideOffer.ride_id == Ride.id,
                                RideOffer.status == RideOfferStatus.PENDING,
                                RideOffer.expires_at <= now,
                            ).exists(),
                            and_(
                                Ride.status == RideStatus.MATCHING,
                                ~select(RideOffer.id).where(
                                    RideOffer.ride_id == Ride.id,
                                    RideOffer.status == RideOfferStatus.PENDING,
                                ).exists(),
                            ),
                        ))
                        .order_by(Ride.created_at, Ride.id)
                        .limit(self._batch_size)
                        .with_for_update(skip_locked=True)
                        .execution_options(populate_existing=True)
                    )
                )
                processed = 0
                for ride in rides:
                    # Claim the aggregate before its offers: acceptance and
                    # cancellation use the same order. Recheck due state after
                    # acquiring the lock instead of trusting discovery results.
                    offers = list(await session.scalars(select(RideOffer).where(
                        RideOffer.ride_id == ride.id,
                        RideOffer.status == RideOfferStatus.PENDING,
                        RideOffer.expires_at <= now,
                    ).order_by(RideOffer.id).with_for_update()
                        .execution_options(populate_existing=True)))
                    for offer in offers:
                        profile = await lock_driver(session, offer.driver_id)
                        offer.status = RideOfferStatus.EXPIRED
                        offer.responded_at = datetime.now(UTC)
                        if profile is not None and profile.availability_status == AvailabilityStatus.OFFERED_RIDE:
                            # Preserve accumulated idle time, including across
                            # a wait behind an offline command.
                            profile.availability_status = AvailabilityStatus.AVAILABLE
                            if profile.available_since is None:
                                profile.available_since = offer.responded_at
                        if ride.status == RideStatus.MATCHING:
                            session.add(RideEvent(
                                ride_id=ride.id, event_type=RideEventType.OFFER_EXPIRED,
                                previous_status=RideStatus.MATCHING, new_status=RideStatus.MATCHING,
                            ))
                    processed += len(offers) or int(ride.status == RideStatus.MATCHING)
                    await session.flush()
                    if ride.status == RideStatus.MATCHING:
                        await dispatch_ride(session, ride.id, self._settings)
                return processed


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
