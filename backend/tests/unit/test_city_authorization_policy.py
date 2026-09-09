"""City restriction policy rejects implicit reinstatement or expiry extension."""

import pytest
from pydantic import ValidationError

from taximobile_api.domains.driver_applications.authorization_lifecycle import (
    AuthorizationAction, AuthorizationDecisionRequest, authorization_target,
)
from taximobile_api.domains.driver_applications.models import CityAuthorizationStatus
from taximobile_api.domains.driver_applications.service import RecruitmentConflict


@pytest.mark.parametrize("current", list(CityAuthorizationStatus))
@pytest.mark.parametrize("action", list(AuthorizationAction))
def test_terminal_and_suspended_states_have_explicit_human_transitions(current, action):
    if action == AuthorizationAction.REINSTATE:
        if current == CityAuthorizationStatus.SUSPENDED:
            assert authorization_target(current, action) == CityAuthorizationStatus.ACTIVE
            return
    elif action == AuthorizationAction.SUSPEND:
        if current == CityAuthorizationStatus.ACTIVE:
            assert authorization_target(current, action) == CityAuthorizationStatus.SUSPENDED
            return
    elif current != CityAuthorizationStatus.REVOKED:
        assert authorization_target(current, action) == CityAuthorizationStatus.REVOKED
        return
    with pytest.raises(RecruitmentConflict):
        authorization_target(current, action)


@pytest.mark.parametrize("change", [
    {"reason_code": "ELIGIBILITY_REVIEW_PASSED"},
    {"expected_application_version": 0},
    {"action": "EXPIRE"},
    {"valid_until": "2099-01-01T00:00:00Z"},
    {"city_id": "00000000-0000-0000-0000-000000000000"},
])
def test_command_rejects_wrong_reason_stale_shape_and_scope_or_expiry_injection(change):
    payload = {"expected_application_version": 1, "action": "SUSPEND", "reason_code": "SAFETY_REVIEW"}
    with pytest.raises(ValidationError):
        AuthorizationDecisionRequest.model_validate(payload | change)
