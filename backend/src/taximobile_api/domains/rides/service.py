from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.elements import WKTElement

from taximobile_api.domains.auth.authority import user_account_is_active
from taximobile_api.domains.drivers.models import AvailabilityStatus, DriverAccountStatus, DriverProfile, Vehicle, VehicleStatus, VehicleVerificationStatus, VerificationStatus
from taximobile_api.domains.drivers.service import invalid_driver_credentials
from taximobile_api.domains.driver_applications.models import (
    CityAuthorizationStatus,
    DriverCityAuthorization,
    DriverCityAuthorizationService,
)
from taximobile_api.domains.markets.models import ServiceType
from taximobile_api.domains.rides.models import Ride, RideEvent, RideEventType, RideOffer, RideOfferStatus, RideStatus
from taximobile_api.domains.rides.schemas import Coordinate, RideCreateRequest
from taximobile_api.domains.pricing.models import PricingRule, RideFinancialSnapshot
from taximobile_api.domains.pricing.service import (
    FinancialQuote,
    NoActiveTariff,
    finalize_fixed_fare_for_rule,
)
from taximobile_api.domains.payments.models import PaymentMethod
from taximobile_api.domains.payments.service import create_pending_payment
from taximobile_api.domains.outbox.service import enqueue
from taximobile_api.domains.notifications.service import notify
from taximobile_api.domains.rides.locking import lock_driver, lock_owned_offer, lock_ride
from taximobile_api.domains.scheduled_bookings.protection import driver_has_protected_commitment


class RideNotFound(ValueError):
    pass


class RideForbidden(ValueError):
    pass


class InvalidRideTransition(ValueError):
    pass


class RideOfferUnavailable(ValueError):
    pass


PASSENGER_CANCELLABLE = {
    RideStatus.REQUESTED,
    RideStatus.MATCHING,
    RideStatus.ACCEPTED,
    RideStatus.DRIVER_EN_ROUTE,
    RideStatus.DRIVER_ARRIVED,
}

# A driver can only cancel a ride that has been assigned but has not begun.
# In-progress rides need a separately documented safety/no-show resolution
# workflow; a simple cancellation must never erase that operational record.
DRIVER_CANCELLABLE = {
    RideStatus.ACCEPTED,
    RideStatus.DRIVER_EN_ROUTE,
    RideStatus.DRIVER_ARRIVED,
}


async def create_ride(
    database_session: AsyncSession,
    passenger_id,
    request: RideCreateRequest,
    financial_quote: FinancialQuote,
    *,
    city_id,
    operator_id,
    pickup: Coordinate,
    destination: Coordinate,
    service_type: ServiceType = ServiceType.ON_DEMAND,
    fixed_route_direction_id=None,
) -> Ride:
    ride = Ride(
        city_id=city_id,
        operator_id=operator_id,
        service_type=service_type,
        fixed_route_direction_id=fixed_route_direction_id,
        passenger_id=passenger_id,
        pickup_point=WKTElement(f"POINT({pickup.longitude} {pickup.latitude})", srid=4326),
        destination_point=WKTElement(f"POINT({destination.longitude} {destination.latitude})", srid=4326),
        pickup_address=pickup.address,
        destination_address=destination.address,
        passenger_note=request.passenger_note,
        quoted_pricing_rule_id=financial_quote.pricing_rule_id,
        quoted_amount=financial_quote.passenger_total_amount,
        quoted_currency=financial_quote.currency,
        payment_method=request.payment_method,
    )
    database_session.add(ride)
    await database_session.flush()
    database_session.add(financial_quote.ride_snapshot(ride.id))
    database_session.add(RideEvent(ride_id=ride.id, event_type=RideEventType.CREATED, new_status=RideStatus.REQUESTED, actor_user_id=passenger_id))
    await database_session.flush()
    return ride


async def owned_ride(database_session: AsyncSession, ride_id, user_id) -> Ride:
    ride = await database_session.get(Ride, ride_id)
    if ride is None:
        raise RideNotFound("Ride not found.")
    if ride.passenger_id != user_id:
        # Driver ownership is added with assignment; do not expose unassigned rides.
        raise RideForbidden("You cannot access this ride.")
    return ride


async def assigned_driver_ride(database_session: AsyncSession, ride_id, driver_id, *, lock: bool = False) -> Ride:
    statement = select(Ride).where(Ride.id == ride_id, Ride.driver_id == driver_id)
    if lock:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    ride = await database_session.scalar(statement)
    if ride is None:
        raise RideForbidden("You cannot manage this ride.")
    return ride


async def cancel_passenger_ride(database_session: AsyncSession, ride: Ride, user_id, reason: str) -> Ride:
    ride = await lock_ride(database_session, ride.id)
    if ride is None:
        raise RideNotFound("Ride not found.")
    if ride.passenger_id != user_id:
        raise RideForbidden("You cannot access this ride.")
    if ride.status not in PASSENGER_CANCELLABLE:
        raise InvalidRideTransition("This ride can no longer be cancelled by the passenger.")
    previous_status = ride.status
    ride.status = RideStatus.CANCELLED
    ride.cancellation_reason = reason
    ride.cancelled_by_user_id = user_id
    now = datetime.now(UTC)
    pending_offers = list(
        await database_session.scalars(
            select(RideOffer)
            .where(RideOffer.ride_id == ride.id, RideOffer.status == RideOfferStatus.PENDING)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    )
    for offer in pending_offers:
        offer.status = RideOfferStatus.CANCELLED
        offer.responded_at = now
        offered_profile = await lock_driver(database_session, offer.driver_id)
        if offered_profile is not None and offered_profile.availability_status == AvailabilityStatus.OFFERED_RIDE:
            offered_profile.availability_status = AvailabilityStatus.AVAILABLE
            if offered_profile.available_since is None:
                offered_profile.available_since = now
    if ride.driver_id is not None:
        assigned_profile = await lock_driver(database_session, ride.driver_id)
        if assigned_profile is not None and assigned_profile.availability_status in {
            AvailabilityStatus.EN_ROUTE,
            AvailabilityStatus.AT_PICKUP,
            AvailabilityStatus.OFFERED_RIDE,
        }:
            assigned_profile.availability_status = AvailabilityStatus.AVAILABLE
            assigned_profile.available_since = now
    database_session.add(RideEvent(ride_id=ride.id, event_type=RideEventType.CANCELLED, previous_status=previous_status, new_status=RideStatus.CANCELLED, actor_user_id=user_id, reason=reason))
    await enqueue(database_session, topic="ride.cancelled", payload={"ride_id": str(ride.id)})
    await database_session.flush()
    return ride


async def cancel_assigned_driver_ride(
    database_session: AsyncSession,
    ride: Ride,
    profile: DriverProfile,
    user_id,
    reason: str,
) -> Ride:
    """Cancel an assigned, pre-start ride and return the driver to availability.

    The MVP deliberately records a terminal cancellation instead of silently
    re-dispatching the passenger to another driver. Re-dispatch needs its own
    passenger communication and offer-expiry policy. The driver remains
    explicitly available, so the normal matching path may offer a later ride.
    """
    ride = await assigned_driver_ride(database_session, ride.id, profile.id, lock=True)
    profile = await lock_driver(database_session, profile.id)
    if profile is None or profile.user_id != user_id:
        raise RideForbidden("You cannot manage this ride.")
    if ride.status not in DRIVER_CANCELLABLE:
        raise InvalidRideTransition("This ride can no longer be cancelled by the driver.")
    previous_status = ride.status
    ride.status = RideStatus.CANCELLED
    ride.cancellation_reason = reason
    ride.cancelled_by_user_id = user_id
    profile.availability_status = AvailabilityStatus.AVAILABLE
    profile.available_since = datetime.now(UTC)
    database_session.add(
        RideEvent(
            ride_id=ride.id,
            event_type=RideEventType.CANCELLED,
            previous_status=previous_status,
            new_status=RideStatus.CANCELLED,
            actor_user_id=user_id,
            reason=reason,
        )
    )
    await enqueue(database_session, topic="ride.cancelled", payload={"ride_id": str(ride.id)})
    await database_session.flush()
    return ride


def is_valid_transition(current: RideStatus, requested: RideStatus) -> bool:
    transitions = {
        RideStatus.REQUESTED: {RideStatus.MATCHING, RideStatus.CANCELLED},
        RideStatus.MATCHING: {RideStatus.ACCEPTED, RideStatus.CANCELLED},
        RideStatus.ACCEPTED: {RideStatus.DRIVER_EN_ROUTE, RideStatus.CANCELLED},
        RideStatus.DRIVER_EN_ROUTE: {RideStatus.DRIVER_ARRIVED, RideStatus.CANCELLED},
        RideStatus.DRIVER_ARRIVED: {RideStatus.IN_PROGRESS, RideStatus.CANCELLED},
        RideStatus.IN_PROGRESS: {RideStatus.COMPLETED},
    }
    return requested in transitions.get(current, set())


async def transition_assigned_ride(
    database_session: AsyncSession,
    ride: Ride,
    profile: DriverProfile,
    target: RideStatus,
    actor_user_id,
) -> Ride:
    ride = await assigned_driver_ride(database_session, ride.id, profile.id, lock=True)
    profile = await lock_driver(database_session, profile.id)
    if profile is None or profile.user_id != actor_user_id:
        raise RideForbidden("You cannot manage this ride.")
    if not is_valid_transition(ride.status, target):
        raise InvalidRideTransition("Ride is not in the required state.")
    previous_status = ride.status
    ride.status = target
    now = datetime.now(UTC)
    if target == RideStatus.DRIVER_EN_ROUTE:
        ride.en_route_at = now
        profile.availability_status = AvailabilityStatus.EN_ROUTE
    elif target == RideStatus.DRIVER_ARRIVED:
        ride.arrived_at = now
        profile.availability_status = AvailabilityStatus.AT_PICKUP
    elif target == RideStatus.IN_PROGRESS:
        ride.started_at = now
        profile.availability_status = AvailabilityStatus.ON_RIDE
    database_session.add(
        RideEvent(
            ride_id=ride.id,
            event_type=RideEventType.STATUS_CHANGED,
            previous_status=previous_status,
            new_status=target,
            actor_user_id=actor_user_id,
        )
    )
    await database_session.flush()
    return ride


async def complete_assigned_ride(
    database_session: AsyncSession,
    ride: Ride,
    profile: DriverProfile,
    actor_user_id,
    latitude: float,
    longitude: float,
):
    ride = await assigned_driver_ride(database_session, ride.id, profile.id, lock=True)
    profile = await lock_driver(database_session, profile.id)
    if profile is None or profile.user_id != actor_user_id:
        raise RideForbidden("You cannot manage this ride.")
    if ride.status != RideStatus.IN_PROGRESS:
        raise InvalidRideTransition("Ride is not in the required state.")
    if ride.quoted_pricing_rule_id is None or ride.quoted_amount is None or ride.quoted_currency is None:
        raise NoActiveTariff("This ride has no locked tariff.")
    quoted_rule = await database_session.get(PricingRule, ride.quoted_pricing_rule_id)
    if quoted_rule is None:
        raise NoActiveTariff("This ride has no locked tariff.")
    financial_snapshot = await database_session.get(RideFinancialSnapshot, ride.id)
    fare = await finalize_fixed_fare_for_rule(
        database_session,
        ride.id,
        quoted_rule,
        locked_amount=ride.quoted_amount,
        locked_currency=ride.quoted_currency,
        financial_snapshot=financial_snapshot,
    )
    payment = create_pending_payment(
        ride_id=ride.id,
        payer_id=ride.passenger_id,
        city_id=ride.city_id,
        operator_id=ride.operator_id,
        payment_capability_version_id=ride.payment_capability_version_id,
        payment_recipient_account_id=ride.payment_recipient_account_id,
        amount=fare.total_amount,
        currency=fare.currency,
        method=ride.payment_method,
    )
    database_session.add(payment)
    ride.completed_point = WKTElement(f"POINT({longitude} {latitude})", srid=4326)
    ride.completed_at = datetime.now(UTC)
    ride.status = RideStatus.COMPLETED
    profile.availability_status = AvailabilityStatus.OFFLINE
    profile.available_since = None
    database_session.add(
        RideEvent(
            ride_id=ride.id,
            event_type=RideEventType.STATUS_CHANGED,
            previous_status=RideStatus.IN_PROGRESS,
            new_status=RideStatus.COMPLETED,
            actor_user_id=actor_user_id,
        )
    )
    await database_session.flush()
    return fare


def offer_failure(offer: RideOffer, ride: Ride, now: datetime) -> str | None:
    if offer.status != RideOfferStatus.PENDING:
        return "Ride offer is no longer pending."
    if offer.expires_at <= now:
        return "Ride offer has expired."
    if ride.status != RideStatus.MATCHING or ride.driver_id is not None:
        return "Ride is no longer available."
    return None


async def accept_offer_atomically(database_session: AsyncSession, offer_id, driver_id) -> Ride:
    ride, offer = await lock_owned_offer(database_session, offer_id, driver_id)
    if ride is None or offer is None:
        raise RideOfferUnavailable("Ride offer is not available.")
    profile = await lock_driver(database_session, driver_id)
    now = datetime.now(UTC)
    if profile is None:
        raise RideOfferUnavailable("Ride offer is not available.")
    if not await user_account_is_active(
        database_session,
        profile.user_id,
        serialize_with_status_change=True,
    ):
        raise RideOfferUnavailable("Driver account is no longer active.")
    vehicle = await database_session.get(Vehicle, profile.active_vehicle_id) if profile.active_vehicle_id else None
    credential_ineligible = bool(
        await database_session.scalar(select(invalid_driver_credentials(profile.id, now)))
    )
    if (
        profile.account_status != DriverAccountStatus.ACTIVE
        or profile.verification_status != VerificationStatus.APPROVED
        or profile.availability_status not in {AvailabilityStatus.AVAILABLE, AvailabilityStatus.OFFERED_RIDE}
        or vehicle is None
        or vehicle.status != VehicleStatus.ACTIVE
        or vehicle.verification_status != VehicleVerificationStatus.VERIFIED
        or credential_ineligible
        or profile.online_city_id is None
    ):
        raise RideOfferUnavailable("Driver is no longer eligible for this offer.")
    if profile.online_city_id != ride.city_id:
        raise RideOfferUnavailable("Driver is no longer online in this ride's city.")
    if profile.online_service_type != ride.service_type:
        raise RideOfferUnavailable("Driver is no longer online for this ride's service type.")
    authorization_id = await database_session.scalar(
        select(DriverCityAuthorization.id)
        .join(
            DriverCityAuthorizationService,
            DriverCityAuthorizationService.authorization_id == DriverCityAuthorization.id,
        )
        .where(
            DriverCityAuthorization.driver_id == profile.id,
            DriverCityAuthorization.city_id == ride.city_id,
            DriverCityAuthorization.status == CityAuthorizationStatus.ACTIVE,
            DriverCityAuthorization.valid_from <= now,
            or_(
                DriverCityAuthorization.valid_until.is_(None),
                DriverCityAuthorization.valid_until > now,
            ),
            or_(
                DriverCityAuthorization.vehicle_id.is_(None),
                DriverCityAuthorization.vehicle_id == vehicle.id,
            ),
            DriverCityAuthorizationService.service_type == ride.service_type,
        )
    )
    if authorization_id is None:
        raise RideOfferUnavailable("Driver is no longer authorized for this city service.")
    reason = offer_failure(offer, ride, now)
    if reason:
        if offer.status == RideOfferStatus.PENDING and offer.expires_at <= datetime.now(UTC):
            offer.status = RideOfferStatus.EXPIRED
        raise RideOfferUnavailable(reason)
    # An offer may predate this window or a concurrent commitment. Recheck only
    # after locking the driver so a delayed offer cannot become a conflicting
    # live assignment.
    if await driver_has_protected_commitment(database_session, driver_id, at=now):
        raise RideOfferUnavailable("Driver is reserved for a scheduled booking at this time.")
    # The driver lock serializes assignment. Taking another ride lock here
    # would invert ride -> driver order against that ride's cancellation/start.
    active_ride = await database_session.scalar(
        select(Ride.id)
        .where(
            Ride.driver_id == driver_id,
            Ride.status.in_({RideStatus.ACCEPTED, RideStatus.DRIVER_EN_ROUTE, RideStatus.DRIVER_ARRIVED, RideStatus.IN_PROGRESS}),
        )
    )
    if active_ride is not None:
        raise RideOfferUnavailable("Driver already has an active ride.")
    offer.status = RideOfferStatus.ACCEPTED
    offer.responded_at = datetime.now(UTC)
    ride.driver_id = driver_id
    ride.vehicle_id = vehicle.id
    # Passenger-facing identity is frozen when the assignment is accepted.
    # A later vehicle/profile edit must not rewrite the completed-ride record.
    ride.assigned_driver_name = profile.display_name
    ride.assigned_vehicle_make = vehicle.make
    ride.assigned_vehicle_model = vehicle.model
    ride.assigned_vehicle_color = vehicle.color
    ride.assigned_taxi_identifier = vehicle.taxi_identifier
    ride.status = RideStatus.ACCEPTED
    ride.accepted_at = datetime.now(UTC)
    profile.availability_status = AvailabilityStatus.EN_ROUTE
    profile.available_since = None
    database_session.add(RideEvent(ride_id=ride.id, event_type=RideEventType.STATUS_CHANGED, previous_status=RideStatus.MATCHING, new_status=RideStatus.ACCEPTED))
    await enqueue(
        database_session,
        topic="ride.accepted",
        payload={"ride_id": str(ride.id), "passenger_id": str(ride.passenger_id), "driver_id": str(driver_id)},
    )
    await notify(
        database_session,
        user_id=ride.passenger_id,
        notification_type="DRIVER_ASSIGNED",
        title="Driver assigned",
        body="A driver has accepted your ride.",
        data={"ride_id": str(ride.id)},
    )
    await database_session.flush()
    return ride


async def decline_offer(database_session: AsyncSession, offer_id, driver_id, reason: str):
    ride, offer = await lock_owned_offer(database_session, offer_id, driver_id)
    if ride is None or ride.status != RideStatus.MATCHING or offer is None or offer.status != RideOfferStatus.PENDING:
        raise RideOfferUnavailable("Ride offer is not available.")
    profile = await lock_driver(database_session, driver_id)
    if offer.expires_at <= datetime.now(UTC):
        offer.status = RideOfferStatus.EXPIRED
        raise RideOfferUnavailable("Ride offer has expired.")
    offer.status = RideOfferStatus.DECLINED
    offer.decline_reason = reason
    offer.responded_at = datetime.now(UTC)
    if profile is not None and profile.availability_status == AvailabilityStatus.OFFERED_RIDE:
        profile.availability_status = AvailabilityStatus.AVAILABLE
        if profile.available_since is None:
            profile.available_since = offer.responded_at
    if ride is not None and ride.status == RideStatus.MATCHING:
        database_session.add(
            RideEvent(
                ride_id=ride.id,
                event_type=RideEventType.OFFER_DECLINED,
                previous_status=RideStatus.MATCHING,
                new_status=RideStatus.MATCHING,
                actor_user_id=profile.user_id if profile is not None else None,
                reason=reason,
            )
        )
    await database_session.flush()
    return offer.ride_id
