from decimal import Decimal
from uuid import uuid4

import pytest

from taximobile_api.domains.pricing.models import FareRecord, PricingModel, PricingRule
from taximobile_api.domains.pricing.service import NoActiveTariff, finalized_fare_breakdown, fixed_fare_amount


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
