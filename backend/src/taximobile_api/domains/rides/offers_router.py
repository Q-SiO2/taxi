from datetime import UTC, datetime
from uuid import UUID

from geoalchemy2 import Geometry
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.auth.dependencies import CurrentPrincipal, authenticated_principal
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.drivers.service import DriverMissing, driver_for_user
from taximobile_api.domains.rides.models import Ride, RideOffer, RideOfferStatus
from taximobile_api.domains.rides.schemas import Coordinate, RideOfferAcceptResponse, RideOfferDeclineRequest, RideOfferDeclineResponse, RideOfferFareResponse, RideOfferListResponse, RideOfferResponse
from taximobile_api.domains.rides.service import RideOfferUnavailable, accept_offer_atomically, decline_offer
from taximobile_api.domains.matching.service import dispatch_ride


router = APIRouter(tags=["ride-offers"])


async def offer_response(session: AsyncSession, offer: RideOffer) -> RideOfferResponse:
    ride_id, latitude, longitude, address, quoted_amount, quoted_currency = (
        await session.execute(
            select(
                Ride.id,
                func.ST_Y(Ride.pickup_point.cast(Geometry(geometry_type="POINT", srid=4326))),
                func.ST_X(Ride.pickup_point.cast(Geometry(geometry_type="POINT", srid=4326))),
                Ride.pickup_address,
                Ride.quoted_amount,
                Ride.quoted_currency,
            ).where(Ride.id == offer.ride_id)
        )
    ).one()
    estimated_fare = (
        RideOfferFareResponse(amount=f"{quoted_amount:.2f}", currency=quoted_currency)
        if quoted_amount is not None and quoted_currency is not None
        else None
    )
    return RideOfferResponse(
        id=offer.id,
        ride_id=ride_id,
        pickup=Coordinate(latitude=latitude, longitude=longitude, address=address),
        estimated_pickup_distance_meters=offer.estimated_pickup_distance_meters,
        estimated_pickup_time_seconds=offer.estimated_pickup_time_seconds,
        estimated_fare=estimated_fare,
        matching_algorithm_version=offer.matching_algorithm_version,
        issued_at=offer.created_at,
        expires_at=offer.expires_at,
    )


@router.get("/drivers/me/ride-offers", response_model=RideOfferListResponse)
async def list_offers(
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> RideOfferListResponse:
    try:
        profile = await driver_for_user(session, principal.user_id)
    except DriverMissing as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    server_time = datetime.now(UTC)
    offers = list(await session.scalars(select(RideOffer).where(RideOffer.driver_id == profile.id, RideOffer.status == RideOfferStatus.PENDING, RideOffer.expires_at > server_time)))
    return RideOfferListResponse(server_time=server_time, offers=[await offer_response(session, offer) for offer in offers])


@router.post("/ride-offers/{offer_id}/accept", response_model=RideOfferAcceptResponse)
async def accept_offer(
    offer_id: UUID,
    request: Request,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> RideOfferAcceptResponse:
    try:
        async with session.begin():
            profile = await driver_for_user(session, principal.user_id)
            ride = await accept_offer_atomically(session, offer_id, profile.id)
    except DriverMissing as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except RideOfferUnavailable as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This ride offer is no longer available.") from error
    # The transactional outbox processor reloads this committed ride before it
    # sends any best-effort refresh hint to a connected passenger.
    return RideOfferAcceptResponse(ride_id=ride.id, status=ride.status.value)


@router.post("/ride-offers/{offer_id}/decline", response_model=RideOfferDeclineResponse)
async def decline_offer_endpoint(
    offer_id: UUID,
    payload: RideOfferDeclineRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> RideOfferDeclineResponse:
    try:
        async with session.begin():
            profile = await driver_for_user(session, principal.user_id)
            ride_id = await decline_offer(session, offer_id, profile.id, payload.reason)
            await dispatch_ride(session, ride_id, request.app.state.settings)
    except DriverMissing as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except RideOfferUnavailable as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This ride offer is no longer available.") from error
    return RideOfferDeclineResponse()
