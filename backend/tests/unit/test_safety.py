from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from taximobile_api.domains.safety.models import (
    SafetyReportCategory,
    SafetyReportStatus,
    SafetyResolutionCode,
)
from taximobile_api.domains.safety.schemas import SafetyReportCreateRequest
from taximobile_api.domains.safety.service import (
    InvalidSafetyTransition,
    create_safety_report_record,
    transition_safety_report,
)
from taximobile_api.domains.support.models import SupportPriority


def report(category: SafetyReportCategory = SafetyReportCategory.UNSAFE_DRIVING):
    created_at = datetime(2026, 8, 24, 12, tzinfo=UTC)
    return create_safety_report_record(
        city_id=uuid4(),
        ride_id=uuid4(),
        reporter_user_id=uuid4(),
        reported_user_id=uuid4(),
        category=category,
        description="Controlled safety report.",
        created_at=created_at,
    )


def test_immediate_danger_has_urgent_five_minute_acknowledgement_target() -> None:
    case = report(SafetyReportCategory.IMMEDIATE_DANGER)
    assert case.priority == SupportPriority.URGENT
    assert case.response_due_at - case.created_at == timedelta(minutes=5)


def test_safety_lifecycle_requires_acknowledgement_before_escalation_and_resolution() -> None:
    case = report()
    assignee_id = uuid4()
    acknowledged_at = case.created_at + timedelta(minutes=2)
    transition_safety_report(
        case,
        target_status=SafetyReportStatus.ACKNOWLEDGED,
        resolution_code=None,
        assigned_to_user_id=assignee_id,
        transitioned_at=acknowledged_at,
    )
    assert case.first_acknowledged_at == acknowledged_at
    transition_safety_report(
        case,
        target_status=SafetyReportStatus.ESCALATED,
        resolution_code=None,
        assigned_to_user_id=assignee_id,
        transitioned_at=acknowledged_at + timedelta(minutes=5),
    )
    transition_safety_report(
        case,
        target_status=SafetyReportStatus.RESOLVED,
        resolution_code=SafetyResolutionCode.SAFETY_ACTION_TAKEN,
        assigned_to_user_id=assignee_id,
        transitioned_at=acknowledged_at + timedelta(hours=1),
    )
    closed_at = acknowledged_at + timedelta(hours=2)
    transition_safety_report(
        case,
        target_status=SafetyReportStatus.CLOSED,
        resolution_code=SafetyResolutionCode.SAFETY_ACTION_TAKEN,
        assigned_to_user_id=assignee_id,
        transitioned_at=closed_at,
    )
    assert case.retention_until == closed_at + timedelta(days=1825)


def test_safety_state_machine_rejects_resolution_without_acknowledgement() -> None:
    case = report()
    with pytest.raises(InvalidSafetyTransition):
        transition_safety_report(
            case,
            target_status=SafetyReportStatus.RESOLVED,
            resolution_code=SafetyResolutionCode.NO_PLATFORM_ACTION,
            assigned_to_user_id=uuid4(),
            transitioned_at=case.created_at,
        )


def test_safety_schema_rejects_whitespace_unknown_fields_and_uncontrolled_category() -> None:
    with pytest.raises(ValidationError):
        SafetyReportCreateRequest(
            ride_id=uuid4(),
            category="UNSAFE_DRIVING",
            description="   ",
        )
    with pytest.raises(ValidationError):
        SafetyReportCreateRequest(
            ride_id=uuid4(),
            category="CUSTOM_CATEGORY",
            description="Controlled description.",
        )
    with pytest.raises(ValidationError):
        SafetyReportCreateRequest(
            ride_id=uuid4(),
            category="UNSAFE_DRIVING",
            description="Controlled description.",
            reported_user_id=uuid4(),
        )
