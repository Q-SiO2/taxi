from datetime import UTC, datetime
from math import asin, cos, radians, sin, sqrt

from geoalchemy2 import Geometry
from geoalchemy2.elements import WKTElement
from sqlalchemy import and_, exists, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.drivers.models import (
    AvailabilityStatus,
    CredentialVerificationStatus,
    DriverAccountStatus,
    DriverCredential,
    DriverProfile,
    DriverVerification,
    Vehicle,
    VehicleStatus,
    VehicleVerificationStatus,
    VerificationStatus,
    DriverLocation,
)
from taximobile_api.domains.drivers.schemas import DriverApplicationRequest, LocationUpdateRequest, VehicleCreateRequest
from taximobile_api.domains.driver_applications.models import (
    ApplicationEvidenceStatus,
    CityApplicationStatus,
    DriverApplicationEvidence,
    DriverCityApplication,
)


class DriverApplicationExists(ValueError):
    pass


class DriverMissing(ValueError):
    pass


class VehicleConflict(ValueError):
    pass


class VehicleNotEligible(ValueError):
    pass


class VehicleOperationUnavailable(ValueError):
    pass


class VerificationSubmissionUnavailable(ValueError):
    pass


class LocationRejected(ValueError):
    pass


async def invalidate_open_application_vehicle_evidence(
    database_session: AsyncSession,
    vehicle_id,
) -> None:
    """Require fresh staff review after an applicant changes/deactivates a vehicle."""
    editable_or_reviewable_applications = select(DriverCityApplication.id).where(
        DriverCityApplication.status.in_(
            {
                CityApplicationStatus.NOT_STARTED,
                CityApplicationStatus.SUBMITTED,
                CityApplicationStatus.UNDER_REVIEW,
                CityApplicationStatus.ADDITIONAL_INFORMATION_REQUIRED,
            }
        )
    )
    await database_session.execute(
        update(DriverApplicationEvidence)
        .where(
            DriverApplicationEvidence.vehicle_id == vehicle_id,
            DriverApplicationEvidence.application_id.in_(
                editable_or_reviewable_applications
            ),
        )
        .values(status=ApplicationEvidenceStatus.PENDING)
    )


def invalid_driver_credentials(driver_id, now: datetime):
    """Return a SQL predicate for known-invalid professional credentials.

    An empty set stays eligible until a jurisdiction-specific required-type
    policy exists. Once a fact exists, non-verification or expiry cannot be
    ignored by availability or dispatch.
    """

    return exists(
        select(DriverCredential.id).where(
            DriverCredential.driver_id == driver_id,
            or_(
                DriverCredential.verification_status != CredentialVerificationStatus.VERIFIED,
                and_(
                    DriverCredential.expires_at.is_not(None),
                    DriverCredential.expires_at <= now,
                ),
            ),
        )
    )


async def apply_to_drive(
    database_session: AsyncSession, user_id, request: DriverApplicationRequest
) -> DriverProfile:
    if await database_session.scalar(select(DriverProfile.id).where(DriverProfile.user_id == user_id)):
        raise DriverApplicationExists("A driver application already exists.")
    profile = DriverProfile(user_id=user_id, display_name=request.display_name.strip())
    database_session.add(profile)
    await database_session.flush()
    database_session.add(DriverVerification(driver_id=profile.id, status=VerificationStatus.NOT_STARTED))
    await database_session.flush()
    # Preserve the original `/drivers/apply` contract by attaching the new
    # profile to the deterministic Casablanca compatibility application.  New
    # city-aware clients use the dedicated application endpoint directly.
    from taximobile_api.domains.driver_applications.service import ensure_legacy_city_application

    await ensure_legacy_city_application(database_session, profile)
    return profile


async def submit_verification(database_session: AsyncSession, profile: DriverProfile) -> DriverVerification:
    """Place a driver application in the human-review queue.

    This is intentionally not evidence that documents are valid. It records the
    driver's explicit submission and lets the administrator decide approval
    only after the jurisdiction's secure-document process has been completed.
    """
    if profile.verification_status == VerificationStatus.SUBMITTED:
        existing = await database_session.scalar(
            select(DriverVerification)
            .where(DriverVerification.driver_id == profile.id, DriverVerification.status == VerificationStatus.SUBMITTED)
            .order_by(DriverVerification.created_at.desc())
            .limit(1)
        )
        assert existing is not None
        return existing
    if profile.verification_status not in {
        VerificationStatus.NOT_STARTED,
        VerificationStatus.ADDITIONAL_INFORMATION_REQUIRED,
    }:
        raise VerificationSubmissionUnavailable("This driver application cannot be submitted in its current verification state.")
    submitted_at = datetime.now(UTC)
    profile.verification_status = VerificationStatus.SUBMITTED
    verification = DriverVerification(
        driver_id=profile.id,
        status=VerificationStatus.SUBMITTED,
        submitted_at=submitted_at,
    )
    database_session.add(verification)
    await database_session.flush()
    from taximobile_api.domains.driver_applications.service import sync_legacy_submission

    await sync_legacy_submission(database_session, profile)
    return verification


async def driver_for_user(database_session: AsyncSession, user_id, *, lock: bool = False) -> DriverProfile:
    statement = select(DriverProfile).where(DriverProfile.user_id == user_id)
    if lock:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    profile = await database_session.scalar(statement)
    if profile is None:
        raise DriverMissing("No driver application exists for this account.")
    return profile


async def register_vehicle(
    database_session: AsyncSession, profile: DriverProfile, request: VehicleCreateRequest
) -> Vehicle:
    if await database_session.scalar(select(Vehicle.id).where(Vehicle.registration_number == request.registration_number)):
        raise VehicleConflict("A vehicle with that registration number already exists.")
    vehicle = Vehicle(driver_id=profile.id, **request.model_dump())
    database_session.add(vehicle)
    await database_session.flush()
    return vehicle


def can_change_vehicle(profile: DriverProfile) -> str | None:
    if profile.availability_status != AvailabilityStatus.OFFLINE:
        return "Go offline before changing a vehicle."
    return None


def active_vehicle_eligibility_failure(profile: DriverProfile, vehicle: Vehicle | None) -> str | None:
    if vehicle is None or vehicle.driver_id != profile.id:
        return "Vehicle not found."
    if vehicle.status != VehicleStatus.ACTIVE or vehicle.verification_status != VehicleVerificationStatus.VERIFIED:
        return "Vehicle is not eligible for active dispatch."
    return None


def online_eligibility_failure(
    profile: DriverProfile,
    vehicle: Vehicle | None,
    *,
    latest_location_at: datetime | None = None,
    now: datetime | None = None,
    location_freshness_seconds: int = 30,
) -> str | None:
    if profile.availability_status not in {
        AvailabilityStatus.OFFLINE,
        AvailabilityStatus.PAUSED,
        AvailabilityStatus.AVAILABLE,
    }:
        return "Driver availability cannot be changed while handling a ride."
    if profile.account_status != DriverAccountStatus.ACTIVE:
        return "Driver account is not active."
    if profile.verification_status != VerificationStatus.APPROVED:
        return "Driver verification is not approved."
    if vehicle is None:
        return "An active vehicle must be selected."
    if vehicle.driver_id != profile.id:
        return "Selected vehicle does not belong to the driver."
    if vehicle.status != VehicleStatus.ACTIVE or vehicle.verification_status != VehicleVerificationStatus.VERIFIED:
        return "Selected vehicle is not eligible."
    current_time = now or datetime.now(UTC)
    if latest_location_at is None:
        return "Update current location before going online."
    location_age = (current_time - latest_location_at.astimezone(UTC)).total_seconds()
    if location_age < -60 or location_age > location_freshness_seconds:
        return "Update current location before going online."
    return None


def location_failure(profile: DriverProfile, observed_at: datetime, now: datetime) -> str | None:
    if profile.availability_status in {AvailabilityStatus.OFFLINE, AvailabilityStatus.PAUSED}:
        if (
            profile.account_status != DriverAccountStatus.ACTIVE
            or profile.verification_status != VerificationStatus.APPROVED
        ):
            return "Only an approved driver can stage an offline location."
    elif profile.availability_status not in {
        AvailabilityStatus.AVAILABLE,
        AvailabilityStatus.OFFERED_RIDE,
        AvailabilityStatus.EN_ROUTE,
        AvailabilityStatus.AT_PICKUP,
        AvailabilityStatus.ON_RIDE,
    }:
        return "Driver is not in an operational availability state."
    if observed_at.tzinfo is None:
        return "Location timestamp must include a timezone."
    age_seconds = (now - observed_at.astimezone(UTC)).total_seconds()
    if age_seconds > 300 or age_seconds < -60:
        return "Location timestamp is outside the accepted freshness window."
    return None


def haversine_meters(first_latitude: float, first_longitude: float, second_latitude: float, second_longitude: float) -> float:
    latitude_delta = radians(second_latitude - first_latitude)
    longitude_delta = radians(second_longitude - first_longitude)
    a = sin(latitude_delta / 2) ** 2 + cos(radians(first_latitude)) * cos(radians(second_latitude)) * sin(longitude_delta / 2) ** 2
    return 6_371_000 * 2 * asin(sqrt(a))


def movement_failure(
    previous_latitude: float,
    previous_longitude: float,
    previous_observed_at: datetime,
    latitude: float,
    longitude: float,
    observed_at: datetime,
) -> str | None:
    seconds = (observed_at - previous_observed_at).total_seconds()
    if seconds <= 0:
        return "Location timestamp must be newer than the previous update."
    speed = haversine_meters(previous_latitude, previous_longitude, latitude, longitude) / seconds
    if speed > 55.56:  # 200 km/h is outside credible taxi movement.
        return "Location movement is not credible."
    return None


async def record_location(
    database_session: AsyncSession, profile: DriverProfile, request: LocationUpdateRequest
) -> DriverLocation:
    now = datetime.now(UTC)
    reason = location_failure(profile, request.observed_at, now)
    if reason:
        raise LocationRejected(reason)
    if profile.availability_status in {AvailabilityStatus.OFFLINE, AvailabilityStatus.PAUSED}:
        vehicle = await database_session.get(Vehicle, profile.active_vehicle_id) if profile.active_vehicle_id else None
        vehicle_reason = active_vehicle_eligibility_failure(profile, vehicle)
        if vehicle_reason:
            raise LocationRejected("Select a verified active vehicle before updating location.")
    previous = (
        await database_session.execute(
            select(
                DriverLocation.observed_at,
                func.ST_Y(DriverLocation.point.cast(Geometry(geometry_type="POINT", srid=4326))),
                func.ST_X(DriverLocation.point.cast(Geometry(geometry_type="POINT", srid=4326))),
            )
        .where(DriverLocation.driver_id == profile.id)
        .order_by(DriverLocation.observed_at.desc())
        .limit(1)
        )
    ).first()
    if previous is not None:
        previous_observed_at, previous_latitude, previous_longitude = previous
        movement_reason = movement_failure(
            previous_latitude,
            previous_longitude,
            previous_observed_at,
            request.latitude,
            request.longitude,
            request.observed_at,
        )
        if movement_reason:
            raise LocationRejected(movement_reason)
    location = DriverLocation(
        driver_id=profile.id,
        point=WKTElement(f"POINT({request.longitude} {request.latitude})", srid=4326),
        observed_at=request.observed_at,
        accuracy_meters=request.accuracy,
        heading_degrees=request.heading,
        speed_meters_per_second=request.speed,
    )
    database_session.add(location)
    await database_session.flush()
    return location
