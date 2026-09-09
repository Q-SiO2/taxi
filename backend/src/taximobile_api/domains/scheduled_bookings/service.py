from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from geoalchemy2 import Geometry
from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql.ranges import Range
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.core.config import Settings
from taximobile_api.domains.auth.authority import user_account_is_active
from taximobile_api.domains.driver_applications.service import (
    RecruitmentConflict,
    select_active_authorization,
)
from taximobile_api.domains.drivers.models import (
    AvailabilityStatus,
    DriverProfile,
    Vehicle,
)
from taximobile_api.domains.fixed_routes.service import (
    FixedRouteConflict,
    resolve_fixed_route_ride,
)
from taximobile_api.domains.markets.models import City, ServiceType
from taximobile_api.domains.markets.service import (
    CityServiceUnavailable,
    resolve_on_demand_service_context,
)
from taximobile_api.domains.matching.service import dispatch_ride
from taximobile_api.domains.notifications.service import notify
from taximobile_api.domains.outbox.service import enqueue
from taximobile_api.domains.pricing.models import (
    BookingType,
    OperatorFeeCalculationMode,
    OperatorFeeFundingMode,
    RideFinancialSnapshot,
    SchedulingPolicy,
    SchedulingRefundMode,
    SchedulingSurchargeBeneficiary,
)
from taximobile_api.domains.pricing.service import (
    FinancialQuote,
    InvalidFinancialPolicy,
    quote_scheduled_ride,
)
from taximobile_api.domains.rides.models import Ride, RideEvent, RideEventType, RideStatus
from taximobile_api.domains.rides.schemas import Coordinate
from taximobile_api.domains.scheduled_bookings.models import (
    CancellationFinancialOutcome,
    DriverScheduledOfferPreference,
    ScheduledBooking,
    ScheduledBookingCommitment,
    ScheduledBookingEvent,
    ScheduledBookingEventType,
    ScheduledBookingOffer,
    ScheduledBookingStatus,
    ScheduledCommitmentStatus,
    ScheduledOfferStatus,
)
from taximobile_api.domains.scheduled_bookings.schemas import ScheduledBookingCreateRequest
from taximobile_api.domains.scheduled_bookings.eligibility import scheduled_driver_eligibility_failure
from taximobile_api.domains.scheduled_bookings.readiness import handoff_readiness_failure
from taximobile_api.domains.scheduled_bookings.locking import lock_booking
from taximobile_api.domains.scheduled_bookings.conflicts import is_driver_window_conflict


class SchedulingConflict(ValueError):
    pass


class ScheduledBookingNotFound(ValueError):
    pass


class ScheduledBookingForbidden(ValueError):
    pass


class ScheduledOfferUnavailable(ValueError):
    pass


TERMINAL_BOOKING_STATUSES = {
    ScheduledBookingStatus.LIVE_RIDE_CREATED,
    ScheduledBookingStatus.UNFULFILLED,
    ScheduledBookingStatus.CANCELLED,
}


def policy_snapshot(policy: SchedulingPolicy) -> dict:
    return {
        "version": policy.version,
        "minimum_lead_minutes": policy.minimum_lead_minutes,
        "maximum_horizon_days": policy.maximum_horizon_days,
        "offer_open_minutes_before": policy.offer_open_minutes_before,
        "offer_response_seconds": policy.offer_response_seconds,
        "commitment_deadline_minutes_before": policy.commitment_deadline_minutes_before,
        "handoff_minutes_before": policy.handoff_minutes_before,
        "protected_duration_minutes": policy.protected_duration_minutes,
        "conflict_buffer_before_minutes": policy.conflict_buffer_before_minutes,
        "conflict_buffer_after_minutes": policy.conflict_buffer_after_minutes,
        "passenger_cancel_cutoff_minutes": policy.passenger_cancel_cutoff_minutes,
        "driver_cancel_cutoff_minutes": policy.driver_cancel_cutoff_minutes,
        "surcharge_refund_mode": policy.surcharge_refund_mode.value,
        "fallback_matching_enabled": policy.fallback_matching_enabled,
        "collection_timing_code": policy.collection_timing_code,
    }


def _validate_requested_time(now: datetime, scheduled_for: datetime, policy: SchedulingPolicy) -> None:
    if scheduled_for <= now + timedelta(minutes=policy.minimum_lead_minutes):
        raise SchedulingConflict(
            f"Pickup must be at least {policy.minimum_lead_minutes} minutes from now."
        )
    if scheduled_for > now + timedelta(days=policy.maximum_horizon_days):
        raise SchedulingConflict(
            f"Pickup cannot be more than {policy.maximum_horizon_days} days from now."
        )


@dataclass(frozen=True)
class ScheduledBookingQuoteContext:
    city_id: UUID
    operator_id: UUID
    service_type: ServiceType
    fixed_route_direction_id: UUID | None
    pickup: Coordinate
    destination: Coordinate
    quote: FinancialQuote
    scheduling_policy: SchedulingPolicy
    city_timezone: str


def _validate_reviewed_versions(
    payload: ScheduledBookingCreateRequest,
    quote: FinancialQuote,
    scheduling_policy: SchedulingPolicy,
) -> None:
    expected = {
        "pricing rule": (payload.expected_pricing_rule_version, quote.pricing_rule_version),
        "operator fee policy": (
            payload.expected_operator_fee_policy_version,
            str(quote.policy_snapshot["operator_fee_policy_version"]),
        ),
        "scheduling policy": (
            payload.expected_scheduling_policy_version,
            scheduling_policy.version,
        ),
    }
    for label, (reviewed, active) in expected.items():
        if reviewed is not None and reviewed != active:
            raise SchedulingConflict(
                f"The {label} changed after review. Request a new scheduled estimate."
            )


async def resolve_scheduled_booking_quote(
    session: AsyncSession,
    *,
    payload: ScheduledBookingCreateRequest,
    now: datetime | None = None,
) -> ScheduledBookingQuoteContext:
    """Resolve and validate one scheduled request without persisting a booking."""
    current_time = now or datetime.now(UTC)
    if payload.payment_method.value != "CASH":
        raise SchedulingConflict("Scheduled bookings currently support cash payment only.")

    fixed_direction_id = None
    if payload.fixed_route_direction_version_id is not None:
        fixed = await resolve_fixed_route_ride(
            session,
            payload.fixed_route_direction_version_id,
            city_hint=payload.city_id,
            at=current_time,
            booking_type=BookingType.SCHEDULED,
        )
        city_id = fixed.city_id
        operator_id = fixed.operator_id
        pickup = Coordinate(
            latitude=fixed.pickup.latitude,
            longitude=fixed.pickup.longitude,
            address=(
                fixed.direction.start_location_name.get("fr")
                or fixed.direction.start_location_name.get("en")
                or fixed.direction.start_location_name.get("ar")
            ),
        )
        destination = Coordinate(
            latitude=fixed.destination.latitude,
            longitude=fixed.destination.longitude,
            address=(
                fixed.direction.finish_location_name.get("fr")
                or fixed.direction.finish_location_name.get("en")
                or fixed.direction.finish_location_name.get("ar")
            ),
        )
        quote = fixed.quote
        if quote.scheduling_policy_id is None:
            raise SchedulingConflict("The fixed route has no active scheduling policy.")
        scheduling_policy = await session.get(SchedulingPolicy, quote.scheduling_policy_id)
        fixed_direction_id = fixed.direction.id
        service_type = ServiceType.FIXED_ROUTE
    else:
        assert payload.pickup is not None and payload.destination is not None
        context = await resolve_on_demand_service_context(
            session,
            pickup_latitude=payload.pickup.latitude,
            pickup_longitude=payload.pickup.longitude,
            city_hint=payload.city_id,
            at=current_time,
        )
        city_id = context.city_id
        operator_id = context.operator_id
        pickup = payload.pickup
        destination = payload.destination
        quote, scheduling_policy = await quote_scheduled_ride(
            session,
            city_id=city_id,
            operator_id=operator_id,
            service_type=ServiceType.ON_DEMAND,
            operator_fee_policy_version_id=context.operator_fee_policy_version_id,
            scheduling_policy_version_id=context.scheduling_policy_version_id,
            at=current_time,
        )
        service_type = ServiceType.ON_DEMAND
    if scheduling_policy is None:
        raise SchedulingConflict("Scheduled booking is not enabled for this service.")
    _validate_requested_time(current_time, payload.scheduled_for, scheduling_policy)
    _validate_reviewed_versions(payload, quote, scheduling_policy)
    city = await session.get(City, city_id)
    if city is None:
        raise SchedulingConflict("The booking city is unavailable.")
    return ScheduledBookingQuoteContext(
        city_id=city_id,
        operator_id=operator_id,
        service_type=service_type,
        fixed_route_direction_id=fixed_direction_id,
        pickup=pickup,
        destination=destination,
        quote=quote,
        scheduling_policy=scheduling_policy,
        city_timezone=city.timezone,
    )


async def create_scheduled_booking(
    session: AsyncSession,
    *,
    passenger_id: UUID,
    payload: ScheduledBookingCreateRequest,
    now: datetime | None = None,
) -> ScheduledBooking:
    current_time = now or datetime.now(UTC)
    context = await resolve_scheduled_booking_quote(session, payload=payload, now=current_time)
    quote = context.quote
    scheduling_policy = context.scheduling_policy
    booking = ScheduledBooking(
        passenger_id=passenger_id,
        city_id=context.city_id,
        operator_id=context.operator_id,
        service_type=context.service_type,
        fixed_route_direction_id=context.fixed_route_direction_id,
        scheduled_for=payload.scheduled_for,
        city_timezone=context.city_timezone,
        status=ScheduledBookingStatus.SCHEDULED,
        pickup_point=WKTElement(
            f"POINT({context.pickup.longitude} {context.pickup.latitude})", srid=4326
        ),
        destination_point=WKTElement(
            f"POINT({context.destination.longitude} {context.destination.latitude})", srid=4326
        ),
        pickup_address=context.pickup.address,
        destination_address=context.destination.address,
        passenger_note=payload.passenger_note,
        payment_method=payload.payment_method,
        pricing_rule_id=quote.pricing_rule_id,
        operator_fee_policy_id=quote.operator_fee_policy_id,
        scheduling_policy_id=scheduling_policy.id,
        transport_fare_amount=quote.transport_fare_amount,
        scheduling_surcharge_amount=quote.scheduling_surcharge_amount,
        operator_fee_amount=quote.operator_fee_amount,
        passenger_total_amount=quote.passenger_total_amount,
        driver_gross_amount=quote.driver_gross_amount,
        driver_fee_deduction_amount=quote.driver_fee_deduction_amount,
        driver_net_amount=quote.driver_net_amount,
        operator_allocation_amount=quote.operator_allocation_amount,
        currency=quote.currency,
        quote_snapshot=quote.policy_snapshot,
        policy_snapshot=policy_snapshot(scheduling_policy),
    )
    session.add(booking)
    await session.flush()
    session.add(
        ScheduledBookingEvent(
            booking_id=booking.id,
            event_type=ScheduledBookingEventType.CREATED,
            new_status=ScheduledBookingStatus.SCHEDULED,
            actor_user_id=passenger_id,
            controlled_metadata={"service_type": context.service_type.value},
        )
    )
    if current_time >= payload.scheduled_for - timedelta(
        minutes=scheduling_policy.offer_open_minutes_before
    ):
        await open_offering(session, booking, now=current_time)
    await session.flush()
    return booking


async def owned_booking(
    session: AsyncSession, booking_id: UUID, passenger_id: UUID, *, lock: bool = False
) -> ScheduledBooking:
    statement = select(ScheduledBooking).where(ScheduledBooking.id == booking_id)
    if lock:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    booking = await session.scalar(statement)
    if booking is None:
        raise ScheduledBookingNotFound("Scheduled booking not found.")
    if booking.passenger_id != passenger_id:
        raise ScheduledBookingForbidden("You cannot access this scheduled booking.")
    return booking


async def booking_coordinates(session: AsyncSession, booking: ScheduledBooking) -> tuple[Coordinate, Coordinate]:
    row = (
        await session.execute(
            select(
                func.ST_Y(ScheduledBooking.pickup_point.cast(Geometry("POINT", srid=4326))),
                func.ST_X(ScheduledBooking.pickup_point.cast(Geometry("POINT", srid=4326))),
                func.ST_Y(ScheduledBooking.destination_point.cast(Geometry("POINT", srid=4326))),
                func.ST_X(ScheduledBooking.destination_point.cast(Geometry("POINT", srid=4326))),
            ).where(ScheduledBooking.id == booking.id)
        )
    ).one()
    return (
        Coordinate(latitude=row[0], longitude=row[1], address=booking.pickup_address),
        Coordinate(latitude=row[2], longitude=row[3], address=booking.destination_address),
    )


async def cancel_booking(
    session: AsyncSession,
    booking: ScheduledBooking,
    *,
    passenger_id: UUID,
    reason: str,
    now: datetime | None = None,
) -> ScheduledBooking:
    booking = await lock_booking(session, booking.id)
    if booking is None:
        raise ScheduledBookingNotFound("Scheduled booking not found.")
    if booking.passenger_id != passenger_id:
        raise ScheduledBookingForbidden("You cannot access this scheduled booking.")
    current_time = now or datetime.now(UTC)
    if booking.status == ScheduledBookingStatus.CANCELLED:
        return booking
    if booking.status in {
        ScheduledBookingStatus.LIVE_RIDE_CREATED,
        ScheduledBookingStatus.UNFULFILLED,
    }:
        raise SchedulingConflict("This scheduled booking can no longer be cancelled.")
    previous = booking.status
    refund_mode = SchedulingRefundMode(booking.policy_snapshot["surcharge_refund_mode"])
    before_cutoff = current_time <= booking.scheduled_for - timedelta(
        minutes=int(booking.policy_snapshot["passenger_cancel_cutoff_minutes"])
    )
    refundable = refund_mode == SchedulingRefundMode.ALWAYS_FULL or (
        refund_mode == SchedulingRefundMode.FULL_BEFORE_CUTOFF and before_cutoff
    )
    # The supported collection timing is settlement, therefore no money has
    # been captured at reservation time. The explicit outcome remains useful to
    # clients and avoids pretending that a refund was processed.
    booking.cancellation_financial_outcome = (
        CancellationFinancialOutcome.NO_CHARGE
        if refundable or booking.policy_snapshot.get("collection_timing_code") != "AT_BOOKING"
        else CancellationFinancialOutcome.SURCHARGE_RETAINED
    )
    booking.status = ScheduledBookingStatus.CANCELLED
    booking.cancelled_at = current_time
    booking.cancellation_reason = reason
    offers = list(
        await session.scalars(
            select(ScheduledBookingOffer)
            .where(
                ScheduledBookingOffer.booking_id == booking.id,
                ScheduledBookingOffer.status == ScheduledOfferStatus.PENDING,
            )
            .with_for_update()
        )
    )
    for offer in offers:
        offer.status = ScheduledOfferStatus.CANCELLED
        offer.responded_at = current_time
    if booking.current_commitment_id is not None:
        commitment = await session.scalar(
            select(ScheduledBookingCommitment)
            .where(ScheduledBookingCommitment.id == booking.current_commitment_id)
            .with_for_update()
        )
        if commitment is not None and commitment.status == ScheduledCommitmentStatus.ACTIVE:
            commitment.status = ScheduledCommitmentStatus.CANCELLED
            commitment.released_at = current_time
            commitment.release_reason = "PASSENGER_CANCELLED"
    session.add(
        ScheduledBookingEvent(
            booking_id=booking.id,
            event_type=ScheduledBookingEventType.CANCELLED,
            actor_user_id=passenger_id,
            previous_status=previous,
            new_status=booking.status,
            controlled_metadata={
                "financial_outcome": booking.cancellation_financial_outcome.value,
                "reason": reason,
            },
        )
    )
    await session.flush()
    return booking


async def set_offer_preference(
    session: AsyncSession,
    *,
    profile: DriverProfile,
    city_id: UUID,
    enabled: bool,
) -> DriverScheduledOfferPreference:
    if enabled:
        authorization_error: RecruitmentConflict | None = None
        for service_type in (ServiceType.ON_DEMAND, ServiceType.FIXED_ROUTE):
            try:
                await select_active_authorization(
                    session,
                    profile=profile,
                    requested_city_id=city_id,
                    requested_service_type=service_type,
                )
                break
            except RecruitmentConflict as error:
                authorization_error = error
        else:
            assert authorization_error is not None
            raise authorization_error
    preference = await session.scalar(
        select(DriverScheduledOfferPreference).where(
            DriverScheduledOfferPreference.driver_id == profile.id,
            DriverScheduledOfferPreference.city_id == city_id,
        )
    )
    if preference is None:
        preference = DriverScheduledOfferPreference(
            driver_id=profile.id, city_id=city_id, enabled=enabled
        )
        session.add(preference)
    else:
        preference.enabled = enabled
        preference.updated_at = datetime.now(UTC)
    await session.flush()
    return preference


async def open_offering(
    session: AsyncSession, booking: ScheduledBooking, *, now: datetime | None = None
) -> list[ScheduledBookingOffer]:
    booking = await lock_booking(session, booking.id)
    if booking is None:
        raise ScheduledBookingNotFound("Scheduled booking not found.")
    current_time = now or datetime.now(UTC)
    if booking.status not in {ScheduledBookingStatus.SCHEDULED, ScheduledBookingStatus.OFFERING}:
        return []
    policy = await session.get(SchedulingPolicy, booking.scheduling_policy_id)
    if policy is None:
        raise SchedulingConflict("The snapshotted scheduling policy is unavailable.")
    if current_time < booking.scheduled_for - timedelta(minutes=policy.offer_open_minutes_before):
        return []
    if booking.status == ScheduledBookingStatus.SCHEDULED:
        booking.status = ScheduledBookingStatus.OFFERING
        booking.offering_started_at = current_time
        session.add(
            ScheduledBookingEvent(
                booking_id=booking.id,
                event_type=ScheduledBookingEventType.OFFERING_STARTED,
                previous_status=ScheduledBookingStatus.SCHEDULED,
                new_status=ScheduledBookingStatus.OFFERING,
            )
        )
    existing_driver_ids = set(
        await session.scalars(
            select(ScheduledBookingOffer.driver_id).where(
                ScheduledBookingOffer.booking_id == booking.id
            )
        )
    )
    candidate_ids = list(
        await session.scalars(
            select(DriverScheduledOfferPreference.driver_id)
            .where(
                DriverScheduledOfferPreference.city_id == booking.city_id,
                DriverScheduledOfferPreference.enabled.is_(True),
            )
            .order_by(DriverScheduledOfferPreference.updated_at, DriverScheduledOfferPreference.driver_id)
            .limit(50)
        )
    )
    created: list[ScheduledBookingOffer] = []
    for driver_id in candidate_ids:
        if driver_id in existing_driver_ids:
            continue
        profile = await session.get(DriverProfile, driver_id)
        vehicle = (
            await session.get(Vehicle, profile.active_vehicle_id)
            if profile is not None and profile.active_vehicle_id is not None
            else None
        )
        if profile is None:
            continue
        if not await user_account_is_active(session, profile.user_id):
            continue
        if await scheduled_driver_eligibility_failure(
            session, profile, vehicle, now=current_time
        ):
            continue
        try:
            await select_active_authorization(
                session,
                profile=profile,
                requested_city_id=booking.city_id,
                requested_service_type=booking.service_type,
                now=current_time,
            )
        except RecruitmentConflict:
            continue
        offer = ScheduledBookingOffer(
            booking_id=booking.id,
            driver_id=driver_id,
            status=ScheduledOfferStatus.PENDING,
            offered_at=current_time,
            expires_at=current_time + timedelta(seconds=policy.offer_response_seconds),
            conflict_policy_snapshot={
                "buffer_before_minutes": policy.conflict_buffer_before_minutes,
                "buffer_after_minutes": policy.conflict_buffer_after_minutes,
                "protected_duration_minutes": policy.protected_duration_minutes,
            },
        )
        session.add(offer)
        created.append(offer)
    await session.flush()
    for offer in created:
        profile = await session.get(DriverProfile, offer.driver_id)
        if profile is not None:
            await notify(
                session,
                user_id=profile.user_id,
                notification_type="SCHEDULED_OFFER",
                title="Scheduled trip offer",
                body="A future trip is available. Review the time and earnings before accepting.",
                data={"booking_id": str(booking.id), "offer_id": str(offer.id)},
            )
            await enqueue(
                session,
                topic="scheduled.offer.created",
                payload={"offer_id": str(offer.id)},
            )
        session.add(
            ScheduledBookingEvent(
                booking_id=booking.id,
                event_type=ScheduledBookingEventType.OFFER_CREATED,
                previous_status=booking.status,
                new_status=booking.status,
                controlled_metadata={"offer_id": str(offer.id)},
            )
        )
    return created


async def driver_offer(
    session: AsyncSession, offer_id: UUID, driver_id: UUID, *, lock: bool = False
) -> tuple[ScheduledBookingOffer, ScheduledBooking]:
    statement = select(ScheduledBookingOffer).where(
        ScheduledBookingOffer.id == offer_id,
        ScheduledBookingOffer.driver_id == driver_id,
    )
    booking_id = await session.scalar(select(ScheduledBookingOffer.booking_id).where(
        ScheduledBookingOffer.id == offer_id,
        ScheduledBookingOffer.driver_id == driver_id,
    ))
    if booking_id is None:
        raise ScheduledOfferUnavailable("Scheduled offer not found.")
    booking = (
        await lock_booking(session, booking_id) if lock
        else await session.get(ScheduledBooking, booking_id)
    )
    if booking is None:
        raise ScheduledOfferUnavailable("The scheduled booking is unavailable.")
    if lock:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    offer = await session.scalar(statement)
    if offer is None:
        raise ScheduledOfferUnavailable("Scheduled offer not found.")
    return offer, booking


async def accept_offer(
    session: AsyncSession,
    *,
    offer: ScheduledBookingOffer,
    booking: ScheduledBooking,
    profile: DriverProfile,
    now: datetime | None = None,
) -> ScheduledBookingCommitment:
    offer, booking = await driver_offer(session, offer.id, profile.id, lock=True)
    profile = await session.scalar(
        select(DriverProfile).where(DriverProfile.id == profile.id)
        .with_for_update().execution_options(populate_existing=True)
    )
    if profile is None:
        raise ScheduledOfferUnavailable("Driver profile is unavailable.")
    current_time = now or datetime.now(UTC)
    if not await user_account_is_active(
        session,
        profile.user_id,
        serialize_with_status_change=True,
    ):
        raise ScheduledOfferUnavailable("Driver account is not active.")
    if offer.status != ScheduledOfferStatus.PENDING or offer.expires_at <= current_time:
        raise ScheduledOfferUnavailable("This scheduled offer is no longer available.")
    if booking.status != ScheduledBookingStatus.OFFERING or booking.current_commitment_id is not None:
        raise ScheduledOfferUnavailable("Another driver already committed or the booking closed.")
    vehicle = await session.get(Vehicle, profile.active_vehicle_id) if profile.active_vehicle_id else None
    eligibility_failure = await scheduled_driver_eligibility_failure(
        session, profile, vehicle, now=current_time
    )
    if eligibility_failure:
        raise ScheduledOfferUnavailable(eligibility_failure)
    try:
        await select_active_authorization(
            session,
            profile=profile,
            requested_city_id=booking.city_id,
            requested_service_type=booking.service_type,
            now=current_time,
        )
    except RecruitmentConflict as error:
        raise ScheduledOfferUnavailable(str(error)) from error
    assert vehicle is not None
    before = int(offer.conflict_policy_snapshot["buffer_before_minutes"])
    after = int(offer.conflict_policy_snapshot["buffer_after_minutes"])
    duration = int(offer.conflict_policy_snapshot["protected_duration_minutes"])
    commitment = ScheduledBookingCommitment(
        booking_id=booking.id,
        offer_id=offer.id,
        driver_id=profile.id,
        vehicle_id=vehicle.id,
        protected_window=Range(
            booking.scheduled_for - timedelta(minutes=before),
            booking.scheduled_for + timedelta(minutes=duration + after),
            bounds="[)",
        ),
        status=ScheduledCommitmentStatus.ACTIVE,
        committed_at=current_time,
    )
    # Live acceptance uses the same driver lock and performs the reciprocal
    # commitment check. If it committed first, refuse a scheduled commitment
    # whose protected window is already occupied by that active ride.
    if commitment.protected_window.lower <= current_time < commitment.protected_window.upper:
        active_ride = await session.scalar(
            select(Ride.id).where(
                Ride.driver_id == profile.id,
                Ride.status.in_({
                    RideStatus.ACCEPTED,
                    RideStatus.DRIVER_EN_ROUTE,
                    RideStatus.DRIVER_ARRIVED,
                    RideStatus.IN_PROGRESS,
                }),
            )
        )
        if active_ride is not None:
            raise ScheduledOfferUnavailable(
                "Driver already has an active ride during this protected window."
            )
    session.add(commitment)
    try:
        await session.flush()
    except IntegrityError as error:
        if not is_driver_window_conflict(error):
            raise  # Preserve internal fault telemetry and the sanitized 500 boundary.
        raise ScheduledOfferUnavailable(
            "This trip overlaps another accepted scheduled commitment."
        ) from error
    offer.status = ScheduledOfferStatus.ACCEPTED
    offer.responded_at = current_time
    previous = booking.status
    booking.status = ScheduledBookingStatus.DRIVER_COMMITTED
    booking.current_commitment_id = commitment.id
    booking.committed_at = current_time
    pending = list(
        await session.scalars(
            select(ScheduledBookingOffer).where(
                ScheduledBookingOffer.booking_id == booking.id,
                ScheduledBookingOffer.id != offer.id,
                ScheduledBookingOffer.status == ScheduledOfferStatus.PENDING,
            )
        )
    )
    for other in pending:
        other.status = ScheduledOfferStatus.CANCELLED
        other.responded_at = current_time
    session.add(
        ScheduledBookingEvent(
            booking_id=booking.id,
            event_type=ScheduledBookingEventType.DRIVER_COMMITTED,
            actor_user_id=profile.user_id,
            previous_status=previous,
            new_status=booking.status,
            controlled_metadata={"commitment_id": str(commitment.id)},
        )
    )
    await notify(
        session,
        user_id=booking.passenger_id,
        notification_type="SCHEDULED_DRIVER_COMMITTED",
        title="A driver committed",
        body="A driver has accepted your scheduled trip. Eligibility is checked again at dispatch.",
        data={"booking_id": str(booking.id)},
    )
    await enqueue(
        session,
        topic="scheduled.driver.committed",
        payload={"booking_id": str(booking.id)},
    )
    await session.flush()
    return commitment


async def decline_offer(
    session: AsyncSession,
    *,
    offer: ScheduledBookingOffer,
    booking: ScheduledBooking,
    profile: DriverProfile,
    reason: str | None,
    now: datetime | None = None,
) -> ScheduledBookingOffer:
    offer, booking = await driver_offer(session, offer.id, profile.id, lock=True)
    current_time = now or datetime.now(UTC)
    if offer.status == ScheduledOfferStatus.DECLINED:
        return offer
    if offer.status != ScheduledOfferStatus.PENDING:
        raise ScheduledOfferUnavailable("This scheduled offer is no longer available.")
    offer.status = ScheduledOfferStatus.DECLINED
    offer.responded_at = current_time
    offer.decline_reason = reason
    session.add(
        ScheduledBookingEvent(
            booking_id=booking.id,
            event_type=ScheduledBookingEventType.OFFER_DECLINED,
            actor_user_id=profile.user_id,
            previous_status=booking.status,
            new_status=booking.status,
            controlled_metadata={"offer_id": str(offer.id)},
        )
    )
    await session.flush()
    return offer


async def handoff_booking(
    session: AsyncSession,
    booking: ScheduledBooking,
    *,
    now: datetime | None = None,
    matching_settings: Settings | None = None,
) -> Ride | ScheduledBooking:
    booking = await lock_booking(session, booking.id)
    if booking is None:
        raise ScheduledBookingNotFound("Scheduled booking not found.")
    current_time = now or datetime.now(UTC)
    if booking.live_ride_id is not None:
        ride = await session.get(Ride, booking.live_ride_id)
        if ride is None:
            raise SchedulingConflict("The booking handoff record is inconsistent.")
        return ride
    if matching_settings is None:
        raise SchedulingConflict("Dispatch readiness configuration is unavailable.")
    if booking.status != ScheduledBookingStatus.DRIVER_COMMITTED or booking.current_commitment_id is None:
        raise SchedulingConflict("The booking has no driver commitment to hand off.")
    policy = await session.get(SchedulingPolicy, booking.scheduling_policy_id)
    if policy is None or current_time < booking.scheduled_for - timedelta(minutes=policy.handoff_minutes_before):
        raise SchedulingConflict("The dispatch handoff window has not opened.")
    commitment = await session.scalar(
        select(ScheduledBookingCommitment)
        .where(ScheduledBookingCommitment.id == booking.current_commitment_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if commitment is None or commitment.status != ScheduledCommitmentStatus.ACTIVE:
        raise SchedulingConflict("The scheduled commitment is no longer active.")
    profile = await session.scalar(
        select(DriverProfile).where(DriverProfile.id == commitment.driver_id)
        .with_for_update().execution_options(populate_existing=True)
    )
    current_time = now or datetime.now(UTC)
    if profile is None:
        return await fallback_handoff_or_unfulfilled(
            session,
            booking,
            commitment=commitment,
            reason="DRIVER_OR_VEHICLE_UNAVAILABLE",
            policy=policy,
            current_time=current_time,
            matching_settings=matching_settings,
        )
    if not await user_account_is_active(
        session,
        profile.user_id,
        serialize_with_status_change=True,
    ):
        return await fallback_handoff_or_unfulfilled(
            session,
            booking,
            commitment=commitment,
            reason="DRIVER_ACCOUNT_INACTIVE",
            policy=policy,
            current_time=current_time,
            matching_settings=matching_settings,
        )
    vehicle = await session.get(Vehicle, commitment.vehicle_id)
    if vehicle is None or profile.active_vehicle_id != vehicle.id:
        return await fallback_handoff_or_unfulfilled(
            session,
            booking,
            commitment=commitment,
            reason="DRIVER_OR_VEHICLE_UNAVAILABLE",
            policy=policy,
            current_time=current_time,
            matching_settings=matching_settings,
        )
    if await scheduled_driver_eligibility_failure(session, profile, vehicle, now=current_time):
        return await fallback_handoff_or_unfulfilled(
            session,
            booking,
            commitment=commitment,
            reason="DRIVER_OR_VEHICLE_INELIGIBLE",
            policy=policy,
            current_time=current_time,
            matching_settings=matching_settings,
        )
    try:
        selected_authorization = await select_active_authorization(
            session,
            profile=profile,
            requested_city_id=booking.city_id,
            requested_service_type=booking.service_type,
            now=current_time,
        )
    except RecruitmentConflict:
        return await fallback_handoff_or_unfulfilled(
            session,
            booking,
            commitment=commitment,
            reason="DRIVER_NOT_ELIGIBLE",
            policy=policy,
            current_time=current_time,
            matching_settings=matching_settings,
        )
    readiness_failure = await handoff_readiness_failure(
        session, profile, selected_authorization.city, booking.service_type,
        now=current_time,
        location_freshness_seconds=matching_settings.matching_location_freshness_seconds,
    )
    if readiness_failure:
        return await fallback_handoff_or_unfulfilled(
            session, booking, commitment=commitment, reason=readiness_failure,
            policy=policy, current_time=current_time, matching_settings=matching_settings,
        )
    conflicting_ride = await session.scalar(
        select(Ride.id).where(
            Ride.driver_id == profile.id,
            Ride.status.in_(
                {
                    RideStatus.ACCEPTED,
                    RideStatus.DRIVER_EN_ROUTE,
                    RideStatus.DRIVER_ARRIVED,
                    RideStatus.IN_PROGRESS,
                }
            ),
        ).limit(1)
    )
    if conflicting_ride is not None:
        return await fallback_handoff_or_unfulfilled(
            session,
            booking,
            commitment=commitment,
            reason="DRIVER_HAS_LIVE_RIDE",
            policy=policy,
            current_time=current_time,
            matching_settings=matching_settings,
        )
    pickup, destination = await booking_coordinates(session, booking)
    previous = booking.status
    booking.status = ScheduledBookingStatus.DISPATCH_HANDOFF
    booking.handoff_started_at = current_time
    session.add(
        ScheduledBookingEvent(
            booking_id=booking.id,
            event_type=ScheduledBookingEventType.HANDOFF_STARTED,
            previous_status=previous,
            new_status=booking.status,
        )
    )
    ride = Ride(
        city_id=booking.city_id,
        operator_id=booking.operator_id,
        service_type=booking.service_type,
        fixed_route_direction_id=booking.fixed_route_direction_id,
        scheduled_booking_id=booking.id,
        passenger_id=booking.passenger_id,
        driver_id=profile.id,
        vehicle_id=vehicle.id,
        assigned_driver_name=profile.display_name,
        assigned_vehicle_make=vehicle.make,
        assigned_vehicle_model=vehicle.model,
        assigned_vehicle_color=vehicle.color,
        assigned_taxi_identifier=vehicle.taxi_identifier,
        quoted_pricing_rule_id=booking.pricing_rule_id,
        quoted_amount=booking.passenger_total_amount,
        quoted_currency=booking.currency,
        payment_method=booking.payment_method,
        status=RideStatus.ACCEPTED,
        pickup_point=WKTElement(f"POINT({pickup.longitude} {pickup.latitude})", srid=4326),
        destination_point=WKTElement(
            f"POINT({destination.longitude} {destination.latitude})", srid=4326
        ),
        pickup_address=pickup.address,
        destination_address=destination.address,
        passenger_note=booking.passenger_note,
        accepted_at=current_time,
    )
    session.add(ride)
    await session.flush()
    session.add(
        RideFinancialSnapshot(
            ride_id=ride.id,
            pricing_rule_id=booking.pricing_rule_id,
            operator_fee_policy_id=booking.operator_fee_policy_id,
            scheduling_policy_id=booking.scheduling_policy_id,
            booking_type=BookingType.SCHEDULED,
            operator_fee_calculation_mode=OperatorFeeCalculationMode(
                booking.quote_snapshot["operator_fee_calculation_mode"]
            ),
            operator_fee_funding_mode=OperatorFeeFundingMode(
                booking.quote_snapshot["operator_fee_funding_mode"]
            ),
            scheduling_surcharge_beneficiary=SchedulingSurchargeBeneficiary(
                booking.quote_snapshot["scheduling_surcharge_beneficiary"]
            ),
            transport_fare_amount=booking.transport_fare_amount,
            scheduling_surcharge_amount=booking.scheduling_surcharge_amount,
            operator_fee_amount=booking.operator_fee_amount,
            passenger_total_amount=booking.passenger_total_amount,
            driver_gross_amount=booking.driver_gross_amount,
            driver_fee_deduction_amount=booking.driver_fee_deduction_amount,
            driver_net_amount=booking.driver_net_amount,
            operator_allocation_amount=booking.operator_allocation_amount,
            currency=booking.currency,
            snapshot=booking.quote_snapshot,
        )
    )
    session.add(
        RideEvent(
            ride_id=ride.id,
            event_type=RideEventType.CREATED,
            new_status=RideStatus.ACCEPTED,
            actor_user_id=profile.user_id,
        )
    )
    booking.status = ScheduledBookingStatus.LIVE_RIDE_CREATED
    booking.live_ride_id = ride.id
    booking.live_ride_created_at = current_time
    commitment.status = ScheduledCommitmentStatus.FULFILLED
    commitment.released_at = current_time
    commitment.release_reason = "LIVE_RIDE_CREATED"
    profile.availability_status = AvailabilityStatus.EN_ROUTE
    profile.online_city_id = booking.city_id
    profile.online_service_type = booking.service_type
    profile.available_since = None
    session.add(
        ScheduledBookingEvent(
            booking_id=booking.id,
            event_type=ScheduledBookingEventType.LIVE_RIDE_CREATED,
            actor_user_id=profile.user_id,
            previous_status=ScheduledBookingStatus.DISPATCH_HANDOFF,
            new_status=booking.status,
            controlled_metadata={"ride_id": str(ride.id)},
        )
    )
    await notify(
        session,
        user_id=booking.passenger_id,
        notification_type="SCHEDULED_DISPATCH_STARTED",
        title="Your scheduled trip is starting",
        body="The driver is now preparing to reach your pickup.",
        data={"booking_id": str(booking.id), "ride_id": str(ride.id)},
    )
    await enqueue(
        session,
        topic="scheduled.dispatch.started",
        payload={"booking_id": str(booking.id)},
    )
    await session.flush()
    return ride


async def fallback_handoff_or_unfulfilled(
    session: AsyncSession,
    booking: ScheduledBooking,
    *,
    commitment: ScheduledBookingCommitment,
    reason: str,
    policy: SchedulingPolicy,
    current_time: datetime,
    matching_settings: Settings | None,
) -> Ride | ScheduledBooking:
    """Enter ordinary live matching only when the immutable policy permits it.

    A fallback ride is retained only when normal dispatch can create a real
    candidate offer in the same transaction. Otherwise the temporary ride and
    its cascaded records are removed and the booking receives the explicit
    unfulfilled outcome; no passenger-facing live ride is invented.
    """
    if not policy.fallback_matching_enabled or matching_settings is None:
        return await mark_unfulfilled(session, booking, reason=reason, now=current_time)
    previous = booking.status
    booking.status = ScheduledBookingStatus.DISPATCH_HANDOFF
    booking.handoff_started_at = current_time
    commitment.status = ScheduledCommitmentStatus.RELEASED
    commitment.released_at = current_time
    commitment.release_reason = reason
    booking.current_commitment_id = None
    session.add(
        ScheduledBookingEvent(
            booking_id=booking.id,
            event_type=ScheduledBookingEventType.HANDOFF_STARTED,
            previous_status=previous,
            new_status=booking.status,
            controlled_metadata={"fallback_reason": reason},
        )
    )
    pickup, destination = await booking_coordinates(session, booking)
    fallback_savepoint = await session.begin_nested()
    ride = Ride(
        city_id=booking.city_id,
        operator_id=booking.operator_id,
        service_type=booking.service_type,
        fixed_route_direction_id=booking.fixed_route_direction_id,
        scheduled_booking_id=booking.id,
        passenger_id=booking.passenger_id,
        quoted_pricing_rule_id=booking.pricing_rule_id,
        quoted_amount=booking.passenger_total_amount,
        quoted_currency=booking.currency,
        payment_method=booking.payment_method,
        pickup_point=WKTElement(f"POINT({pickup.longitude} {pickup.latitude})", srid=4326),
        destination_point=WKTElement(
            f"POINT({destination.longitude} {destination.latitude})", srid=4326
        ),
        pickup_address=pickup.address,
        destination_address=destination.address,
        passenger_note=booking.passenger_note,
    )
    session.add(ride)
    await session.flush()
    session.add(
        RideFinancialSnapshot(
            ride_id=ride.id,
            pricing_rule_id=booking.pricing_rule_id,
            operator_fee_policy_id=booking.operator_fee_policy_id,
            scheduling_policy_id=booking.scheduling_policy_id,
            booking_type=BookingType.SCHEDULED,
            operator_fee_calculation_mode=OperatorFeeCalculationMode(
                booking.quote_snapshot["operator_fee_calculation_mode"]
            ),
            operator_fee_funding_mode=OperatorFeeFundingMode(
                booking.quote_snapshot["operator_fee_funding_mode"]
            ),
            scheduling_surcharge_beneficiary=SchedulingSurchargeBeneficiary(
                booking.quote_snapshot["scheduling_surcharge_beneficiary"]
            ),
            transport_fare_amount=booking.transport_fare_amount,
            scheduling_surcharge_amount=booking.scheduling_surcharge_amount,
            operator_fee_amount=booking.operator_fee_amount,
            passenger_total_amount=booking.passenger_total_amount,
            driver_gross_amount=booking.driver_gross_amount,
            driver_fee_deduction_amount=booking.driver_fee_deduction_amount,
            driver_net_amount=booking.driver_net_amount,
            operator_allocation_amount=booking.operator_allocation_amount,
            currency=booking.currency,
            snapshot=booking.quote_snapshot,
        )
    )
    session.add(
        RideEvent(
            ride_id=ride.id,
            event_type=RideEventType.CREATED,
            new_status=RideStatus.REQUESTED,
        )
    )
    await session.flush()
    fallback_offer = await dispatch_ride(
        session, ride.id, matching_settings, excluded_driver_ids=(commitment.driver_id,),
    )
    if fallback_offer is None:
        # Dispatch may have recorded an unmatched event, notification, and
        # outbox row. Roll back the complete fallback attempt so none can point
        # at a ride that the scheduled aggregate never exposed.
        await fallback_savepoint.rollback()
        return await mark_unfulfilled(
            session,
            booking,
            reason=f"{reason}_FALLBACK_NO_SUPPLY",
            now=current_time,
        )
    await fallback_savepoint.commit()
    booking.status = ScheduledBookingStatus.LIVE_RIDE_CREATED
    booking.live_ride_id = ride.id
    booking.live_ride_created_at = current_time
    session.add(
        ScheduledBookingEvent(
            booking_id=booking.id,
            event_type=ScheduledBookingEventType.LIVE_RIDE_CREATED,
            previous_status=ScheduledBookingStatus.DISPATCH_HANDOFF,
            new_status=booking.status,
            controlled_metadata={
                "ride_id": str(ride.id),
                "fallback_matching": True,
            },
        )
    )
    await notify(
        session,
        user_id=booking.passenger_id,
        notification_type="SCHEDULED_FALLBACK_MATCHING",
        title="Finding another taxi",
        body="The original commitment became unavailable. We are matching the live pickup request now.",
        data={"booking_id": str(booking.id), "ride_id": str(ride.id)},
    )
    await enqueue(
        session,
        topic="scheduled.fallback.matching",
        payload={"booking_id": str(booking.id)},
    )
    await session.flush()
    return ride


async def mark_unfulfilled(
    session: AsyncSession,
    booking: ScheduledBooking,
    *,
    reason: str,
    now: datetime | None = None,
):
    current_time = now or datetime.now(UTC)
    previous = booking.status
    booking.status = ScheduledBookingStatus.UNFULFILLED
    booking.unfulfilled_at = current_time
    if booking.current_commitment_id is not None:
        commitment = await session.get(
            ScheduledBookingCommitment, booking.current_commitment_id
        )
        if commitment is not None and commitment.status == ScheduledCommitmentStatus.ACTIVE:
            commitment.status = ScheduledCommitmentStatus.RELEASED
            commitment.released_at = current_time
            commitment.release_reason = reason
    session.add(
        ScheduledBookingEvent(
            booking_id=booking.id,
            event_type=ScheduledBookingEventType.UNFULFILLED,
            previous_status=previous,
            new_status=booking.status,
            controlled_metadata={"reason": reason},
        )
    )
    await notify(
        session,
        user_id=booking.passenger_id,
        notification_type="SCHEDULED_UNFULFILLED",
        title="Scheduled trip not fulfilled",
        body="We could not confirm an eligible taxi for this pickup. No ride was created.",
        data={"booking_id": str(booking.id)},
    )
    await enqueue(
        session,
        topic="scheduled.unfulfilled",
        payload={"booking_id": str(booking.id)},
    )
    await session.flush()
    return booking


async def advance_due_bookings(
    session: AsyncSession,
    *,
    now: datetime | None = None,
    limit: int = 100,
    matching_settings: Settings | None = None,
) -> dict[str, int]:
    current_time = now or datetime.now(UTC)
    bookings = list(
        await session.scalars(
            select(ScheduledBooking)
            .where(
                ScheduledBooking.status.in_(
                    {
                        ScheduledBookingStatus.SCHEDULED,
                        ScheduledBookingStatus.OFFERING,
                        ScheduledBookingStatus.DRIVER_COMMITTED,
                    }
                )
            )
            .order_by(ScheduledBooking.scheduled_for, ScheduledBooking.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
    )
    counts = {"offering": 0, "handoff": 0, "unfulfilled": 0}
    for booking in bookings:
        policy = await session.get(SchedulingPolicy, booking.scheduling_policy_id)
        if policy is None:
            await mark_unfulfilled(session, booking, reason="POLICY_UNAVAILABLE", now=current_time)
            counts["unfulfilled"] += 1
            continue
        if booking.status == ScheduledBookingStatus.SCHEDULED and current_time >= (
            booking.scheduled_for - timedelta(minutes=policy.offer_open_minutes_before)
        ):
            await open_offering(session, booking, now=current_time)
            counts["offering"] += 1
        if booking.status == ScheduledBookingStatus.OFFERING and current_time >= (
            booking.scheduled_for
            - timedelta(minutes=policy.commitment_deadline_minutes_before)
        ):
            await mark_unfulfilled(session, booking, reason="NO_DRIVER_COMMITMENT", now=current_time)
            counts["unfulfilled"] += 1
        elif booking.status == ScheduledBookingStatus.DRIVER_COMMITTED and current_time >= (
            booking.scheduled_for - timedelta(minutes=policy.handoff_minutes_before)
        ):
            result = await handoff_booking(
                session,
                booking,
                now=current_time,
                matching_settings=matching_settings,
            )
            if isinstance(result, Ride):
                counts["handoff"] += 1
            else:
                counts["unfulfilled"] += 1
    return counts
