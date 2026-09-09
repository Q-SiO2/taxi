"""Scoped requirement administration, application review, and onboarding aggregates."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.administration.operations_dependencies import (
    OperationsSessionIdentity,
    require_recent_operations_mfa,
    require_operations_permission,
)
from taximobile_api.domains.administration.permissions import (
    OperationsPermission,
    OperationsPrincipal,
)
from taximobile_api.domains.administration.service import audit
from taximobile_api.domains.auth.models import User
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.driver_applications.models import (
    ApplicationEvidenceStatus,
    ApplicationDecisionType,
    CityApplicationStatus,
    DocumentScanStatus,
    DriverApplicationDecision,
    DriverApplicationDocument,
    DriverApplicationEvidence,
    DriverCityApplication,
    DriverRequirementItem,
    DriverRequirementVersion,
    RequirementEvidenceType,
    RequirementVersionStatus,
)
from taximobile_api.domains.driver_applications.presenters import (
    city_application_response,
    operations_decision_response,
    requirement_version_response,
)
from taximobile_api.domains.driver_applications.schemas import (
    ApplicationDecisionRequest,
    DriverOnboardingAggregateResponse,
    OperationsDriverApplicationDetailResponse,
    OperationsDriverApplicationListResponse,
    OperationsDriverApplicationSummary,
    RequirementVersionCommandRequest,
    RequirementVersionCreateRequest,
    RequirementVersionListResponse,
    RequirementVersionResponse,
    RequirementVersionUpdateRequest,
    SuppressedAggregateCount,
    VehicleVerificationRequest,
)
from taximobile_api.domains.driver_applications.service import (
    ApplicationIncomplete,
    ApplicationReferenceInvalid,
    RecruitmentConflict,
    REVIEWABLE_APPLICATION_STATUSES,
    advisory_scope_lock,
    decide_application,
    require_expected_version,
)
from taximobile_api.domains.drivers.models import (
    DriverProfile,
    Vehicle,
    VehicleStatus,
    VehicleVerificationStatus,
)
from taximobile_api.domains.drivers.schemas import VehicleResponse
from taximobile_api.domains.idempotency.service import (
    IdempotencyKeyReuse,
    IdempotentReplay,
    InvalidIdempotencyKey,
    begin_command,
    finish_command,
)
from taximobile_api.domains.markets.models import City
from taximobile_api.integrations.driver_documents import DriverDocumentError


router = APIRouter(prefix="/operations", tags=["operations-driver-applications"])

MANAGE_REQUIREMENTS = OperationsPermission.MANAGE_DRIVER_REQUIREMENTS
REVIEW_APPLICATIONS = OperationsPermission.REVIEW_DRIVER_APPLICATIONS
VIEW_AGGREGATES = OperationsPermission.VIEW_SCOPED_OPERATIONAL_AGGREGATES
MINIMUM_AGGREGATE_CELL_SIZE = 5


def operations_error(error: Exception) -> HTTPException:
    if isinstance(error, (ApplicationReferenceInvalid, ApplicationIncomplete)):
        return HTTPException(status_code=422, detail=str(error))
    return HTTPException(status_code=409, detail=str(error))


async def scoped_city_or_404(
    session: AsyncSession,
    principal: OperationsPrincipal,
    city_id: UUID,
    permission: OperationsPermission,
    *,
    lock: bool = False,
) -> City:
    if not principal.allows(permission, city_id=city_id):
        raise HTTPException(status_code=404, detail="City not found.")
    statement = select(City).where(City.id == city_id)
    if lock:
        statement = statement.with_for_update()
    city = await session.scalar(statement)
    if city is None:
        raise HTTPException(status_code=404, detail="City not found.")
    return city


def add_requirement_items(
    session: AsyncSession,
    version_id: UUID,
    items,
) -> None:
    for item in items:
        session.add(
            DriverRequirementItem(
                requirement_version_id=version_id,
                requirement_code=item.requirement_code,
                evidence_type=item.evidence_type,
                required=item.required,
                validity_rule_code=item.validity_rule_code,
                reference_type_code=item.reference_type_code,
                display_order=item.display_order,
                localized_copy_key=item.localized_copy_key,
                localized_label=item.localized_label.model_dump(),
                localized_description=item.localized_description.model_dump(),
            )
        )


@router.get(
    "/cities/{city_id}/driver-requirement-versions",
    response_model=RequirementVersionListResponse,
)
async def list_driver_requirement_versions(
    city_id: UUID,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE_REQUIREMENTS)),
    session: AsyncSession = Depends(database_session),
) -> RequirementVersionListResponse:
    await scoped_city_or_404(session, principal, city_id, MANAGE_REQUIREMENTS)
    statement = (
        select(DriverRequirementVersion)
        .where(DriverRequirementVersion.city_id == city_id)
        .order_by(DriverRequirementVersion.created_at.desc(), DriverRequirementVersion.id)
    )
    versions = list(
        await session.scalars(statement.offset((page - 1) * limit).limit(limit))
    )
    total = await session.scalar(
        select(func.count())
        .select_from(DriverRequirementVersion)
        .where(DriverRequirementVersion.city_id == city_id)
    )
    return RequirementVersionListResponse(
        items=[await requirement_version_response(session, version) for version in versions],
        page=page,
        limit=limit,
        total=total or 0,
    )


@router.post(
    "/cities/{city_id}/driver-requirement-versions",
    response_model=RequirementVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_driver_requirement_version(
    city_id: UUID,
    payload: RequirementVersionCreateRequest,
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE_REQUIREMENTS)),
    session: AsyncSession = Depends(database_session),
) -> RequirementVersionResponse:
    try:
        async with session.begin():
            city = await scoped_city_or_404(
                session, principal, city_id, MANAGE_REQUIREMENTS, lock=True
            )
            await advisory_scope_lock(session, f"driver-requirement-version:{city_id}")
            duplicate = await session.scalar(
                select(DriverRequirementVersion.id).where(
                    DriverRequirementVersion.city_id == city_id,
                    DriverRequirementVersion.version == payload.version,
                )
            )
            if duplicate is not None:
                raise RecruitmentConflict(
                    "A driver requirement version with this city/version already exists."
                )
            version = DriverRequirementVersion(
                city_id=city_id,
                version=payload.version,
                status=RequirementVersionStatus.DRAFT,
                effective_from=payload.effective_from,
                effective_until=payload.effective_until,
                created_by_user_id=principal.user_id,
            )
            session.add(version)
            await session.flush()
            add_requirement_items(session, version.id, payload.items)
            await session.flush()
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="DRIVER_REQUIREMENT_VERSION_CREATED",
                resource_type="driver_requirement_version",
                resource_id=version.id,
                market_id=city.market_id,
                city_id=city.id,
                changes={
                    "version": version.version,
                    "status": version.status.value,
                    "item_count": len(payload.items),
                },
            )
            result = await requirement_version_response(session, version)
        return result
    except RecruitmentConflict as error:
        raise operations_error(error) from error


async def scoped_requirement_version_or_404(
    session: AsyncSession,
    principal: OperationsPrincipal,
    version_id: UUID,
    *,
    lock: bool = False,
) -> tuple[DriverRequirementVersion, City]:
    statement = (
        select(DriverRequirementVersion, City)
        .join(City, City.id == DriverRequirementVersion.city_id)
        .where(DriverRequirementVersion.id == version_id)
    )
    if lock:
        statement = statement.with_for_update(of=DriverRequirementVersion)
    row = (await session.execute(statement)).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Driver requirement version not found.")
    version, city = row
    if not principal.allows(MANAGE_REQUIREMENTS, city_id=city.id):
        raise HTTPException(status_code=404, detail="Driver requirement version not found.")
    return version, city


@router.get(
    "/driver-requirement-versions/{version_id}",
    response_model=RequirementVersionResponse,
)
async def get_driver_requirement_version(
    version_id: UUID,
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE_REQUIREMENTS)),
    session: AsyncSession = Depends(database_session),
) -> RequirementVersionResponse:
    version, _ = await scoped_requirement_version_or_404(
        session, principal, version_id
    )
    return await requirement_version_response(session, version)


@router.patch(
    "/driver-requirement-versions/{version_id}",
    response_model=RequirementVersionResponse,
)
async def update_driver_requirement_version(
    version_id: UUID,
    payload: RequirementVersionUpdateRequest,
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE_REQUIREMENTS)),
    session: AsyncSession = Depends(database_session),
) -> RequirementVersionResponse:
    try:
        async with session.begin():
            version, city = await scoped_requirement_version_or_404(
                session, principal, version_id, lock=True
            )
            if version.status != RequirementVersionStatus.DRAFT:
                raise RecruitmentConflict("Only a draft requirement version can be edited.")
            require_expected_version(version.optimistic_version, payload.expected_version)
            new_from = payload.effective_from or version.effective_from
            new_until = (
                None
                if payload.clear_effective_until
                else payload.effective_until
                if payload.effective_until is not None
                else version.effective_until
            )
            if new_until is not None and new_until <= new_from:
                raise ApplicationReferenceInvalid(
                    "effective_until must be after effective_from."
                )
            version.effective_from = new_from
            version.effective_until = new_until
            if payload.items is not None:
                await session.execute(
                    delete(DriverRequirementItem).where(
                        DriverRequirementItem.requirement_version_id == version.id
                    )
                )
                add_requirement_items(session, version.id, payload.items)
            version.optimistic_version += 1
            version.updated_at = datetime.now(UTC)
            await session.flush()
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="DRIVER_REQUIREMENT_VERSION_UPDATED",
                resource_type="driver_requirement_version",
                resource_id=version.id,
                market_id=city.market_id,
                city_id=city.id,
                changes={
                    "optimistic_version": version.optimistic_version,
                    "items_replaced": payload.items is not None,
                },
            )
            result = await requirement_version_response(session, version)
        return result
    except (RecruitmentConflict, ApplicationReferenceInvalid) as error:
        raise operations_error(error) from error


async def transition_requirement_version(
    session: AsyncSession,
    *,
    principal: OperationsPrincipal,
    version_id: UUID,
    payload: RequirementVersionCommandRequest,
    target: RequirementVersionStatus,
) -> DriverRequirementVersion:
    version, city = await scoped_requirement_version_or_404(
        session, principal, version_id, lock=True
    )
    if version.status == target:
        return version
    require_expected_version(version.optimistic_version, payload.expected_version)
    expected_source = {
        RequirementVersionStatus.IN_REVIEW: RequirementVersionStatus.DRAFT,
        RequirementVersionStatus.ACTIVE: RequirementVersionStatus.IN_REVIEW,
    }[target]
    if version.status != expected_source:
        raise RecruitmentConflict(
            f"Requirement version cannot transition from {version.status.value} to {target.value}."
        )
    item_count = await session.scalar(
        select(func.count())
        .select_from(DriverRequirementItem)
        .where(DriverRequirementItem.requirement_version_id == version.id)
    )
    if not item_count:
        raise RecruitmentConflict("A requirement version must contain at least one item.")
    now = datetime.now(UTC)
    if target == RequirementVersionStatus.ACTIVE:
        if version.effective_from > now or (
            version.effective_until is not None and version.effective_until <= now
        ):
            raise RecruitmentConflict(
                "Only a currently effective requirement version can be activated."
            )
        await advisory_scope_lock(session, f"driver-requirement-activation:{city.id}")
        previous_active = await session.scalar(
            select(DriverRequirementVersion)
            .where(
                DriverRequirementVersion.city_id == city.id,
                DriverRequirementVersion.status == RequirementVersionStatus.ACTIVE,
                DriverRequirementVersion.id != version.id,
            )
            .with_for_update()
        )
        if previous_active is not None:
            previous_active.status = RequirementVersionStatus.REPLACED
            previous_active.updated_at = now
        version.activated_by_user_id = principal.user_id
        version.activated_at = now
    else:
        version.submitted_by_user_id = principal.user_id
        version.submitted_at = now
    previous = version.status
    version.status = target
    version.optimistic_version += 1
    version.updated_at = now
    await session.flush()
    await audit(
        session,
        actor_user_id=principal.user_id,
        action=f"DRIVER_REQUIREMENT_VERSION_{target.value}",
        resource_type="driver_requirement_version",
        resource_id=version.id,
        market_id=city.market_id,
        city_id=city.id,
        changes={
            "previous_status": previous.value,
            "current_status": target.value,
            "reason": payload.reason,
            "optimistic_version": version.optimistic_version,
        },
    )
    return version


@router.post(
    "/driver-requirement-versions/{version_id}/submit",
    response_model=RequirementVersionResponse,
)
async def submit_driver_requirement_version(
    version_id: UUID,
    payload: RequirementVersionCommandRequest,
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE_REQUIREMENTS)),
    session: AsyncSession = Depends(database_session),
) -> RequirementVersionResponse:
    try:
        async with session.begin():
            version = await transition_requirement_version(
                session=session,
                principal=principal,
                version_id=version_id,
                payload=payload,
                target=RequirementVersionStatus.IN_REVIEW,
            )
            result = await requirement_version_response(session, version)
        return result
    except RecruitmentConflict as error:
        raise operations_error(error) from error


@router.post(
    "/driver-requirement-versions/{version_id}/activate",
    response_model=RequirementVersionResponse,
)
async def activate_driver_requirement_version(
    version_id: UUID,
    payload: RequirementVersionCommandRequest,
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE_REQUIREMENTS)),
    session: AsyncSession = Depends(database_session),
) -> RequirementVersionResponse:
    try:
        async with session.begin():
            version = await transition_requirement_version(
                session=session,
                principal=principal,
                version_id=version_id,
                payload=payload,
                target=RequirementVersionStatus.ACTIVE,
            )
            result = await requirement_version_response(session, version)
        return result
    except RecruitmentConflict as error:
        raise operations_error(error) from error


def review_scope_condition(principal: OperationsPrincipal):
    city_ids = principal.city_ids_for(REVIEW_APPLICATIONS)
    if not city_ids:
        return DriverCityApplication.city_id.in_([])
    return DriverCityApplication.city_id.in_(city_ids)


@router.get(
    "/driver-applications",
    response_model=OperationsDriverApplicationListResponse,
)
async def list_driver_applications(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    city_id: UUID | None = Query(default=None),
    application_status: CityApplicationStatus | None = Query(default=None, alias="status"),
    principal: OperationsPrincipal = Depends(require_operations_permission(REVIEW_APPLICATIONS)),
    session: AsyncSession = Depends(database_session),
) -> OperationsDriverApplicationListResponse:
    filters = [review_scope_condition(principal)]
    if city_id is not None:
        if not principal.allows(REVIEW_APPLICATIONS, city_id=city_id):
            raise HTTPException(status_code=404, detail="City not found.")
        filters.append(DriverCityApplication.city_id == city_id)
    if application_status is not None:
        filters.append(DriverCityApplication.status == application_status)
    base = (
        select(
            DriverCityApplication,
            DriverProfile.display_name,
            City,
            DriverRequirementVersion,
        )
        .join(DriverProfile, DriverProfile.id == DriverCityApplication.driver_id)
        .join(City, City.id == DriverCityApplication.city_id)
        .join(
            DriverRequirementVersion,
            DriverRequirementVersion.id == DriverCityApplication.requirement_version_id,
        )
        .where(*filters)
    )
    rows = (
        await session.execute(
            base.order_by(
                DriverCityApplication.submitted_at.asc().nulls_last(),
                DriverCityApplication.created_at,
                DriverCityApplication.id,
            )
            .offset((page - 1) * limit)
            .limit(limit)
        )
    ).all()
    total = await session.scalar(
        select(func.count()).select_from(DriverCityApplication).where(*filters)
    )
    return OperationsDriverApplicationListResponse(
        items=[
            OperationsDriverApplicationSummary(
                id=application.id,
                driver_id=application.driver_id,
                display_name=display_name,
                city_id=city.id,
                city_code=city.code,
                city_name=city.localized_name,
                requirement_version_id=version.id,
                requirement_version=version.version,
                status=application.status.value,
                optimistic_version=application.optimistic_version,
                submitted_at=application.submitted_at,
                updated_at=application.updated_at,
            )
            for application, display_name, city, version in rows
        ],
        page=page,
        limit=limit,
        total=total or 0,
    )


async def scoped_application_or_404(
    session: AsyncSession,
    principal: OperationsPrincipal,
    application_id: UUID,
    *,
    lock: bool = False,
) -> DriverCityApplication:
    statement = select(DriverCityApplication).where(
        DriverCityApplication.id == application_id,
        review_scope_condition(principal),
    )
    if lock:
        statement = statement.with_for_update()
    application = await session.scalar(statement)
    if application is None:
        raise HTTPException(status_code=404, detail="Driver city application not found.")
    return application


async def operations_application_detail(
    session: AsyncSession,
    application: DriverCityApplication,
    *,
    document_upload_available: bool,
) -> OperationsDriverApplicationDetailResponse:
    profile = await session.get(DriverProfile, application.driver_id)
    assert profile is not None
    user = await session.get(User, profile.user_id)
    assert user is not None
    decisions = list(
        await session.scalars(
            select(DriverApplicationDecision)
            .where(DriverApplicationDecision.application_id == application.id)
            .order_by(DriverApplicationDecision.created_at, DriverApplicationDecision.id)
        )
    )
    return OperationsDriverApplicationDetailResponse(
        application=await city_application_response(
            session,
            application,
            document_upload_available=document_upload_available,
        ),
        applicant_display_name=profile.display_name,
        applicant_phone_number=user.phone_number,
        applicant_email=user.email,
        decisions=[operations_decision_response(decision) for decision in decisions],
    )


def vehicle_response(vehicle: Vehicle) -> VehicleResponse:
    return VehicleResponse(
        id=vehicle.id,
        make=vehicle.make,
        model=vehicle.model,
        color=vehicle.color,
        status=vehicle.status.value,
        verification_status=vehicle.verification_status.value,
    )


@router.get(
    "/driver-applications/{application_id}",
    response_model=OperationsDriverApplicationDetailResponse,
)
async def get_driver_application(
    application_id: UUID,
    request: Request,
    principal: OperationsPrincipal = Depends(require_operations_permission(REVIEW_APPLICATIONS)),
    session: AsyncSession = Depends(database_session),
) -> OperationsDriverApplicationDetailResponse:
    application = await scoped_application_or_404(
        session, principal, application_id
    )
    return await operations_application_detail(
        session,
        application,
        document_upload_available=request.app.state.driver_document_store.available,
    )


@router.post(
    "/driver-applications/{application_id}/decisions",
    response_model=OperationsDriverApplicationDetailResponse,
)
async def decide_driver_application(
    application_id: UUID,
    payload: ApplicationDecisionRequest,
    request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(require_operations_permission(REVIEW_APPLICATIONS)),
    session: AsyncSession = Depends(database_session),
) -> OperationsDriverApplicationDetailResponse | JSONResponse:
    try:
        async with session.begin():
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation=f"operations-driver-application-decision:{application_id}",
                key=idempotency_key,
                payload=payload.model_dump(mode="json"),
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            application = await scoped_application_or_404(
                session, principal, application_id, lock=True
            )
            city = await session.get(City, application.city_id)
            assert city is not None
            previous_status = application.status
            await decide_application(
                session,
                application=application,
                reviewer_user_id=principal.user_id,
                payload=payload,
            )
            await audit(
                session,
                actor_user_id=principal.user_id,
                action=f"DRIVER_CITY_APPLICATION_{payload.decision.value}",
                resource_type="driver_city_application",
                resource_id=application.id,
                market_id=city.market_id,
                city_id=city.id,
                changes={
                    "previous_status": previous_status.value,
                    "current_status": application.status.value,
                    "decision": payload.decision.value,
                    "reason_code": payload.reason_code,
                    "requirement_version_id": str(application.requirement_version_id),
                    "submission_revision": application.submission_revision,
                },
            )
            result = await operations_application_detail(
                session,
                application,
                document_upload_available=request.app.state.driver_document_store.available,
            )
            await finish_command(
                session,
                command,
                status_code=200,
                payload=result.model_dump(mode="json"),
            )
        return result
    except InvalidIdempotencyKey as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except IdempotencyKeyReuse as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except (RecruitmentConflict, ApplicationReferenceInvalid, ApplicationIncomplete) as error:
        raise operations_error(error) from error


@router.post(
    "/driver-applications/{application_id}/vehicles/{vehicle_id}/verify",
    response_model=VehicleResponse,
)
async def verify_driver_application_vehicle(
    application_id: UUID,
    vehicle_id: UUID,
    payload: VehicleVerificationRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(require_operations_permission(REVIEW_APPLICATIONS)),
    session: AsyncSession = Depends(database_session),
) -> VehicleResponse | JSONResponse:
    """Verify only the active vehicle selected in an authorized city application."""
    try:
        async with session.begin():
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation=(
                    "operations-driver-application-vehicle-verify:"
                    f"{application_id}:{vehicle_id}"
                ),
                key=idempotency_key,
                payload=payload.model_dump(mode="json"),
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)

            application = await scoped_application_or_404(
                session,
                principal,
                application_id,
                lock=True,
            )
            require_expected_version(
                application.optimistic_version,
                payload.expected_application_version,
            )
            if application.status not in REVIEWABLE_APPLICATION_STATUSES:
                raise RecruitmentConflict(
                    "A vehicle can be verified only while its city application is under review."
                )
            vehicle = await session.scalar(
                select(Vehicle).where(Vehicle.id == vehicle_id).with_for_update()
            )
            if vehicle is None or vehicle.driver_id != application.driver_id:
                raise HTTPException(status_code=404, detail="Vehicle not found.")
            if vehicle.status != VehicleStatus.ACTIVE:
                raise RecruitmentConflict("An inactive vehicle cannot be verified.")
            evidence = await session.scalar(
                select(DriverApplicationEvidence)
                .join(
                    DriverRequirementItem,
                    DriverRequirementItem.id
                    == DriverApplicationEvidence.requirement_item_id,
                )
                .where(
                    DriverApplicationEvidence.application_id == application.id,
                    DriverApplicationEvidence.vehicle_id == vehicle.id,
                    DriverRequirementItem.evidence_type == RequirementEvidenceType.VEHICLE,
                )
            )
            if evidence is None:
                raise HTTPException(
                    status_code=422,
                    detail="The vehicle is not selected as evidence in this application.",
                )

            previous_status = vehicle.verification_status
            vehicle.verification_status = VehicleVerificationStatus.VERIFIED
            evidence.status = ApplicationEvidenceStatus.ACCEPTED
            city = await session.get(City, application.city_id)
            assert city is not None
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="DRIVER_APPLICATION_VEHICLE_VERIFIED",
                resource_type="vehicle",
                resource_id=vehicle.id,
                market_id=city.market_id,
                city_id=city.id,
                changes={
                    "application_id": str(application.id),
                    "previous_verification_status": previous_status.value,
                    "current_verification_status": vehicle.verification_status.value,
                    "reason_code": payload.reason_code,
                    "application_version": application.optimistic_version,
                    "submission_revision": application.submission_revision,
                },
            )
            result = vehicle_response(vehicle)
            await finish_command(
                session,
                command,
                status_code=200,
                payload=result.model_dump(mode="json"),
            )
        return result
    except InvalidIdempotencyKey as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except IdempotencyKeyReuse as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except RecruitmentConflict as error:
        raise operations_error(error) from error


@router.get(
    "/driver-applications/{application_id}/documents/{document_id}",
    response_model=None,
)
async def read_driver_application_document(
    application_id: UUID,
    document_id: UUID,
    request: Request,
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(require_operations_permission(REVIEW_APPLICATIONS)),
    session: AsyncSession = Depends(database_session),
) -> Response:
    application = await scoped_application_or_404(
        session, principal, application_id
    )
    if not request.app.state.driver_document_store.available:
        raise HTTPException(
            status_code=503,
            detail="Protected driver-document storage is not configured.",
        )
    document = await session.scalar(
        select(DriverApplicationDocument).where(
            DriverApplicationDocument.id == document_id,
            DriverApplicationDocument.application_id == application.id,
            DriverApplicationDocument.deleted_at.is_(None),
        )
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Driver application document not found.")
    if document.malware_scan_status != DocumentScanStatus.CLEAN:
        raise HTTPException(status_code=409, detail="The document is not cleared for review.")
    if not await request.app.state.rate_limiter.allow(
        f"driver-document-read:{principal.user_id}",
        limit=request.app.state.settings.driver_document_access_rate_limit_per_minute,
        window_seconds=60,
    ):
        raise HTTPException(status_code=429, detail="Too many document retrievals. Try again later.")
    try:
        content = await request.app.state.driver_document_store.read(
            document.opaque_storage_key
        )
    except DriverDocumentError as error:
        raise HTTPException(
            status_code=503,
            detail="Protected document retrieval is temporarily unavailable.",
        ) from error

    city = await session.get(City, application.city_id)
    assert city is not None
    await audit(
        session,
        actor_user_id=principal.user_id,
        action="DRIVER_APPLICATION_DOCUMENT_READ",
        resource_type="driver_application_document",
        resource_id=document.id,
        market_id=city.market_id,
        city_id=city.id,
        changes={
            "application_id": str(application.id),
            "requirement_item_id": str(document.requirement_item_id),
            "media_type": document.media_type,
            "byte_size": document.byte_size,
        },
    )
    await session.commit()
    extension = {
        "application/pdf": "pdf",
        "image/jpeg": "jpg",
        "image/png": "png",
    }[document.media_type]
    return Response(
        content=content,
        media_type=document.media_type,
        headers={
            "Cache-Control": "no-store, max-age=0",
            "Content-Disposition": (
                f'attachment; filename="driver-document-{document.id}.{extension}"'
            ),
            "X-Content-Type-Options": "nosniff",
        },
    )


def suppressed(value: int) -> tuple[int | None, bool]:
    return (value, False) if value >= MINIMUM_AGGREGATE_CELL_SIZE else (None, True)


@router.get(
    "/cities/{city_id}/operational-aggregates",
    response_model=DriverOnboardingAggregateResponse,
)
async def get_city_onboarding_aggregates(
    city_id: UUID,
    principal: OperationsPrincipal = Depends(require_operations_permission(VIEW_AGGREGATES)),
    session: AsyncSession = Depends(database_session),
) -> DriverOnboardingAggregateResponse:
    await scoped_city_or_404(session, principal, city_id, VIEW_AGGREGATES)
    rows = (
        await session.execute(
            select(DriverCityApplication.status, func.count())
            .where(DriverCityApplication.city_id == city_id)
            .group_by(DriverCityApplication.status)
        )
    ).all()
    raw_counts = {application_status: int(count) for application_status, count in rows}
    total_raw = sum(raw_counts.values())
    total_value, total_suppressed = suppressed(total_raw)
    decided_count, average_review_seconds = (
        await session.execute(
            select(
                func.count(),
                func.avg(
                    func.extract(
                        "epoch",
                        DriverCityApplication.reviewed_at
                        - DriverCityApplication.submitted_at,
                    )
                ),
            ).where(
                DriverCityApplication.city_id == city_id,
                DriverCityApplication.reviewed_at.is_not(None),
                DriverCityApplication.submitted_at.is_not(None),
            )
        )
    ).one()
    review_suppressed = int(decided_count) < MINIMUM_AGGREGATE_CELL_SIZE
    status_counts = []
    for application_status in CityApplicationStatus:
        value, is_suppressed = suppressed(raw_counts.get(application_status, 0))
        status_counts.append(
            SuppressedAggregateCount(
                status=application_status.value,
                value=value,
                suppressed=is_suppressed,
            )
        )
    return DriverOnboardingAggregateResponse(
        city_id=city_id,
        as_of=datetime.now(UTC),
        minimum_cell_size=MINIMUM_AGGREGATE_CELL_SIZE,
        total_applications=total_value,
        total_suppressed=total_suppressed,
        status_counts=status_counts,
        decided_application_count=(None if review_suppressed else int(decided_count)),
        average_review_seconds=(
            None
            if review_suppressed or average_review_seconds is None
            else float(average_review_seconds)
        ),
        review_duration_suppressed=review_suppressed,
    )
