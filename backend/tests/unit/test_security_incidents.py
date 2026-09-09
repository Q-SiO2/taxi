from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from taximobile_api.domains.security_incidents.models import (
    SecurityIncidentPostmortemOutcome,
    SecurityIncidentResponsibility,
    SecurityIncidentStatus,
    SecurityIncidentTimelineKind,
)
from taximobile_api.domains.security_incidents.schemas import (
    SecurityIncidentPostmortemCompleteRequest,
    SecurityIncidentResponsibilityAssignRequest,
    SecurityIncidentTimelineCreateRequest,
    SecurityIncidentTransitionRequest,
)
from taximobile_api.domains.security_incidents.service import (
    InvalidSecurityIncidentTransition,
    SecurityIncidentTransition,
    apply_transition,
)


def test_security_incident_lifecycle_is_forward_only_and_sets_milestones() -> None:
    now = datetime.now(UTC)
    result = apply_transition(
        current_status=SecurityIncidentStatus.OPEN,
        transition=SecurityIncidentTransition.START_CONTAINMENT,
        changed_at=now,
        contained_at=None,
        recovered_at=None,
        closed_at=None,
    )
    assert result.status == SecurityIncidentStatus.CONTAINING
    assert result.contained_at is None

    with pytest.raises(InvalidSecurityIncidentTransition):
        apply_transition(
            current_status=result.status,
            transition=SecurityIncidentTransition.START_RECOVERY,
            changed_at=now,
            contained_at=None,
            recovered_at=None,
            closed_at=None,
        )

    contained = apply_transition(
        current_status=result.status,
        transition=SecurityIncidentTransition.MARK_CONTAINED,
        changed_at=now + timedelta(minutes=1),
        contained_at=None,
        recovered_at=None,
        closed_at=None,
    )
    assert contained.status == SecurityIncidentStatus.CONTAINED
    assert contained.contained_at == now + timedelta(minutes=1)

    recovering = apply_transition(
        current_status=contained.status,
        transition=SecurityIncidentTransition.START_RECOVERY,
        changed_at=now + timedelta(minutes=2),
        contained_at=contained.contained_at,
        recovered_at=None,
        closed_at=None,
    )
    recovered = apply_transition(
        current_status=recovering.status,
        transition=SecurityIncidentTransition.MARK_RECOVERED,
        changed_at=now + timedelta(minutes=3),
        contained_at=recovering.contained_at,
        recovered_at=None,
        closed_at=None,
    )
    closed = apply_transition(
        current_status=recovered.status,
        transition=SecurityIncidentTransition.CLOSE,
        changed_at=now + timedelta(minutes=4),
        contained_at=recovered.contained_at,
        recovered_at=recovered.recovered_at,
        closed_at=None,
    )
    assert closed.status == SecurityIncidentStatus.CLOSED
    assert closed.contained_at == now + timedelta(minutes=1)
    assert closed.recovered_at == now + timedelta(minutes=3)
    assert closed.closed_at == now + timedelta(minutes=4)


def test_manual_timeline_contract_requires_traceable_reference() -> None:
    base = {
        "kind": SecurityIncidentTimelineKind.CONTAINMENT_ACTION,
        "summary": "Revoked the affected sessions through the reviewed account action.",
        "occurred_at": datetime.now(UTC),
    }
    with pytest.raises(ValidationError):
        SecurityIncidentTimelineCreateRequest.model_validate(base)

    entry = SecurityIncidentTimelineCreateRequest.model_validate(
        {**base, "external_reference": "RUNBOOK-SEC-001"}
    )
    assert entry.external_reference == "RUNBOOK-SEC-001"

    with pytest.raises(ValidationError):
        SecurityIncidentTimelineCreateRequest.model_validate(
            {
                **base,
                "kind": SecurityIncidentTimelineKind.STATUS_TRANSITION,
                "audit_log_id": uuid4(),
            }
        )


def test_close_contract_requires_postmortem_deadline_only_for_close() -> None:
    now = datetime.now(UTC)
    common = {
        "expected_version": 5,
        "summary": "Recovery validation completed and the incident can be closed.",
        "occurred_at": now,
    }
    with pytest.raises(ValidationError):
        SecurityIncidentTransitionRequest.model_validate(
            {**common, "transition": SecurityIncidentTransition.CLOSE}
        )
    with pytest.raises(ValidationError):
        SecurityIncidentTransitionRequest.model_validate(
            {
                **common,
                "transition": SecurityIncidentTransition.START_CONTAINMENT,
                "postmortem_due_at": now + timedelta(days=7),
            }
        )


def test_postmortem_completion_requires_version_and_traceable_evidence() -> None:
    payload = {
        "expected_version": 6,
        "outcome": SecurityIncidentPostmortemOutcome.CONTROL_CHANGED,
        "summary": "The synthetic exercise produced one reviewed control change.",
        "occurred_at": datetime.now(UTC),
    }
    with pytest.raises(ValidationError):
        SecurityIncidentPostmortemCompleteRequest.model_validate(payload)

    completed = SecurityIncidentPostmortemCompleteRequest.model_validate(
        {**payload, "external_reference": "POSTMORTEM-SEC-001"}
    )
    assert completed.expected_version == 6
    assert completed.outcome == SecurityIncidentPostmortemOutcome.CONTROL_CHANGED
    assert completed.external_reference == "POSTMORTEM-SEC-001"


def test_responsibility_assignment_requires_version_exact_user_and_reference() -> None:
    user_id = uuid4()
    payload = {
        "expected_version": 2,
        "assigned_user_id": user_id,
        "occurred_at": datetime.now(UTC),
        "external_reference": "ROSTER-SEC-001",
    }

    request = SecurityIncidentResponsibilityAssignRequest.model_validate(payload)

    assert request.assigned_user_id == user_id
    assert request.expected_version == 2
    assert request.external_reference == "ROSTER-SEC-001"
    assert set(SecurityIncidentResponsibility) == {
        SecurityIncidentResponsibility.SECURITY_RESPONSE_LEAD,
        SecurityIncidentResponsibility.COMMUNICATIONS_LEAD,
        SecurityIncidentResponsibility.OPERATIONS_LIAISON,
        SecurityIncidentResponsibility.POSTMORTEM_OWNER,
    }

    for invalid_reference in ("", "bad reference with spaces", "x" * 161):
        with pytest.raises(ValidationError):
            SecurityIncidentResponsibilityAssignRequest.model_validate(
                {**payload, "external_reference": invalid_reference}
            )
