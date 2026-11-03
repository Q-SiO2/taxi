from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from taximobile_api.domains.cooperatives.operations_schemas import (
    OperatorMembershipCreateRequest, OperatorMembershipUpdateRequest,
)


def test_enrollment_has_no_account_or_driver_approval_fields():
    payload = dict(driver_id=uuid4(), reason="Verified synthetic roster")
    assert OperatorMembershipCreateRequest(**payload).status == "PENDING"
    for status in ("SUSPENDED", "ENDED"):
        with pytest.raises(ValidationError):
            OperatorMembershipCreateRequest(**payload, status=status)
    with pytest.raises(ValidationError):
        OperatorMembershipCreateRequest(**payload, roles=["ADMIN"])


def test_member_edit_requires_reviewed_version_and_all_nullable_fields():
    at = datetime.now(UTC)
    payload = dict(status="ACTIVE", expected_updated_at=at, membership_number=None,
                   joined_at=None, ended_at=None, reason="Confirmed roster")
    assert OperatorMembershipUpdateRequest(**payload).membership_number is None
    for field in ("expected_updated_at", "membership_number", "joined_at", "ended_at"):
        with pytest.raises(ValidationError):
            OperatorMembershipUpdateRequest(**{key: value for key, value in payload.items() if key != field})


@pytest.mark.parametrize("invalid", ["naive", "reversed", "blank-reason", "blank-number"])
def test_member_dates_and_bounded_review_fields_are_validated(invalid):
    at = datetime.now(UTC)
    payload = dict(driver_id=uuid4(), reason="Confirmed roster", joined_at=at, ended_at=at)
    if invalid == "naive":
        payload["joined_at"] = at.replace(tzinfo=None)
    elif invalid == "reversed":
        payload["ended_at"] = at - timedelta(seconds=1)
    elif invalid == "blank-reason":
        payload["reason"] = "   "
    else:
        payload["membership_number"] = "  "
    with pytest.raises(ValidationError):
        OperatorMembershipCreateRequest(**payload)
