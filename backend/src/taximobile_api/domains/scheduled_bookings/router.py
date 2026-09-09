from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.auth.dependencies import CurrentPrincipal, authenticated_principal
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.drivers.service import DriverMissing, driver_for_user
from taximobile_api.domains.fixed_routes.service import FixedRouteConflict
from taximobile_api.domains.idempotency.service import (
    IdempotencyKeyReuse,
    IdempotentReplay,
    InvalidIdempotencyKey,
    begin_command,
    finish_command,
)
from taximobile_api.domains.markets.service import CityServiceUnavailable
from taximobile_api.domains.pricing.service import InvalidFinancialPolicy, NoActiveTariff
from taximobile_api.domains.scheduled_bookings.models import (
    DriverScheduledOfferPreference,
    ScheduledBooking,
    ScheduledBookingCommitment,
    ScheduledBookingOffer,
    ScheduledBookingStatus,
    ScheduledCommitmentStatus,
    ScheduledOfferStatus,
)
from taximobile_api.domains.scheduled_bookings.schemas import (
    BookingEconomicsResponse,
    CancellationTermsResponse,
    ScheduledBookingCancelRequest,
    ScheduledBookingCreateRequest,
    ScheduledBookingEstimateResponse,
    ScheduledBookingListResponse,
    ScheduledBookingResponse,
    ScheduledCommitmentListResponse,
    ScheduledCommitmentResponse,
    ScheduledOfferDeclineRequest,
    ScheduledOfferListResponse,
    ScheduledOfferPreferenceRequest,
    ScheduledOfferPreferenceListResponse,
    ScheduledOfferPreferenceResponse,
    ScheduledOfferResponse,
)
from taximobile_api.domains.scheduled_bookings.service import (
    ScheduledBookingForbidden,
    ScheduledBookingNotFound,
    ScheduledOfferUnavailable,
    SchedulingConflict,
    accept_offer,
    booking_coordinates,
    cancel_booking,
    create_scheduled_booking,
    decline_offer,
    driver_offer,
    owned_booking,
    resolve_scheduled_booking_quote,
    set_offer_preference,
)


router = APIRouter(tags=["scheduled-bookings"])


def economics_response(booking: ScheduledBooking) -> BookingEconomicsResponse:
    return BookingEconomicsResponse(
        transport_fare=booking.transport_fare_amount,
        scheduling_surcharge=booking.scheduling_surcharge_amount,
        operator_service_fee=booking.operator_fee_amount,
        passenger_total=booking.passenger_total_amount,
        expected_driver_net=booking.driver_net_amount,
        operator_allocation=booking.operator_allocation_amount,
        currency=booking.currency,
        pricing_rule_version=str(booking.quote_snapshot["tariff_version"]),
        operator_fee_policy_version=str(
            booking.quote_snapshot["operator_fee_policy_version"]
        ),
        scheduling_policy_version=str(
            booking.quote_snapshot["scheduling_policy_version"]
        ),
    )


def cancellation_terms(booking: ScheduledBooking) -> CancellationTermsResponse:
    cutoff = int(booking.policy_snapshot["passenger_cancel_cutoff_minutes"])
    mode = str(booking.policy_snapshot["surcharge_refund_mode"])
    if mode == "ALWAYS_FULL":
        summary = "Cancellation does not retain the scheduling surcharge."
    elif mode == "FULL_BEFORE_CUTOFF":
        summary = (
            f"The scheduling surcharge is refundable until {cutoff} minutes before pickup."
        )
    else:
        summary = "The scheduling surcharge is non-refundable after confirmation."
    return CancellationTermsResponse(
        passenger_cancel_cutoff_minutes=cutoff,
        surcharge_refund_mode=mode,
        summary=summary,
    )


def quote_economics_response(quote) -> BookingEconomicsResponse:
    return BookingEconomicsResponse(
        transport_fare=quote.transport_fare_amount,
        scheduling_surcharge=quote.scheduling_surcharge_amount,
        operator_service_fee=quote.operator_fee_amount,
        passenger_total=quote.passenger_total_amount,
        expected_driver_net=quote.driver_net_amount,
        operator_allocation=quote.operator_allocation_amount,
        currency=quote.currency,
        pricing_rule_version=quote.pricing_rule_version,
        operator_fee_policy_version=str(quote.policy_snapshot["operator_fee_policy_version"]),
        scheduling_policy_version=str(quote.policy_snapshot["scheduling_policy_version"]),
    )


def policy_cancellation_terms(policy) -> CancellationTermsResponse:
    cutoff = policy.passenger_cancel_cutoff_minutes
    mode = policy.surcharge_refund_mode.value
    if mode == "ALWAYS_FULL":
        summary = "Cancellation does not retain the scheduling surcharge."
    elif mode == "FULL_BEFORE_CUTOFF":
        summary = f"The scheduling surcharge is refundable until {cutoff} minutes before pickup."
    else:
        summary = "The scheduling surcharge is non-refundable after confirmation."
    return CancellationTermsResponse(
        passenger_cancel_cutoff_minutes=cutoff,
        surcharge_refund_mode=mode,
        summary=summary,
    )


async def booking_response(
    session: AsyncSession, booking: ScheduledBooking
) -> ScheduledBookingResponse:
    pickup, destination = await booking_coordinates(session, booking)
    return ScheduledBookingResponse(
        id=booking.id,
        city_id=booking.city_id,
        operator_id=booking.operator_id,
        service_type=booking.service_type.value,
        fixed_route_direction_version_id=booking.fixed_route_direction_id,
        scheduled_for=booking.scheduled_for,
        city_timezone=booking.city_timezone,
        status=booking.status.value,
        pickup=pickup,
        destination=destination,
        economics=economics_response(booking),
        cancellation_terms=cancellation_terms(booking),
        driver_committed=booking.current_commitment_id is not None
        and booking.status
        in {
            ScheduledBookingStatus.DRIVER_COMMITTED,
            ScheduledBookingStatus.DISPATCH_HANDOFF,
            ScheduledBookingStatus.LIVE_RIDE_CREATED,
        },
        live_ride_id=booking.live_ride_id,
        cancellation_financial_outcome=(
            booking.cancellation_financial_outcome.value
            if booking.cancellation_financial_outcome is not None
            else None
        ),
        created_at=booking.created_at,
    )


def _raise_scheduling_error(error: Exception) -> None:
    if isinstance(error, ScheduledBookingNotFound):
        raise HTTPException(status_code=404, detail=str(error)) from error
    if isinstance(error, ScheduledBookingForbidden):
        raise HTTPException(status_code=403, detail="You cannot access this scheduled booking.") from error
    if isinstance(error, InvalidIdempotencyKey):
        raise HTTPException(status_code=400, detail=str(error)) from error
    if isinstance(error, IdempotencyKeyReuse):
        raise HTTPException(status_code=409, detail=str(error)) from error
    raise HTTPException(status_code=409, detail=str(error)) from error


@router.post(
    "/scheduled-bookings/estimate",
    response_model=ScheduledBookingEstimateResponse,
)
async def estimate_booking(
    payload: ScheduledBookingCreateRequest,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> ScheduledBookingEstimateResponse:
    del principal
    try:
        context = await resolve_scheduled_booking_quote(session, payload=payload)
    except (
        SchedulingConflict,
        FixedRouteConflict,
        CityServiceUnavailable,
        InvalidFinancialPolicy,
        NoActiveTariff,
    ) as error:
        _raise_scheduling_error(error)
    return ScheduledBookingEstimateResponse(
        city_id=context.city_id,
        operator_id=context.operator_id,
        service_type=context.service_type.value,
        fixed_route_direction_version_id=context.fixed_route_direction_id,
        scheduled_for=payload.scheduled_for,
        city_timezone=context.city_timezone,
        pickup=context.pickup,
        destination=context.destination,
        economics=quote_economics_response(context.quote),
        cancellation_terms=policy_cancellation_terms(context.scheduling_policy),
        payment_method=payload.payment_method,
    )


@router.post(
    "/scheduled-bookings",
    response_model=ScheduledBookingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_booking(
    payload: ScheduledBookingCreateRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> ScheduledBookingResponse:
    try:
        async with session.begin():
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="scheduled_booking.create",
                key=idempotency_key,
                payload=payload.model_dump(mode="json"),
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            booking = await create_scheduled_booking(
                session, passenger_id=principal.user_id, payload=payload
            )
            response = await booking_response(session, booking)
            await finish_command(
                session,
                command,
                status_code=status.HTTP_201_CREATED,
                payload=response.model_dump(mode="json"),
            )
        return response
    except (
        SchedulingConflict,
        FixedRouteConflict,
        CityServiceUnavailable,
        InvalidFinancialPolicy,
        NoActiveTariff,
        InvalidIdempotencyKey,
        IdempotencyKeyReuse,
    ) as error:
        _raise_scheduling_error(error)


@router.get("/scheduled-bookings", response_model=ScheduledBookingListResponse)
async def list_bookings(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    booking_status: ScheduledBookingStatus | None = Query(default=None, alias="status"),
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> ScheduledBookingListResponse:
    filters = [ScheduledBooking.passenger_id == principal.user_id]
    if booking_status is not None:
        filters.append(ScheduledBooking.status == booking_status)
    items = list(
        await session.scalars(
            select(ScheduledBooking)
            .where(*filters)
            .order_by(ScheduledBooking.scheduled_for.desc(), ScheduledBooking.id)
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    total = await session.scalar(
        select(func.count()).select_from(ScheduledBooking).where(*filters)
    )
    return ScheduledBookingListResponse(
        items=[await booking_response(session, item) for item in items],
        page=page,
        limit=limit,
        total=total or 0,
    )


@router.get("/scheduled-bookings/{booking_id}", response_model=ScheduledBookingResponse)
async def get_booking(
    booking_id: UUID,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> ScheduledBookingResponse:
    try:
        return await booking_response(
            session, await owned_booking(session, booking_id, principal.user_id)
        )
    except (ScheduledBookingNotFound, ScheduledBookingForbidden) as error:
        _raise_scheduling_error(error)


@router.post(
    "/scheduled-bookings/{booking_id}/cancel",
    response_model=ScheduledBookingResponse,
)
async def cancel_scheduled_booking(
    booking_id: UUID,
    payload: ScheduledBookingCancelRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> ScheduledBookingResponse:
    try:
        async with session.begin():
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="scheduled_booking.cancel",
                key=idempotency_key,
                payload={"booking_id": str(booking_id), **payload.model_dump(mode="json")},
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            booking = await owned_booking(
                session, booking_id, principal.user_id, lock=True
            )
            await cancel_booking(
                session,
                booking,
                passenger_id=principal.user_id,
                reason=payload.reason,
            )
            response = await booking_response(session, booking)
            await finish_command(
                session, command, status_code=200, payload=response.model_dump(mode="json")
            )
        return response
    except (
        ScheduledBookingNotFound,
        ScheduledBookingForbidden,
        SchedulingConflict,
        InvalidIdempotencyKey,
        IdempotencyKeyReuse,
    ) as error:
        _raise_scheduling_error(error)


@router.patch(
    "/drivers/me/scheduled-offer-preference",
    response_model=ScheduledOfferPreferenceResponse,
)
async def update_offer_preference(
    payload: ScheduledOfferPreferenceRequest,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> ScheduledOfferPreferenceResponse:
    try:
        async with session.begin():
            profile = await driver_for_user(session, principal.user_id)
            preference = await set_offer_preference(
                session,
                profile=profile,
                city_id=payload.city_id,
                enabled=payload.enabled,
            )
        return ScheduledOfferPreferenceResponse(
            city_id=preference.city_id,
            enabled=preference.enabled,
            updated_at=preference.updated_at,
        )
    except (DriverMissing, SchedulingConflict, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get(
    "/drivers/me/scheduled-offer-preferences",
    response_model=ScheduledOfferPreferenceListResponse,
)
async def list_offer_preferences(
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> ScheduledOfferPreferenceListResponse:
    try:
        profile = await driver_for_user(session, principal.user_id)
    except DriverMissing as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    items = list(
        await session.scalars(
            select(DriverScheduledOfferPreference)
            .where(DriverScheduledOfferPreference.driver_id == profile.id)
            .order_by(DriverScheduledOfferPreference.city_id)
        )
    )
    return ScheduledOfferPreferenceListResponse(
        items=[
            ScheduledOfferPreferenceResponse(
                city_id=item.city_id,
                enabled=item.enabled,
                updated_at=item.updated_at,
            )
            for item in items
        ]
    )


async def offer_response(
    session: AsyncSession,
    offer: ScheduledBookingOffer,
    booking: ScheduledBooking,
) -> ScheduledOfferResponse:
    pickup, destination = await booking_coordinates(session, booking)
    return ScheduledOfferResponse(
        id=offer.id,
        booking_id=booking.id,
        status=offer.status.value,
        city_id=booking.city_id,
        service_type=booking.service_type.value,
        scheduled_for=booking.scheduled_for,
        city_timezone=booking.city_timezone,
        expires_at=offer.expires_at,
        pickup=pickup,
        destination=destination,
        economics=economics_response(booking),
        cancellation_terms=cancellation_terms(booking),
        server_time=datetime.now(UTC),
    )


@router.get("/drivers/me/scheduled-offers", response_model=ScheduledOfferListResponse)
async def list_scheduled_offers(
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> ScheduledOfferListResponse:
    try:
        profile = await driver_for_user(session, principal.user_id)
    except DriverMissing as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    rows = (
        await session.execute(
            select(ScheduledBookingOffer, ScheduledBooking)
            .join(ScheduledBooking, ScheduledBooking.id == ScheduledBookingOffer.booking_id)
            .where(
                ScheduledBookingOffer.driver_id == profile.id,
                ScheduledBookingOffer.status == ScheduledOfferStatus.PENDING,
                ScheduledBookingOffer.expires_at > datetime.now(UTC),
                ScheduledBooking.status == ScheduledBookingStatus.OFFERING,
            )
            .order_by(ScheduledBooking.scheduled_for, ScheduledBookingOffer.id)
        )
    ).all()
    return ScheduledOfferListResponse(
        items=[await offer_response(session, offer, booking) for offer, booking in rows]
    )


@router.post(
    "/scheduled-offers/{offer_id}/accept",
    response_model=ScheduledCommitmentResponse,
)
async def accept_scheduled_offer(
    offer_id: UUID,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> ScheduledCommitmentResponse:
    try:
        async with session.begin():
            profile = await driver_for_user(session, principal.user_id)
            offer, booking = await driver_offer(session, offer_id, profile.id, lock=True)
            commitment = await accept_offer(
                session, offer=offer, booking=booking, profile=profile
            )
            response = await commitment_response(session, commitment, booking)
        return response
    except (DriverMissing, ScheduledOfferUnavailable) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/scheduled-offers/{offer_id}/decline", response_model=ScheduledOfferResponse)
async def decline_scheduled_offer(
    offer_id: UUID,
    payload: ScheduledOfferDeclineRequest,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> ScheduledOfferResponse:
    try:
        async with session.begin():
            profile = await driver_for_user(session, principal.user_id)
            offer, booking = await driver_offer(session, offer_id, profile.id, lock=True)
            await decline_offer(
                session,
                offer=offer,
                booking=booking,
                profile=profile,
                reason=payload.reason,
            )
            response = await offer_response(session, offer, booking)
        return response
    except (DriverMissing, ScheduledOfferUnavailable) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


async def commitment_response(
    session: AsyncSession,
    commitment: ScheduledBookingCommitment,
    booking: ScheduledBooking,
) -> ScheduledCommitmentResponse:
    pickup, destination = await booking_coordinates(session, booking)
    return ScheduledCommitmentResponse(
        id=commitment.id,
        booking_id=booking.id,
        city_id=booking.city_id,
        service_type=booking.service_type.value,
        scheduled_for=booking.scheduled_for,
        city_timezone=booking.city_timezone,
        status=commitment.status.value,
        protected_from=commitment.protected_window.lower,
        protected_until=commitment.protected_window.upper,
        pickup=pickup,
        destination=destination,
        economics=economics_response(booking),
    )


@router.get(
    "/drivers/me/scheduled-commitments",
    response_model=ScheduledCommitmentListResponse,
)
async def list_scheduled_commitments(
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> ScheduledCommitmentListResponse:
    try:
        profile = await driver_for_user(session, principal.user_id)
    except DriverMissing as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    rows = (
        await session.execute(
            select(ScheduledBookingCommitment, ScheduledBooking)
            .join(ScheduledBooking, ScheduledBooking.id == ScheduledBookingCommitment.booking_id)
            .where(
                ScheduledBookingCommitment.driver_id == profile.id,
                ScheduledBookingCommitment.status.in_(
                    {
                        ScheduledCommitmentStatus.ACTIVE,
                        ScheduledCommitmentStatus.FULFILLED,
                    }
                ),
            )
            .order_by(ScheduledBooking.scheduled_for, ScheduledBookingCommitment.id)
        )
    ).all()
    return ScheduledCommitmentListResponse(
        items=[
            await commitment_response(session, commitment, booking)
            for commitment, booking in rows
        ]
    )
