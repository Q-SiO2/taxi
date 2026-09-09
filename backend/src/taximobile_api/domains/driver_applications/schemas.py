"""Strict public, applicant, and operations contracts for city recruitment."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from taximobile_api.domains.driver_applications.models import (
    ApplicationAnswerType,
    ApplicationDecisionType,
    RequirementEvidenceType,
    RequirementValidityRule,
)
from taximobile_api.domains.markets.models import ServiceType


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LocalizedRecruitmentCopy(StrictModel):
    en: str = Field(min_length=1, max_length=500)
    fr: str = Field(min_length=1, max_length=500)
    ar: str = Field(min_length=1, max_length=500)

    @field_validator("en", "fr", "ar")
    @classmethod
    def clean_copy(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Localized recruitment copy cannot be blank.")
        return cleaned


RULES_BY_EVIDENCE_TYPE: dict[RequirementEvidenceType, frozenset[RequirementValidityRule]] = {
    RequirementEvidenceType.PROFILE: frozenset({RequirementValidityRule.PROFILE_OWNED}),
    RequirementEvidenceType.VEHICLE: frozenset(
        {RequirementValidityRule.VEHICLE_OWNED, RequirementValidityRule.VEHICLE_VERIFIED}
    ),
    RequirementEvidenceType.CREDENTIAL: frozenset(
        {
            RequirementValidityRule.CREDENTIAL_OWNED,
            RequirementValidityRule.CREDENTIAL_VERIFIED,
            RequirementValidityRule.CREDENTIAL_UNEXPIRED,
        }
    ),
    RequirementEvidenceType.DOCUMENT: frozenset(
        {RequirementValidityRule.DOCUMENT_SCANNED_CLEAN}
    ),
    RequirementEvidenceType.BOOLEAN: frozenset({RequirementValidityRule.BOOLEAN_TRUE}),
    RequirementEvidenceType.DATE: frozenset({RequirementValidityRule.DATE_NOT_FUTURE}),
    RequirementEvidenceType.TEXT: frozenset({RequirementValidityRule.TEXT_PRESENT}),
}


class RequirementItemInput(StrictModel):
    requirement_code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{1,63}$")
    evidence_type: RequirementEvidenceType
    required: bool = True
    validity_rule_code: RequirementValidityRule
    reference_type_code: str | None = Field(
        default=None,
        pattern=r"^[A-Z][A-Z0-9_]{1,63}$",
    )
    display_order: int = Field(ge=0, le=1_000)
    localized_copy_key: str = Field(
        pattern=r"^[a-z][a-z0-9_.-]{2,119}$",
    )
    localized_label: LocalizedRecruitmentCopy
    localized_description: LocalizedRecruitmentCopy

    @model_validator(mode="after")
    def compatible_rule_and_reference(self):
        if self.validity_rule_code not in RULES_BY_EVIDENCE_TYPE[self.evidence_type]:
            raise ValueError("The validity rule is incompatible with the evidence type.")
        if self.evidence_type == RequirementEvidenceType.CREDENTIAL:
            if self.reference_type_code is None:
                raise ValueError("Credential requirements need a reference_type_code.")
        elif self.reference_type_code is not None:
            raise ValueError("reference_type_code is supported only for credential requirements.")
        return self


class RequirementVersionCreateRequest(StrictModel):
    version: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
    effective_from: datetime
    effective_until: datetime | None = None
    items: list[RequirementItemInput] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def valid_version(self):
        if self.effective_from.tzinfo is None:
            raise ValueError("effective_from must include a timezone.")
        if self.effective_until is not None:
            if self.effective_until.tzinfo is None:
                raise ValueError("effective_until must include a timezone.")
            if self.effective_until <= self.effective_from:
                raise ValueError("effective_until must be after effective_from.")
        codes = [item.requirement_code for item in self.items]
        if len(codes) != len(set(codes)):
            raise ValueError("Requirement codes must be unique within a version.")
        orders = [item.display_order for item in self.items]
        if len(orders) != len(set(orders)):
            raise ValueError("Requirement display_order values must be unique within a version.")
        return self


class RequirementVersionUpdateRequest(StrictModel):
    expected_version: int = Field(ge=1)
    effective_from: datetime | None = None
    effective_until: datetime | None = None
    clear_effective_until: bool = False
    items: list[RequirementItemInput] | None = Field(default=None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def valid_update(self):
        if (
            self.effective_from is None
            and self.effective_until is None
            and not self.clear_effective_until
            and self.items is None
        ):
            raise ValueError("At least one requirement-version field must be supplied.")
        if self.effective_from is not None and self.effective_from.tzinfo is None:
            raise ValueError("effective_from must include a timezone.")
        if self.effective_until is not None and self.effective_until.tzinfo is None:
            raise ValueError("effective_until must include a timezone.")
        if self.effective_until is not None and self.clear_effective_until:
            raise ValueError("effective_until and clear_effective_until cannot be combined.")
        if self.items is not None:
            codes = [item.requirement_code for item in self.items]
            orders = [item.display_order for item in self.items]
            if len(codes) != len(set(codes)):
                raise ValueError("Requirement codes must be unique within a version.")
            if len(orders) != len(set(orders)):
                raise ValueError("Requirement display_order values must be unique within a version.")
        return self


class RequirementVersionCommandRequest(StrictModel):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=240)

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, value: str) -> str:
        return value.strip()


class RequirementItemResponse(BaseModel):
    id: UUID
    requirement_code: str
    evidence_type: str
    allowed_evidence_types: list[str]
    required: bool
    validity_rule_code: str
    reference_type_code: str | None
    display_order: int
    localized_copy_key: str
    localized_label: LocalizedRecruitmentCopy
    localized_description: LocalizedRecruitmentCopy


class RequirementVersionResponse(BaseModel):
    id: UUID
    city_id: UUID
    version: str
    status: str
    effective_from: datetime
    effective_until: datetime | None
    optimistic_version: int
    items: list[RequirementItemResponse]
    submitted_at: datetime | None
    activated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RequirementVersionListResponse(BaseModel):
    items: list[RequirementVersionResponse]
    page: int
    limit: int
    total: int


class RecruitingCityResponse(BaseModel):
    id: UUID
    code: str
    localized_name: dict[str, str]
    timezone: str
    lifecycle_status: str
    requirement_version_id: UUID
    requirement_version: str


class RecruitingCityListResponse(BaseModel):
    items: list[RecruitingCityResponse]


class PublicRequirementVersionResponse(BaseModel):
    city: RecruitingCityResponse
    requirement_version_id: UUID
    requirement_version: str
    effective_from: datetime
    effective_until: datetime | None
    document_upload_available: bool
    items: list[RequirementItemResponse]


class CityApplicationCreateRequest(StrictModel):
    city_id: UUID
    # Required only when the account does not yet have its single driver identity.
    display_name: str | None = Field(default=None, min_length=1, max_length=120)

    @field_validator("display_name")
    @classmethod
    def clean_display_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class ApplicationAnswerInput(StrictModel):
    requirement_item_id: UUID
    answer_type: ApplicationAnswerType
    boolean_value: bool | None = None
    date_value: date | None = None
    text_value: str | None = Field(default=None, min_length=1, max_length=1000)

    @field_validator("text_value")
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def exact_typed_value(self):
        present = sum(
            value is not None
            for value in (self.boolean_value, self.date_value, self.text_value)
        )
        if present != 1:
            raise ValueError("Exactly one typed answer value must be supplied.")
        expected = {
            ApplicationAnswerType.BOOLEAN: self.boolean_value,
            ApplicationAnswerType.DATE: self.date_value,
            ApplicationAnswerType.TEXT: self.text_value,
        }[self.answer_type]
        if expected is None:
            raise ValueError("answer_type must match the supplied value.")
        return self


class ApplicationEvidenceInput(StrictModel):
    requirement_item_id: UUID
    profile_id: UUID | None = None
    vehicle_id: UUID | None = None
    credential_id: UUID | None = None

    @model_validator(mode="after")
    def exact_reference(self):
        if sum(value is not None for value in (self.profile_id, self.vehicle_id, self.credential_id)) != 1:
            raise ValueError("Exactly one owned evidence reference must be supplied.")
        return self


class CityApplicationUpdateRequest(StrictModel):
    expected_version: int = Field(ge=1)
    answers: list[ApplicationAnswerInput] | None = Field(default=None, max_length=64)
    evidence: list[ApplicationEvidenceInput] | None = Field(default=None, max_length=64)
    remove_answer_item_ids: list[UUID] = Field(default_factory=list, max_length=64)
    remove_evidence_item_ids: list[UUID] = Field(default_factory=list, max_length=64)

    @model_validator(mode="after")
    def has_non_conflicting_changes(self):
        if (
            self.answers is None
            and self.evidence is None
            and not self.remove_answer_item_ids
            and not self.remove_evidence_item_ids
        ):
            raise ValueError("At least one application change must be supplied.")
        answer_ids = [item.requirement_item_id for item in self.answers or []]
        evidence_ids = [item.requirement_item_id for item in self.evidence or []]
        if len(answer_ids) != len(set(answer_ids)) or len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("Each requirement item may be updated only once per request.")
        if set(answer_ids) & set(self.remove_answer_item_ids):
            raise ValueError("An answer cannot be set and removed in the same request.")
        if set(evidence_ids) & set(self.remove_evidence_item_ids):
            raise ValueError("Evidence cannot be set and removed in the same request.")
        return self


class ApplicationAnswerResponse(BaseModel):
    requirement_item_id: UUID
    answer_type: str
    boolean_value: bool | None
    date_value: date | None
    text_value: str | None


class ApplicationEvidenceResponse(BaseModel):
    requirement_item_id: UUID
    evidence_type: str
    profile_id: UUID | None
    vehicle_id: UUID | None
    credential_id: UUID | None
    document_id: UUID | None
    status: str


class ApplicationDocumentResponse(BaseModel):
    id: UUID
    requirement_item_id: UUID
    media_type: str
    byte_size: int
    scan_status: str
    uploaded_at: datetime
    deleted_at: datetime | None


class ApplicantSafeDecisionResponse(BaseModel):
    decision: str
    reason_code: str
    message: str
    created_at: datetime


class CityAuthorizationResponse(BaseModel):
    id: UUID
    city_id: UUID
    status: str
    vehicle_id: UUID | None
    service_types: list[str]
    scheduled_offers_enabled: bool
    valid_from: datetime
    valid_until: datetime | None


class CityApplicationResponse(BaseModel):
    id: UUID
    driver_id: UUID
    city_id: UUID
    city_code: str
    city_name: dict[str, str]
    requirement_version_id: UUID
    requirement_version: str
    status: str
    optimistic_version: int
    submission_revision: int
    editable: bool
    complete: bool
    missing_required_item_ids: list[UUID]
    document_upload_available: bool
    submitted_at: datetime | None
    reviewed_at: datetime | None
    withdrawn_at: datetime | None
    created_at: datetime
    updated_at: datetime
    requirements: list[RequirementItemResponse]
    answers: list[ApplicationAnswerResponse]
    evidence: list[ApplicationEvidenceResponse]
    documents: list[ApplicationDocumentResponse]
    latest_decision: ApplicantSafeDecisionResponse | None
    authorization: CityAuthorizationResponse | None


class CityApplicationSummaryResponse(BaseModel):
    id: UUID
    city_id: UUID
    city_code: str
    city_name: dict[str, str]
    requirement_version_id: UUID
    requirement_version: str
    status: str
    optimistic_version: int
    submitted_at: datetime | None
    reviewed_at: datetime | None
    updated_at: datetime
    latest_applicant_message: str | None


class CityApplicationListResponse(BaseModel):
    items: list[CityApplicationSummaryResponse]


class OperationsDriverApplicationSummary(BaseModel):
    id: UUID
    driver_id: UUID
    display_name: str
    city_id: UUID
    city_code: str
    city_name: dict[str, str]
    requirement_version_id: UUID
    requirement_version: str
    status: str
    optimistic_version: int
    submitted_at: datetime | None
    updated_at: datetime


class OperationsDriverApplicationListResponse(BaseModel):
    items: list[OperationsDriverApplicationSummary]
    page: int
    limit: int
    total: int


class OperationsDecisionResponse(BaseModel):
    id: UUID
    reviewer_user_id: UUID
    decision: str
    reason_code: str
    applicant_safe_message: str
    application_version: int
    submission_revision: int
    created_at: datetime


class OperationsDriverApplicationDetailResponse(BaseModel):
    application: CityApplicationResponse
    applicant_display_name: str
    applicant_phone_number: str | None
    applicant_email: str | None
    decisions: list[OperationsDecisionResponse]


class ApplicationDecisionRequest(StrictModel):
    expected_version: int = Field(ge=1)
    decision: ApplicationDecisionType
    reason_code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{2,63}$")
    applicant_safe_message: str = Field(min_length=3, max_length=500)
    authorized_service_types: list[ServiceType] | None = Field(default=None, min_length=1, max_length=3)
    authorized_vehicle_id: UUID | None = None
    authorization_valid_until: datetime | None = None

    @field_validator("applicant_safe_message")
    @classmethod
    def clean_message(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def approval_fields_only_for_approval(self):
        approval_values_present = (
            self.authorized_service_types is not None
            or self.authorized_vehicle_id is not None
            or self.authorization_valid_until is not None
        )
        if self.decision == ApplicationDecisionType.APPROVE:
            if self.authorized_service_types is None:
                raise ValueError("Approval requires at least one authorized service type.")
            if len(self.authorized_service_types) != len(set(self.authorized_service_types)):
                raise ValueError("Authorized service types must be unique.")
            if self.authorization_valid_until is not None and self.authorization_valid_until.tzinfo is None:
                raise ValueError("authorization_valid_until must include a timezone.")
        elif approval_values_present:
            raise ValueError("Authorization fields are accepted only for an approval decision.")
        return self


class VehicleVerificationRequest(StrictModel):
    """A scoped reviewer decision over the vehicle selected in one application."""

    expected_application_version: int = Field(ge=1)
    reason_code: str = Field(pattern=r"^VEHICLE_REQUIREMENTS_CONFIRMED$")


class SuppressedAggregateCount(BaseModel):
    status: str
    value: int | None
    suppressed: bool


class DriverOnboardingAggregateResponse(BaseModel):
    city_id: UUID
    as_of: datetime
    minimum_cell_size: int
    total_applications: int | None
    total_suppressed: bool
    status_counts: list[SuppressedAggregateCount]
    decided_application_count: int | None
    average_review_seconds: float | None
    review_duration_suppressed: bool
