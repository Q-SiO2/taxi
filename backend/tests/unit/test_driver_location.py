from datetime import UTC, datetime, timedelta
from uuid import uuid4

from taximobile_api.domains.drivers.models import AvailabilityStatus, DriverAccountStatus, DriverProfile, VerificationStatus
from taximobile_api.domains.drivers.service import haversine_meters, location_failure, movement_failure


def operational_driver() -> DriverProfile:
    return DriverProfile(user_id=uuid4(), display_name="Driver", availability_status=AvailabilityStatus.AVAILABLE)


def test_location_requires_operational_driver_and_fresh_timestamp() -> None:
    now = datetime.now(UTC)
    profile = operational_driver()

    assert location_failure(profile, now, now) is None
    assert location_failure(profile, now - timedelta(minutes=6), now) == "Location timestamp is outside the accepted freshness window."
    profile.availability_status = AvailabilityStatus.OFFLINE
    assert location_failure(profile, now, now) == "Only an approved driver can stage an offline location."
    profile.account_status = DriverAccountStatus.ACTIVE
    profile.verification_status = VerificationStatus.APPROVED
    assert location_failure(profile, now, now) is None


def test_haversine_distance_is_approximately_correct() -> None:
    assert 90 < haversine_meters(0, 0, 0, 0.001) < 120


def test_location_rejects_impossible_movement_and_non_increasing_timestamps() -> None:
    start = datetime.now(UTC)

    assert movement_failure(34.0, -6.0, start, 35.0, -6.0, start + timedelta(seconds=1)) == "Location movement is not credible."
    assert movement_failure(34.0, -6.0, start, 34.0, -6.0, start) == "Location timestamp must be newer than the previous update."
