from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from taximobile_api.domains.administration.schemas import PricingRuleCreateRequest


def test_fixed_pricing_rule_request_normalizes_user_supplied_text() -> None:
    rule = PricingRuleCreateRequest(
        name="  Rabat flat fare  ",
        version=" v1.0 ",
        fixed_amount="35.00",
        currency=" mad ",
        effective_from=datetime.now(UTC),
    )

    assert rule.name == "Rabat flat fare"
    assert rule.version == "v1.0"
    assert rule.currency == "MAD"


def test_fixed_pricing_rule_request_requires_an_aware_ordered_time_range() -> None:
    starts_at = datetime.now(UTC)

    with pytest.raises(ValidationError):
        PricingRuleCreateRequest(
            name="Flat fare",
            version="v1",
            fixed_amount="35.00",
            effective_from=starts_at.replace(tzinfo=None),
        )

    with pytest.raises(ValidationError):
        PricingRuleCreateRequest(
            name="Flat fare",
            version="v1",
            fixed_amount="35.00",
            effective_from=starts_at,
            effective_until=starts_at - timedelta(seconds=1),
        )
