"""Current operational location at immediate assignment, not offer-time history.

The caller owns the ride -> offer -> driver locks. Location ingestion also owns
the driver lock, so a competing observation either commits before this read or
waits for assignment. Read scalar facts rather than a cached ORM observation.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.driver_applications.service import location_is_inside_active_service_area
from taximobile_api.domains.drivers.models import DriverLocation
from taximobile_api.domains.markets.models import City


def observation_age_failure(
    observed_at: datetime | None, *, now: datetime, freshness_seconds: int,
) -> str | None:
    """Fixed internal refusal codes; never expose coordinates or another ride."""
    if observed_at is None:
        return "DRIVER_LOCATION_MISSING"
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        return "DRIVER_LOCATION_INVALID_TIME"
    age = (now - observed_at).total_seconds()
    if age < -60:
        return "DRIVER_LOCATION_FUTURE"
    if age > freshness_seconds:
        return "DRIVER_LOCATION_STALE"
    return None


async def offer_location_failure(
    session: AsyncSession, *, driver_id: UUID, city_id: UUID,
    now: datetime, freshness_seconds: int,
) -> str | None:
    location = (await session.execute(
        select(DriverLocation.id, DriverLocation.observed_at)
        .where(DriverLocation.driver_id == driver_id)
        .order_by(DriverLocation.observed_at.desc(), DriverLocation.id.desc())
        .limit(1)
    )).first()
    failure = observation_age_failure(
        location.observed_at if location is not None else None,
        now=now, freshness_seconds=freshness_seconds,
    )
    if failure:
        return failure
    # Refresh after driver/account lock waits: a preloaded city object is not
    # authority for its current active service-area configuration.
    city = await session.get(City, city_id, populate_existing=True)
    if city is None or not await location_is_inside_active_service_area(
        session, city=city, location_id=location.id, now=now,
    ):
        return "DRIVER_OUTSIDE_SERVICE_AREA"
    return None
