from datetime import UTC, datetime, timedelta
from uuid import uuid4

from taximobile_api.domains.drivers.models import (
    AvailabilityStatus,
    DriverAccountStatus,
    DriverProfile,
    Vehicle,
    VehicleStatus,
    VehicleVerificationStatus,
    VerificationStatus,
)
from taximobile_api.domains.drivers.service import active_vehicle_eligibility_failure, online_eligibility_failure


def driver_profile() -> DriverProfile:
    return DriverProfile(
        user_id=uuid4(),
        display_name="Driver",
        account_status=DriverAccountStatus.PENDING,
        verification_status=VerificationStatus.NOT_STARTED,
        availability_status=AvailabilityStatus.OFFLINE,
    )


def test_pending_driver_cannot_go_online() -> None:
    assert online_eligibility_failure(driver_profile(), None) == "Driver account is not active."


def test_driver_handling_a_ride_cannot_overwrite_availability() -> None:
    profile = driver_profile()
    profile.availability_status = AvailabilityStatus.ON_RIDE

    assert online_eligibility_failure(profile, None) == (
        "Driver availability cannot be changed while handling a ride."
    )


def test_approved_driver_requires_a_verified_active_vehicle() -> None:
    profile = driver_profile()
    profile.account_status = DriverAccountStatus.ACTIVE
    profile.verification_status = VerificationStatus.APPROVED
    vehicle = Vehicle(
        driver_id=profile.id,
        make="Example",
        model="Taxi",
        year=2025,
        color="White",
        registration_number="AB-123",
        status=VehicleStatus.ACTIVE,
        verification_status=VehicleVerificationStatus.PENDING,
    )

    assert online_eligibility_failure(profile, vehicle) == "Selected vehicle is not eligible."

    vehicle.verification_status = VehicleVerificationStatus.VERIFIED
    now = datetime.now(UTC)
    assert online_eligibility_failure(profile, vehicle, latest_location_at=now, now=now) is None
    assert online_eligibility_failure(profile, vehicle, latest_location_at=now - timedelta(seconds=31), now=now) == (
        "Update current location before going online."
    )
    assert active_vehicle_eligibility_failure(profile, vehicle) is None

    vehicle.verification_status = VehicleVerificationStatus.PENDING
    assert active_vehicle_eligibility_failure(profile, vehicle) == "Vehicle is not eligible for active dispatch."
