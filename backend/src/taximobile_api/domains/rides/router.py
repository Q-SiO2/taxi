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
from taximobile_api.domains.ride_communications.models import RideCoordinationMessage
from taximobile_api.domains.ride_communications.policy import (
    ACTIVE_COORDINATION_STATUSES,
    sender_role_for_code,
)
from taximobile_api.domains.ride_communications.schemas import RideCoordinationMessageResponse
from taximobile_api.domains.fixed_routes.service import (
    FixedRouteConflict,
    fixed_route_ride_summary,
    resolve_fixed_route_ride,
)
from taximobile_api.domains.drivers.models import DriverLocation, DriverProfile, Vehicle
from taximobile_api.domains.drivers.service import DriverMissing, driver_for_user
from taximobile_api.domains.rides.schemas import AssignedDriverResponse, AssignedVehicleResponse, CancellationRequest, Coordinate, LastKnownDriverLocationResponse, ManualTransferInstructionsResponse, RideCompletionRequest, RideCompletionResponse, FareBreakdownResponse, FareEconomicsResponse, FareEstimate, FareResponse, PaymentReceiptResponse, RideCreateRequest, RideEstimateRequest, RideEstimateResponse, RideListResponse, RideRatingCreateRequest, RideRatingListResponse, RideRatingResponse, RideReceiptResponse, RideResponse, RideTransitionResponse
from taximobile_api.domains.rides.models import RideStatus
from taximobile_api.domains.rides.service import InvalidRideTransition, RideForbidden, RideNotFound, assigned_driver_ride, cancel_assigned_driver_ride, cancel_passenger_ride, complete_assigned_ride, create_ride, owned_ride, transition_assigned_ride
from taximobile_api.domains.pricing.models import FareRecord
from taximobile_api.domains.payments.models import ManualTransferClaim, Payment, PaymentMethod, PaymentRefund
from taximobile_api.domains.payments.service import (
    PaymentCapabilityUnavailable,
    resolve_payment_capability,
)
from taximobile_api.domains.payments.schemas import (
    PassengerRefundResponse,
    PassengerRefundSummaryResponse,
)
from taximobile_api.domains.pricing.service import (
    FinancialQuote,
    InvalidFinancialPolicy,
    NoActiveTariff,
    finalized_fare_breakdown,
    quote_immediate_ride,
)
from taximobile_api.domains.matching.service import dispatch_ride
from taximobile_api.domains.notifications.service import notify
from taximobile_api.domains.idempotency.service import (
    IdempotencyKeyReuse,
    IdempotentReplay,
    InvalidIdempotencyKey,
    begin_command,
    finish_command,
)
from taximobile_api.domains.markets.service import (
    CityServiceUnavailable,
    resolve_on_demand_service_context,
)
from taximobile_api.domains.markets.models import ServiceType


router = APIRouter(tags=["rides"])


def quote_economics_response(quote: FinancialQuote) -> FareEconomicsResponse:
    return FareEconomicsResponse(
        transport_fare=str(quote.transport_fare_amount),
        scheduling_surcharge=str(quote.scheduling_surcharge_amount),
        operator_service_fee=str(quote.operator_fee_amount),
        passenger_total=str(quote.passenger_total_amount),
        expected_driver_net=str(quote.driver_net_amount),
        operator_allocation=str(quote.operator_allocation_amount),
        operator_fee_policy_version=quote.operator_fee_policy_version,
        operator_fee_calculation_mode=quote.operator_fee_calculation_mode.value,
        operator_fee_funding_mode=quote.operator_fee_funding_mode.value,
        scheduling_policy_version=quote.scheduling_policy_version,
    )


def fare_economics_response(fare: FareRecord) -> FareEconomicsResponse | None:
    snapshot = fare.snapshot
    if "operator_fee_policy_version" not in snapshot:
        return None
    return FareEconomicsResponse(
        transport_fare=str(snapshot["transport_fare"]),
        scheduling_surcharge=str(snapshot["scheduling_surcharge"]),
        operator_service_fee=str(snapshot["operator_fee"]),
        passenger_total=str(snapshot["passenger_total"]),
        expected_driver_net=str(snapshot["driver_net"]),
        operator_allocation=str(snapshot["operator_allocation"]),
        operator_fee_policy_version=str(snapshot["operator_fee_policy_version"]),
        operator_fee_calculation_mode=str(snapshot["operator_fee_calculation_mode"]),
        operator_fee_funding_mode=str(snapshot["operator_fee_funding_mode"]),
        scheduling_policy_version=(
            str(snapshot["scheduling_policy_version"])
            if snapshot.get("scheduling_policy_version") is not None
            else None
        ),
    )


async def response_for(
    session: AsyncSession,
    ride: Ride,
    *,
    include_driver_location: bool = False,
    include_coordination: bool = False,
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
    latest_coordination_message = None
    if include_coordination and ride.driver_id is not None and ride.status in ACTIVE_COORDINATION_STATUSES:
        latest_message = await session.scalar(
            select(RideCoordinationMessage)
            .where(RideCoordinationMessage.ride_id == ride.id)
            .order_by(RideCoordinationMessage.created_at.desc(), RideCoordinationMessage.id.desc())
            .limit(1)
        )
        if latest_message is not None:
            latest_coordination_message = RideCoordinationMessageResponse(
                id=latest_message.id,
                ride_id=latest_message.ride_id,
                sender_role=sender_role_for_code(latest_message.code),
                code=latest_message.code,
                created_at=latest_message.created_at,
            )
    return RideResponse(
        id=ride.id,
        city_id=ride.city_id,
        operator_id=ride.operator_id,
        service_type=ride.service_type.value,
        fixed_route=(
            await fixed_route_ride_summary(session, ride.fixed_route_direction_id)
            if ride.fixed_route_direction_id is not None
            else None
        ),
        status=ride.status.value,
        pickup=Coordinate(latitude=pickup_latitude, longitude=pickup_longitude, address=ride.pickup_address),
        destination=Coordinate(latitude=destination_latitude, longitude=destination_longitude, address=ride.destination_address),
        completed_at=ride.completed_at,
        driver=assigned_driver,
        last_known_driver_location=last_known_driver_location,
        latest_coordination_message=latest_coordination_message,
        payment_method=ride.payment_method.value,
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
            fixed_route = None
            if payload.fixed_route_direction_version_id is not None:
                fixed_context = await resolve_fixed_route_ride(
                    session,
                    payload.fixed_route_direction_version_id,
                    city_hint=payload.city_id,
                )
                pickup = Coordinate(
                    latitude=fixed_context.pickup.latitude,
                    longitude=fixed_context.pickup.longitude,
                    address=(
                        fixed_context.direction.start_location_name.get("fr")
                        or fixed_context.direction.start_location_name.get("en")
                        or fixed_context.direction.start_location_name.get("ar")
                    ),
                )
                destination = Coordinate(
                    latitude=fixed_context.destination.latitude,
                    longitude=fixed_context.destination.longitude,
                    address=(
                        fixed_context.direction.finish_location_name.get("fr")
                        or fixed_context.direction.finish_location_name.get("en")
                        or fixed_context.direction.finish_location_name.get("ar")
                    ),
                )
                city_id = fixed_context.city_id
                operator_id = fixed_context.operator_id
                quote = fixed_context.quote
                service_type = ServiceType.FIXED_ROUTE
                direction_id = fixed_context.direction.id
                fixed_route = await fixed_route_ride_summary(session, direction_id)
            else:
                assert payload.pickup is not None and payload.destination is not None
                context = await resolve_on_demand_service_context(
                    session,
                    pickup_latitude=payload.pickup.latitude,
                    pickup_longitude=payload.pickup.longitude,
                    city_hint=payload.city_id,
                )
                pickup = payload.pickup
                destination = payload.destination
                city_id = context.city_id
                operator_id = context.operator_id
                quote = await quote_immediate_ride(
                    session,
                    city_id=context.city_id,
                    operator_id=context.operator_id,
                    tariff_version_id=context.tariff_version_id,
                    operator_fee_policy_version_id=context.operator_fee_policy_version_id,
                    at=datetime.now(UTC),
                )
                service_type = ServiceType.ON_DEMAND
                direction_id = None
            payment_capability = await resolve_payment_capability(
                session,
                city_id=city_id,
                operator_id=operator_id,
                service_type=service_type,
                settings=request.app.state.settings,
            )
            if payload.payment_method not in payment_capability.methods:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="The selected payment method is not available.",
                )
            ride = await create_ride(
                session,
                principal.user_id,
                payload,
                quote,
                city_id=city_id,
                operator_id=operator_id,
                pickup=pickup,
                destination=destination,
                service_type=service_type,
                fixed_route_direction_id=direction_id,
            )
            ride.payment_capability_version_id = payment_capability.capability_version_id
            ride.payment_recipient_account_id = payment_capability.recipient_account_id
            if ride.payment_method == PaymentMethod.MANUAL_TRANSFER:
                ride.transfer_recipient_name = payment_capability.recipient_name
                ride.transfer_bank_account = payment_capability.bank_account
                ride.transfer_wallet_id = payment_capability.wallet_id
            offer = await dispatch_ride(session, ride.id, request.app.state.settings)
            response = RideResponse(
                id=ride.id,
                city_id=ride.city_id,
                operator_id=ride.operator_id,
                service_type=ride.service_type.value,
                fixed_route=fixed_route,
                status=ride.status.value,
                pickup=pickup,
                destination=destination,
                completed_at=ride.completed_at,
                payment_method=ride.payment_method.value,
            )
            await finish_command(session, command, status_code=status.HTTP_201_CREATED, payload=response.model_dump(mode="json"))
    except (NoActiveTariff, InvalidFinancialPolicy) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except (CityServiceUnavailable, FixedRouteConflict, PaymentCapabilityUnavailable) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
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
    request: Request,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> RideEstimateResponse:
    del principal
    try:
        fixed_route = None
        if payload.fixed_route_direction_version_id is not None:
            fixed_context = await resolve_fixed_route_ride(
                session,
                payload.fixed_route_direction_version_id,
                city_hint=payload.city_id,
            )
            quote = fixed_context.quote
            city_id = fixed_context.city_id
            operator_id = fixed_context.operator_id
            service_type = ServiceType.FIXED_ROUTE
            fixed_route = await fixed_route_ride_summary(
                session, fixed_context.direction.id
            )
        else:
            assert payload.pickup is not None and payload.destination is not None
            context = await resolve_on_demand_service_context(
                session,
                pickup_latitude=payload.pickup.latitude,
                pickup_longitude=payload.pickup.longitude,
                city_hint=payload.city_id,
            )
            quote = await quote_immediate_ride(
                session,
                city_id=context.city_id,
                operator_id=context.operator_id,
                tariff_version_id=context.tariff_version_id,
                operator_fee_policy_version_id=context.operator_fee_policy_version_id,
                at=datetime.now(UTC),
            )
            city_id = context.city_id
            operator_id = context.operator_id
            service_type = ServiceType.ON_DEMAND
        payment_capability = await resolve_payment_capability(
            session,
            city_id=city_id,
            operator_id=operator_id,
            service_type=service_type,
            settings=request.app.state.settings,
        )
    except (NoActiveTariff, InvalidFinancialPolicy) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except (CityServiceUnavailable, FixedRouteConflict, PaymentCapabilityUnavailable) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return RideEstimateResponse(
        estimate=FareEstimate(
            amount=str(quote.passenger_total_amount),
            currency=quote.currency,
            pricing_rule_version=quote.pricing_rule_version,
            city_id=city_id,
            operator_id=operator_id,
            service_type=service_type.value,
            fixed_route=fixed_route,
            economics=quote_economics_response(quote),
        ),
        payment_methods=[method.value for method in payment_capability.methods],
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
    return await response_for(
        session,
        ride,
        include_driver_location=True,
        include_coordination=True,
    )


def fare_breakdown_response(fare: FareRecord) -> FareBreakdownResponse:
    version, components = finalized_fare_breakdown(fare)
    return FareBreakdownResponse(
        amount=str(fare.total_amount),
        currency=fare.currency,
        pricing_rule_version=version,
        components=components,
        economics=fare_economics_response(fare),
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


@router.get(
    "/rides/{ride_id}/receipt",
    response_model=RideReceiptResponse,
    response_model_exclude_none=True,
)
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
    manual_transfer = None
    if payment.method == PaymentMethod.MANUAL_TRANSFER:
        if (
            ride.transfer_recipient_name is None
            or (ride.transfer_bank_account is None and ride.transfer_wallet_id is None)
            or payment.provider_reference is None
        ):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Manual transfer instructions are unavailable. Cash support remains available for new rides.",
            )
        latest_claim_status = await session.scalar(
            select(ManualTransferClaim.status)
            .where(ManualTransferClaim.payment_id == payment.id)
            .order_by(
                ManualTransferClaim.submitted_at.desc(),
                ManualTransferClaim.id.desc(),
            )
            .limit(1)
        )
        manual_transfer = ManualTransferInstructionsResponse(
            recipient_name=ride.transfer_recipient_name,
            bank_account=ride.transfer_bank_account,
            wallet_id=ride.transfer_wallet_id,
            payment_reference=payment.provider_reference,
            latest_claim_status=(
                latest_claim_status.value if latest_claim_status is not None else None
            ),
        )
    refund_rows = list(
        await session.scalars(
            select(PaymentRefund)
            .where(PaymentRefund.payment_id == payment.id)
            .order_by(PaymentRefund.refunded_at.asc(), PaymentRefund.id.asc())
        )
    )
    refund_summary = None
    if refund_rows:
        if any(refund.currency != payment.currency for refund in refund_rows):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Refund reconciliation is temporarily unavailable.",
            )
        refunded_amount = sum(
            (refund.amount for refund in refund_rows),
            start=payment.amount * 0,
        )
        if refunded_amount > payment.amount:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Refund reconciliation is temporarily unavailable.",
            )
        refund_summary = PassengerRefundSummaryResponse(
            refunded_amount=refunded_amount,
            net_paid_amount=payment.amount - refunded_amount,
            currency=payment.currency,
            items=[
                PassengerRefundResponse(
                    id=refund.id,
                    amount=refund.amount,
                    currency=refund.currency,
                    reason=refund.reason,
                    refunded_at=refund.refunded_at,
                )
                for refund in refund_rows
            ],
        )
    return RideReceiptResponse(
        ride_id=ride.id,
        completed_at=ride.completed_at,
        fare=fare_breakdown_response(fare),
        payment=PaymentReceiptResponse(
            method=payment.method.value,
            status=payment.status.value,
            manual_transfer=manual_transfer,
            refunds=refund_summary,
        ),
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
                payment_method=ride.payment_method.value,
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
