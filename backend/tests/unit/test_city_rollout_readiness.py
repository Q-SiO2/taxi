"""Phase 18 staged city-rollout contract tests."""

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
