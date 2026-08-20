from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.auth.dependencies import CurrentPrincipal, authenticated_principal
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.drivers.service import DriverMissing, driver_for_user
from taximobile_api.domains.payments.models import DriverEarning, Payment, PaymentMethod, PaymentStatus
from taximobile_api.domains.payments.schemas import DriverEarningResponse, EarningsResponse, PaymentResponse
from taximobile_api.domains.payments.service import InvalidPaymentTransition, create_driver_earning, settle_cash_payment
from taximobile_api.domains.rides.models import Ride, RideStatus
from taximobile_api.domains.idempotency.service import (
    IdempotencyKeyReuse,
    IdempotentReplay,
    InvalidIdempotencyKey,
    begin_command,
    finish_command,
)


router = APIRouter(tags=["payments"])


def payment_response(payment: Payment) -> PaymentResponse:
    return PaymentResponse(id=payment.id, ride_id=payment.ride_id, amount=payment.amount, currency=payment.currency, method=payment.method.value, status=payment.status.value)


@router.post("/rides/{ride_id}/payments/cash/settle", response_model=PaymentResponse)
async def settle_cash(
    ride_id: UUID,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> PaymentResponse:
    try:
        async with session.begin():
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="payment.cash.settle",
                key=idempotency_key,
                payload={"ride_id": str(ride_id)},
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            profile = await driver_for_user(session, principal.user_id)
            ride = await session.scalar(select(Ride).where(Ride.id == ride_id, Ride.driver_id == profile.id).with_for_update())
            if ride is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot settle this payment.")
            if ride.status != RideStatus.COMPLETED:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ride must be completed before settlement.")
            payment = await session.scalar(select(Payment).where(Payment.ride_id == ride.id).with_for_update())
            if payment is None or payment.method != PaymentMethod.CASH:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cash payment not found.")
            if payment.status == PaymentStatus.PENDING:
                settle_cash_payment(payment)
            elif payment.status != PaymentStatus.COMPLETED:
                raise InvalidPaymentTransition("Cash payment cannot be settled in its current state.")
            earning = await session.scalar(select(DriverEarning).where(DriverEarning.payment_id == payment.id).with_for_update())
            if earning is None:
                session.add(create_driver_earning(driver_id=profile.id, payment=payment))
            response = payment_response(payment)
            await finish_command(session, command, status_code=status.HTTP_200_OK, payload=response.model_dump(mode="json"))
    except DriverMissing as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except InvalidPaymentTransition as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except InvalidIdempotencyKey as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except IdempotencyKeyReuse as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return response


@router.get("/drivers/me/earnings", response_model=EarningsResponse)
async def driver_earnings(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> EarningsResponse:
    if from_date is not None and to_date is not None and to_date < from_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="to must not precede from.")
    try:
        profile = await driver_for_user(session, principal.user_id)
    except DriverMissing as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    filters = [DriverEarning.driver_id == profile.id]
    if from_date is not None:
        filters.append(DriverEarning.settled_at >= datetime.combine(from_date, time.min, tzinfo=UTC))
    if to_date is not None:
        filters.append(DriverEarning.settled_at < datetime.combine(to_date, time.min, tzinfo=UTC) + timedelta(days=1))
    currencies = list(await session.scalars(select(DriverEarning.currency).where(*filters).distinct()))
    if len(currencies) > 1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Earnings span multiple currencies.")
    totals = (
        await session.execute(
            select(
                func.coalesce(func.sum(DriverEarning.gross_amount), 0),
                func.coalesce(func.sum(DriverEarning.fee_amount), 0),
                func.coalesce(func.sum(DriverEarning.adjustment_amount), 0),
                func.coalesce(func.sum(DriverEarning.net_amount), 0),
                func.max(DriverEarning.settled_at),
            ).where(*filters)
        )
    ).one()
    count = await session.scalar(select(func.count()).select_from(DriverEarning).where(*filters)) or 0
    earning_rows = list(
        await session.scalars(
            select(DriverEarning)
            .where(*filters)
            .order_by(DriverEarning.settled_at.desc(), DriverEarning.id.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    return EarningsResponse(
        currency=currencies[0] if currencies else "MAD",
        gross=Decimal(totals[0]),
        fees=Decimal(totals[1]),
        adjustments=Decimal(totals[2]),
        net=Decimal(totals[3]),
        settled_through=totals[4],
        count=count,
        page=page,
        limit=limit,
        items=[
            DriverEarningResponse(
                id=earning.id,
                ride_id=earning.ride_id,
                gross=earning.gross_amount,
                fees=earning.fee_amount,
                adjustments=earning.adjustment_amount,
                net=earning.net_amount,
                currency=earning.currency,
                settled_at=earning.settled_at,
            )
            for earning in earning_rows
        ],
    )
