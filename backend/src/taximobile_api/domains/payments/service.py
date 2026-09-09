from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select

from taximobile_api.domains.payments.models import (
    DriverEarning,
    ManualTransferClaim,
    ManualTransferClaimStatus,
    Payment,
    PaymentCapabilityStatus,
    PaymentCapabilityVersion,
    PaymentMethod,
    PaymentRecipientAccount,
    PaymentRecipientStatus,
    PaymentRefund,
    PaymentStatus,
    RefundReason,
    RefundSettlementMethod,
)
from taximobile_api.domains.markets.models import (
    City,
    CityConfigurationService,
    ServiceType,
)
from taximobile_api.domains.pricing.models import RideFinancialSnapshot


class InvalidPaymentTransition(ValueError):
    pass


class PaymentCapabilityUnavailable(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PaymentCapabilitySelection:
    methods: tuple[PaymentMethod, ...]
    capability_version_id: UUID | None
    recipient_account_id: UUID | None
    recipient_name: str | None
    bank_account: str | None
    wallet_id: str | None


async def resolve_payment_capability(
    database_session,
    *,
    city_id,
    operator_id,
    service_type: ServiceType,
    settings,
    at: datetime | None = None,
) -> PaymentCapabilitySelection:
    """Resolve methods only through the active coherent city bundle.

    The deployment-wide settings remain an explicit compatibility path for the
    one migrated pilot city. New cities fail closed if their bundle has no
    payment capability.
    """

    now = at or datetime.now(UTC)
    city = await database_session.get(City, city_id)
    if city is None:
        raise PaymentCapabilityUnavailable("The payment city does not exist.")
    configured = None
    if city.active_configuration_version_id is not None:
        configured = await database_session.scalar(
            select(CityConfigurationService).where(
                CityConfigurationService.configuration_version_id
                == city.active_configuration_version_id,
                CityConfigurationService.service_type == service_type,
                CityConfigurationService.enabled.is_(True),
            )
        )
    if configured is not None and configured.payment_capability_version_id is not None:
        capability = await database_session.get(
            PaymentCapabilityVersion,
            configured.payment_capability_version_id,
        )
        if (
            capability is None
            or capability.city_id != city_id
            or capability.operator_id != operator_id
            or capability.service_type != service_type
            or capability.status != PaymentCapabilityStatus.ACTIVE
            or capability.effective_from > now
            or (
                capability.effective_until is not None
                and capability.effective_until <= now
            )
        ):
            raise PaymentCapabilityUnavailable(
                "The configured payment capability is not active for this service."
            )
        methods = [PaymentMethod.CASH]
        recipient = None
        if capability.manual_transfer_enabled:
            recipient = await database_session.get(
                PaymentRecipientAccount,
                capability.recipient_account_id,
            )
            if (
                recipient is None
                or recipient.status != PaymentRecipientStatus.VERIFIED
                or recipient.city_id != city_id
                or recipient.operator_id != operator_id
            ):
                raise PaymentCapabilityUnavailable(
                    "The configured transfer recipient is not verified for this service."
                )
            methods.append(PaymentMethod.MANUAL_TRANSFER)
        return PaymentCapabilitySelection(
            methods=tuple(methods),
            capability_version_id=capability.id,
            recipient_account_id=recipient.id if recipient is not None else None,
            recipient_name=recipient.recipient_name if recipient is not None else None,
            bank_account=recipient.bank_account if recipient is not None else None,
            wallet_id=recipient.wallet_id if recipient is not None else None,
        )

    if city.is_legacy_compatibility:
        methods = [PaymentMethod.CASH]
        if settings.manual_transfer_configured:
            methods.append(PaymentMethod.MANUAL_TRANSFER)
        return PaymentCapabilitySelection(
            methods=tuple(methods),
            capability_version_id=None,
            recipient_account_id=None,
            recipient_name=settings.manual_transfer_recipient_name,
            bank_account=settings.manual_transfer_bank_account,
            wallet_id=settings.manual_transfer_wallet_id,
        )
    raise PaymentCapabilityUnavailable(
        "The city service has no approved payment capability in its active configuration."
    )


_MONEY_QUANTUM = Decimal("0.01")


def create_pending_payment(
    *,
    ride_id,
    payer_id,
    city_id,
    operator_id,
    payment_capability_version_id,
    payment_recipient_account_id,
    amount,
    currency: str,
    method: PaymentMethod,
) -> Payment:
    provider = None
    provider_reference = None
    if method == PaymentMethod.MANUAL_TRANSFER:
        provider = "MANUAL_RECONCILIATION"
        # This reference identifies a statement line; it is not an authorization
        # secret. A full 128-bit value avoids cross-city reference collisions.
        provider_reference = f"TM-{uuid4().hex.upper()}"
    return Payment(
        ride_id=ride_id,
        payer_id=payer_id,
        city_id=city_id,
        operator_id=operator_id,
        payment_capability_version_id=payment_capability_version_id,
        payment_recipient_account_id=payment_recipient_account_id,
        amount=amount,
        currency=currency,
        method=method,
        status=PaymentStatus.PENDING,
        provider=provider,
        provider_reference=provider_reference,
    )


def settle_cash_payment(payment: Payment) -> None:
    if payment.method != PaymentMethod.CASH or payment.status != PaymentStatus.PENDING:
        raise InvalidPaymentTransition("Cash payment cannot be settled in its current state.")
    payment.status = PaymentStatus.COMPLETED
    payment.completed_at = datetime.now(UTC)


def submit_manual_transfer_claim(
    payment: Payment,
    *,
    claimant_user_id,
    payer_reference: str | None,
) -> ManualTransferClaim:
    if payment.method != PaymentMethod.MANUAL_TRANSFER or payment.status != PaymentStatus.PENDING:
        raise InvalidPaymentTransition("Manual transfer cannot be submitted in its current state.")
    payment.status = PaymentStatus.PROCESSING
    return ManualTransferClaim(
        payment_id=payment.id,
        claimant_user_id=claimant_user_id,
        payer_reference=payer_reference,
        status=ManualTransferClaimStatus.SUBMITTED,
    )


def verify_manual_transfer_claim(
    payment: Payment,
    claim: ManualTransferClaim,
    *,
    reviewer_user_id,
    settlement_reference: str,
) -> None:
    if (
        payment.method != PaymentMethod.MANUAL_TRANSFER
        or payment.status != PaymentStatus.PROCESSING
        or claim.payment_id != payment.id
        or claim.status != ManualTransferClaimStatus.SUBMITTED
    ):
        raise InvalidPaymentTransition("Manual transfer claim cannot be verified in its current state.")
    reviewed_at = datetime.now(UTC)
    claim.status = ManualTransferClaimStatus.VERIFIED
    claim.reviewed_at = reviewed_at
    claim.reviewed_by_user_id = reviewer_user_id
    claim.settlement_reference = settlement_reference
    claim.review_reason = None
    payment.status = PaymentStatus.COMPLETED
    payment.completed_at = reviewed_at


def reject_manual_transfer_claim(
    payment: Payment,
    claim: ManualTransferClaim,
    *,
    reviewer_user_id,
    reason: str,
) -> None:
    if (
        payment.method != PaymentMethod.MANUAL_TRANSFER
        or payment.status != PaymentStatus.PROCESSING
        or claim.payment_id != payment.id
        or claim.status != ManualTransferClaimStatus.SUBMITTED
    ):
        raise InvalidPaymentTransition("Manual transfer claim cannot be rejected in its current state.")
    claim.status = ManualTransferClaimStatus.REJECTED
    claim.reviewed_at = datetime.now(UTC)
    claim.reviewed_by_user_id = reviewer_user_id
    claim.review_reason = reason
    payment.status = PaymentStatus.PENDING


def create_payment_refund(
    payment: Payment,
    *,
    amount: Decimal,
    already_refunded: Decimal,
    reason: RefundReason,
    settlement_method: RefundSettlementMethod,
    settlement_reference: str,
    operator_note: str,
    authorized_by_user_id,
) -> PaymentRefund:
    """Record confirmed returned money without rewriting charge or earning facts.

    The launch policy is deliberately operator-funded. Driver recovery requires
    the later versioned city/operator economics policy and a separate append-only
    driver adjustment; this function must never infer one from a passenger refund.
    """

    if payment.status != PaymentStatus.COMPLETED or payment.completed_at is None:
        raise InvalidPaymentTransition("Only a completed payment can be refunded.")
    if amount <= 0 or amount != amount.quantize(_MONEY_QUANTUM):
        raise InvalidPaymentTransition("Refund amount must be positive with at most two decimal places.")
    if already_refunded < 0 or already_refunded != already_refunded.quantize(_MONEY_QUANTUM):
        raise InvalidPaymentTransition("Existing refund total is invalid.")
    remaining = payment.amount - already_refunded
    if amount > remaining:
        raise InvalidPaymentTransition("Refund amount exceeds the payment's remaining refundable amount.")

    refunded_at = datetime.now(UTC)
    refund = PaymentRefund(
        payment_id=payment.id,
        city_id=payment.city_id,
        operator_id=payment.operator_id,
        amount=amount,
        currency=payment.currency,
        reason=reason,
        settlement_method=settlement_method,
        settlement_reference=settlement_reference,
        operator_note=operator_note,
        driver_recovery_amount=Decimal("0.00"),
        operator_funded_amount=amount,
        authorized_by_user_id=authorized_by_user_id,
        refunded_at=refunded_at,
    )
    if amount == remaining:
        payment.status = PaymentStatus.REFUNDED
        payment.refunded_at = refunded_at
    return refund


def create_driver_earning(
    *,
    driver_id,
    payment: Payment,
    financial_snapshot: RideFinancialSnapshot | None = None,
) -> DriverEarning:
    """Create settlement only from the immutable ride economics snapshot."""

    adjustment = Decimal("0.00")
    if financial_snapshot is None:
        gross = payment.amount
        fee = Decimal("0.00")
        net = payment.amount
        transport_fare = payment.amount
        scheduling_surcharge = Decimal("0.00")
        operator_fee = Decimal("0.00")
        operator_allocation = Decimal("0.00")
        operator_fee_policy_id = None
        scheduling_policy_id = None
        funding_mode = None
    else:
        if financial_snapshot.ride_id != payment.ride_id:
            raise InvalidPaymentTransition("The payment economics snapshot belongs to another ride.")
        if financial_snapshot.passenger_total_amount != payment.amount:
            raise InvalidPaymentTransition("The payment amount does not reconcile with the ride economics snapshot.")
        gross = financial_snapshot.driver_gross_amount
        fee = financial_snapshot.driver_fee_deduction_amount
        net = financial_snapshot.driver_net_amount
        transport_fare = financial_snapshot.transport_fare_amount
        scheduling_surcharge = financial_snapshot.scheduling_surcharge_amount
        operator_fee = financial_snapshot.operator_fee_amount
        operator_allocation = financial_snapshot.operator_allocation_amount
        operator_fee_policy_id = financial_snapshot.operator_fee_policy_id
        scheduling_policy_id = financial_snapshot.scheduling_policy_id
        funding_mode = financial_snapshot.operator_fee_funding_mode
    return DriverEarning(
        driver_id=driver_id,
        ride_id=payment.ride_id,
        payment_id=payment.id,
        gross_amount=gross,
        fee_amount=fee,
        adjustment_amount=adjustment,
        net_amount=net + adjustment,
        transport_fare_amount=transport_fare,
        scheduling_surcharge_amount=scheduling_surcharge,
        operator_fee_amount=operator_fee,
        operator_allocation_amount=operator_allocation,
        operator_fee_policy_id=operator_fee_policy_id,
        scheduling_policy_id=scheduling_policy_id,
        operator_fee_funding_mode=funding_mode,
        currency=payment.currency,
        settled_at=payment.completed_at or datetime.now(UTC),
    )
