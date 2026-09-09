"""Administrative payment reconciliation, isolated from mobile payment routes."""

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.administration.service import audit
from taximobile_api.domains.auth.dependencies import CurrentPrincipal, administrator
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.idempotency.service import (
    IdempotencyKeyReuse,
    IdempotentReplay,
    InvalidIdempotencyKey,
    begin_command,
    finish_command,
)
from taximobile_api.domains.payments.models import (
    DriverEarning,
    ManualTransferClaim,
    ManualTransferClaimStatus,
    Payment,
    PaymentMethod,
    PaymentRefund,
    RefundReason,
    RefundSettlementMethod,
)
from taximobile_api.domains.payments.schemas import (
    ManualTransferAdminListResponse,
    ManualTransferAdminResponse,
    ManualTransferRejectionRequest,
    ManualTransferReviewRequest,
    PaymentRefundAdminListResponse,
    PaymentRefundAdminResponse,
    PaymentRefundCreateRequest,
)
from taximobile_api.domains.payments.service import (
    InvalidPaymentTransition,
    create_driver_earning,
    create_payment_refund,
    reject_manual_transfer_claim,
    verify_manual_transfer_claim,
)
from taximobile_api.domains.rides.models import Ride, RideStatus
from taximobile_api.domains.pricing.models import RideFinancialSnapshot


router = APIRouter(prefix="/admin", tags=["administration"])
_SETTLEMENT_REFERENCE_CONSTRAINT = "uq_manual_transfer_claims_settlement_reference"
_REFUND_REFERENCE_CONSTRAINT = "uq_payment_refunds_settlement_reference"


def violated_constraint(error: IntegrityError) -> str | None:
    """Read only the database constraint identifier; never expose driver text."""

    direct = getattr(error.orig, "constraint_name", None)
    cause = getattr(error.orig, "__cause__", None)
    return direct or getattr(cause, "constraint_name", None)


def manual_transfer_admin_response(
    claim: ManualTransferClaim,
    payment: Payment,
) -> ManualTransferAdminResponse:
    if payment.provider_reference is None:
        raise RuntimeError("Manual transfer payment is missing its backend reference.")
    return ManualTransferAdminResponse(
        claim_id=claim.id,
        payment_id=payment.id,
        ride_id=payment.ride_id,
        payment_reference=payment.provider_reference,
        payer_reference=claim.payer_reference,
        amount=payment.amount,
        currency=payment.currency,
        status=claim.status.value,
        submitted_at=claim.submitted_at,
        reviewed_at=claim.reviewed_at,
    )


@router.get(
    "/payments/manual-transfers",
    response_model=ManualTransferAdminListResponse,
)
async def list_manual_transfers(
    claim_status: ManualTransferClaimStatus = Query(
        default=ManualTransferClaimStatus.SUBMITTED,
        alias="status",
    ),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    _: CurrentPrincipal = Depends(administrator),
    session: AsyncSession = Depends(database_session),
) -> ManualTransferAdminListResponse:
    filters = [ManualTransferClaim.status == claim_status]
    rows = (
        await session.execute(
            select(ManualTransferClaim, Payment)
            .join(Payment, Payment.id == ManualTransferClaim.payment_id)
            .where(*filters)
            .order_by(ManualTransferClaim.submitted_at.desc(), ManualTransferClaim.id.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    ).all()
    total = await session.scalar(
        select(func.count()).select_from(ManualTransferClaim).where(*filters)
    )
    return ManualTransferAdminListResponse(
        items=[manual_transfer_admin_response(claim, payment) for claim, payment in rows],
        page=page,
        limit=limit,
        total=total or 0,
    )


async def locked_manual_transfer(
    session: AsyncSession,
    payment_id: UUID,
) -> tuple[Payment, ManualTransferClaim, Ride]:
    payment = await session.scalar(
        select(Payment).where(Payment.id == payment_id).with_for_update()
    )
    if payment is None or payment.method != PaymentMethod.MANUAL_TRANSFER:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manual transfer not found.")
    claim = await session.scalar(
        select(ManualTransferClaim)
        .where(
            ManualTransferClaim.payment_id == payment.id,
            ManualTransferClaim.status == ManualTransferClaimStatus.SUBMITTED,
        )
        .with_for_update()
    )
    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No submitted transfer claim is available for review.",
        )
    ride = await session.scalar(select(Ride).where(Ride.id == payment.ride_id).with_for_update())
    if ride is None or ride.driver_id is None or ride.status != RideStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The transfer is not linked to an assigned completed ride.",
        )
    return payment, claim, ride


@router.post(
    "/payments/{payment_id}/manual-transfer/verify",
    response_model=ManualTransferAdminResponse,
)
async def verify_manual_transfer(
    payment_id: UUID,
    payload: ManualTransferReviewRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(administrator),
    session: AsyncSession = Depends(database_session),
) -> ManualTransferAdminResponse:
    try:
        async with session.begin():
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="payment.manual_transfer.verify",
                key=idempotency_key,
                payload={
                    "payment_id": str(payment_id),
                    "settlement_reference": payload.settlement_reference,
                },
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            payment, claim, ride = await locked_manual_transfer(session, payment_id)
            duplicate_reference = await session.scalar(
                select(ManualTransferClaim.id).where(
                    ManualTransferClaim.settlement_reference == payload.settlement_reference,
                    ManualTransferClaim.id != claim.id,
                )
            )
            if duplicate_reference is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Settlement reference has already been reconciled.",
                )
            verify_manual_transfer_claim(
                payment,
                claim,
                reviewer_user_id=principal.user_id,
                settlement_reference=payload.settlement_reference,
            )
            earning = await session.scalar(
                select(DriverEarning)
                .where(DriverEarning.payment_id == payment.id)
                .with_for_update()
            )
            if earning is None:
                snapshot = await session.get(RideFinancialSnapshot, ride.id)
                session.add(
                    create_driver_earning(
                        driver_id=ride.driver_id,
                        payment=payment,
                        financial_snapshot=snapshot,
                    )
                )
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="MANUAL_TRANSFER_VERIFIED",
                resource_type="payment",
                resource_id=payment.id,
                changes={"claim_id": str(claim.id), "status": payment.status.value},
            )
            await session.flush()
            response = manual_transfer_admin_response(claim, payment)
            await finish_command(
                session,
                command,
                status_code=status.HTTP_200_OK,
                payload=response.model_dump(mode="json"),
            )
    except InvalidPaymentTransition as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except IntegrityError as error:
        if violated_constraint(error) != _SETTLEMENT_REFERENCE_CONSTRAINT:
            raise
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Settlement reference has already been reconciled.",
        ) from error
    except InvalidIdempotencyKey as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except IdempotencyKeyReuse as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return response


@router.post(
    "/payments/{payment_id}/manual-transfer/reject",
    response_model=ManualTransferAdminResponse,
)
async def reject_manual_transfer(
    payment_id: UUID,
    payload: ManualTransferRejectionRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(administrator),
    session: AsyncSession = Depends(database_session),
) -> ManualTransferAdminResponse:
    try:
        async with session.begin():
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="payment.manual_transfer.reject",
                key=idempotency_key,
                payload={"payment_id": str(payment_id), "reason": payload.reason},
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            payment, claim, _ride = await locked_manual_transfer(session, payment_id)
            reject_manual_transfer_claim(
                payment,
                claim,
                reviewer_user_id=principal.user_id,
                reason=payload.reason,
            )
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="MANUAL_TRANSFER_REJECTED",
                resource_type="payment",
                resource_id=payment.id,
                changes={"claim_id": str(claim.id), "status": payment.status.value},
            )
            await session.flush()
            response = manual_transfer_admin_response(claim, payment)
            await finish_command(
                session,
                command,
                status_code=status.HTTP_200_OK,
                payload=response.model_dump(mode="json"),
            )
    except InvalidPaymentTransition as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except InvalidIdempotencyKey as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except IdempotencyKeyReuse as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return response


def payment_refund_admin_response(
    refund: PaymentRefund,
    payment: Payment,
    *,
    total_refunded: Decimal,
) -> PaymentRefundAdminResponse:
    return PaymentRefundAdminResponse(
        id=refund.id,
        payment_id=payment.id,
        ride_id=payment.ride_id,
        city_id=payment.city_id,
        operator_id=payment.operator_id,
        amount=refund.amount,
        currency=refund.currency,
        reason=refund.reason,
        settlement_method=refund.settlement_method,
        settlement_reference=refund.settlement_reference,
        operator_note=refund.operator_note,
        driver_recovery_amount=refund.driver_recovery_amount,
        operator_funded_amount=refund.operator_funded_amount,
        authorized_by_user_id=refund.authorized_by_user_id,
        refunded_at=refund.refunded_at,
        payment_status=payment.status.value,
        remaining_refundable_amount=max(payment.amount - total_refunded, Decimal("0.00")),
    )


@router.get(
    "/payments/refunds",
    response_model=PaymentRefundAdminListResponse,
)
async def list_payment_refunds(
    payment_id: UUID | None = Query(default=None),
    reason: RefundReason | None = Query(default=None),
    settlement_method: RefundSettlementMethod | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    _: CurrentPrincipal = Depends(administrator),
    session: AsyncSession = Depends(database_session),
) -> PaymentRefundAdminListResponse:
    filters = []
    if payment_id is not None:
        filters.append(PaymentRefund.payment_id == payment_id)
    if reason is not None:
        filters.append(PaymentRefund.reason == reason)
    if settlement_method is not None:
        filters.append(PaymentRefund.settlement_method == settlement_method)

    totals = (
        select(
            PaymentRefund.payment_id.label("payment_id"),
            func.sum(PaymentRefund.amount).label("total_refunded"),
        )
        .group_by(PaymentRefund.payment_id)
        .subquery()
    )
    rows = (
        await session.execute(
            select(PaymentRefund, Payment, totals.c.total_refunded)
            .join(Payment, Payment.id == PaymentRefund.payment_id)
            .join(totals, totals.c.payment_id == PaymentRefund.payment_id)
            .where(*filters)
            .order_by(PaymentRefund.refunded_at.desc(), PaymentRefund.id.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    ).all()
    total = await session.scalar(
        select(func.count()).select_from(PaymentRefund).where(*filters)
    )
    return PaymentRefundAdminListResponse(
        items=[
            payment_refund_admin_response(
                refund,
                payment,
                total_refunded=Decimal(total_refunded),
            )
            for refund, payment, total_refunded in rows
        ],
        page=page,
        limit=limit,
        total=total or 0,
    )


@router.post(
    "/payments/{payment_id}/refunds",
    response_model=PaymentRefundAdminResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_refund(
    payment_id: UUID,
    payload: PaymentRefundCreateRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(administrator),
    session: AsyncSession = Depends(database_session),
) -> PaymentRefundAdminResponse:
    try:
        async with session.begin():
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="payment.refund.create",
                key=idempotency_key,
                payload={"payment_id": str(payment_id), **payload.model_dump(mode="json")},
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)

            payment = await session.scalar(
                select(Payment).where(Payment.id == payment_id).with_for_update()
            )
            if payment is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found.")
            duplicate_reference = await session.scalar(
                select(PaymentRefund.id).where(
                    PaymentRefund.settlement_reference == payload.settlement_reference
                )
            )
            if duplicate_reference is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Refund settlement reference has already been recorded.",
                )
            total_refunded = Decimal(
                await session.scalar(
                    select(func.coalesce(func.sum(PaymentRefund.amount), 0)).where(
                        PaymentRefund.payment_id == payment.id
                    )
                )
                or 0
            )
            refund = create_payment_refund(
                payment,
                amount=payload.amount,
                already_refunded=total_refunded,
                reason=payload.reason,
                settlement_method=payload.settlement_method,
                settlement_reference=payload.settlement_reference,
                operator_note=payload.operator_note,
                authorized_by_user_id=principal.user_id,
            )
            session.add(refund)
            await session.flush()
            new_total = total_refunded + refund.amount
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="PAYMENT_REFUND_RECORDED",
                resource_type="payment_refund",
                resource_id=refund.id,
                changes={
                    "payment_id": str(payment.id),
                    "amount": str(refund.amount),
                    "currency": refund.currency,
                    "reason": refund.reason.value,
                    "settlement_method": refund.settlement_method.value,
                    "driver_recovery_amount": "0.00",
                    "operator_funded_amount": str(refund.operator_funded_amount),
                    "payment_status": payment.status.value,
                },
            )
            response = payment_refund_admin_response(
                refund,
                payment,
                total_refunded=new_total,
            )
            await finish_command(
                session,
                command,
                status_code=status.HTTP_201_CREATED,
                payload=response.model_dump(mode="json"),
            )
    except InvalidPaymentTransition as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except IntegrityError as error:
        if violated_constraint(error) != _REFUND_REFERENCE_CONSTRAINT:
            raise
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Refund settlement reference has already been recorded.",
        ) from error
    except InvalidIdempotencyKey as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except IdempotencyKeyReuse as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return response
