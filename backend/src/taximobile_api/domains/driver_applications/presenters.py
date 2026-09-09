"""Privacy-specific response assembly for recruitment surfaces."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.driver_applications.models import (
    DriverApplicationAnswer,
    DriverApplicationDecision,
    DriverApplicationDocument,
    DriverApplicationEvidence,
    DriverCityApplication,
    DriverCityAuthorization,
    DriverCityAuthorizationService,
    DriverRequirementItem,
    DriverRequirementVersion,
)
from taximobile_api.domains.driver_applications.schemas import (
    ApplicantSafeDecisionResponse,
    ApplicationAnswerResponse,
    ApplicationDocumentResponse,
    ApplicationEvidenceResponse,
    CityApplicationResponse,
    CityApplicationSummaryResponse,
    CityAuthorizationResponse,
    OperationsDecisionResponse,
    RecruitingCityResponse,
    RequirementItemResponse,
    RequirementVersionResponse,
)
from taximobile_api.domains.driver_applications.service import (
    EDITABLE_APPLICATION_STATUSES,
    application_completion,
    requirement_items,
)
from taximobile_api.domains.markets.models import City


def requirement_item_response(item: DriverRequirementItem) -> RequirementItemResponse:
    return RequirementItemResponse(
        id=item.id,
        requirement_code=item.requirement_code,
        evidence_type=item.evidence_type.value,
        allowed_evidence_types=[item.evidence_type.value],
        required=item.required,
        validity_rule_code=item.validity_rule_code.value,
        reference_type_code=item.reference_type_code,
        display_order=item.display_order,
        localized_copy_key=item.localized_copy_key,
        localized_label=item.localized_label,
        localized_description=item.localized_description,
    )


async def requirement_version_response(
    session: AsyncSession,
    version: DriverRequirementVersion,
) -> RequirementVersionResponse:
    items = await requirement_items(session, version.id)
    return RequirementVersionResponse(
        id=version.id,
        city_id=version.city_id,
        version=version.version,
        status=version.status.value,
        effective_from=version.effective_from,
        effective_until=version.effective_until,
        optimistic_version=version.optimistic_version,
        items=[requirement_item_response(item) for item in items],
        submitted_at=version.submitted_at,
        activated_at=version.activated_at,
        created_at=version.created_at,
        updated_at=version.updated_at,
    )


def recruiting_city_response(
    city: City,
    requirement_version: DriverRequirementVersion,
) -> RecruitingCityResponse:
    return RecruitingCityResponse(
        id=city.id,
        code=city.code,
        localized_name=city.localized_name,
        timezone=city.timezone,
        lifecycle_status=city.lifecycle_status.value,
        requirement_version_id=requirement_version.id,
        requirement_version=requirement_version.version,
    )


async def authorization_response(
    session: AsyncSession,
    authorization: DriverCityAuthorization,
) -> CityAuthorizationResponse:
    service_types = list(
        await session.scalars(
            select(DriverCityAuthorizationService.service_type)
            .where(
                DriverCityAuthorizationService.authorization_id == authorization.id
            )
            .order_by(DriverCityAuthorizationService.service_type)
        )
    )
    return CityAuthorizationResponse(
        id=authorization.id,
        city_id=authorization.city_id,
        status=authorization.status.value,
        vehicle_id=authorization.vehicle_id,
        service_types=[service.value for service in service_types],
        scheduled_offers_enabled=authorization.scheduled_offers_enabled,
        valid_from=authorization.valid_from,
        valid_until=authorization.valid_until,
    )


async def city_application_response(
    session: AsyncSession,
    application: DriverCityApplication,
    *,
    document_upload_available: bool,
) -> CityApplicationResponse:
    city = await session.get(City, application.city_id)
    requirement_version = await session.get(
        DriverRequirementVersion,
        application.requirement_version_id,
    )
    assert city is not None and requirement_version is not None
    items = await requirement_items(session, requirement_version.id)
    answers = list(
        await session.scalars(
            select(DriverApplicationAnswer)
            .where(DriverApplicationAnswer.application_id == application.id)
            .order_by(DriverApplicationAnswer.requirement_item_id)
        )
    )
    evidence = list(
        await session.scalars(
            select(DriverApplicationEvidence)
            .where(DriverApplicationEvidence.application_id == application.id)
            .order_by(DriverApplicationEvidence.requirement_item_id)
        )
    )
    item_types = {item.id: item.evidence_type.value for item in items}
    documents = list(
        await session.scalars(
            select(DriverApplicationDocument)
            .where(
                DriverApplicationDocument.application_id == application.id,
                DriverApplicationDocument.deleted_at.is_(None),
            )
            .order_by(DriverApplicationDocument.uploaded_at, DriverApplicationDocument.id)
        )
    )
    latest_decision = (
        await session.get(DriverApplicationDecision, application.latest_decision_id)
        if application.latest_decision_id is not None
        else None
    )
    authorization = await session.scalar(
        select(DriverCityAuthorization).where(
            DriverCityAuthorization.application_id == application.id
        )
    )
    completion = await application_completion(session, application)
    return CityApplicationResponse(
        id=application.id,
        driver_id=application.driver_id,
        city_id=city.id,
        city_code=city.code,
        city_name=city.localized_name,
        requirement_version_id=requirement_version.id,
        requirement_version=requirement_version.version,
        status=application.status.value,
        optimistic_version=application.optimistic_version,
        submission_revision=application.submission_revision,
        editable=application.status in EDITABLE_APPLICATION_STATUSES,
        complete=completion.complete,
        missing_required_item_ids=list(completion.missing_item_ids),
        document_upload_available=document_upload_available,
        submitted_at=application.submitted_at,
        reviewed_at=application.reviewed_at,
        withdrawn_at=application.withdrawn_at,
        created_at=application.created_at,
        updated_at=application.updated_at,
        requirements=[requirement_item_response(item) for item in items],
        answers=[
            ApplicationAnswerResponse(
                requirement_item_id=answer.requirement_item_id,
                answer_type=answer.answer_type.value,
                boolean_value=answer.boolean_value,
                date_value=answer.date_value,
                text_value=answer.bounded_text_value,
            )
            for answer in answers
        ],
        evidence=[
            ApplicationEvidenceResponse(
                requirement_item_id=item.requirement_item_id,
                evidence_type=item_types[item.requirement_item_id],
                profile_id=item.profile_id,
                vehicle_id=item.vehicle_id,
                credential_id=item.credential_id,
                document_id=item.document_id,
                status=item.status.value,
            )
            for item in evidence
        ],
        documents=[
            ApplicationDocumentResponse(
                id=document.id,
                requirement_item_id=document.requirement_item_id,
                media_type=document.media_type,
                byte_size=document.byte_size,
                scan_status=document.malware_scan_status.value,
                uploaded_at=document.uploaded_at,
                deleted_at=document.deleted_at,
            )
            for document in documents
        ],
        latest_decision=(
            ApplicantSafeDecisionResponse(
                decision=latest_decision.decision.value,
                reason_code=latest_decision.bounded_reason_code,
                message=latest_decision.applicant_safe_message,
                created_at=latest_decision.created_at,
            )
            if latest_decision is not None
            else None
        ),
        authorization=(
            await authorization_response(session, authorization)
            if authorization is not None
            else None
        ),
    )


async def city_application_summary_response(
    session: AsyncSession,
    application: DriverCityApplication,
) -> CityApplicationSummaryResponse:
    city = await session.get(City, application.city_id)
    requirement_version = await session.get(
        DriverRequirementVersion,
        application.requirement_version_id,
    )
    latest_decision = (
        await session.get(DriverApplicationDecision, application.latest_decision_id)
        if application.latest_decision_id is not None
        else None
    )
    assert city is not None and requirement_version is not None
    return CityApplicationSummaryResponse(
        id=application.id,
        city_id=city.id,
        city_code=city.code,
        city_name=city.localized_name,
        requirement_version_id=requirement_version.id,
        requirement_version=requirement_version.version,
        status=application.status.value,
        optimistic_version=application.optimistic_version,
        submitted_at=application.submitted_at,
        reviewed_at=application.reviewed_at,
        updated_at=application.updated_at,
        latest_applicant_message=(
            latest_decision.applicant_safe_message if latest_decision is not None else None
        ),
    )


def operations_decision_response(
    decision: DriverApplicationDecision,
) -> OperationsDecisionResponse:
    return OperationsDecisionResponse(
        id=decision.id,
        reviewer_user_id=decision.reviewer_user_id,
        decision=decision.decision.value,
        reason_code=decision.bounded_reason_code,
        applicant_safe_message=decision.applicant_safe_message,
        application_version=decision.application_version,
        submission_revision=decision.submission_revision,
        created_at=decision.created_at,
    )
