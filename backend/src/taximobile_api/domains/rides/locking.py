"""Live ride commands lock the aggregate before offers and driver state.

Call inside the command transaction. Refresh existing ORM objects after waits:
an identity-map cache is not authority for a competing committed command.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.drivers.models import DriverProfile
from taximobile_api.domains.rides.models import Ride, RideOffer


async def lock_ride(session: AsyncSession, ride_id: UUID) -> Ride | None:
    return await session.scalar(
        select(Ride).where(Ride.id == ride_id)
        .with_for_update().execution_options(populate_existing=True)
    )


async def lock_driver(session: AsyncSession, driver_id: UUID) -> DriverProfile | None:
    return await session.scalar(
        select(DriverProfile).where(DriverProfile.id == driver_id)
        .with_for_update().execution_options(populate_existing=True)
    )


async def lock_owned_offer(
    session: AsyncSession, offer_id: UUID, driver_id: UUID,
) -> tuple[Ride | None, RideOffer | None]:
    # Resolve ownership without locking the child ahead of the parent.
    ride_id = await session.scalar(
        select(RideOffer.ride_id).where(
            RideOffer.id == offer_id, RideOffer.driver_id == driver_id,
        )
    )
    if ride_id is None:
        return None, None
    ride = await lock_ride(session, ride_id)
    if ride is None:
        return None, None
    offer = await session.scalar(
        select(RideOffer).where(RideOffer.id == offer_id, RideOffer.driver_id == driver_id)
        .with_for_update().execution_options(populate_existing=True)
    )
    return ride, offer
