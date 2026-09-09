from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from taximobile_api.domains.payments.models import (
    ManualTransferClaimStatus,
    PaymentMethod,
    PaymentStatus,
    RefundReason,
    RefundSettlementMethod,
)
from taximobile_api.domains.payments.service import (
    InvalidPaymentTransition,
    create_driver_earning,
    create_payment_refund,
    create_pending_payment,
    reject_manual_transfer_claim,
    settle_cash_payment,
    submit_manual_transfer_claim,
    verify_manual_transfer_claim,
)
from taximobile_api.domains.payments.schemas import (
    ManualTransferClaimRequest,
    ManualTransferRejectionRequest,
    ManualTransferReviewRequest,
    PaymentRefundCreateRequest,
)
from taximobile_api.domains.pricing.models import (
    BookingType,
    OperatorFeeCalculationMode,
    OperatorFeeFundingMode,
    RideFinancialSnapshot,
)


def test_cash_payment_requires_backend_settlement() -> None:
    payment = create_pending_payment(ride_id=uuid4(), payer_id=uuid4(), city_id=uuid4(), operator_id=uuid4(), payment_capability_version_id=None, payment_recipient_account_id=None, amount=Decimal("35.00"), currency="MAD", method=PaymentMethod.CASH)
    assert payment.status == PaymentStatus.PENDING
    settle_cash_payment(payment)
    assert payment.status == PaymentStatus.COMPLETED


def test_non_cash_payment_cannot_be_marked_settled_by_cash_flow() -> None:
    payment = create_pending_payment(ride_id=uuid4(), payer_id=uuid4(), city_id=uuid4(), operator_id=uuid4(), payment_capability_version_id=None, payment_recipient_account_id=None, amount=Decimal("35.00"), currency="MAD", method=PaymentMethod.CARD)
    with pytest.raises(InvalidPaymentTransition):
        settle_cash_payment(payment)


def test_cash_payment_cannot_be_settled_twice() -> None:
    payment = create_pending_payment(ride_id=uuid4(), payer_id=uuid4(), city_id=uuid4(), operator_id=uuid4(), payment_capability_version_id=None, payment_recipient_account_id=None, amount=Decimal("35.00"), currency="MAD", method=PaymentMethod.CASH)
    settle_cash_payment(payment)
    with pytest.raises(InvalidPaymentTransition):
        settle_cash_payment(payment)


def test_driver_earning_is_an_explicit_zero_fee_settlement_record() -> None:
    payment = create_pending_payment(ride_id=uuid4(), payer_id=uuid4(), city_id=uuid4(), operator_id=uuid4(), payment_capability_version_id=None, payment_recipient_account_id=None, amount=Decimal("35.00"), currency="MAD", method=PaymentMethod.CASH)
    settle_cash_payment(payment)

    earning = create_driver_earning(driver_id=uuid4(), payment=payment)

    assert earning.gross_amount == Decimal("35.00")
    assert earning.fee_amount == Decimal("0.00")
    assert earning.net_amount == Decimal("35.00")


def test_driver_earning_reuses_exact_immutable_ride_economics() -> None:
    ride_id = uuid4()
    fee_policy_id = uuid4()
    payment = create_pending_payment(
        ride_id=ride_id,
        payer_id=uuid4(),
        city_id=uuid4(),
        operator_id=uuid4(),
        payment_capability_version_id=None,
        payment_recipient_account_id=None,
        amount=Decimal("42.00"),
        currency="MAD",
        method=PaymentMethod.CASH,
    )
    payment.id = uuid4()
    settle_cash_payment(payment)
    snapshot = RideFinancialSnapshot(
        ride_id=ride_id,
        pricing_rule_id=uuid4(),
        operator_fee_policy_id=fee_policy_id,
        scheduling_policy_id=None,
        booking_type=BookingType.IMMEDIATE,
        operator_fee_calculation_mode=(
            OperatorFeeCalculationMode.FLAT_PER_COMPLETED_BOOKING
        ),
        operator_fee_funding_mode=OperatorFeeFundingMode.PASSENGER_SURCHARGE,
        scheduling_surcharge_beneficiary=None,
        transport_fare_amount=Decimal("40.00"),
        scheduling_surcharge_amount=Decimal("0.00"),
        operator_fee_amount=Decimal("2.00"),
        passenger_total_amount=Decimal("42.00"),
        driver_gross_amount=Decimal("40.00"),
        driver_fee_deduction_amount=Decimal("0.00"),
        driver_net_amount=Decimal("40.00"),
        operator_allocation_amount=Decimal("2.00"),
        currency="MAD",
        snapshot={"operator_fee_policy_version": "fee-v1"},
    )

    earning = create_driver_earning(
        driver_id=uuid4(),
        payment=payment,
        financial_snapshot=snapshot,
    )

    assert earning.transport_fare_amount == Decimal("40.00")
    assert earning.operator_fee_amount == Decimal("2.00")
    assert earning.gross_amount == Decimal("40.00")
    assert earning.fee_amount == Decimal("0.00")
    assert earning.net_amount == Decimal("40.00")
    assert earning.operator_allocation_amount == Decimal("2.00")
    assert earning.operator_fee_policy_id == fee_policy_id
    assert (
        earning.operator_fee_funding_mode
        == OperatorFeeFundingMode.PASSENGER_SURCHARGE
    )


def test_settlement_rejects_payment_that_does_not_match_ride_snapshot() -> None:
    ride_id = uuid4()
    payment = create_pending_payment(
        ride_id=ride_id,
        payer_id=uuid4(),
        city_id=uuid4(),
        operator_id=uuid4(),
        payment_capability_version_id=None,
        payment_recipient_account_id=None,
        amount=Decimal("41.00"),
        currency="MAD",
        method=PaymentMethod.CASH,
    )
    payment.id = uuid4()
    settle_cash_payment(payment)
    snapshot = RideFinancialSnapshot(
        ride_id=ride_id,
        pricing_rule_id=uuid4(),
        operator_fee_policy_id=uuid4(),
        booking_type=BookingType.IMMEDIATE,
        operator_fee_calculation_mode=(
            OperatorFeeCalculationMode.FLAT_PER_COMPLETED_BOOKING
        ),
        operator_fee_funding_mode=OperatorFeeFundingMode.PASSENGER_SURCHARGE,
        transport_fare_amount=Decimal("40.00"),
        scheduling_surcharge_amount=Decimal("0.00"),
        operator_fee_amount=Decimal("2.00"),
        passenger_total_amount=Decimal("42.00"),
        driver_gross_amount=Decimal("40.00"),
        driver_fee_deduction_amount=Decimal("0.00"),
        driver_net_amount=Decimal("40.00"),
        operator_allocation_amount=Decimal("2.00"),
        currency="MAD",
        snapshot={"operator_fee_policy_version": "fee-v1"},
    )

    with pytest.raises(InvalidPaymentTransition, match="does not reconcile"):
        create_driver_earning(
            driver_id=uuid4(),
            payment=payment,
            financial_snapshot=snapshot,
        )


def test_manual_transfer_submission_never_completes_payment() -> None:
    payment = create_pending_payment(
        ride_id=uuid4(),
        payer_id=uuid4(),
        city_id=uuid4(),
        operator_id=uuid4(),
        payment_capability_version_id=None,
        payment_recipient_account_id=None,
        amount=Decimal("35.00"),
        currency="MAD",
        method=PaymentMethod.MANUAL_TRANSFER,
    )
    payment.id = uuid4()

    claim = submit_manual_transfer_claim(
        payment,
        claimant_user_id=payment.payer_id,
        payer_reference="BANK-123",
    )

    assert payment.status == PaymentStatus.PROCESSING
    assert payment.completed_at is None
    assert payment.provider == "MANUAL_RECONCILIATION"
    assert payment.provider_reference is not None
    assert payment.provider_reference.startswith("TM-")
    assert claim.status == ManualTransferClaimStatus.SUBMITTED


def test_only_operator_verification_completes_manual_transfer() -> None:
    payment = create_pending_payment(
        ride_id=uuid4(),
        payer_id=uuid4(),
        city_id=uuid4(),
        operator_id=uuid4(),
        payment_capability_version_id=None,
        payment_recipient_account_id=None,
        amount=Decimal("35.00"),
        currency="MAD",
        method=PaymentMethod.MANUAL_TRANSFER,
    )
    payment.id = uuid4()
    claim = submit_manual_transfer_claim(
        payment,
        claimant_user_id=payment.payer_id,
        payer_reference=None,
    )
    reviewer_id = uuid4()

    verify_manual_transfer_claim(
        payment,
        claim,
        reviewer_user_id=reviewer_id,
        settlement_reference="STATEMENT-456",
    )

    assert payment.status == PaymentStatus.COMPLETED
    assert payment.completed_at is not None
    assert claim.status == ManualTransferClaimStatus.VERIFIED
    assert claim.reviewed_by_user_id == reviewer_id
    assert claim.settlement_reference == "STATEMENT-456"


def test_rejected_manual_transfer_can_be_submitted_again_without_marking_paid() -> None:
    payment = create_pending_payment(
        ride_id=uuid4(),
        payer_id=uuid4(),
        city_id=uuid4(),
        operator_id=uuid4(),
        payment_capability_version_id=None,
        payment_recipient_account_id=None,
        amount=Decimal("35.00"),
        currency="MAD",
        method=PaymentMethod.MANUAL_TRANSFER,
    )
    payment.id = uuid4()
    claim = submit_manual_transfer_claim(
        payment,
        claimant_user_id=payment.payer_id,
        payer_reference="FIRST-CLAIM",
    )

    reject_manual_transfer_claim(
        payment,
        claim,
        reviewer_user_id=uuid4(),
        reason="No matching statement line.",
    )

    assert payment.status == PaymentStatus.PENDING
    assert payment.completed_at is None
    assert claim.status == ManualTransferClaimStatus.REJECTED
    assert claim.review_reason == "No matching statement line."


def test_cash_settlement_cannot_complete_a_manual_transfer() -> None:
    payment = create_pending_payment(
        ride_id=uuid4(),
        payer_id=uuid4(),
        city_id=uuid4(),
        operator_id=uuid4(),
        payment_capability_version_id=None,
        payment_recipient_account_id=None,
        amount=Decimal("35.00"),
        currency="MAD",
        method=PaymentMethod.MANUAL_TRANSFER,
    )

    with pytest.raises(InvalidPaymentTransition):
        settle_cash_payment(payment)


def test_manual_transfer_references_are_bounded_ascii_or_empty() -> None:
    assert ManualTransferClaimRequest(payer_reference="  ").payer_reference is None
    assert ManualTransferClaimRequest(payer_reference=" BANK-123 ").payer_reference == "BANK-123"

    for invalid in ("ab", "مرجع-123", 123):
        with pytest.raises(ValidationError):
            ManualTransferClaimRequest(payer_reference=invalid)

    with pytest.raises(ValidationError):
        ManualTransferReviewRequest(settlement_reference=None)
    with pytest.raises(ValidationError):
        ManualTransferRejectionRequest(reason=None)


def test_partial_refund_is_append_only_and_operator_funded() -> None:
    payment = create_pending_payment(
        ride_id=uuid4(),
        payer_id=uuid4(),
        city_id=uuid4(),
        operator_id=uuid4(),
        payment_capability_version_id=None,
        payment_recipient_account_id=None,
        amount=Decimal("35.00"),
        currency="MAD",
        method=PaymentMethod.CASH,
    )
    payment.id = uuid4()
    settle_cash_payment(payment)

    refund = create_payment_refund(
        payment,
        amount=Decimal("5.00"),
        already_refunded=Decimal("0.00"),
        reason=RefundReason.FARE_CORRECTION,
        settlement_method=RefundSettlementMethod.CASH,
        settlement_reference="CASH-REFUND-001",
        operator_note="Approved fare correction returned in cash.",
        authorized_by_user_id=uuid4(),
    )

    assert payment.amount == Decimal("35.00")
    assert payment.status == PaymentStatus.COMPLETED
    assert payment.refunded_at is None
    assert refund.amount == Decimal("5.00")
    assert refund.driver_recovery_amount == Decimal("0.00")
    assert refund.operator_funded_amount == Decimal("5.00")


def test_cumulative_full_refund_marks_payment_refunded_without_rewriting_amount() -> None:
    payment = create_pending_payment(
        ride_id=uuid4(),
        payer_id=uuid4(),
        city_id=uuid4(),
        operator_id=uuid4(),
        payment_capability_version_id=None,
        payment_recipient_account_id=None,
        amount=Decimal("35.00"),
        currency="MAD",
        method=PaymentMethod.CASH,
    )
    payment.id = uuid4()
    settle_cash_payment(payment)

    refund = create_payment_refund(
        payment,
        amount=Decimal("25.00"),
        already_refunded=Decimal("10.00"),
        reason=RefundReason.SERVICE_RECOVERY,
        settlement_method=RefundSettlementMethod.EXTERNAL_TRANSFER,
        settlement_reference="OUTBOUND-REFUND-002",
        operator_note="Final confirmed refund tranche.",
        authorized_by_user_id=uuid4(),
    )

    assert payment.amount == Decimal("35.00")
    assert payment.status == PaymentStatus.REFUNDED
    assert payment.refunded_at == refund.refunded_at


def test_refund_rejects_unsettled_and_excess_amounts() -> None:
    payment = create_pending_payment(
        ride_id=uuid4(),
        payer_id=uuid4(),
        city_id=uuid4(),
        operator_id=uuid4(),
        payment_capability_version_id=None,
        payment_recipient_account_id=None,
        amount=Decimal("35.00"),
        currency="MAD",
        method=PaymentMethod.CASH,
    )
    payment.id = uuid4()
    arguments = {
        "amount": Decimal("1.00"),
        "already_refunded": Decimal("0.00"),
        "reason": RefundReason.OTHER_APPROVED,
        "settlement_method": RefundSettlementMethod.CASH,
        "settlement_reference": "REFUND-EVIDENCE-003",
        "operator_note": "Controlled test refund evidence.",
        "authorized_by_user_id": uuid4(),
    }
    with pytest.raises(InvalidPaymentTransition):
        create_payment_refund(payment, **arguments)

    settle_cash_payment(payment)
    arguments["amount"] = Decimal("30.01")
    arguments["already_refunded"] = Decimal("5.00")
    with pytest.raises(InvalidPaymentTransition):
        create_payment_refund(payment, **arguments)


def test_refund_request_rejects_unbounded_or_imprecise_evidence() -> None:
    valid = PaymentRefundCreateRequest(
        amount=Decimal("5.00"),
        reason="FARE_CORRECTION",
        settlement_method="CASH",
        settlement_reference="  CASH-REFUND-004  ",
        operator_note="  Passenger signed the controlled cash-return record.  ",
    )
    assert valid.settlement_reference == "CASH-REFUND-004"
    assert valid.operator_note == "Passenger signed the controlled cash-return record."

    for invalid_amount in (Decimal("0.00"), Decimal("1.001")):
        with pytest.raises(ValidationError):
            PaymentRefundCreateRequest(
                amount=invalid_amount,
                reason="FARE_CORRECTION",
                settlement_method="CASH",
                settlement_reference="CASH-REFUND-005",
                operator_note="Controlled evidence note.",
            )
    with pytest.raises(ValidationError):
        PaymentRefundCreateRequest(
            amount=Decimal("1.00"),
            reason="UNREVIEWED_REASON",
            settlement_method="CASH",
            settlement_reference="مرجع",
            operator_note="Controlled evidence note.",
        )
