from geoalchemy2 import Geometry
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from taximobile_api.domains.auth.dependencies import CurrentPrincipal, authenticated_principal
from taximobile_api.domains.auth.router import database_session
from datetime import UTC, datetime

from taximobile_api.domains.rides.models import Ride, RideRating
from taximobile_api.domains.drivers.models import DriverLocation, DriverProfile, Vehicle
from taximobile_api.domains.drivers.service import DriverMissing, driver_for_user
from taximobile_api.domains.rides.schemas import AssignedDriverResponse, AssignedVehicleResponse, CancellationRequest, Coordinate, LastKnownDriverLocationResponse, RideCompletionRequest, RideCompletionResponse, FareBreakdownResponse, FareEstimate, FareResponse, PaymentReceiptResponse, RideCreateRequest, RideEstimateRequest, RideEstimateResponse, RideListResponse, RideRatingCreateRequest, RideRatingListResponse, RideRatingResponse, RideReceiptResponse, RideResponse, RideTransitionResponse
from taximobile_api.domains.rides.models import RideStatus
from taximobile_api.domains.rides.service import InvalidRideTransition, RideForbidden, RideNotFound, assigned_driver_ride, cancel_assigned_driver_ride, cancel_passenger_ride, complete_assigned_ride, create_ride, owned_ride, transition_assigned_ride
from taximobile_api.domains.pricing.models import FareRecord
from taximobile_api.domains.payments.models import Payment
from taximobile_api.domains.pricing.service import NoActiveTariff, active_tariff, finalized_fare_breakdown, fixed_fare_amount
from taximobile_api.domains.matching.service import dispatch_ride
from taximobile_api.domains.notifications.service import notify
from taximobile_api.domains.idempotency.service import (
    IdempotencyKeyReuse,
    IdempotentReplay,
    InvalidIdempotencyKey,
    begin_command,
    finish_command,
)


router = APIRouter(tags=["rides"])


async def response_for(
    session: AsyncSession,
    ride: Ride,
    *,
    include_driver_location: bool = False,
) -> RideResponse:
    pickup_latitude, pickup_longitude, destination_latitude, destination_longitude = (
        await session.execute(
            select(
                func.ST_Y(Ride.pickup_point.cast(Geometry(geometry_type="POINT", srid=4326))),
                func.ST_X(Ride.pickup_point.cast(Geometry(geometry_type="POINT", srid=4326))),
                func.ST_Y(Ride.destination_point.cast(Geometry(geometry_type="POINT", srid=4326))),
                func.ST_X(Ride.destination_point.cast(Geometry(geometry_type="POINT", srid=4326))),
            )
            .where(Ride.id == ride.id)
        )
    ).one()
    assigned_driver = None
    if (
        ride.assigned_driver_name is not None
        and ride.assigned_vehicle_make is not None
        and ride.assigned_vehicle_model is not None
        and ride.assigned_vehicle_color is not None
    ):
        assigned_driver = AssignedDriverResponse(
            display_name=ride.assigned_driver_name,
            vehicle=AssignedVehicleResponse(
                make=ride.assigned_vehicle_make,
                model=ride.assigned_vehicle_model,
                color=ride.assigned_vehicle_color,
                taxi_identifier=ride.assigned_taxi_identifier,
            ),
        )
    elif ride.driver_id is not None and ride.vehicle_id is not None:
        # Compatibility fallback for rides accepted before the snapshot upgrade.
        driver_and_vehicle = await session.execute(
            select(DriverProfile.display_name, Vehicle.make, Vehicle.model, Vehicle.color, Vehicle.taxi_identifier)
            .join(Vehicle, Vehicle.id == ride.vehicle_id)
            .where(DriverProfile.id == ride.driver_id)
        )
        row = driver_and_vehicle.one_or_none()
        if row is not None:
            display_name, make, model, color, taxi_identifier = row
            assigned_driver = AssignedDriverResponse(
                display_name=display_name,
                vehicle=AssignedVehicleResponse(
                    make=make,
                    model=model,
                    color=color,
                    taxi_identifier=taxi_identifier,
                ),
            )
    last_known_driver_location = None
    if (
        include_driver_location
        and ride.driver_id is not None
        and ride.accepted_at is not None
        and ride.status in {
            RideStatus.ACCEPTED,
            RideStatus.DRIVER_EN_ROUTE,
            RideStatus.DRIVER_ARRIVED,
            RideStatus.IN_PROGRESS,
        }
    ):
        # Expose only a single observation submitted after this ride was
        # assigned. Pre-assignment dispatch history and all terminal-ride
        # locations stay private.
        location_row = (
            await session.execute(
                select(
                    func.ST_Y(DriverLocation.point.cast(Geometry(geometry_type="POINT", srid=4326))),
                    func.ST_X(DriverLocation.point.cast(Geometry(geometry_type="POINT", srid=4326))),
                    DriverLocation.observed_at,
                    DriverLocation.accuracy_meters,
                )
                .where(
                    DriverLocation.driver_id == ride.driver_id,
                    DriverLocation.observed_at >= ride.accepted_at,
                )
                .order_by(DriverLocation.observed_at.desc())
                .limit(1)
            )
        ).one_or_none()
        if location_row is not None:
            latitude, longitude, observed_at, accuracy_meters = location_row
            last_known_driver_location = LastKnownDriverLocationResponse(
                latitude=latitude,
                longitude=longitude,
                observed_at=observed_at,
                accuracy_meters=accuracy_meters,
            )
    return RideResponse(
        id=ride.id,
        status=ride.status.value,
        pickup=Coordinate(latitude=pickup_latitude, longitude=pickup_longitude, address=ride.pickup_address),
        destination=Coordinate(latitude=destination_latitude, longitude=destination_longitude, address=ride.destination_address),
        completed_at=ride.completed_at,
        driver=assigned_driver,
        last_known_driver_location=last_known_driver_location,
    )


@router.post("/rides", response_model=RideResponse, status_code=status.HTTP_201_CREATED)
async def request_ride(
    payload: RideCreateRequest,
    request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
    ) -> RideResponse:
    try:
        async with session.begin():
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="ride.create",
                key=idempotency_key,
                payload=payload.model_dump(mode="json"),
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            if not await request.app.state.rate_limiter.allow(
                f"ride-create:{principal.user_id}",
                limit=request.app.state.settings.ride_creation_rate_limit_per_minute,
                window_seconds=60,
            ):
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many ride requests. Try again shortly.")
            quote = await active_tariff(session, datetime.now(UTC))
            fixed_fare_amount(quote)
            ride = await create_ride(session, principal.user_id, payload, quote)
            offer = await dispatch_ride(session, ride.id, request.app.state.settings)
            response = RideResponse(
                id=ride.id,
                status=ride.status.value,
                pickup=payload.pickup,
                destination=payload.destination,
                completed_at=ride.completed_at,
            )
            await finish_command(session, command, status_code=status.HTTP_201_CREATED, payload=response.model_dump(mode="json"))
    except NoActiveTariff as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No active tariff is available.") from error
    except InvalidIdempotencyKey as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except IdempotencyKeyReuse as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    # The transactional outbox processor reloads and delivers the optional
    # refresh hint after commit; the command response remains authoritative.
    return response


@router.post("/rides/estimate", response_model=RideEstimateResponse)
async def estimate_ride(
    payload: RideEstimateRequest,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> RideEstimateResponse:
    del payload, principal  # Route validation/authentication are intentional even for an MVP fixed tariff.
    try:
        rule = await active_tariff(session, datetime.now(UTC))
        amount = fixed_fare_amount(rule)
    except NoActiveTariff as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No active tariff is available.") from error
    return RideEstimateResponse(
        estimate=FareEstimate(amount=str(amount), currency=rule.currency, pricing_rule_version=rule.version)
    )


@router.get("/rides/{ride_id}", response_model=RideResponse)
async def get_ride(
    ride_id: UUID,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> RideResponse:
    try:
        ride = await participant_ride(session, ride_id, principal.user_id)
    except RideNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except RideForbidden as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot access this ride.") from error
    return await response_for(session, ride, include_driver_location=True)


def fare_breakdown_response(fare: FareRecord) -> FareBreakdownResponse:
    version, components = finalized_fare_breakdown(fare)
    return FareBreakdownResponse(
        amount=str(fare.total_amount),
        currency=fare.currency,
        pricing_rule_version=version,
        components=components,
    )


@router.get("/rides/{ride_id}/fare", response_model=FareBreakdownResponse)
async def get_ride_fare(
    ride_id: UUID,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> FareBreakdownResponse:
    try:
        await owned_ride(session, ride_id, principal.user_id)
    except RideNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except RideForbidden as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot access this ride.") from error
    fare = await session.scalar(select(FareRecord).where(FareRecord.ride_id == ride_id))
    if fare is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="A finalized fare is not available.")
    return fare_breakdown_response(fare)


@router.get("/rides/{ride_id}/receipt", response_model=RideReceiptResponse)
async def get_ride_receipt(
    ride_id: UUID,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> RideReceiptResponse:
    """Return a completed passenger ride's server-authoritative receipt.

    A receipt is a read of immutable fare/payment facts, never evidence that a
    client has completed payment. Provider identifiers intentionally stay out of
    this participant-facing payload.
    """
    try:
        ride = await owned_ride(session, ride_id, principal.user_id)
    except RideNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except RideForbidden as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot access this ride.") from error
    fare = await session.scalar(select(FareRecord).where(FareRecord.ride_id == ride.id))
    payment = await session.scalar(select(Payment).where(Payment.ride_id == ride.id))
    if ride.status != RideStatus.COMPLETED or ride.completed_at is None or fare is None or payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="A finalized receipt is not available.")
    return RideReceiptResponse(
        ride_id=ride.id,
        completed_at=ride.completed_at,
        fare=fare_breakdown_response(fare),
        payment=PaymentReceiptResponse(method=payment.method.value, status=payment.status.value),
    )


async def participant_ride(session: AsyncSession, ride_id: UUID, user_id: UUID) -> Ride:
    """Return a ride only to its passenger or assigned driver.

    This shared ownership check prevents both ride detail and ratings from
    becoming a way to discover unrelated rides or passenger identity.
    """
    ride = await session.get(Ride, ride_id)
    if ride is None:
        raise RideNotFound("Ride not found.")
    if ride.passenger_id == user_id:
        return ride
    try:
        profile = await driver_for_user(session, user_id)
    except DriverMissing as error:
        raise RideForbidden("You cannot access this ride.") from error
    if ride.driver_id != profile.id:
        raise RideForbidden("You cannot access this ride.")
    return ride


@router.post("/rides/{ride_id}/rating", response_model=RideRatingResponse, status_code=status.HTTP_201_CREATED)
async def create_rating(
    ride_id: UUID,
    payload: RideRatingCreateRequest,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> RideRatingResponse:
    try:
        async with session.begin():
            ride = await owned_ride(session, ride_id, principal.user_id)
            if ride.status != RideStatus.COMPLETED or ride.driver_id is None:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only completed assigned rides can be rated.")
            driver = await session.get(DriverProfile, ride.driver_id)
            if driver is None:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This ride has no rateable driver.")
            existing = await session.scalar(
                select(RideRating).where(RideRating.ride_id == ride.id, RideRating.reviewer_id == principal.user_id)
            )
            if existing is not None:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You have already rated this ride.")
            rating = RideRating(
                ride_id=ride.id,
                reviewer_id=principal.user_id,
                reviewed_user_id=driver.user_id,
                score=payload.score,
                comment=payload.comment,
            )
            session.add(rating)
            await session.flush()
    except RideNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except RideForbidden as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot rate this ride.") from error
    return RideRatingResponse(id=rating.id, score=rating.score, comment=rating.comment, created_at=rating.created_at)


@router.get("/rides/{ride_id}/ratings", response_model=RideRatingListResponse)
async def list_ratings(
    ride_id: UUID,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> RideRatingListResponse:
    try:
        await participant_ride(session, ride_id, principal.user_id)
    except RideNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except RideForbidden as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot access ratings for this ride.") from error
    ratings = list(await session.scalars(select(RideRating).where(RideRating.ride_id == ride_id).order_by(RideRating.created_at)))
    return RideRatingListResponse(
        items=[RideRatingResponse(id=rating.id, score=rating.score, comment=rating.comment, created_at=rating.created_at) for rating in ratings]
    )


@router.get("/rides", response_model=RideListResponse)
async def list_rides(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    ride_status: RideStatus | None = Query(default=None, alias="status"),
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> RideListResponse:
    filters = [Ride.passenger_id == principal.user_id]
    if ride_status is not None:
        filters.append(Ride.status == ride_status)
    statement = select(Ride).where(*filters).order_by(Ride.created_at.desc())
    rides = list(await session.scalars(statement.offset((page - 1) * limit).limit(limit)))
    total = await session.scalar(select(func.count()).select_from(Ride).where(*filters))
    return RideListResponse(items=[await response_for(session, ride) for ride in rides], page=page, limit=limit, total=total or 0)


@router.post("/rides/{ride_id}/cancel", response_model=RideResponse)
async def cancel_ride(
    ride_id: UUID,
    payload: CancellationRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> RideResponse:
    try:
        async with session.begin():
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="ride.cancel",
                key=idempotency_key,
                payload={"ride_id": str(ride_id), **payload.model_dump(mode="json")},
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            ride = await owned_ride(session, ride_id, principal.user_id)
            await cancel_passenger_ride(session, ride, principal.user_id, payload.reason)
            response = await response_for(session, ride)
            await finish_command(session, command, status_code=status.HTTP_200_OK, payload=response.model_dump(mode="json"))
    except RideNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except RideForbidden as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot access this ride.") from error
    except InvalidRideTransition as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except InvalidIdempotencyKey as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except IdempotencyKeyReuse as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return response


@router.post("/rides/{ride_id}/driver-cancel", response_model=RideResponse)
async def cancel_driver_ride(
    ride_id: UUID,
    payload: CancellationRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> RideResponse:
    """Record a driver's pre-start cancellation without reopening the ride.

    The route is distinct from passenger cancellation so audit data and
    authorization cannot be inferred from a client-provided cancellation type.
    """
    try:
        async with session.begin():
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="ride.driver_cancel",
                key=idempotency_key,
                payload={"ride_id": str(ride_id), **payload.model_dump(mode="json")},
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            profile = await driver_for_user(session, principal.user_id)
            ride = await assigned_driver_ride(session, ride_id, profile.id, lock=True)
            await cancel_assigned_driver_ride(session, ride, profile, principal.user_id, payload.reason)
            await notify(
                session,
                user_id=ride.passenger_id,
                notification_type="RIDE_CANCELLED_BY_DRIVER",
                title="Ride cancelled",
                body="Your driver cancelled this ride.",
                data={"ride_id": str(ride.id)},
            )
            response = await response_for(session, ride)
            await finish_command(session, command, status_code=status.HTTP_200_OK, payload=response.model_dump(mode="json"))
    except DriverMissing as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except RideForbidden as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot manage this ride.") from error
    except InvalidRideTransition as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except InvalidIdempotencyKey as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except IdempotencyKeyReuse as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return response


async def driver_transition(
    ride_id: UUID,
    target: RideStatus,
    principal: CurrentPrincipal,
    session: AsyncSession,
) -> RideTransitionResponse:
    try:
        async with session.begin():
            profile = await driver_for_user(session, principal.user_id)
            ride = await assigned_driver_ride(session, ride_id, profile.id, lock=True)
            await transition_assigned_ride(session, ride, profile, target, principal.user_id)
    except DriverMissing as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except RideForbidden as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot manage this ride.") from error
    except InvalidRideTransition as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    timestamp = ride.arrived_at if target == RideStatus.DRIVER_ARRIVED else ride.started_at if target == RideStatus.IN_PROGRESS else ride.en_route_at
    assert timestamp is not None
    return RideTransitionResponse(ride_id=ride.id, status=ride.status.value, occurred_at=timestamp)


@router.post("/rides/{ride_id}/en-route", response_model=RideTransitionResponse)
async def en_route(
    ride_id: UUID,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> RideTransitionResponse:
    return await driver_transition(ride_id, RideStatus.DRIVER_EN_ROUTE, principal, session)


@router.post("/rides/{ride_id}/arrived", response_model=RideTransitionResponse)
async def arrived(
    ride_id: UUID,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> RideTransitionResponse:
    return await driver_transition(ride_id, RideStatus.DRIVER_ARRIVED, principal, session)


@router.post("/rides/{ride_id}/start", response_model=RideTransitionResponse)
async def start(
    ride_id: UUID,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> RideTransitionResponse:
    return await driver_transition(ride_id, RideStatus.IN_PROGRESS, principal, session)


@router.post("/rides/{ride_id}/complete", response_model=RideCompletionResponse)
async def complete(
    ride_id: UUID,
    payload: RideCompletionRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> RideCompletionResponse:
    try:
        async with session.begin():
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="ride.complete",
                key=idempotency_key,
                payload={"ride_id": str(ride_id), **payload.model_dump(mode="json")},
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            profile = await driver_for_user(session, principal.user_id)
            ride = await assigned_driver_ride(session, ride_id, profile.id, lock=True)
            fare = await complete_assigned_ride(session, ride, profile, principal.user_id, payload.latitude, payload.longitude)
            response = RideCompletionResponse(
                ride_id=ride.id,
                status=ride.status.value,
                fare=FareResponse(amount=str(fare.total_amount), currency=fare.currency),
            )
            await finish_command(session, command, status_code=status.HTTP_200_OK, payload=response.model_dump(mode="json"))
    except DriverMissing as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except RideForbidden as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot manage this ride.") from error
    except InvalidRideTransition as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except NoActiveTariff as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No active tariff is available.") from error
    except InvalidIdempotencyKey as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except IdempotencyKeyReuse as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return response
