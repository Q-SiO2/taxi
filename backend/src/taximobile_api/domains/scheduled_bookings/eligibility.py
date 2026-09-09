"""Professional eligibility shared by scheduled offering, commitment and handoff.

Future commitments do not require immediate online availability. They do require
current professional eligibility, independently of a city's evidence requirements.
Live-location/readiness admission is a separate policy concern.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.drivers.models import (
    DriverAccountStatus, DriverProfile, Vehicle, VerificationStatus,
)
from taximobile_api.domains.drivers.service import (
    active_vehicle_eligibility_failure, invalid_driver_credentials,
)


async def scheduled_driver_eligibility_failure(
    session: AsyncSession,
    profile: DriverProfile,
    vehicle: Vehicle | None,
    *,
    now: datetime,
) -> str | None:
    """Do not let city authorization mask suspension or expired global facts."""
    if profile.account_status != DriverAccountStatus.ACTIVE:
        return "Driver account is not active."
    if profile.verification_status != VerificationStatus.APPROVED:
        return "Driver verification is not approved."
    if vehicle is None or profile.active_vehicle_id != vehicle.id:
        return "An eligible active vehicle must be selected."
    vehicle_failure = active_vehicle_eligibility_failure(profile, vehicle)
    if vehicle_failure:
        return vehicle_failure
    if await session.scalar(select(invalid_driver_credentials(profile.id, now))):
        return "A professional credential is unverified or expired."
    return None
