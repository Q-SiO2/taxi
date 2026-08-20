from datetime import UTC, datetime
from decimal import Decimal

from taximobile_api.domains.payments.models import DriverEarning, Payment, PaymentMethod, PaymentStatus


class InvalidPaymentTransition(ValueError):
    pass


def create_pending_payment(*, ride_id, payer_id, amount, currency: str, method: PaymentMethod) -> Payment:
    return Payment(ride_id=ride_id, payer_id=payer_id, amount=amount, currency=currency, method=method, status=PaymentStatus.PENDING)


def settle_cash_payment(payment: Payment) -> None:
    if payment.method != PaymentMethod.CASH or payment.status != PaymentStatus.PENDING:
        raise InvalidPaymentTransition("Cash payment cannot be settled in its current state.")
    payment.status = PaymentStatus.COMPLETED
    payment.completed_at = datetime.now(UTC)


def create_driver_earning(*, driver_id, payment: Payment) -> DriverEarning:
    """MVP settlement has no platform fee; the explicit zero is retained for auditability."""
    fee = Decimal("0.00")
    adjustment = Decimal("0.00")
    return DriverEarning(
        driver_id=driver_id,
        ride_id=payment.ride_id,
        payment_id=payment.id,
        gross_amount=payment.amount,
        fee_amount=fee,
        adjustment_amount=adjustment,
        net_amount=payment.amount - fee + adjustment,
        currency=payment.currency,
        settled_at=payment.completed_at or datetime.now(UTC),
    )
