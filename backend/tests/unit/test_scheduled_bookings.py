from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from taximobile_api.domains.markets.models import ServiceType
from taximobile_api.domains.payments.models import PaymentMethod
from taximobile_api.domains.pricing.models import (
    FinancialPolicyStatus,
    OperatorFeeCalculationMode,
    OperatorFeeFundingMode,
    OperatorFeePolicy,
    PricingModel,
    PricingRoundingRule,
    PricingRule,
    PricingRuleStatus,
    SchedulingPolicy,
    SchedulingRefundMode,
    SchedulingSurchargeBeneficiary,
)
from taximobile_api.domains.scheduled_bookings.schemas import ScheduledBookingCreateRequest
from taximobile_api.domains.scheduled_bookings.service import (
    SchedulingConflict,
    _validate_requested_time,
    _validate_reviewed_versions,
    policy_snapshot,
)


def scheduling_policy(**overrides) -> SchedulingPolicy:
    now = datetime.now(UTC)
    values = {
        "id": uuid4(),
        "city_id": uuid4(),
        "operator_id": uuid4(),
        "service_type": ServiceType.ON_DEMAND,
        "version": "schedule-v1",
        "status": FinancialPolicyStatus.ACTIVE,
        "surcharge_amount": Decimal("5.00"),
        "currency": "MAD",
        "beneficiary": SchedulingSurchargeBeneficiary.DRIVER,
        "collection_timing_code": "AT_RIDE_SETTLEMENT",
        "minimum_lead_minutes": 60,
        "maximum_horizon_days": 30,
        "offer_open_minutes_before": 1440,
        "offer_response_seconds": 120,
        "commitment_deadline_minutes_before": 180,
        "handoff_minutes_before": 30,
        "protected_duration_minutes": 90,
        "conflict_buffer_before_minutes": 30,
        "conflict_buffer_after_minutes": 30,
        "passenger_cancel_cutoff_minutes": 60,
        "driver_cancel_cutoff_minutes": 120,
        "surcharge_refund_mode": SchedulingRefundMode.FULL_BEFORE_CUTOFF,
        "fallback_matching_enabled": True,
        "effective_from": now - timedelta(days=1),
        "effective_until": None,
    }
    values.update(overrides)
    return SchedulingPolicy(**values)


def test_scheduled_request_requires_exactly_one_service_shape() -> None:
    scheduled_for = datetime.now(UTC) + timedelta(hours=2)
    valid = ScheduledBookingCreateRequest(
        scheduled_for=scheduled_for,
        pickup={"latitude": 33.57, "longitude": -7.59},
        destination={"latitude": 33.59, "longitude": -7.62},
        payment_method=PaymentMethod.CASH,
    )
    assert valid.fixed_route_direction_version_id is None

    with pytest.raises(ValidationError):
        ScheduledBookingCreateRequest(scheduled_for=scheduled_for)
    with pytest.raises(ValidationError):
        ScheduledBookingCreateRequest(
            scheduled_for=scheduled_for,
            fixed_route_direction_version_id=uuid4(),
            pickup={"latitude": 33.57, "longitude": -7.59},
            destination={"latitude": 33.59, "longitude": -7.62},
        )


def test_scheduling_time_bounds_are_backend_policy() -> None:
    now = datetime(2026, 8, 29, 12, tzinfo=UTC)
    policy = scheduling_policy()

    _validate_requested_time(now, now + timedelta(hours=2), policy)
    with pytest.raises(SchedulingConflict, match="at least 60 minutes"):
        _validate_requested_time(now, now + timedelta(minutes=30), policy)
    with pytest.raises(SchedulingConflict, match="more than 30 days"):
        _validate_requested_time(now, now + timedelta(days=31), policy)


def test_policy_snapshot_contains_conflict_handoff_and_cancellation_authority() -> None:
    snapshot = policy_snapshot(scheduling_policy())

    assert snapshot["offer_open_minutes_before"] == 1440
    assert snapshot["handoff_minutes_before"] == 30
    assert snapshot["conflict_buffer_before_minutes"] == 30
    assert snapshot["protected_duration_minutes"] == 90
    assert snapshot["surcharge_refund_mode"] == "FULL_BEFORE_CUTOFF"
    assert snapshot["fallback_matching_enabled"] is True


def test_confirmation_rejects_policy_versions_that_changed_after_review() -> None:
    policy = scheduling_policy(version="schedule-v2")
    payload = ScheduledBookingCreateRequest(
        scheduled_for=datetime.now(UTC) + timedelta(hours=2),
        pickup={"latitude": 33.57, "longitude": -7.59},
        destination={"latitude": 33.59, "longitude": -7.62},
        expected_pricing_rule_version="fare-v1",
        expected_operator_fee_policy_version="fee-v1",
        expected_scheduling_policy_version="schedule-v1",
    )
    quote = SimpleNamespace(
        pricing_rule_version="fare-v1",
        policy_snapshot={
            "operator_fee_policy_version": "fee-v1",
            "scheduling_policy_version": "schedule-v2",
        },
    )

    with pytest.raises(SchedulingConflict, match="scheduling policy changed"):
        _validate_reviewed_versions(payload, quote, policy)
