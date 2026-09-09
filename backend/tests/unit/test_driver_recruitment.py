from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from taximobile_api.domains.driver_applications.schemas import (
    ApplicationAnswerInput,
    ApplicationDecisionRequest,
    CityApplicationCreateRequest,
    RequirementItemInput,
)
from taximobile_api.integrations.driver_documents import (
    DisabledDriverDocumentStore,
    create_driver_document_store,
)


def localized(value: str) -> dict[str, str]:
    return {"en": value, "fr": value, "ar": value}


def test_requirement_rule_must_match_its_evidence_type() -> None:
    with pytest.raises(ValidationError, match="validity rule is incompatible"):
        RequirementItemInput(
            requirement_code="DRIVER_PROFILE",
            evidence_type="PROFILE",
            validity_rule_code="TEXT_PRESENT",
            display_order=0,
            localized_copy_key="driver.requirement.profile",
            localized_label=localized("Driver profile"),
            localized_description=localized("Confirm the account-owned profile."),
        )


def test_credential_requirement_needs_a_typed_reference() -> None:
    with pytest.raises(ValidationError, match="reference_type_code"):
        RequirementItemInput(
            requirement_code="DRIVING_LICENCE",
            evidence_type="CREDENTIAL",
            validity_rule_code="CREDENTIAL_UNEXPIRED",
            display_order=0,
            localized_copy_key="driver.requirement.licence",
            localized_label=localized("Driving licence"),
            localized_description=localized("Choose a verified driving licence."),
        )


def test_application_answer_requires_one_matching_typed_value() -> None:
    item_id = uuid4()

    answer = ApplicationAnswerInput(
        requirement_item_id=item_id,
        answer_type="BOOLEAN",
        boolean_value=False,
    )
    assert answer.boolean_value is False

    with pytest.raises(ValidationError, match="Exactly one typed answer"):
        ApplicationAnswerInput(
            requirement_item_id=item_id,
            answer_type="TEXT",
            text_value="I agree",
            boolean_value=True,
        )

    with pytest.raises(ValidationError, match="answer_type must match"):
        ApplicationAnswerInput(
            requirement_item_id=item_id,
            answer_type="DATE",
            text_value="not a date",
        )


def test_application_creation_cannot_smuggle_status_or_authority() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        CityApplicationCreateRequest(
            city_id=uuid4(),
            display_name="Applicant",
            status="APPROVED",
        )


def test_approval_requires_services_and_other_decisions_reject_authorization_fields() -> None:
    with pytest.raises(ValidationError, match="Approval requires"):
        ApplicationDecisionRequest(
            expected_version=1,
            decision="APPROVE",
            reason_code="REQUIREMENTS_CONFIRMED",
            applicant_safe_message="Your application was approved.",
        )

    with pytest.raises(ValidationError, match="only for an approval"):
        ApplicationDecisionRequest(
            expected_version=1,
            decision="REJECT",
            reason_code="CREDENTIAL_NOT_VALID",
            applicant_safe_message="The credential could not be validated.",
            authorized_service_types=["ON_DEMAND"],
            authorization_valid_until=datetime.now(UTC),
        )


def test_driver_document_storage_is_explicitly_fail_closed() -> None:
    store = create_driver_document_store()

    assert isinstance(store, DisabledDriverDocumentStore)
    assert store.available is False
