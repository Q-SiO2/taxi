"""Authoritative city recruitment and authorization state transitions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

from geoalchemy2 import Geometry
from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.auth.models import Role, UserRole
from taximobile_api.domains.driver_applications.models import (
    ApplicationAnswerType,
    ApplicationDecisionType,
    ApplicationEvidenceStatus,
    CityApplicationStatus,
    CityAuthorizationStatus,
    DocumentScanStatus,
    DriverApplicationAnswer,
    DriverApplicationDecision,
    DriverApplicationDocument,
    DriverApplicationEvidence,
    DriverCityApplication,
    DriverCityAuthorization,
    DriverCityAuthorizationService,
    DriverRequirementItem,
    DriverRequirementVersion,
    RequirementEvidenceType,
    RequirementValidityRule,
    RequirementVersionStatus,
)
from taximobile_api.domains.driver_applications.schemas import (
    ApplicationDecisionRequest,
    CityApplicationUpdateRequest,
    RequirementItemInput,
)
from taximobile_api.domains.drivers.models import (
    CredentialVerificationStatus,
    DriverAccountStatus,
    DriverCredential,
    DriverProfile,
    DriverVerification,
    Vehicle,
    VehicleStatus,
    VehicleVerificationStatus,
    VerificationStatus,
)
from taximobile_api.domains.markets.constants import (
    LEGACY_CITY_ID,
    LEGACY_DRIVER_PROFILE_REQUIREMENT_ITEM_ID,
    LEGACY_DRIVER_REQUIREMENT_VERSION_ID,
)
from taximobile_api.domains.markets.models import (
    City,
    CityConfigurationService,
    CityConfigurationVersion,
    CityLifecycleStatus,
    CityServiceAreaVersion,
    ConfigurationStatus,
    ServiceAreaStatus,
    ServiceType,
)


EDITABLE_APPLICATION_STATUSES = frozenset(
    {
        CityApplicationStatus.NOT_STARTED,
        CityApplicationStatus.ADDITIONAL_INFORMATION_REQUIRED,
    }
)
REVIEWABLE_APPLICATION_STATUSES = frozenset(
    {CityApplicationStatus.SUBMITTED, CityApplicationStatus.UNDER_REVIEW}
)
RECRUITING_CITY_STATUSES = frozenset(
    {
        CityLifecycleStatus.CONFIGURING,
        CityLifecycleStatus.PILOT,
        CityLifecycleStatus.ACTIVE,
    }
)
ACTIVE_AUTHORIZATION_CITY_STATUSES = frozenset(
    {CityLifecycleStatus.PILOT, CityLifecycleStatus.ACTIVE}
)

ALLOWED_DECISION_REASON_CODES: dict[ApplicationDecisionType, frozenset[str]] = {
    ApplicationDecisionType.START_REVIEW: frozenset({"MANUAL_REVIEW_STARTED"}),
    ApplicationDecisionType.REQUEST_ADDITIONAL_INFORMATION: frozenset(
        {
            "MISSING_OR_INVALID_EVIDENCE",
            "CREDENTIAL_NOT_VALID",
            "VEHICLE_NOT_ELIGIBLE",
            "JURISDICTION_REQUIREMENT_NOT_MET",
        }
    ),
    ApplicationDecisionType.APPROVE: frozenset(
        {"REQUIREMENTS_CONFIRMED", "LEGACY_COMPATIBILITY_APPROVAL"}
    ),
    ApplicationDecisionType.REJECT: frozenset(
        {
            "CREDENTIAL_NOT_VALID",
            "VEHICLE_NOT_ELIGIBLE",
            "JURISDICTION_REQUIREMENT_NOT_MET",
            "DUPLICATE_APPLICATION",
        }
    ),
}


class RecruitmentNotFound(ValueError):
    pass


class RecruitmentConflict(ValueError):
    pass


class ApplicationIncomplete(ValueError):
    def __init__(self, missing_item_ids: list[UUID]) -> None:
        super().__init__("The application does not satisfy every required item.")
        self.missing_item_ids = missing_item_ids


class ApplicationReferenceInvalid(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CompletionResult:
    missing_item_ids: tuple[UUID, ...]

    @property
    def complete(self) -> bool:
        return not self.missing_item_ids


@dataclass(frozen=True, slots=True)
class SelectedAuthorization:
    authorization: DriverCityAuthorization
    city: City
    service_type: ServiceType


async def advisory_scope_lock(session: AsyncSession, scope: str) -> None:
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))"),
        {"scope": scope},
    )


def require_expected_version(current: int, expected: int) -> None:
    if current != expected:
        raise RecruitmentConflict(
            "The application changed after it was loaded. Refresh it before trying again."
        )


async def requirement_items(
    session: AsyncSession,
    requirement_version_id: UUID,
) -> list[DriverRequirementItem]:
    return list(
        await session.scalars(
            select(DriverRequirementItem)
            .where(DriverRequirementItem.requirement_version_id == requirement_version_id)
            .order_by(DriverRequirementItem.display_order, DriverRequirementItem.id)
        )
    )


async def active_requirement_for_city(
    session: AsyncSession,
    city_id: UUID,
    *,
    now: datetime | None = None,
) -> tuple[City, DriverRequirementVersion]:
    current_time = now or datetime.now(UTC)
    row = (
        await session.execute(
            select(City, DriverRequirementVersion)
            .join(DriverRequirementVersion, DriverRequirementVersion.city_id == City.id)
            .where(
                City.id == city_id,
                City.lifecycle_status.in_(RECRUITING_CITY_STATUSES),
                DriverRequirementVersion.status == RequirementVersionStatus.ACTIVE,
                DriverRequirementVersion.effective_from <= current_time,
                or_(
                    DriverRequirementVersion.effective_until.is_(None),
                    DriverRequirementVersion.effective_until > current_time,
                ),
            )
        )
    ).one_or_none()
    if row is None:
        raise RecruitmentNotFound("This city is not currently accepting driver applications.")
    return row


async def owned_application(
    session: AsyncSession,
    application_id: UUID,
    driver_id: UUID,
    *,
    lock: bool = False,
) -> DriverCityApplication:
    statement = select(DriverCityApplication).where(
        DriverCityApplication.id == application_id,
        DriverCityApplication.driver_id == driver_id,
    )
    if lock:
        statement = statement.with_for_update()
    application = await session.scalar(statement)
    if application is None:
        raise RecruitmentNotFound("Driver city application not found.")
    return application


async def create_city_application(
    session: AsyncSession,
    *,
    user_id: UUID,
    city_id: UUID,
    display_name: str | None,
) -> tuple[DriverCityApplication, bool]:
    city, requirement_version = await active_requirement_for_city(session, city_id)
    profile = await session.scalar(
        select(DriverProfile).where(DriverProfile.user_id == user_id).with_for_update()
    )
    if profile is None:
        if display_name is None:
            raise ApplicationReferenceInvalid(
                "display_name is required when creating the account's driver identity."
            )
        profile = DriverProfile(user_id=user_id, display_name=display_name)
        session.add(profile)
        await session.flush()
        session.add(
            DriverVerification(driver_id=profile.id, status=VerificationStatus.NOT_STARTED)
        )
    elif display_name is not None and display_name != profile.display_name:
        raise RecruitmentConflict(
            "The supplied display name does not match the existing driver identity."
        )
    await session.flush()
    await advisory_scope_lock(session, f"driver-city-application:{profile.id}:{city.id}")

    active_authorization = await session.scalar(
        select(DriverCityAuthorization.id).where(
            DriverCityAuthorization.driver_id == profile.id,
            DriverCityAuthorization.city_id == city.id,
            DriverCityAuthorization.status == CityAuthorizationStatus.ACTIVE,
        )
    )
    if active_authorization is not None:
        raise RecruitmentConflict("This driver already has active authorization for the city.")
    existing = await session.scalar(
        select(DriverCityApplication)
        .where(
            DriverCityApplication.driver_id == profile.id,
            DriverCityApplication.city_id == city.id,
            DriverCityApplication.status.in_(
                {
                    CityApplicationStatus.NOT_STARTED,
                    CityApplicationStatus.SUBMITTED,
                    CityApplicationStatus.UNDER_REVIEW,
                    CityApplicationStatus.ADDITIONAL_INFORMATION_REQUIRED,
                }
            ),
        )
        .with_for_update()
    )
    if existing is not None:
        return existing, False

    application = DriverCityApplication(
        driver_id=profile.id,
        city_id=city.id,
        requirement_version_id=requirement_version.id,
        status=CityApplicationStatus.NOT_STARTED,
    )
    session.add(application)
    await session.flush()
    for item in await requirement_items(session, requirement_version.id):
        if item.evidence_type == RequirementEvidenceType.PROFILE:
            session.add(
                DriverApplicationEvidence(
                    application_id=application.id,
                    requirement_item_id=item.id,
                    profile_id=profile.id,
                    status=ApplicationEvidenceStatus.PENDING,
                )
            )
    await session.flush()
    return application, True


def answer_matches_item(
    item: DriverRequirementItem,
    answer: DriverApplicationAnswer | None,
    *,
    today: date,
) -> bool:
    if answer is None:
        return False
    if item.evidence_type == RequirementEvidenceType.BOOLEAN:
        return (
            answer.answer_type == ApplicationAnswerType.BOOLEAN
            and answer.boolean_value is True
        )
    if item.evidence_type == RequirementEvidenceType.DATE:
        return (
            answer.answer_type == ApplicationAnswerType.DATE
            and answer.date_value is not None
            and answer.date_value <= today
        )
    if item.evidence_type == RequirementEvidenceType.TEXT:
        return (
            answer.answer_type == ApplicationAnswerType.TEXT
            and bool(answer.bounded_text_value and answer.bounded_text_value.strip())
        )
    return False


async def evidence_matches_item(
    session: AsyncSession,
    application: DriverCityApplication,
    item: DriverRequirementItem,
    evidence: DriverApplicationEvidence | None,
    *,
    now: datetime,
) -> bool:
    if evidence is None:
        return False
    if item.evidence_type == RequirementEvidenceType.PROFILE:
        return evidence.profile_id == application.driver_id
    if item.evidence_type == RequirementEvidenceType.VEHICLE:
        if evidence.vehicle_id is None:
            return False
        vehicle = await session.get(Vehicle, evidence.vehicle_id)
        if vehicle is None or vehicle.driver_id != application.driver_id:
            return False
        if item.validity_rule_code == RequirementValidityRule.VEHICLE_VERIFIED:
            return (
                vehicle.status == VehicleStatus.ACTIVE
                and vehicle.verification_status == VehicleVerificationStatus.VERIFIED
            )
        return True
    if item.evidence_type == RequirementEvidenceType.CREDENTIAL:
        if evidence.credential_id is None:
            return False
        credential = await session.get(DriverCredential, evidence.credential_id)
        if credential is None or credential.driver_id != application.driver_id:
            return False
        if (
            item.reference_type_code is not None
            and credential.credential_type != item.reference_type_code
        ):
            return False
        if item.validity_rule_code in {
            RequirementValidityRule.CREDENTIAL_VERIFIED,
            RequirementValidityRule.CREDENTIAL_UNEXPIRED,
        } and credential.verification_status != CredentialVerificationStatus.VERIFIED:
            return False
        if (
            item.validity_rule_code == RequirementValidityRule.CREDENTIAL_UNEXPIRED
            and credential.expires_at is not None
            and credential.expires_at <= now
        ):
            return False
        return True
    if item.evidence_type == RequirementEvidenceType.DOCUMENT:
        if evidence.document_id is None:
            return False
        document = await session.get(DriverApplicationDocument, evidence.document_id)
        return bool(
            document is not None
            and document.application_id == application.id
            and document.requirement_item_id == item.id
            and document.deleted_at is None
            and document.malware_scan_status == DocumentScanStatus.CLEAN
        )
    return False


async def application_completion(
    session: AsyncSession,
    application: DriverCityApplication,
    *,
    now: datetime | None = None,
) -> CompletionResult:
    current_time = now or datetime.now(UTC)
    items = await requirement_items(session, application.requirement_version_id)
    answers = {
        answer.requirement_item_id: answer
        for answer in await session.scalars(
            select(DriverApplicationAnswer).where(
                DriverApplicationAnswer.application_id == application.id
            )
        )
    }
    evidence_by_item = {
        evidence.requirement_item_id: evidence
        for evidence in await session.scalars(
            select(DriverApplicationEvidence).where(
                DriverApplicationEvidence.application_id == application.id
            )
        )
    }
    missing: list[UUID] = []
    for item in items:
        if not item.required:
            continue
        if item.evidence_type in {
            RequirementEvidenceType.BOOLEAN,
            RequirementEvidenceType.DATE,
            RequirementEvidenceType.TEXT,
        }:
            satisfied = answer_matches_item(
                item,
                answers.get(item.id),
                today=current_time.date(),
            )
        else:
            satisfied = await evidence_matches_item(
                session,
                application,
                item,
                evidence_by_item.get(item.id),
                now=current_time,
            )
        if not satisfied:
            missing.append(item.id)
    return CompletionResult(tuple(missing))


async def update_city_application(
    session: AsyncSession,
    application: DriverCityApplication,
    payload: CityApplicationUpdateRequest,
) -> DriverCityApplication:
    if application.status not in EDITABLE_APPLICATION_STATUSES:
        raise RecruitmentConflict("This application is not editable in its current status.")
    require_expected_version(application.optimistic_version, payload.expected_version)
    items = {
        item.id: item
        for item in await requirement_items(session, application.requirement_version_id)
    }
    touched_ids = {
        *(item.requirement_item_id for item in payload.answers or []),
        *(item.requirement_item_id for item in payload.evidence or []),
        *payload.remove_answer_item_ids,
        *payload.remove_evidence_item_ids,
    }
    if not touched_ids.issubset(items):
        raise ApplicationReferenceInvalid(
            "Every updated item must belong to the application's requirement version."
        )

    for answer_input in payload.answers or []:
        item = items[answer_input.requirement_item_id]
        expected_type = {
            RequirementEvidenceType.BOOLEAN: ApplicationAnswerType.BOOLEAN,
            RequirementEvidenceType.DATE: ApplicationAnswerType.DATE,
            RequirementEvidenceType.TEXT: ApplicationAnswerType.TEXT,
        }.get(item.evidence_type)
        if expected_type is None or expected_type != answer_input.answer_type:
            raise ApplicationReferenceInvalid("The answer type does not match the requirement item.")
        answer = await session.scalar(
            select(DriverApplicationAnswer).where(
                DriverApplicationAnswer.application_id == application.id,
                DriverApplicationAnswer.requirement_item_id == item.id,
            )
        )
        if answer is None:
            answer = DriverApplicationAnswer(
                application_id=application.id,
                requirement_item_id=item.id,
                answer_type=answer_input.answer_type,
            )
            session.add(answer)
        answer.answer_type = answer_input.answer_type
        answer.boolean_value = answer_input.boolean_value
        answer.date_value = answer_input.date_value
        answer.bounded_text_value = answer_input.text_value

    if payload.remove_answer_item_ids:
        await session.execute(
            delete(DriverApplicationAnswer).where(
                DriverApplicationAnswer.application_id == application.id,
                DriverApplicationAnswer.requirement_item_id.in_(payload.remove_answer_item_ids),
            )
        )

    for evidence_input in payload.evidence or []:
        item = items[evidence_input.requirement_item_id]
        supplied_type = (
            RequirementEvidenceType.PROFILE
            if evidence_input.profile_id is not None
            else RequirementEvidenceType.VEHICLE
            if evidence_input.vehicle_id is not None
            else RequirementEvidenceType.CREDENTIAL
        )
        if supplied_type != item.evidence_type:
            raise ApplicationReferenceInvalid(
                "The reference type does not match the requirement item."
            )
        if evidence_input.profile_id is not None:
            if evidence_input.profile_id != application.driver_id:
                raise ApplicationReferenceInvalid("Driver profile reference is not owned by the applicant.")
        elif evidence_input.vehicle_id is not None:
            vehicle = await session.get(Vehicle, evidence_input.vehicle_id)
            if vehicle is None or vehicle.driver_id != application.driver_id:
                raise ApplicationReferenceInvalid("Vehicle reference is not owned by the applicant.")
        elif evidence_input.credential_id is not None:
            credential = await session.get(DriverCredential, evidence_input.credential_id)
            if credential is None or credential.driver_id != application.driver_id:
                raise ApplicationReferenceInvalid("Credential reference is not owned by the applicant.")
            if (
                item.reference_type_code is not None
                and credential.credential_type != item.reference_type_code
            ):
                raise ApplicationReferenceInvalid(
                    "Credential reference does not match the required credential type."
                )
        evidence = await session.scalar(
            select(DriverApplicationEvidence).where(
                DriverApplicationEvidence.application_id == application.id,
                DriverApplicationEvidence.requirement_item_id == item.id,
            )
        )
        if evidence is None:
            evidence = DriverApplicationEvidence(
                application_id=application.id,
                requirement_item_id=item.id,
            )
            session.add(evidence)
        evidence.profile_id = evidence_input.profile_id
        evidence.vehicle_id = evidence_input.vehicle_id
        evidence.credential_id = evidence_input.credential_id
        evidence.document_id = None
        evidence.status = ApplicationEvidenceStatus.PENDING

    if payload.remove_evidence_item_ids:
        await session.execute(
            delete(DriverApplicationEvidence).where(
                DriverApplicationEvidence.application_id == application.id,
                DriverApplicationEvidence.requirement_item_id.in_(
                    payload.remove_evidence_item_ids
                ),
            )
        )

    application.optimistic_version += 1
    application.updated_at = datetime.now(UTC)
    await session.flush()
    return application


async def submit_city_application(
    session: AsyncSession,
    application: DriverCityApplication,
) -> DriverCityApplication:
    if application.status in {
        CityApplicationStatus.SUBMITTED,
        CityApplicationStatus.UNDER_REVIEW,
    }:
        return application
    if application.status not in EDITABLE_APPLICATION_STATUSES:
        raise RecruitmentConflict("This application cannot be submitted in its current status.")
    completion = await application_completion(session, application)
    if not completion.complete:
        raise ApplicationIncomplete(list(completion.missing_item_ids))
    now = datetime.now(UTC)
    application.status = CityApplicationStatus.SUBMITTED
    application.submitted_at = now
    application.submission_revision += 1
    application.optimistic_version += 1
    application.updated_at = now
    await session.flush()
    return application


async def withdraw_city_application(
    session: AsyncSession,
    application: DriverCityApplication,
) -> DriverCityApplication:
    if application.status == CityApplicationStatus.WITHDRAWN:
        return application
    if application.status not in {
        CityApplicationStatus.NOT_STARTED,
        CityApplicationStatus.SUBMITTED,
        CityApplicationStatus.UNDER_REVIEW,
        CityApplicationStatus.ADDITIONAL_INFORMATION_REQUIRED,
    }:
        raise RecruitmentConflict("This application can no longer be withdrawn.")
    now = datetime.now(UTC)
    application.status = CityApplicationStatus.WITHDRAWN
    application.withdrawn_at = now
    application.optimistic_version += 1
    application.updated_at = now
    await session.flush()
    return application


async def reviewed_service_types_for_city(
    session: AsyncSession,
    city_id: UUID,
) -> frozenset[ServiceType]:
    rows = await session.scalars(
        select(CityConfigurationService.service_type)
        .join(
            CityConfigurationVersion,
            CityConfigurationVersion.id
            == CityConfigurationService.configuration_version_id,
        )
        .where(
            CityConfigurationVersion.city_id == city_id,
            CityConfigurationVersion.status.in_(
                {ConfigurationStatus.APPROVED, ConfigurationStatus.ACTIVE}
            ),
            CityConfigurationService.enabled.is_(True),
        )
    )
    return frozenset(rows)


async def decide_application(
    session: AsyncSession,
    *,
    application: DriverCityApplication,
    reviewer_user_id: UUID,
    payload: ApplicationDecisionRequest,
) -> DriverApplicationDecision:
    require_expected_version(application.optimistic_version, payload.expected_version)
    if payload.reason_code not in ALLOWED_DECISION_REASON_CODES[payload.decision]:
        raise ApplicationReferenceInvalid("The reason code is not allowed for this decision.")

    if payload.decision == ApplicationDecisionType.START_REVIEW:
        if application.status != CityApplicationStatus.SUBMITTED:
            raise RecruitmentConflict("Only a submitted application can enter review.")
        target_status = CityApplicationStatus.UNDER_REVIEW
    elif payload.decision == ApplicationDecisionType.REQUEST_ADDITIONAL_INFORMATION:
        if application.status not in REVIEWABLE_APPLICATION_STATUSES:
            raise RecruitmentConflict(
                "Additional information can be requested only from a reviewable application."
            )
        target_status = CityApplicationStatus.ADDITIONAL_INFORMATION_REQUIRED
    elif payload.decision == ApplicationDecisionType.REJECT:
        if application.status not in REVIEWABLE_APPLICATION_STATUSES:
            raise RecruitmentConflict("Only a reviewable application can be rejected.")
        target_status = CityApplicationStatus.REJECTED
    else:
        if application.status not in REVIEWABLE_APPLICATION_STATUSES:
            raise RecruitmentConflict("Only a reviewable application can be approved.")
        completion = await application_completion(session, application)
        if not completion.complete:
            raise ApplicationIncomplete(list(completion.missing_item_ids))
        target_status = CityApplicationStatus.APPROVED

    now = datetime.now(UTC)
    if payload.authorization_valid_until is not None and payload.authorization_valid_until <= now:
        raise ApplicationReferenceInvalid("Authorization expiry must be in the future.")

    authorization: DriverCityAuthorization | None = None
    if payload.decision == ApplicationDecisionType.APPROVE:
        assert payload.authorized_service_types is not None
        reviewed_services = await reviewed_service_types_for_city(session, application.city_id)
        if not set(payload.authorized_service_types).issubset(reviewed_services):
            raise RecruitmentConflict(
                "Every authorized service must be enabled by a reviewed city configuration."
            )
        if payload.authorized_vehicle_id is not None:
            vehicle = await session.get(Vehicle, payload.authorized_vehicle_id)
            if (
                vehicle is None
                or vehicle.driver_id != application.driver_id
                or vehicle.status != VehicleStatus.ACTIVE
                or vehicle.verification_status != VehicleVerificationStatus.VERIFIED
            ):
                raise ApplicationReferenceInvalid(
                    "The authorized vehicle must be owned, active, and verified."
                )
        required_vehicle_items = list(
            await session.scalars(
                select(DriverRequirementItem.id).where(
                    DriverRequirementItem.requirement_version_id
                    == application.requirement_version_id,
                    DriverRequirementItem.required.is_(True),
                    DriverRequirementItem.evidence_type == RequirementEvidenceType.VEHICLE,
                )
            )
        )
        if required_vehicle_items:
            if payload.authorized_vehicle_id is None:
                raise ApplicationReferenceInvalid(
                    "Approval requires the verified vehicle referenced by this city application."
                )
            matching_evidence = await session.scalar(
                select(DriverApplicationEvidence.id).where(
                    DriverApplicationEvidence.application_id == application.id,
                    DriverApplicationEvidence.requirement_item_id.in_(required_vehicle_items),
                    DriverApplicationEvidence.vehicle_id == payload.authorized_vehicle_id,
                )
            )
            if matching_evidence is None:
                raise ApplicationReferenceInvalid(
                    "The authorized vehicle is not the vehicle reviewed in this application."
                )
        # Serialize city approval with reinstatement and assignment before
        # checking for an existing active authorization or creating a new one.
        profile = await session.scalar(
            select(DriverProfile)
            .where(DriverProfile.id == application.driver_id)
            .with_for_update().execution_options(populate_existing=True)
        )
        assert profile is not None
        active_authorization = await session.scalar(
            select(DriverCityAuthorization.id).where(
                DriverCityAuthorization.driver_id == application.driver_id,
                DriverCityAuthorization.city_id == application.city_id,
                DriverCityAuthorization.status == CityAuthorizationStatus.ACTIVE,
            )
        )
        if active_authorization is not None:
            raise RecruitmentConflict("The driver already has active authorization for this city.")
        authorization = DriverCityAuthorization(
            driver_id=application.driver_id,
            city_id=application.city_id,
            application_id=application.id,
            vehicle_id=payload.authorized_vehicle_id,
            status=CityAuthorizationStatus.ACTIVE,
            scheduled_offers_enabled=False,
            valid_from=now,
            valid_until=payload.authorization_valid_until,
        )
        session.add(authorization)
        await session.flush()
        for service_type in payload.authorized_service_types:
            session.add(
                DriverCityAuthorizationService(
                    authorization_id=authorization.id,
                    service_type=service_type,
                )
            )
        profile.verification_status = VerificationStatus.APPROVED
        profile.account_status = DriverAccountStatus.ACTIVE
        existing_role = await session.scalar(
            select(UserRole).where(
                UserRole.user_id == profile.user_id,
                UserRole.role == Role.DRIVER,
            )
        )
        if existing_role is None:
            session.add(UserRole(user_id=profile.user_id, role=Role.DRIVER))
        for evidence in await session.scalars(
            select(DriverApplicationEvidence).where(
                DriverApplicationEvidence.application_id == application.id
            )
        ):
            evidence.status = ApplicationEvidenceStatus.ACCEPTED

    application.status = target_status
    application.optimistic_version += 1
    application.updated_at = now
    if target_status in {CityApplicationStatus.APPROVED, CityApplicationStatus.REJECTED}:
        application.reviewed_at = now
    decision = DriverApplicationDecision(
        application_id=application.id,
        requirement_version_id=application.requirement_version_id,
        reviewer_user_id=reviewer_user_id,
        decision=payload.decision,
        bounded_reason_code=payload.reason_code,
        applicant_safe_message=payload.applicant_safe_message,
        application_version=application.optimistic_version,
        submission_revision=application.submission_revision,
    )
    session.add(decision)
    await session.flush()
    application.latest_decision_id = decision.id
    # Keep the timestamp materialized across this second UPDATE.  Otherwise the
    # SQL expression configured by ``onupdate`` expires the attribute and an
    # async response presenter can trigger forbidden implicit database I/O.
    application.updated_at = now
    await session.flush()
    await session.refresh(application)
    return decision


async def ensure_legacy_city_application(
    session: AsyncSession,
    profile: DriverProfile,
) -> DriverCityApplication | None:
    requirement_version = await session.get(
        DriverRequirementVersion,
        LEGACY_DRIVER_REQUIREMENT_VERSION_ID,
    )
    if requirement_version is None:
        return None
    existing = await session.scalar(
        select(DriverCityApplication).where(
            DriverCityApplication.driver_id == profile.id,
            DriverCityApplication.city_id == LEGACY_CITY_ID,
            DriverCityApplication.status.in_(
                {
                    CityApplicationStatus.NOT_STARTED,
                    CityApplicationStatus.SUBMITTED,
                    CityApplicationStatus.UNDER_REVIEW,
                    CityApplicationStatus.ADDITIONAL_INFORMATION_REQUIRED,
                    CityApplicationStatus.APPROVED,
                }
            ),
        )
    )
    if existing is not None:
        return existing
    application = DriverCityApplication(
        driver_id=profile.id,
        city_id=LEGACY_CITY_ID,
        requirement_version_id=LEGACY_DRIVER_REQUIREMENT_VERSION_ID,
        status=CityApplicationStatus.NOT_STARTED,
    )
    session.add(application)
    await session.flush()
    session.add(
        DriverApplicationEvidence(
            application_id=application.id,
            requirement_item_id=LEGACY_DRIVER_PROFILE_REQUIREMENT_ITEM_ID,
            profile_id=profile.id,
            status=ApplicationEvidenceStatus.PENDING,
        )
    )
    await session.flush()
    return application


async def sync_legacy_submission(
    session: AsyncSession,
    profile: DriverProfile,
) -> None:
    application = await ensure_legacy_city_application(session, profile)
    if application is None or application.status == CityApplicationStatus.SUBMITTED:
        return
    if application.status in EDITABLE_APPLICATION_STATUSES:
        await submit_city_application(session, application)


async def sync_legacy_approval(
    session: AsyncSession,
    *,
    profile: DriverProfile,
    reviewer_user_id: UUID,
) -> None:
    application = await ensure_legacy_city_application(session, profile)
    if application is None:
        return
    if application.status == CityApplicationStatus.NOT_STARTED:
        await submit_city_application(session, application)
    if application.status == CityApplicationStatus.APPROVED:
        return
    if application.status not in REVIEWABLE_APPLICATION_STATUSES:
        return
    await decide_application(
        session,
        application=application,
        reviewer_user_id=reviewer_user_id,
        payload=ApplicationDecisionRequest(
            expected_version=application.optimistic_version,
            decision=ApplicationDecisionType.APPROVE,
            reason_code="LEGACY_COMPATIBILITY_APPROVAL",
            applicant_safe_message="Your Casablanca driver application was approved.",
            authorized_service_types=[ServiceType.ON_DEMAND],
        ),
    )


async def select_active_authorization(
    session: AsyncSession,
    *,
    profile: DriverProfile,
    requested_city_id: UUID | None,
    requested_service_type: ServiceType,
    now: datetime | None = None,
) -> SelectedAuthorization:
    current_time = now or datetime.now(UTC)
    statement = (
        select(DriverCityAuthorization, City)
        .join(City, City.id == DriverCityAuthorization.city_id)
        .join(
            DriverCityAuthorizationService,
            DriverCityAuthorizationService.authorization_id == DriverCityAuthorization.id,
        )
        .where(
            DriverCityAuthorization.driver_id == profile.id,
            DriverCityAuthorization.status == CityAuthorizationStatus.ACTIVE,
            DriverCityAuthorization.valid_from <= current_time,
            or_(
                DriverCityAuthorization.valid_until.is_(None),
                DriverCityAuthorization.valid_until > current_time,
            ),
            DriverCityAuthorizationService.service_type == requested_service_type,
            City.lifecycle_status.in_(ACTIVE_AUTHORIZATION_CITY_STATUSES),
        )
        .order_by(City.code, DriverCityAuthorization.id)
    )
    if requested_city_id is not None:
        statement = statement.where(DriverCityAuthorization.city_id == requested_city_id)
    rows = (await session.execute(statement)).all()
    if not rows:
        raise RecruitmentConflict(
            "No active city authorization covers the selected service."
        )
    if requested_city_id is None and len(rows) > 1:
        raise RecruitmentConflict("Select which authorized city to use before going online.")
    authorization, city = rows[0]
    if authorization.vehicle_id is not None and authorization.vehicle_id != profile.active_vehicle_id:
        raise RecruitmentConflict(
            "Select the vehicle authorized for this city before going online."
        )
    application = await session.get(DriverCityApplication, authorization.application_id)
    if application is None:
        raise RecruitmentConflict("The city authorization has no valid application record.")
    completion = await application_completion(session, application, now=current_time)
    if not completion.complete:
        raise RecruitmentConflict(
            "A city credential or vehicle requirement is no longer valid."
        )
    return SelectedAuthorization(authorization, city, requested_service_type)


async def location_is_inside_active_service_area(
    session: AsyncSession,
    *,
    city: City,
    location_id: UUID,
    now: datetime | None = None,
) -> bool:
    current_time = now or datetime.now(UTC)
    if city.active_configuration_version_id is None:
        return False
    from taximobile_api.domains.drivers.models import DriverLocation

    result = await session.scalar(
        select(
            func.ST_Covers(
                CityServiceAreaVersion.boundary.cast(
                    Geometry(geometry_type="MULTIPOLYGON", srid=4326)
                ),
                DriverLocation.point.cast(Geometry(geometry_type="POINT", srid=4326)),
            )
        )
        .join(
            CityConfigurationVersion,
            CityConfigurationVersion.service_area_version_id == CityServiceAreaVersion.id,
        )
        .join(DriverLocation, DriverLocation.id == location_id)
        .where(
            CityConfigurationVersion.id == city.active_configuration_version_id,
            CityConfigurationVersion.city_id == city.id,
            CityConfigurationVersion.status == ConfigurationStatus.ACTIVE,
            CityServiceAreaVersion.city_id == city.id,
            CityServiceAreaVersion.status == ServiceAreaStatus.ACTIVE,
            CityServiceAreaVersion.effective_from <= current_time,
            or_(
                CityServiceAreaVersion.effective_until.is_(None),
                CityServiceAreaVersion.effective_until > current_time,
            ),
        )
    )
    return bool(result)
