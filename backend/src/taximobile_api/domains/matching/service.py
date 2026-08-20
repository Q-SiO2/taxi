"""Eligibility-first, deterministic and fairness-aware ranked dispatch."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.core.config import Settings
from taximobile_api.domains.drivers.models import (
    AvailabilityStatus,
    DriverAccountStatus,
    DriverLocation,
    DriverProfile,
    Vehicle,
    VehicleStatus,
    VehicleVerificationStatus,
    VerificationStatus,
)
from taximobile_api.domains.drivers.service import invalid_driver_credentials
from taximobile_api.domains.matching.scoring import CandidateSignals, MatchingPolicy, rank_candidates
from taximobile_api.domains.notifications.service import notify
from taximobile_api.domains.outbox.service import enqueue
from taximobile_api.domains.rides.models import (
    Ride,
    RideEvent,
    RideEventType,
    RideOffer,
    RideOfferStatus,
    RideStatus,
)


ACTIVE_RIDE_STATUSES = {
    RideStatus.ACCEPTED,
    RideStatus.DRIVER_EN_ROUTE,
    RideStatus.DRIVER_ARRIVED,
    RideStatus.IN_PROGRESS,
}


def matching_policy(settings: Settings) -> MatchingPolicy:
    return MatchingPolicy(
        radius_meters=settings.matching_radius_meters,
        idle_cap_seconds=settings.matching_idle_cap_seconds,
        assumed_pickup_speed_mps=settings.matching_assumed_pickup_speed_mps,
        proximity_weight=settings.matching_proximity_weight,
        idle_weight=settings.matching_idle_weight,
        fairness_weight=settings.matching_fairness_weight,
        algorithm_version=settings.matching_algorithm_version,
    )


async def dispatch_ride(database_session: AsyncSession, ride_id, settings: Settings) -> RideOffer | None:
    """Offer a locked matching ride to its highest-ranked untried candidate.

    One active offer is used in the MVP. Declined and expired drivers are
    excluded for this ride, so each subsequent invocation advances through the
    bounded candidate set instead of repeatedly selecting the same driver.
    """
    now = datetime.now(UTC)
    ride = await database_session.scalar(select(Ride).where(Ride.id == ride_id).with_for_update())
    if ride is None or ride.status in {
        RideStatus.CANCELLED,
        RideStatus.COMPLETED,
        RideStatus.UNMATCHED,
        RideStatus.ACCEPTED,
    }:
        return None
    if ride.status == RideStatus.REQUESTED:
        ride.status = RideStatus.MATCHING
        database_session.add(
            RideEvent(
                ride_id=ride.id,
                event_type=RideEventType.STATUS_CHANGED,
                previous_status=RideStatus.REQUESTED,
                new_status=RideStatus.MATCHING,
            )
        )
    pending_offer = await database_session.scalar(
        select(RideOffer.id).where(
            RideOffer.ride_id == ride.id,
            RideOffer.status == RideOfferStatus.PENDING,
            RideOffer.expires_at > now,
        )
    )
    if pending_offer is not None:
        return None
    created_at = ride.created_at
    if created_at is not None:
        created_at = created_at.replace(tzinfo=UTC) if created_at.tzinfo is None else created_at.astimezone(UTC)
        if now >= created_at + timedelta(seconds=settings.matching_timeout_seconds):
            await mark_ride_unmatched(
                database_session,
                ride,
                reason="The configured matching time limit elapsed.",
            )
            return None

    latest_location_id = (
        select(DriverLocation.id)
        .where(DriverLocation.driver_id == DriverProfile.id)
        .order_by(DriverLocation.observed_at.desc(), DriverLocation.id.desc())
        .limit(1)
        .correlate(DriverProfile)
        .scalar_subquery()
    )
    distance_meters = func.ST_Distance(DriverLocation.point, ride.pickup_point).label("distance_meters")
    recent_assignments = (
        select(func.count(Ride.id))
        .where(
            Ride.driver_id == DriverProfile.id,
            Ride.accepted_at >= now - timedelta(hours=settings.matching_fairness_lookback_hours),
        )
        .correlate(DriverProfile)
        .scalar_subquery()
        .label("recent_assignment_count")
    )
    has_active_ride = exists(
        select(Ride.id).where(
            Ride.driver_id == DriverProfile.id,
            Ride.status.in_(ACTIVE_RIDE_STATUSES),
        )
    )
    already_considered = exists(
        select(RideOffer.id).where(
            RideOffer.ride_id == ride.id,
            RideOffer.driver_id == DriverProfile.id,
        )
    )
    candidate_rows = (
        await database_session.execute(
            select(DriverProfile, distance_meters, recent_assignments)
            .join(Vehicle, Vehicle.id == DriverProfile.active_vehicle_id)
            .join(DriverLocation, DriverLocation.id == latest_location_id)
            .where(
                DriverProfile.account_status == DriverAccountStatus.ACTIVE,
                DriverProfile.verification_status == VerificationStatus.APPROVED,
                DriverProfile.availability_status == AvailabilityStatus.AVAILABLE,
                Vehicle.status == VehicleStatus.ACTIVE,
                Vehicle.verification_status == VehicleVerificationStatus.VERIFIED,
                ~invalid_driver_credentials(DriverProfile.id, now),
                DriverLocation.observed_at >= now
                - timedelta(seconds=settings.matching_location_freshness_seconds),
                func.ST_DWithin(DriverLocation.point, ride.pickup_point, settings.matching_radius_meters),
                ~has_active_ride,
                ~already_considered,
            )
            # Bound the scoring set geographically before applying the policy.
            .order_by(distance_meters, DriverProfile.id)
            .limit(settings.matching_candidate_limit)
            .with_for_update(of=DriverProfile, skip_locked=True)
        )
    ).all()
    profiles = {profile.id: profile for profile, _, _ in candidate_rows}
    ranked = rank_candidates(
        [
            CandidateSignals(
                driver_id=profile.id,
                distance_meters=float(distance),
                available_since=profile.available_since,
                recent_assignment_count=int(assignment_count),
            )
            for profile, distance, assignment_count in candidate_rows
        ],
        now=now,
        policy=matching_policy(settings),
    )
    if not ranked:
        await mark_ride_unmatched(database_session, ride)
        return None

    selected = ranked[0]
    candidate = profiles[selected.driver_id]
    candidate.availability_status = AvailabilityStatus.OFFERED_RIDE
    offer = RideOffer(
        ride_id=ride.id,
        driver_id=candidate.id,
        expires_at=now + timedelta(seconds=settings.ride_offer_seconds),
        estimated_pickup_distance_meters=selected.distance_meters,
        estimated_pickup_time_seconds=selected.estimated_pickup_time_seconds,
        idle_seconds_at_offer=selected.idle_seconds,
        recent_assignment_count=selected.recent_assignment_count,
        proximity_score=selected.proximity_score,
        idle_score=selected.idle_score,
        fairness_score=selected.fairness_score,
        ranking_score=selected.ranking_score,
        matching_algorithm_version=settings.matching_algorithm_version,
    )
    database_session.add(offer)
    await database_session.flush()
    database_session.add(
        RideEvent(
            ride_id=ride.id,
            event_type=RideEventType.OFFER_CREATED,
            previous_status=RideStatus.MATCHING,
            new_status=RideStatus.MATCHING,
            reason=f"algorithm={settings.matching_algorithm_version}",
        )
    )
    await enqueue(
        database_session,
        topic="ride.offer.created",
        payload={"offer_id": str(offer.id), "ride_id": str(ride.id), "driver_id": str(candidate.id)},
    )
    await notify(
        database_session,
        user_id=candidate.user_id,
        notification_type="RIDE_OFFER_AVAILABLE",
        title="New ride offer",
        body="A nearby passenger ride is available.",
        data={"offer_id": str(offer.id), "ride_id": str(ride.id)},
    )
    return offer


async def mark_ride_unmatched(
    database_session: AsyncSession,
    ride: Ride,
    *,
    reason: str = "No eligible untried driver remained within the configured search radius.",
) -> None:
    """End a bounded candidate search with an explicit passenger-visible fact."""
    previous_status = ride.status
    ride.status = RideStatus.UNMATCHED
    database_session.add(
        RideEvent(
            ride_id=ride.id,
            event_type=RideEventType.MATCHING_FAILED,
            previous_status=previous_status,
            new_status=RideStatus.UNMATCHED,
            reason=reason,
        )
    )
    await enqueue(
        database_session,
        topic="ride.matching.failed",
        payload={"ride_id": str(ride.id)},
    )
    await notify(
        database_session,
        user_id=ride.passenger_id,
        notification_type="NO_DRIVER_AVAILABLE",
        title="No taxi available",
        body="No available taxi was found nearby. You can request another ride.",
        data={"ride_id": str(ride.id)},
    )
