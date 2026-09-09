"""Live readiness at scheduled handoff, independent of future commitment eligibility."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.driver_applications.service import location_is_inside_active_service_area
from taximobile_api.domains.drivers.models import AvailabilityStatus, DriverLocation, DriverProfile
from taximobile_api.domains.markets.models import City, ServiceType


async def handoff_readiness_failure(
    session: AsyncSession,
    profile: DriverProfile,
    city: City,
    service_type: ServiceType,
    *,
    now: datetime,
    location_freshness_seconds: int,
) -> str | None:
    """Return a fixed audit code, never location data or client-supplied authority."""
    if profile.availability_status != AvailabilityStatus.AVAILABLE:
        return "DRIVER_NOT_AVAILABLE"
    if profile.online_city_id != city.id or profile.online_service_type != service_type:
        return "DRIVER_LIVE_SCOPE_MISMATCH"
    location = await session.scalar(
        select(DriverLocation)
        .where(DriverLocation.driver_id == profile.id)
        .order_by(DriverLocation.observed_at.desc(), DriverLocation.id.desc())
        .limit(1)
    )
    if location is None:
        return "DRIVER_LOCATION_MISSING"
    age = (now - location.observed_at).total_seconds()
    # Match the existing online admission clock-skew allowance.
    if age < -60:
        return "DRIVER_LOCATION_FUTURE"
    if age > location_freshness_seconds:
        return "DRIVER_LOCATION_STALE"
    if not await location_is_inside_active_service_area(
        session, city=city, location_id=location.id, now=now,
    ):
        return "DRIVER_OUTSIDE_SERVICE_AREA"
    return None
