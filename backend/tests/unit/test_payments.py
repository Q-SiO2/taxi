from decimal import Decimal
from uuid import uuid4

import pytest

from taximobile_api.domains.payments.models import PaymentMethod, PaymentStatus
from taximobile_api.domains.payments.service import (
    InvalidPaymentTransition,
    create_driver_earning,
    create_pending_payment,
    settle_cash_payment,
)


def test_cash_payment_requires_backend_settlement() -> None:
    payment = create_pending_payment(ride_id=uuid4(), payer_id=uuid4(), amount=Decimal("35.00"), currency="MAD", method=PaymentMethod.CASH)
    assert payment.status == PaymentStatus.PENDING
    settle_cash_payment(payment)
    assert payment.status == PaymentStatus.COMPLETED


def test_non_cash_payment_cannot_be_marked_settled_by_cash_flow() -> None:
    payment = create_pending_payment(ride_id=uuid4(), payer_id=uuid4(), amount=Decimal("35.00"), currency="MAD", method=PaymentMethod.CARD)
    with pytest.raises(InvalidPaymentTransition):
        settle_cash_payment(payment)


def test_cash_payment_cannot_be_settled_twice() -> None:
    payment = create_pending_payment(ride_id=uuid4(), payer_id=uuid4(), amount=Decimal("35.00"), currency="MAD", method=PaymentMethod.CASH)
    settle_cash_payment(payment)
    with pytest.raises(InvalidPaymentTransition):
        settle_cash_payment(payment)


def test_driver_earning_is_an_explicit_zero_fee_settlement_record() -> None:
    payment = create_pending_payment(ride_id=uuid4(), payer_id=uuid4(), amount=Decimal("35.00"), currency="MAD", method=PaymentMethod.CASH)
    settle_cash_payment(payment)

    earning = create_driver_earning(driver_id=uuid4(), payment=payment)

    assert earning.gross_amount == Decimal("35.00")
    assert earning.fee_amount == Decimal("0.00")
    assert earning.net_amount == Decimal("35.00")
