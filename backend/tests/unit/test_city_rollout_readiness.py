"""Phase 18 staged city-rollout contract tests."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from taximobile_api.domains.markets.constants import (
    ALL_CITY_READINESS_GATES,
    PILOT_ENTRY_CITY_READINESS_GATES,
    POST_LAUNCH_CITY_EVIDENCE_GATES,
    PUBLIC_ACTIVATION_CITY_READINESS_GATES,
)
from taximobile_api.domains.markets.models import ReadinessStatus
from taximobile_api.domains.markets.schemas import ReadinessDecisionRequest
from taximobile_api.domains.markets.service import (
    ControlPlaneConflict,
    require_independent_configuration_reviewer,
)


def test_public_activation_adds_pilot_outcome_evidence_to_pre_pilot_gates() -> None:
    assert (
        PUBLIC_ACTIVATION_CITY_READINESS_GATES - PILOT_ENTRY_CITY_READINESS_GATES
        == {"PILOT_SERVICE_AND_FAIRNESS"}
    )
    assert POST_LAUNCH_CITY_EVIDENCE_GATES == {"POST_LAUNCH_REVIEW"}
    assert ALL_CITY_READINESS_GATES == (
        PUBLIC_ACTIVATION_CITY_READINESS_GATES | POST_LAUNCH_CITY_EVIDENCE_GATES
    )


@pytest.mark.parametrize("gate", sorted(ALL_CITY_READINESS_GATES))
def test_every_rollout_gate_is_an_explicit_bounded_request(gate: str) -> None:
    request = ReadinessDecisionRequest(
        gate_code=gate.lower(),
        status=ReadinessStatus.PASSED,
        non_secret_evidence_reference="runbook:city-review-42",
        expected_configuration_version=1,
    )

    assert request.gate_code == gate


def test_unknown_rollout_gate_fails_closed() -> None:
    with pytest.raises(ValidationError, match="not allowlisted"):
        ReadinessDecisionRequest(
            gate_code="MODEL_INVENTED_GATE",
            status=ReadinessStatus.PASSED,
            non_secret_evidence_reference="ticket:42",
            expected_configuration_version=1,
        )


def test_configuration_submitter_cannot_review_own_rollout_bundle() -> None:
    submitter_id = uuid4()
    configuration = type(
        "SubmittedConfiguration",
        (),
        {"submitted_by_user_id": submitter_id},
    )()

    with pytest.raises(ControlPlaneConflict, match="independent authorized reviewer"):
        require_independent_configuration_reviewer(configuration, submitter_id)


def test_configuration_review_requires_an_identified_submitter() -> None:
    configuration = type(
        "UnsubmittedConfiguration",
        (),
        {"submitted_by_user_id": None},
    )()

    with pytest.raises(ControlPlaneConflict, match="identified configuration submitter"):
        require_independent_configuration_reviewer(configuration, uuid4())


def test_independent_configuration_reviewer_is_accepted() -> None:
    configuration = type(
        "SubmittedConfiguration",
        (),
        {"submitted_by_user_id": uuid4()},
    )()

    require_independent_configuration_reviewer(configuration, uuid4())
