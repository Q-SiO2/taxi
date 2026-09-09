from decimal import Decimal
from uuid import uuid4

import pytest

from taximobile_api.domains.markets.models import ServiceType
from taximobile_api.domains.pricing.models import (
    BookingType,
    FareRecord,
    OperatorFeeCalculationMode,
    OperatorFeeFundingMode,
    OperatorFeePolicy,
    PricingModel,
    PricingRoundingRule,
    PricingRule,
    SchedulingPolicy,
    SchedulingSurchargeBeneficiary,
)
from taximobile_api.domains.pricing.service import (
    InvalidFinancialPolicy,
    NoActiveTariff,
    calculate_financial_quote,
    finalized_fare_breakdown,
    fixed_fare_amount,
)


def fixed_rule(amount: str = "40.00") -> PricingRule:
    return PricingRule(
        id=uuid4(),
        city_id=uuid4(),
        operator_id=uuid4(),
        service_type=ServiceType.ON_DEMAND,
        booking_type=BookingType.IMMEDIATE,
        name="Regulated",
        version="tariff-v1",
        model=PricingModel.FIXED,
        fixed_amount=Decimal(amount),
        currency="MAD",
    )


def fee_policy(
    *,
    calculation_mode: OperatorFeeCalculationMode,
    funding_mode: OperatorFeeFundingMode,
    percentage_rate: str | None = None,
    flat_amount: str | None = None,
    minimum_driver_net: str = "0.00",
) -> OperatorFeePolicy:
    return OperatorFeePolicy(
        id=uuid4(),
        city_id=uuid4(),
        operator_id=uuid4(),
        service_type=ServiceType.ON_DEMAND,
        version="fee-v1",
        calculation_mode=calculation_mode,
        funding_mode=funding_mode,
        eligible_base_code="TRANSPORT_FARE",
        percentage_rate=Decimal(percentage_rate) if percentage_rate is not None else None,
        flat_amount=Decimal(flat_amount) if flat_amount is not None else None,
        currency="MAD",
        rounding_rule=PricingRoundingRule.HALF_UP_0_01,
        minimum_driver_net=Decimal(minimum_driver_net),
    )


def test_fixed_fare_keeps_decimal_precision() -> None:
    rule = PricingRule(id=uuid4(), name="Regulated", version="v1", model=PricingModel.FIXED, fixed_amount=Decimal("35.125"), currency="MAD")
    assert fixed_fare_amount(rule) == Decimal("35.13")


def test_non_fixed_tariff_cannot_finalize_a_fare() -> None:
    rule = PricingRule(id=uuid4(), name="Meter", version="v1", model=PricingModel.METERED, currency="MAD")
    with pytest.raises(NoActiveTariff):
        fixed_fare_amount(rule)


def test_fixed_fare_rejects_a_negative_authoritative_amount() -> None:
    rule = PricingRule(id=uuid4(), name="Invalid", version="v1", model=PricingModel.FIXED, fixed_amount=Decimal("-1"), currency="MAD")

    with pytest.raises(NoActiveTariff):
        fixed_fare_amount(rule)


def test_fixed_fare_breakdown_exposes_only_immutable_recorded_components() -> None:
    record = FareRecord(
        ride_id=uuid4(),
        pricing_rule_id=uuid4(),
        base_amount=Decimal("35.00"),
        total_amount=Decimal("35.00"),
        currency="MAD",
        snapshot={"tariff_version": "v1", "model": "FIXED"},
    )

    version, components = finalized_fare_breakdown(record)

    assert version == "v1"
    assert components == [{"code": "BASE_FARE", "label": "Base fare", "amount": "35.00"}]


def test_driver_funded_fee_is_not_misrepresented_as_a_passenger_charge_component() -> None:
    record = FareRecord(
        ride_id=uuid4(),
        pricing_rule_id=uuid4(),
        base_amount=Decimal("40.00"),
        total_amount=Decimal("40.00"),
        currency="MAD",
        snapshot={
            "tariff_version": "v2",
            "transport_fare": "40.00",
            "scheduling_surcharge": "0.00",
            "operator_fee": "2.00",
            "operator_fee_funding_mode": "DRIVER_SETTLEMENT_DEDUCTION",
        },
    )

    _, components = finalized_fare_breakdown(record)

    assert components == [
        {"code": "TRANSPORT_FARE", "label": "Transport fare", "amount": "40.00"}
    ]


def test_passenger_funded_fee_and_schedule_are_separate_receipt_components() -> None:
    record = FareRecord(
        ride_id=uuid4(),
        pricing_rule_id=uuid4(),
        base_amount=Decimal("40.00"),
        total_amount=Decimal("47.00"),
        currency="MAD",
        snapshot={
            "tariff_version": "v3",
            "transport_fare": "40.00",
            "scheduling_surcharge": "5.00",
            "operator_fee": "2.00",
            "operator_fee_funding_mode": "PASSENGER_SURCHARGE",
        },
    )

    version, components = finalized_fare_breakdown(record)

    assert version == "v3"
    assert [component["code"] for component in components] == [
        "TRANSPORT_FARE",
        "SCHEDULING_SURCHARGE",
        "OPERATOR_SERVICE_FEE",
    ]
    assert sum(Decimal(component["amount"]) for component in components) == record.total_amount


def test_percentage_fee_rounds_once_and_reconciles_driver_deduction() -> None:
    quote = calculate_financial_quote(
        fixed_rule("35.13"),
        fee_policy(
            calculation_mode=OperatorFeeCalculationMode.PERCENTAGE_OF_TRANSPORT_FARE,
            funding_mode=OperatorFeeFundingMode.DRIVER_SETTLEMENT_DEDUCTION,
            percentage_rate="5.0000",
        ),
        booking_type=BookingType.IMMEDIATE,
    )

    assert quote.transport_fare_amount == Decimal("35.13")
    assert quote.operator_fee_amount == Decimal("1.76")
    assert quote.passenger_total_amount == Decimal("35.13")
    assert quote.driver_fee_deduction_amount == Decimal("1.76")
    assert quote.driver_net_amount == Decimal("33.37")
    assert quote.operator_allocation_amount == Decimal("1.76")


def test_flat_passenger_surcharge_does_not_reduce_driver_transport_credit() -> None:
    quote = calculate_financial_quote(
        fixed_rule(),
        fee_policy(
            calculation_mode=OperatorFeeCalculationMode.FLAT_PER_COMPLETED_BOOKING,
            funding_mode=OperatorFeeFundingMode.PASSENGER_SURCHARGE,
            flat_amount="2.00",
        ),
        booking_type=BookingType.IMMEDIATE,
    )

    assert quote.operator_fee_amount == Decimal("2.00")
    assert quote.passenger_total_amount == Decimal("42.00")
    assert quote.driver_gross_amount == Decimal("40.00")
    assert quote.driver_fee_deduction_amount == Decimal("0.00")
    assert quote.driver_net_amount == Decimal("40.00")
    assert quote.operator_allocation_amount == Decimal("2.00")


def test_explicit_zero_fee_preserves_passenger_and_driver_amounts() -> None:
    quote = calculate_financial_quote(
        fixed_rule(),
        fee_policy(
            calculation_mode=OperatorFeeCalculationMode.FLAT_PER_COMPLETED_BOOKING,
            funding_mode=OperatorFeeFundingMode.DRIVER_SETTLEMENT_DEDUCTION,
            flat_amount="0.00",
        ),
        booking_type=BookingType.IMMEDIATE,
    )

    assert quote.passenger_total_amount == Decimal("40.00")
    assert quote.driver_net_amount == Decimal("40.00")
    assert quote.operator_allocation_amount == Decimal("0.00")


def test_operator_fee_cannot_violate_driver_net_floor() -> None:
    with pytest.raises(InvalidFinancialPolicy, match="driver-net floor"):
        calculate_financial_quote(
            fixed_rule("8.00"),
            fee_policy(
                calculation_mode=OperatorFeeCalculationMode.FLAT_PER_COMPLETED_BOOKING,
                funding_mode=OperatorFeeFundingMode.DRIVER_SETTLEMENT_DEDUCTION,
                flat_amount="3.00",
                minimum_driver_net="6.00",
            ),
            booking_type=BookingType.IMMEDIATE,
        )


@pytest.mark.parametrize(
    ("beneficiary", "expected_driver_net", "expected_operator_allocation"),
    [
        (SchedulingSurchargeBeneficiary.DRIVER, "41.00", "4.00"),
        (SchedulingSurchargeBeneficiary.OPERATOR, "36.00", "9.00"),
    ],
)
def test_scheduling_surcharge_is_separate_and_has_explicit_beneficiary(
    beneficiary: SchedulingSurchargeBeneficiary,
    expected_driver_net: str,
    expected_operator_allocation: str,
) -> None:
    schedule = SchedulingPolicy(
        id=uuid4(),
        city_id=uuid4(),
        operator_id=uuid4(),
        service_type=ServiceType.ON_DEMAND,
        version="schedule-v1",
        surcharge_amount=Decimal("5.00"),
        currency="MAD",
        beneficiary=beneficiary,
        collection_timing_code="AT_RIDE_SETTLEMENT",
    )
    quote = calculate_financial_quote(
        fixed_rule(),
        fee_policy(
            calculation_mode=OperatorFeeCalculationMode.PERCENTAGE_OF_TRANSPORT_FARE,
            funding_mode=OperatorFeeFundingMode.DRIVER_SETTLEMENT_DEDUCTION,
            percentage_rate="10.0000",
        ),
        booking_type=BookingType.SCHEDULED,
        scheduling_policy=schedule,
    )

    assert quote.transport_fare_amount == Decimal("40.00")
    assert quote.scheduling_surcharge_amount == Decimal("5.00")
    assert quote.operator_fee_amount == Decimal("4.00")
    assert quote.passenger_total_amount == Decimal("45.00")
    assert quote.driver_net_amount == Decimal(expected_driver_net)
    assert quote.operator_allocation_amount == Decimal(expected_operator_allocation)
