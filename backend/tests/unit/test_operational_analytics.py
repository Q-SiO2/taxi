from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from taximobile_api.domains.analytics.definitions import (
    LATE_EVENT_POLICY,
    METRIC_DEFINITION_BY_CODE,
    MINIMUM_CELL_SIZE,
)
from taximobile_api.domains.analytics.service import hour_bucket, present_fact


def fact_row(*, sample_count: int):
    return SimpleNamespace(
        bucket_start=datetime(2026, 8, 29, 12, tzinfo=UTC),
        city_id=uuid4(),
        operator_id=uuid4(),
        service_type="ON_DEMAND",
        booking_type="IMMEDIATE",
        fixed_route_direction_id=None,
        pricing_rule_id=uuid4(),
        operator_fee_policy_id=uuid4(),
        scheduling_policy_id=None,
        matching_algorithm_version="mvp-v1",
        metric_code="RIDE_COMPLETED",
        outcome_code="COMPLETED",
        category_code=None,
        currency="MAD",
        sample_count=sample_count,
        integer_value=sample_count,
        duration_seconds_sum=sample_count * 600,
        distance_meters_sum=sample_count * 3200,
        amount_sum=Decimal(sample_count * 35),
        numeric_value_sum=Decimal(sample_count) * Decimal("0.75"),
        minimum_per_entity=1,
        maximum_per_entity=3,
        distribution_gini=Decimal("0.2"),
        source_watermark=datetime(2026, 8, 29, 12, 30, tzinfo=UTC),
        computed_at=datetime(2026, 8, 29, 12, 31, tzinfo=UTC),
    )


def test_small_cells_remove_every_measure_not_only_the_count() -> None:
    response = present_fact(fact_row(sample_count=MINIMUM_CELL_SIZE - 1))

    assert response.suppressed is True
    assert response.sample_count is None
    assert response.integer_value is None
    assert response.average_duration_seconds is None
    assert response.average_distance_meters is None
    assert response.amount_sum is None
    assert response.average_numeric_value is None
    assert response.average_per_entity is None
    assert response.minimum_per_entity is None
    assert response.maximum_per_entity is None
    assert response.distribution_gini is None


def test_publishable_fact_derives_averages_from_aggregate_sums() -> None:
    response = present_fact(fact_row(sample_count=MINIMUM_CELL_SIZE))

    assert response.suppressed is False
    assert response.sample_count == MINIMUM_CELL_SIZE
    assert response.average_duration_seconds == Decimal("600.00")
    assert response.average_distance_meters == Decimal("3200.00")
    assert response.amount_sum == Decimal("175")
    assert response.average_numeric_value == Decimal("0.75")
    assert response.average_per_entity == Decimal("1.00")
    assert response.minimum_per_entity == 1
    assert response.maximum_per_entity == 3
    assert response.distribution_gini == Decimal("0.2")


def test_metric_registry_has_explicit_purpose_source_and_late_policy() -> None:
    definition = METRIC_DEFINITION_BY_CODE["SUPPLY_AVAILABLE"]

    assert definition.source == "operational_supply_snapshots_hourly"
    assert "participant trails" in definition.purpose
    assert LATE_EVENT_POLICY == "RECOMPUTE_FROM_SOURCE_UNTIL_RETENTION"
    assert METRIC_DEFINITION_BY_CODE["DRIVER_WORK_DISTRIBUTION"].family == "fairness"
    assert METRIC_DEFINITION_BY_CODE["FINANCIAL_DRIVER_NET"].unit == "money_and_count"
    assert {
        "DRIVER_EN_ROUTE",
        "RIDE_OFFER_CANCELLED",
        "SCHEDULED_OFFERING_STARTED",
        "SCHEDULED_OFFER_CREATED",
        "SCHEDULED_OFFER_DECLINED",
        "SCHEDULED_HANDOFF_STARTED",
    }.issubset(METRIC_DEFINITION_BY_CODE)


def test_hour_bucket_requires_timezone_and_normalizes_to_utc() -> None:
    assert hour_bucket(datetime(2026, 8, 29, 13, 45, tzinfo=UTC)) == datetime(
        2026, 8, 29, 13, tzinfo=UTC
    )
    with pytest.raises(ValueError, match="timezone"):
        hour_bucket(datetime(2026, 8, 29, 13, 45))
