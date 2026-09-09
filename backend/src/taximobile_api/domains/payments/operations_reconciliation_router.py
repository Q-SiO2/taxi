"""City-scoped payment reconciliation and append-only refund commands."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import and_, false, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.administration.operations_dependencies import (
    OperationsSessionIdentity,
    require_operations_permission,
    require_recent_operations_mfa,
)
from taximobile_api.domains.administration.permissions import (
    OperationsPermission,
    OperationsPrincipal,
)
from taximobile_api.domains.administration.service import audit
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.idempotency.service import (
    IdempotencyKeyReuse,
    IdempotentReplay,
    InvalidIdempotencyKey,
    begin_command,
    finish_command,
)
from taximobile_api.domains.payments.admin_router import (
    payment_refund_admin_response,
    violated_constraint,
)
from taximobile_api.domains.payments.models import (
    DriverEarning,
    ManualTransferClaim,
    ManualTransferClaimStatus,
    Payment,
    PaymentMethod,
    PaymentRefund,
    PaymentRecipientAccount,
    RefundReason,
    RefundSettlementMethod,
)
from taximobile_api.domains.payments.schemas import (
    ManualTransferRejectionRequest,
    ManualTransferReviewRequest,
    OperationsManualTransferListResponse,
    OperationsManualTransferResponse,
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
from taximobile_api.domains.pricing.models import RideFinancialSnapshot
from taximobile_api.domains.rides.models import Ride, RideStatus


router = APIRouter(prefix="/operations", tags=["operations-payments"])
RECONCILE = OperationsPermission.RECONCILE_PAYMENTS
_TRANSFER_REFERENCE_CONSTRAINT = "uq_manual_transfer_claims_settlement_reference"
_REFUND_REFERENCE_CONSTRAINT = "uq_payment_refunds_settlement_reference"


def _same_grant(
    principal: OperationsPrincipal,
    *,
    city_id: UUID,
    operator_id: UUID,
) -> bool:
    return any(
        grant.allows(RECONCILE, city_id=city_id)
        and grant.allows(RECONCILE, operator_id=operator_id)
        for grant in principal.grants
    )


def _scope_predicate(city_column, operator_column, principal: OperationsPrincipal):
    clauses = []
    for grant in principal.grants:
        if RECONCILE not in grant.permissions:
            continue
        clauses.append(
            and_(
                city_column.in_(grant.covered_city_ids),
                operator_column.in_(grant.covered_operator_ids),
            )
        )
    return or_(*clauses) if clauses else false()


def _claim_response(
    claim: ManualTransferClaim,
    payment: Payment,
    recipient: PaymentRecipientAccount | None,
) -> OperationsManualTransferResponse:
    if payment.provider_reference is None:
        raise RuntimeError("Manual transfer payment is missing its backend reference.")
    return OperationsManualTransferResponse(
        claim_id=claim.id,
        payment_id=payment.id,
        ride_id=payment.ride_id,
        city_id=payment.city_id,
        operator_id=payment.operator_id,
        recipient_account_id=payment.payment_recipient_account_id,
        recipient_label=recipient.label if recipient is not None else None,
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
    response_model=OperationsManualTransferListResponse,
)
async def list_manual_transfers(
    claim_status: ManualTransferClaimStatus = Query(
        default=ManualTransferClaimStatus.SUBMITTED, alias="status"
    ),
    city_id: UUID | None = Query(default=None),
    operator_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: OperationsPrincipal = Depends(require_operations_permission(RECONCILE)),
    session: AsyncSession = Depends(database_session),
) -> OperationsManualTransferListResponse:
    filters = [
        ManualTransferClaim.status == claim_status,
        _scope_predicate(Payment.city_id, Payment.operator_id, principal),
    ]
    if city_id is not None:
        filters.append(Payment.city_id == city_id)
    if operator_id is not None:
        filters.append(Payment.operator_id == operator_id)
    statement = (
        select(ManualTransferClaim, Payment, PaymentRecipientAccount)
        .join(Payment, Payment.id == ManualTransferClaim.payment_id)
        .outerjoin(
            PaymentRecipientAccount,
            PaymentRecipientAccount.id == Payment.payment_recipient_account_id,
        )
        .where(*filters)
        .order_by(ManualTransferClaim.submitted_at.desc(), ManualTransferClaim.id.desc())
    )
    total = await session.scalar(
        select(func.count())
        .select_from(ManualTransferClaim)
        .join(Payment, Payment.id == ManualTransferClaim.payment_id)
        .where(*filters)
    )
    rows = (
        await session.execute(
            statement.offset((page - 1) * limit).limit(limit)
        )
    ).all()
    return OperationsManualTransferListResponse(
        items=[_claim_response(claim, payment, recipient) for claim, payment, recipient in rows],
        page=page,
        limit=limit,
        total=total or 0,
    )


async def _locked_claim(
    session: AsyncSession,
    principal: OperationsPrincipal,
    payment_id: UUID,
) -> tuple[Payment, ManualTransferClaim, Ride, PaymentRecipientAccount | None]:
    payment = await session.scalar(
        select(Payment)
        .where(
            Payment.id == payment_id,
            _scope_predicate(Payment.city_id, Payment.operator_id, principal),
        )
        .with_for_update()
    )
    if (
        payment is None
        or payment.method != PaymentMethod.MANUAL_TRANSFER
        or not _same_grant(
            principal, city_id=payment.city_id, operator_id=payment.operator_id
        )
    ):
        raise HTTPException(status_code=404, detail="Manual transfer not found.")
    claim = await session.scalar(
        select(ManualTransferClaim)
        .where(
            ManualTransferClaim.payment_id == payment.id,
            ManualTransferClaim.status == ManualTransferClaimStatus.SUBMITTED,
        )
        .with_for_update()
    )
    if claim is None:
        raise HTTPException(status_code=409, detail="No submitted transfer claim is available for review.")
    ride = await session.scalar(
        select(Ride).where(Ride.id == payment.ride_id).with_for_update()
    )
    if ride is None or ride.driver_id is None or ride.status != RideStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="The transfer is not linked to an assigned completed ride.")
    recipient = (
        await session.get(PaymentRecipientAccount, payment.payment_recipient_account_id)
        if payment.payment_recipient_account_id is not None
        else None
    )
    return payment, claim, ride, recipient


@router.post(
    "/payments/{payment_id}/manual-transfer/verify",
    response_model=OperationsManualTransferResponse,
)
async def verify_manual_transfer(
    payment_id: UUID,
    payload: ManualTransferReviewRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    _mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(require_operations_permission(RECONCILE)),
    session: AsyncSession = Depends(database_session),
) -> OperationsManualTransferResponse:
    try:
        async with session.begin():
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="operations.payment.manual_transfer.verify",
                key=idempotency_key,
                payload={"payment_id": str(payment_id), "settlement_reference": payload.settlement_reference},
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            payment, claim, ride, recipient = await _locked_claim(session, principal, payment_id)
            duplicate = await session.scalar(
                select(ManualTransferClaim.id).where(
                    ManualTransferClaim.settlement_reference == payload.settlement_reference,
                    ManualTransferClaim.id != claim.id,
                )
            )
            if duplicate is not None:
                raise HTTPException(status_code=409, detail="Settlement reference has already been reconciled.")
            verify_manual_transfer_claim(
                payment,
                claim,
                reviewer_user_id=principal.user_id,
                settlement_reference=payload.settlement_reference,
            )
            earning = await session.scalar(
                select(DriverEarning).where(DriverEarning.payment_id == payment.id).with_for_update()
            )
            if earning is None:
                session.add(
                    create_driver_earning(
                        driver_id=ride.driver_id,
                        payment=payment,
                        financial_snapshot=await session.get(RideFinancialSnapshot, ride.id),
                    )
                )
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="MANUAL_TRANSFER_VERIFIED",
                resource_type="payment",
                resource_id=payment.id,
                operator_id=payment.operator_id,
                city_id=payment.city_id,
                changes={"claim_id": str(claim.id), "status": payment.status.value},
            )
            await session.flush()
            response = _claim_response(claim, payment, recipient)
            await finish_command(
                session, command, status_code=200, payload=response.model_dump(mode="json")
            )
            return response
    except InvalidPaymentTransition as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except IntegrityError as error:
        if violated_constraint(error) != _TRANSFER_REFERENCE_CONSTRAINT:
            raise
        raise HTTPException(status_code=409, detail="Settlement reference has already been reconciled.") from error
    except InvalidIdempotencyKey as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except IdempotencyKeyReuse as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post(
    "/payments/{payment_id}/manual-transfer/reject",
    response_model=OperationsManualTransferResponse,
)
async def reject_manual_transfer(
    payment_id: UUID,
    payload: ManualTransferRejectionRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: OperationsPrincipal = Depends(require_operations_permission(RECONCILE)),
    session: AsyncSession = Depends(database_session),
) -> OperationsManualTransferResponse:
    try:
        async with session.begin():
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="operations.payment.manual_transfer.reject",
                key=idempotency_key,
                payload={"payment_id": str(payment_id), "reason": payload.reason},
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            payment, claim, _ride, recipient = await _locked_claim(session, principal, payment_id)
            reject_manual_transfer_claim(
                payment, claim, reviewer_user_id=principal.user_id, reason=payload.reason
            )
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="MANUAL_TRANSFER_REJECTED",
                resource_type="payment",
                resource_id=payment.id,
                operator_id=payment.operator_id,
                city_id=payment.city_id,
                changes={"claim_id": str(claim.id), "status": payment.status.value},
            )
            await session.flush()
            response = _claim_response(claim, payment, recipient)
            await finish_command(
                session, command, status_code=200, payload=response.model_dump(mode="json")
            )
            return response
    except InvalidPaymentTransition as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except InvalidIdempotencyKey as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except IdempotencyKeyReuse as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/payments/refunds", response_model=PaymentRefundAdminListResponse)
async def list_refunds(
    city_id: UUID | None = Query(default=None),
    operator_id: UUID | None = Query(default=None),
    payment_id: UUID | None = Query(default=None),
    reason: RefundReason | None = Query(default=None),
    settlement_method: RefundSettlementMethod | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: OperationsPrincipal = Depends(require_operations_permission(RECONCILE)),
    session: AsyncSession = Depends(database_session),
) -> PaymentRefundAdminListResponse:
    filters = [
        _scope_predicate(PaymentRefund.city_id, PaymentRefund.operator_id, principal),
    ]
    if city_id is not None:
        filters.append(PaymentRefund.city_id == city_id)
    if operator_id is not None:
        filters.append(PaymentRefund.operator_id == operator_id)
    if payment_id is not None:
        filters.append(PaymentRefund.payment_id == payment_id)
    if reason is not None:
        filters.append(PaymentRefund.reason == reason)
    if settlement_method is not None:
        filters.append(PaymentRefund.settlement_method == settlement_method)
    totals = (
        select(PaymentRefund.payment_id, func.sum(PaymentRefund.amount).label("total_refunded"))
        .group_by(PaymentRefund.payment_id)
        .subquery()
    )
    total = await session.scalar(
        select(func.count()).select_from(PaymentRefund).where(*filters)
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
    return PaymentRefundAdminListResponse(
        items=[
            payment_refund_admin_response(refund, payment, total_refunded=Decimal(total_refunded))
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
async def record_refund(
    payment_id: UUID,
    payload: PaymentRefundCreateRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    _mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(require_operations_permission(RECONCILE)),
    session: AsyncSession = Depends(database_session),
) -> PaymentRefundAdminResponse:
    try:
        async with session.begin():
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="operations.payment.refund.record",
                key=idempotency_key,
                payload={"payment_id": str(payment_id), **payload.model_dump(mode="json")},
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            payment = await session.scalar(
                select(Payment)
                .where(
                    Payment.id == payment_id,
                    _scope_predicate(Payment.city_id, Payment.operator_id, principal),
                )
                .with_for_update()
            )
            if payment is None or not _same_grant(
                principal, city_id=payment.city_id, operator_id=payment.operator_id
            ):
                raise HTTPException(status_code=404, detail="Payment not found.")
            duplicate = await session.scalar(
                select(PaymentRefund.id).where(
                    PaymentRefund.settlement_reference == payload.settlement_reference
                )
            )
            if duplicate is not None:
                raise HTTPException(status_code=409, detail="Refund settlement reference has already been recorded.")
            total_refunded = Decimal(
                await session.scalar(
                    select(func.coalesce(func.sum(PaymentRefund.amount), 0)).where(
                        PaymentRefund.payment_id == payment.id
                    )
                ) or 0
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
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="PAYMENT_REFUND_RECORDED",
                resource_type="payment_refund",
                resource_id=refund.id,
                operator_id=payment.operator_id,
                city_id=payment.city_id,
                changes={
                    "payment_id": str(payment.id),
                    "amount": str(refund.amount),
                    "currency": refund.currency,
                    "reason": refund.reason.value,
                    "payment_status": payment.status.value,
                },
            )
            response = payment_refund_admin_response(
                refund, payment, total_refunded=total_refunded + refund.amount
            )
            await finish_command(
                session, command, status_code=201, payload=response.model_dump(mode="json")
            )
            return response
    except InvalidPaymentTransition as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except IntegrityError as error:
        if violated_constraint(error) != _REFUND_REFERENCE_CONSTRAINT:
            raise
        raise HTTPException(status_code=409, detail="Refund settlement reference has already been recorded.") from error
    except InvalidIdempotencyKey as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except IdempotencyKeyReuse as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
