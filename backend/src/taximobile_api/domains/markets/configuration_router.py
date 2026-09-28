"""Versioned service-area, coherent configuration, and readiness commands."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2 import Geometry
from geoalchemy2.elements import WKTElement
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
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
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.driver_applications.models import DriverRequirementVersion
from taximobile_api.domains.fixed_routes.models import (
    CityConfigurationRoute,
    FixedRoute,
    FixedRoutePublicationStatus,
    FixedRouteStatus,
    FixedRouteVersion,
)
from taximobile_api.domains.markets.models import (
    City,
    CityConfigurationService,
    CityConfigurationVersion,
    CityLifecycleStatus,
    CityReadinessCheck,
    CityServiceAreaVersion,
    ConfigurationStatus,
    OperatorCityAssignment,
    ReadinessStatus,
    ServiceAreaStatus,
    ServiceType,
)
from taximobile_api.domains.markets.constants import (
    PILOT_ENTRY_CITY_READINESS_GATES,
    POST_LAUNCH_CITY_EVIDENCE_GATES,
    PUBLIC_ACTIVATION_CITY_READINESS_GATES,
)
from taximobile_api.domains.markets.operations_router import scoped_city_or_404
from taximobile_api.domains.markets.schemas import (
    CityConfigurationCreateRequest,
    CityConfigurationListResponse,
    CityConfigurationResponse,
    CityConfigurationUpdateRequest,
    ConfigurationCommandRequest,
    ConfigurationRouteInput,
    ConfigurationRouteResponse,
    ConfigurationServiceInput,
    ConfigurationServiceResponse,
    MultiPolygonGeometry,
    ReadinessCheckResponse,
    ReadinessDecisionRequest,
    ServiceAreaTransitionRequest,
    ServiceAreaVersionCreateRequest,
    ServiceAreaVersionListResponse,
    ServiceAreaVersionResponse,
    ServiceAreaVersionUpdateRequest,
)
from taximobile_api.domains.markets.service import (
    ControlPlaneConflict,
    OptimisticVersionConflict,
    missing_readiness_gates,
    require_independent_configuration_reviewer,
    require_expected_version,
    validate_configuration_components,
)
from taximobile_api.domains.pricing.models import (
    BookingType,
    OperatorFeePolicy,
    PricingRule,
    SchedulingPolicy,
)
from taximobile_api.domains.payments.models import (
    PaymentCapabilityStatus,
    PaymentCapabilityVersion,
)


router = APIRouter(prefix="/operations", tags=["operations-city-configuration"])


async def _valid_boundary(session: AsyncSession, boundary: MultiPolygonGeometry) -> WKTElement:
    wkt = boundary.to_wkt()
    valid, reason = (
        await session.execute(
            select(
                func.ST_IsValid(func.ST_GeomFromText(wkt, 4326)),
                func.ST_IsValidReason(func.ST_GeomFromText(wkt, 4326)),
            )
        )
    ).one()
    if not valid:
        raise ControlPlaneConflict(f"Service-area geometry is invalid: {reason}")
    return WKTElement(wkt, srid=4326)


async def service_area_response(
    session: AsyncSession,
    area: CityServiceAreaVersion,
) -> ServiceAreaVersionResponse:
    geojson_text = await session.scalar(
        select(
            func.ST_AsGeoJSON(
                CityServiceAreaVersion.boundary.cast(
                    Geometry(geometry_type="MULTIPOLYGON", srid=4326)
                )
            )
        ).where(CityServiceAreaVersion.id == area.id)
    )
    assert geojson_text is not None
    return ServiceAreaVersionResponse(
        id=area.id,
        city_id=area.city_id,
        version=area.version,
        boundary=MultiPolygonGeometry.model_validate(json.loads(geojson_text)),
        status=area.status.value,
        effective_from=area.effective_from,
        effective_until=area.effective_until,
        optimistic_version=area.optimistic_version,
        created_at=area.created_at,
        updated_at=area.updated_at,
    )


async def _configuration_services(
    session: AsyncSession,
    configuration_id: UUID,
) -> list[ConfigurationServiceResponse]:
    services = list(
        await session.scalars(
            select(CityConfigurationService)
            .where(CityConfigurationService.configuration_version_id == configuration_id)
            .order_by(CityConfigurationService.service_type)
        )
    )
    return [
        ConfigurationServiceResponse(
            service_type=service.service_type.value,
            operator_city_assignment_id=service.operator_city_assignment_id,
            tariff_version_id=service.tariff_version_id,
            operator_fee_policy_version_id=service.operator_fee_policy_version_id,
            scheduling_policy_version_id=service.scheduling_policy_version_id,
            payment_capability_version_id=service.payment_capability_version_id,
            enabled=service.enabled,
        )
        for service in services
    ]


async def _configuration_routes(
    session: AsyncSession,
    configuration_id: UUID,
) -> list[ConfigurationRouteResponse]:
    routes = list(
        await session.scalars(
            select(CityConfigurationRoute)
            .where(
                CityConfigurationRoute.configuration_version_id == configuration_id
            )
            .order_by(CityConfigurationRoute.fixed_route_version_id)
        )
    )
    return [
        ConfigurationRouteResponse(
            fixed_route_version_id=route.fixed_route_version_id,
            immediate_booking_enabled=route.immediate_booking_enabled,
            scheduled_booking_enabled=route.scheduled_booking_enabled,
        )
        for route in routes
    ]


async def _readiness_checks(
    session: AsyncSession,
    configuration_id: UUID,
) -> list[ReadinessCheckResponse]:
    checks = list(
        await session.scalars(
            select(CityReadinessCheck)
            .where(CityReadinessCheck.configuration_version_id == configuration_id)
            .order_by(CityReadinessCheck.gate_code)
        )
    )
    return [
        ReadinessCheckResponse(
            id=check.id,
            gate_code=check.gate_code,
            status=check.status.value,
            non_secret_evidence_reference=check.non_secret_evidence_reference,
            decided_at=check.decided_at,
        )
        for check in checks
    ]


async def configuration_response(
    session: AsyncSession,
    configuration: CityConfigurationVersion,
) -> CityConfigurationResponse:
    checks = await _readiness_checks(session, configuration.id)
    post_launch_status = next(
        (
            check.status
            for check in checks
            if check.gate_code in POST_LAUNCH_CITY_EVIDENCE_GATES
        ),
        ReadinessStatus.PENDING.value,
    )
    missing_public = await missing_readiness_gates(
        session,
        configuration.id,
        PUBLIC_ACTIVATION_CITY_READINESS_GATES,
    )
    return CityConfigurationResponse(
        id=configuration.id,
        city_id=configuration.city_id,
        version=configuration.version,
        status=configuration.status.value,
        service_area_version_id=configuration.service_area_version_id,
        driver_requirement_version_id=configuration.driver_requirement_version_id,
        optimistic_version=configuration.optimistic_version,
        services=await _configuration_services(session, configuration.id),
        routes=await _configuration_routes(session, configuration.id),
        readiness_checks=checks,
        missing_readiness_gates=missing_public,
        missing_pilot_entry_gates=await missing_readiness_gates(
            session,
            configuration.id,
            PILOT_ENTRY_CITY_READINESS_GATES,
        ),
        missing_public_activation_gates=missing_public,
        post_launch_review_status=post_launch_status,
        submitted_at=configuration.submitted_at,
        approved_at=configuration.approved_at,
        activated_at=configuration.activated_at,
        created_at=configuration.created_at,
        updated_at=configuration.updated_at,
    )


async def _scoped_area_or_404(
    session: AsyncSession,
    principal: OperationsPrincipal,
    version_id: UUID,
    permission: OperationsPermission,
    *,
    lock: bool = False,
) -> CityServiceAreaVersion:
    city_ids = principal.city_ids_for(permission)
    statement = select(CityServiceAreaVersion).where(
        CityServiceAreaVersion.id == version_id,
        CityServiceAreaVersion.city_id.in_(city_ids),
    )
    if lock:
        statement = statement.with_for_update()
    area = await session.scalar(statement)
    if area is None:
        raise HTTPException(status_code=404, detail="Service-area version not found.")
    return area


async def _scoped_configuration_or_404(
    session: AsyncSession,
    principal: OperationsPrincipal,
    version_id: UUID,
    permission: OperationsPermission,
    *,
    lock: bool = False,
) -> CityConfigurationVersion:
    city_ids = principal.city_ids_for(permission)
    statement = select(CityConfigurationVersion).where(
        CityConfigurationVersion.id == version_id,
        CityConfigurationVersion.city_id.in_(city_ids),
    )
    if lock:
        statement = statement.with_for_update()
    configuration = await session.scalar(statement)
    if configuration is None:
        raise HTTPException(status_code=404, detail="City configuration version not found.")
    return configuration


async def _validate_draft_services(
    session: AsyncSession,
    city_id: UUID,
    services: list[ConfigurationServiceInput],
) -> None:
    for service in services:
        assignment = await session.get(OperatorCityAssignment, service.operator_city_assignment_id)
        if (
            assignment is None
            or assignment.city_id != city_id
            or assignment.service_type != service.service_type
        ):
            raise ControlPlaneConflict(
                "Configuration services must reference same-city assignments of the same service type."
            )
        if service.tariff_version_id is not None:
            tariff = await session.get(PricingRule, service.tariff_version_id)
            if (
                tariff is None
                or tariff.city_id != city_id
                or tariff.operator_id != assignment.operator_id
                or tariff.service_type != service.service_type
                or tariff.booking_type != BookingType.IMMEDIATE
            ):
                raise ControlPlaneConflict(
                    "A referenced immediate tariff must match the service city, operator, and type."
                )
        if service.operator_fee_policy_version_id is not None:
            fee_policy = await session.get(
                OperatorFeePolicy,
                service.operator_fee_policy_version_id,
            )
            if (
                fee_policy is None
                or fee_policy.city_id != city_id
                or fee_policy.operator_id != assignment.operator_id
                or fee_policy.service_type != service.service_type
            ):
                raise ControlPlaneConflict(
                    "A referenced operator-fee policy must match the service city, operator, and type."
                )
        if service.scheduling_policy_version_id is not None:
            scheduling_policy = await session.get(
                SchedulingPolicy,
                service.scheduling_policy_version_id,
            )
            if (
                scheduling_policy is None
                or scheduling_policy.city_id != city_id
                or scheduling_policy.operator_id != assignment.operator_id
                or scheduling_policy.service_type != service.service_type
            ):
                raise ControlPlaneConflict(
                    "A referenced scheduling policy must match the service city, operator, and type."
                )
        if service.payment_capability_version_id is not None:
            payment_capability = await session.get(
                PaymentCapabilityVersion,
                service.payment_capability_version_id,
            )
            if (
                payment_capability is None
                or payment_capability.city_id != city_id
                or payment_capability.operator_id != assignment.operator_id
                or payment_capability.service_type != service.service_type
            ):
                raise ControlPlaneConflict(
                    "A referenced payment capability must match the service city, operator, and type."
                )


async def _replace_services(
    session: AsyncSession,
    configuration: CityConfigurationVersion,
    services: list[ConfigurationServiceInput],
) -> None:
    await _validate_draft_services(session, configuration.city_id, services)
    await session.execute(
        delete(CityConfigurationService).where(
            CityConfigurationService.configuration_version_id == configuration.id
        )
    )
    for service in services:
        session.add(
            CityConfigurationService(
                configuration_version_id=configuration.id,
                service_type=service.service_type,
                operator_city_assignment_id=service.operator_city_assignment_id,
                tariff_version_id=service.tariff_version_id,
                operator_fee_policy_version_id=service.operator_fee_policy_version_id,
                scheduling_policy_version_id=service.scheduling_policy_version_id,
                payment_capability_version_id=service.payment_capability_version_id,
                enabled=service.enabled,
            )
        )
    await session.flush()


async def _replace_routes(
    session: AsyncSession,
    configuration: CityConfigurationVersion,
    routes: list[ConfigurationRouteInput],
) -> None:
    fixed_service = await session.scalar(
        select(CityConfigurationService).where(
            CityConfigurationService.configuration_version_id == configuration.id,
            CityConfigurationService.service_type == ServiceType.FIXED_ROUTE,
            CityConfigurationService.enabled.is_(True),
        )
    )
    if routes and fixed_service is None:
        raise ControlPlaneConflict(
            "Configured fixed routes require an enabled FIXED_ROUTE city service."
        )
    assignment = (
        await session.get(
            OperatorCityAssignment,
            fixed_service.operator_city_assignment_id,
        )
        if fixed_service is not None
        else None
    )
    for route_input in routes:
        row = (
            await session.execute(
                select(FixedRouteVersion, FixedRoute)
                .join(FixedRoute, FixedRoute.id == FixedRouteVersion.fixed_route_id)
                .where(FixedRouteVersion.id == route_input.fixed_route_version_id)
            )
        ).one_or_none()
        if row is None:
            raise ControlPlaneConflict("A configured fixed-route version does not exist.")
        version, route = row
        if (
            assignment is None
            or route.city_id != configuration.city_id
            or route.operator_id != assignment.operator_id
            or route.status != FixedRouteStatus.ACTIVE
            or version.status
            not in {
                FixedRoutePublicationStatus.IN_REVIEW,
                FixedRoutePublicationStatus.PUBLISHED,
            }
        ):
            raise ControlPlaneConflict(
                "Every configured route must match the configuration city/operator and be reviewed."
            )
    await session.execute(
        delete(CityConfigurationRoute).where(
            CityConfigurationRoute.configuration_version_id == configuration.id
        )
    )
    for route_input in routes:
        session.add(
            CityConfigurationRoute(
                configuration_version_id=configuration.id,
                fixed_route_version_id=route_input.fixed_route_version_id,
                immediate_booking_enabled=route_input.immediate_booking_enabled,
                scheduled_booking_enabled=route_input.scheduled_booking_enabled,
            )
        )
    await session.flush()


@router.get(
    "/cities/{city_id}/service-area-versions",
    response_model=ServiceAreaVersionListResponse,
)
async def list_service_area_versions(
    city_id: UUID,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: OperationsPrincipal = Depends(
        require_operations_permission(OperationsPermission.VIEW_CONTROL_PLANE)
    ),
    session: AsyncSession = Depends(database_session),
) -> ServiceAreaVersionListResponse:
    await scoped_city_or_404(
        session,
        principal,
        city_id,
        OperationsPermission.VIEW_CONTROL_PLANE,
    )
    filters = [CityServiceAreaVersion.city_id == city_id]
    areas = list(
        await session.scalars(
            select(CityServiceAreaVersion)
            .where(*filters)
            .order_by(CityServiceAreaVersion.created_at.desc(), CityServiceAreaVersion.id)
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    total = await session.scalar(
        select(func.count()).select_from(CityServiceAreaVersion).where(*filters)
    )
    return ServiceAreaVersionListResponse(
        items=[await service_area_response(session, area) for area in areas],
        page=page,
        limit=limit,
        total=total or 0,
    )


@router.post(
    "/cities/{city_id}/service-area-versions",
    response_model=ServiceAreaVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_service_area_version(
    city_id: UUID,
    payload: ServiceAreaVersionCreateRequest,
    principal: OperationsPrincipal = Depends(
        require_operations_permission(OperationsPermission.MANAGE_SERVICE_AREAS)
    ),
    session: AsyncSession = Depends(database_session),
) -> ServiceAreaVersionResponse:
    try:
        async with session.begin():
            city = await scoped_city_or_404(
                session,
                principal,
                city_id,
                OperationsPermission.MANAGE_SERVICE_AREAS,
                lock=True,
            )
            if city.lifecycle_status not in {
                CityLifecycleStatus.DRAFT,
                CityLifecycleStatus.CONFIGURING,
            }:
                raise ControlPlaneConflict(
                    "Create a reviewed replacement configuration before changing an operating city boundary."
                )
            area = CityServiceAreaVersion(
                city_id=city.id,
                version=payload.version,
                boundary=await _valid_boundary(session, payload.boundary),
                status=ServiceAreaStatus.DRAFT,
                effective_from=payload.effective_from,
                effective_until=payload.effective_until,
                created_by_user_id=principal.user_id,
            )
            session.add(area)
            await session.flush()
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="SERVICE_AREA_VERSION_CREATED",
                resource_type="city_service_area_version",
                resource_id=area.id,
                market_id=city.market_id,
                city_id=city.id,
                changes={
                    "version": area.version,
                    "status": area.status.value,
                    "boundary_recorded": True,
                },
            )
            await session.flush()
            await session.refresh(area)
            response = await service_area_response(session, area)
    except ControlPlaneConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except IntegrityError as error:
        raise HTTPException(status_code=409, detail="That service-area version already exists.") from error
    return response


@router.get("/service-area-versions/{version_id}", response_model=ServiceAreaVersionResponse)
async def get_service_area_version(
    version_id: UUID,
    principal: OperationsPrincipal = Depends(
        require_operations_permission(OperationsPermission.VIEW_CONTROL_PLANE)
    ),
    session: AsyncSession = Depends(database_session),
) -> ServiceAreaVersionResponse:
    return await service_area_response(
        session,
        await _scoped_area_or_404(
            session,
            principal,
            version_id,
            OperationsPermission.VIEW_CONTROL_PLANE,
        ),
    )


@router.patch("/service-area-versions/{version_id}", response_model=ServiceAreaVersionResponse)
async def update_service_area_version(
    version_id: UUID,
    payload: ServiceAreaVersionUpdateRequest,
    principal: OperationsPrincipal = Depends(
        require_operations_permission(OperationsPermission.MANAGE_SERVICE_AREAS)
    ),
    session: AsyncSession = Depends(database_session),
) -> ServiceAreaVersionResponse:
    try:
        async with session.begin():
            area = await _scoped_area_or_404(
                session,
                principal,
                version_id,
                OperationsPermission.MANAGE_SERVICE_AREAS,
                lock=True,
            )
            require_expected_version(area.optimistic_version, payload.expected_version)
            if area.status != ServiceAreaStatus.DRAFT:
                raise ControlPlaneConflict("Only a draft service-area version can be edited.")
            if payload.boundary is not None:
                area.boundary = await _valid_boundary(session, payload.boundary)
            if payload.effective_from is not None:
                area.effective_from = payload.effective_from
            if "effective_until" in payload.model_fields_set:
                area.effective_until = payload.effective_until
            if area.effective_until is not None and area.effective_until <= area.effective_from:
                raise ControlPlaneConflict("effective_until must be after effective_from.")
            area.optimistic_version += 1
            area.updated_at = datetime.now(UTC)
            city = await session.get(City, area.city_id)
            assert city is not None
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="SERVICE_AREA_VERSION_UPDATED",
                resource_type="city_service_area_version",
                resource_id=area.id,
                market_id=city.market_id,
                city_id=area.city_id,
                changes={
                    "expected_version": payload.expected_version,
                    "current_version": area.optimistic_version,
                    "boundary_updated": payload.boundary is not None,
                },
            )
            await session.flush()
            await session.refresh(area)
            response = await service_area_response(session, area)
    except (ControlPlaneConflict, OptimisticVersionConflict) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return response


@router.post(
    "/service-area-versions/{version_id}/transitions",
    response_model=ServiceAreaVersionResponse,
)
async def transition_service_area_version(
    version_id: UUID,
    payload: ServiceAreaTransitionRequest,
    principal: OperationsPrincipal = Depends(
        require_operations_permission(OperationsPermission.MANAGE_SERVICE_AREAS)
    ),
    session: AsyncSession = Depends(database_session),
) -> ServiceAreaVersionResponse:
    transitions = {
        ServiceAreaStatus.DRAFT: ServiceAreaStatus.IN_REVIEW,
        ServiceAreaStatus.IN_REVIEW: ServiceAreaStatus.APPROVED,
    }
    try:
        async with session.begin():
            area = await _scoped_area_or_404(
                session,
                principal,
                version_id,
                OperationsPermission.MANAGE_SERVICE_AREAS,
                lock=True,
            )
            if area.status == payload.target_status:
                return await service_area_response(session, area)
            require_expected_version(area.optimistic_version, payload.expected_version)
            if transitions.get(area.status) != payload.target_status:
                raise ControlPlaneConflict(
                    "Service areas transition DRAFT to IN_REVIEW to APPROVED; activation occurs with a coherent bundle."
                )
            previous = area.status
            area.status = payload.target_status
            area.optimistic_version += 1
            area.updated_at = datetime.now(UTC)
            if area.status == ServiceAreaStatus.APPROVED:
                area.reviewed_by_user_id = principal.user_id
                area.reviewed_at = datetime.now(UTC)
            city = await session.get(City, area.city_id)
            assert city is not None
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="SERVICE_AREA_VERSION_TRANSITIONED",
                resource_type="city_service_area_version",
                resource_id=area.id,
                market_id=city.market_id,
                city_id=area.city_id,
                changes={
                    "previous_status": previous.value,
                    "current_status": area.status.value,
                    "reason": payload.reason,
                    "current_version": area.optimistic_version,
                },
            )
            await session.flush()
            await session.refresh(area)
            response = await service_area_response(session, area)
    except (ControlPlaneConflict, OptimisticVersionConflict) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return response


@router.get(
    "/cities/{city_id}/configuration-versions",
    response_model=CityConfigurationListResponse,
)
async def list_city_configurations(
    city_id: UUID,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: OperationsPrincipal = Depends(
        require_operations_permission(OperationsPermission.VIEW_CONTROL_PLANE)
    ),
    session: AsyncSession = Depends(database_session),
) -> CityConfigurationListResponse:
    await scoped_city_or_404(
        session,
        principal,
        city_id,
        OperationsPermission.VIEW_CONTROL_PLANE,
    )
    filters = [CityConfigurationVersion.city_id == city_id]
    configurations = list(
        await session.scalars(
            select(CityConfigurationVersion)
            .where(*filters)
            .order_by(CityConfigurationVersion.created_at.desc(), CityConfigurationVersion.id)
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    total = await session.scalar(
        select(func.count()).select_from(CityConfigurationVersion).where(*filters)
    )
    return CityConfigurationListResponse(
        items=[await configuration_response(session, item) for item in configurations],
        page=page,
        limit=limit,
        total=total or 0,
    )


@router.post(
    "/cities/{city_id}/configuration-versions",
    response_model=CityConfigurationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_city_configuration(
    city_id: UUID,
    payload: CityConfigurationCreateRequest,
    principal: OperationsPrincipal = Depends(
        require_operations_permission(OperationsPermission.MANAGE_CITY_CONFIGURATION)
    ),
    session: AsyncSession = Depends(database_session),
) -> CityConfigurationResponse:
    try:
        async with session.begin():
            city = await scoped_city_or_404(
                session,
                principal,
                city_id,
                OperationsPermission.MANAGE_CITY_CONFIGURATION,
                lock=True,
            )
            area = await session.get(CityServiceAreaVersion, payload.service_area_version_id)
            if area is None or area.city_id != city.id:
                raise ControlPlaneConflict("Service area must belong to the same city.")
            requirement_version = None
            if payload.driver_requirement_version_id is not None:
                requirement_version = await session.get(
                    DriverRequirementVersion,
                    payload.driver_requirement_version_id,
                )
                if requirement_version is None or requirement_version.city_id != city.id:
                    raise ControlPlaneConflict(
                        "Driver requirements must belong to the same city."
                    )
            configuration = CityConfigurationVersion(
                city_id=city.id,
                version=payload.version,
                status=ConfigurationStatus.DRAFT,
                service_area_version_id=area.id,
                driver_requirement_version_id=(
                    requirement_version.id if requirement_version is not None else None
                ),
                created_by_user_id=principal.user_id,
            )
            session.add(configuration)
            await session.flush()
            await _replace_services(session, configuration, payload.services)
            await _replace_routes(session, configuration, payload.routes)
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="CITY_CONFIGURATION_CREATED",
                resource_type="city_configuration_version",
                resource_id=configuration.id,
                market_id=city.market_id,
                city_id=city.id,
                changes={
                    "version": configuration.version,
                    "status": configuration.status.value,
                    "service_count": len(payload.services),
                    "route_count": len(payload.routes),
                    "has_driver_requirements": requirement_version is not None,
                },
            )
            await session.flush()
            await session.refresh(configuration)
            response = await configuration_response(session, configuration)
    except ControlPlaneConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except IntegrityError as error:
        raise HTTPException(status_code=409, detail="That city configuration version already exists.") from error
    return response


@router.get(
    "/city-configuration-versions/{version_id}",
    response_model=CityConfigurationResponse,
)
async def get_city_configuration(
    version_id: UUID,
    principal: OperationsPrincipal = Depends(
        require_operations_permission(OperationsPermission.VIEW_CONTROL_PLANE)
    ),
    session: AsyncSession = Depends(database_session),
) -> CityConfigurationResponse:
    return await configuration_response(
        session,
        await _scoped_configuration_or_404(
            session,
            principal,
            version_id,
            OperationsPermission.VIEW_CONTROL_PLANE,
        ),
    )


@router.patch(
    "/city-configuration-versions/{version_id}",
    response_model=CityConfigurationResponse,
)
async def update_city_configuration(
    version_id: UUID,
    payload: CityConfigurationUpdateRequest,
    principal: OperationsPrincipal = Depends(
        require_operations_permission(OperationsPermission.MANAGE_CITY_CONFIGURATION)
    ),
    session: AsyncSession = Depends(database_session),
) -> CityConfigurationResponse:
    try:
        async with session.begin():
            configuration = await _scoped_configuration_or_404(
                session,
                principal,
                version_id,
                OperationsPermission.MANAGE_CITY_CONFIGURATION,
                lock=True,
            )
            require_expected_version(configuration.optimistic_version, payload.expected_version)
            if configuration.status != ConfigurationStatus.DRAFT:
                raise ControlPlaneConflict("Only a draft configuration can be edited.")
            if payload.service_area_version_id is not None:
                area = await session.get(CityServiceAreaVersion, payload.service_area_version_id)
                if area is None or area.city_id != configuration.city_id:
                    raise ControlPlaneConflict("Service area must belong to the same city.")
                configuration.service_area_version_id = area.id
            if payload.driver_requirement_version_id is not None:
                requirement_version = await session.get(
                    DriverRequirementVersion,
                    payload.driver_requirement_version_id,
                )
                if (
                    requirement_version is None
                    or requirement_version.city_id != configuration.city_id
                ):
                    raise ControlPlaneConflict(
                        "Driver requirements must belong to the same city."
                    )
                configuration.driver_requirement_version_id = requirement_version.id
            if payload.services is not None:
                await _replace_services(session, configuration, payload.services)
            if payload.routes is not None:
                await _replace_routes(session, configuration, payload.routes)
            configuration.optimistic_version += 1
            configuration.updated_at = datetime.now(UTC)
            city = await session.get(City, configuration.city_id)
            assert city is not None
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="CITY_CONFIGURATION_UPDATED",
                resource_type="city_configuration_version",
                resource_id=configuration.id,
                market_id=city.market_id,
                city_id=city.id,
                changes={
                    "expected_version": payload.expected_version,
                    "current_version": configuration.optimistic_version,
                    "service_area_updated": payload.service_area_version_id is not None,
                    "driver_requirements_updated": payload.driver_requirement_version_id is not None,
                    "services_updated": payload.services is not None,
                    "routes_updated": payload.routes is not None,
                },
            )
            await session.flush()
            await session.refresh(configuration)
            response = await configuration_response(session, configuration)
    except (ControlPlaneConflict, OptimisticVersionConflict) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return response


async def _configuration_command(
    *,
    session: AsyncSession,
    principal: OperationsPrincipal,
    version_id: UUID,
    payload: ConfigurationCommandRequest,
    target: ConfigurationStatus,
) -> CityConfigurationVersion:
    configuration = await _scoped_configuration_or_404(
        session,
        principal,
        version_id,
        OperationsPermission.MANAGE_CITY_CONFIGURATION,
        lock=True,
    )
    city = await session.scalar(select(City).where(City.id == configuration.city_id).with_for_update())
    assert city is not None
    if configuration.status == target:
        return configuration
    require_expected_version(configuration.optimistic_version, payload.expected_version)
    transitions = {
        ConfigurationStatus.DRAFT: ConfigurationStatus.IN_REVIEW,
        ConfigurationStatus.IN_REVIEW: ConfigurationStatus.APPROVED,
        ConfigurationStatus.APPROVED: ConfigurationStatus.ACTIVE,
    }
    if transitions.get(configuration.status) != target:
        raise ControlPlaneConflict(
            f"Configuration cannot transition from {configuration.status.value} to {target.value}."
        )
    if target in {ConfigurationStatus.IN_REVIEW, ConfigurationStatus.ACTIVE}:
        await validate_configuration_components(
            session,
            configuration,
            require_live_components=target == ConfigurationStatus.ACTIVE,
        )
    if target == ConfigurationStatus.APPROVED:
        require_independent_configuration_reviewer(configuration, principal.user_id)

    previous = configuration.status
    now = datetime.now(UTC)
    configuration.status = target
    configuration.optimistic_version += 1
    configuration.updated_at = now
    if target == ConfigurationStatus.IN_REVIEW:
        configuration.submitted_by_user_id = principal.user_id
        configuration.submitted_at = now
    elif target == ConfigurationStatus.APPROVED:
        configuration.approved_by_user_id = principal.user_id
        configuration.approved_at = now
    elif target == ConfigurationStatus.ACTIVE:
        required_replacement_gates = None
        if city.lifecycle_status == CityLifecycleStatus.PILOT:
            required_replacement_gates = PILOT_ENTRY_CITY_READINESS_GATES
        elif city.lifecycle_status in {
            CityLifecycleStatus.ACTIVE,
            CityLifecycleStatus.PAUSED,
        }:
            required_replacement_gates = PUBLIC_ACTIVATION_CITY_READINESS_GATES
        if required_replacement_gates is not None:
            missing = await missing_readiness_gates(
                session,
                configuration.id,
                required_replacement_gates,
            )
            if missing:
                raise ControlPlaneConflict(
                    "An operating city cannot replace its active configuration "
                    "until the replacement readiness gates pass: " + ", ".join(missing)
                )
        previous_active = None
        if city.active_configuration_version_id is not None:
            previous_active = await session.get(
                CityConfigurationVersion,
                city.active_configuration_version_id,
            )
        if previous_active is not None and previous_active.id != configuration.id:
            previous_active.status = ConfigurationStatus.REPLACED
            old_capability_ids = set(
                await session.scalars(
                    select(CityConfigurationService.payment_capability_version_id).where(
                        CityConfigurationService.configuration_version_id == previous_active.id,
                        CityConfigurationService.payment_capability_version_id.is_not(None),
                    )
                )
            )
            new_capability_ids = set(
                await session.scalars(
                    select(CityConfigurationService.payment_capability_version_id).where(
                        CityConfigurationService.configuration_version_id == configuration.id,
                        CityConfigurationService.payment_capability_version_id.is_not(None),
                    )
                )
            )
            replaced_capability_ids = old_capability_ids - new_capability_ids
            if replaced_capability_ids:
                replaced_capabilities = list(
                    await session.scalars(
                        select(PaymentCapabilityVersion)
                        .where(
                            PaymentCapabilityVersion.id.in_(replaced_capability_ids),
                            PaymentCapabilityVersion.status == PaymentCapabilityStatus.ACTIVE,
                        )
                        .with_for_update()
                    )
                )
                for payment_capability in replaced_capabilities:
                    payment_capability.status = PaymentCapabilityStatus.REPLACED
                    payment_capability.updated_at = now
        new_area = await session.get(CityServiceAreaVersion, configuration.service_area_version_id)
        assert new_area is not None
        if previous_active is not None and previous_active.id != configuration.id:
            old_area = await session.get(
                CityServiceAreaVersion,
                previous_active.service_area_version_id,
            )
            if old_area is not None and old_area.id != new_area.id:
                old_area.status = ServiceAreaStatus.REPLACED
        new_area.status = ServiceAreaStatus.ACTIVE
        configuration.activated_by_user_id = principal.user_id
        configuration.activated_at = now
        city.active_configuration_version_id = configuration.id
        city.optimistic_version += 1
        city.updated_at = now
    await audit(
        session,
        actor_user_id=principal.user_id,
        action=f"CITY_CONFIGURATION_{target.value}",
        resource_type="city_configuration_version",
        resource_id=configuration.id,
        market_id=city.market_id,
        city_id=city.id,
        changes={
            "previous_status": previous.value,
            "current_status": target.value,
            "reason": payload.reason,
            "current_version": configuration.optimistic_version,
            "became_city_active_configuration": target == ConfigurationStatus.ACTIVE,
        },
    )
    return configuration


@router.post(
    "/city-configuration-versions/{version_id}/submit",
    response_model=CityConfigurationResponse,
)
async def submit_city_configuration(
    version_id: UUID,
    payload: ConfigurationCommandRequest,
    principal: OperationsPrincipal = Depends(
        require_operations_permission(OperationsPermission.MANAGE_CITY_CONFIGURATION)
    ),
    session: AsyncSession = Depends(database_session),
) -> CityConfigurationResponse:
    try:
        async with session.begin():
            configuration = await _configuration_command(
                session=session,
                principal=principal,
                version_id=version_id,
                payload=payload,
                target=ConfigurationStatus.IN_REVIEW,
            )
            await session.flush()
            await session.refresh(configuration)
            response = await configuration_response(session, configuration)
    except (ControlPlaneConflict, OptimisticVersionConflict) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return response


@router.post(
    "/city-configuration-versions/{version_id}/approve",
    response_model=CityConfigurationResponse,
)
async def approve_city_configuration(
    version_id: UUID,
    payload: ConfigurationCommandRequest,
    principal: OperationsPrincipal = Depends(
        require_operations_permission(OperationsPermission.MANAGE_CITY_CONFIGURATION)
    ),
    session: AsyncSession = Depends(database_session),
) -> CityConfigurationResponse:
    try:
        async with session.begin():
            configuration = await _configuration_command(
                session=session,
                principal=principal,
                version_id=version_id,
                payload=payload,
                target=ConfigurationStatus.APPROVED,
            )
            await session.flush()
            await session.refresh(configuration)
            response = await configuration_response(session, configuration)
    except (ControlPlaneConflict, OptimisticVersionConflict) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return response


@router.post(
    "/city-configuration-versions/{version_id}/activate",
    response_model=CityConfigurationResponse,
)
async def activate_city_configuration(
    version_id: UUID,
    payload: ConfigurationCommandRequest,
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(
        require_operations_permission(OperationsPermission.MANAGE_CITY_CONFIGURATION)
    ),
    session: AsyncSession = Depends(database_session),
) -> CityConfigurationResponse:
    try:
        async with session.begin():
            configuration = await _configuration_command(
                session=session,
                principal=principal,
                version_id=version_id,
                payload=payload,
                target=ConfigurationStatus.ACTIVE,
            )
            await session.flush()
            await session.refresh(configuration)
            response = await configuration_response(session, configuration)
    except (ControlPlaneConflict, OptimisticVersionConflict) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return response


@router.post(
    "/city-configuration-versions/{version_id}/readiness-decisions",
    response_model=CityConfigurationResponse,
)
async def decide_city_readiness_gate(
    version_id: UUID,
    payload: ReadinessDecisionRequest,
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(
        require_operations_permission(OperationsPermission.MANAGE_CITY_LIFECYCLE)
    ),
    session: AsyncSession = Depends(database_session),
) -> CityConfigurationResponse:
    if payload.status == ReadinessStatus.PENDING:
        raise HTTPException(status_code=422, detail="A readiness decision must be PASSED or FAILED.")
    try:
        async with session.begin():
            configuration = await _scoped_configuration_or_404(
                session,
                principal,
                version_id,
                OperationsPermission.MANAGE_CITY_LIFECYCLE,
                lock=True,
            )
            require_expected_version(
                configuration.optimistic_version,
                payload.expected_configuration_version,
            )
            if configuration.status not in {
                ConfigurationStatus.APPROVED,
                ConfigurationStatus.ACTIVE,
            }:
                raise ControlPlaneConflict(
                    "Readiness decisions require an approved or active configuration bundle."
                )
            require_independent_configuration_reviewer(configuration, principal.user_id)
            check = await session.scalar(
                select(CityReadinessCheck)
                .where(
                    CityReadinessCheck.configuration_version_id == configuration.id,
                    CityReadinessCheck.gate_code == payload.gate_code,
                )
                .with_for_update()
            )
            now = datetime.now(UTC)
            if check is None:
                check = CityReadinessCheck(
                    configuration_version_id=configuration.id,
                    gate_code=payload.gate_code,
                )
                session.add(check)
            check.status = payload.status
            check.non_secret_evidence_reference = payload.non_secret_evidence_reference
            check.decided_by_user_id = principal.user_id
            check.decided_at = now
            configuration.optimistic_version += 1
            configuration.updated_at = now
            city = await session.get(City, configuration.city_id)
            assert city is not None
            if (
                payload.status == ReadinessStatus.PASSED
                and payload.gate_code == "PILOT_SERVICE_AND_FAIRNESS"
                and not (
                    (
                        city.lifecycle_status == CityLifecycleStatus.PILOT
                        and city.active_configuration_version_id == configuration.id
                    )
                    or city.lifecycle_status
                    in {CityLifecycleStatus.ACTIVE, CityLifecycleStatus.PAUSED}
                )
            ):
                raise ControlPlaneConflict(
                    "Pilot service and fairness evidence requires a city in PILOT, ACTIVE, or PAUSED; initial launch evidence must belong to the active PILOT bundle."
                )
            if (
                payload.status == ReadinessStatus.PASSED
                and payload.gate_code == "POST_LAUNCH_REVIEW"
                and (
                    city.lifecycle_status
                    not in {CityLifecycleStatus.ACTIVE, CityLifecycleStatus.PAUSED}
                    or city.active_configuration_version_id != configuration.id
                )
            ):
                raise ControlPlaneConflict(
                    "Post-launch review evidence can pass only on the active configuration after a city has reached ACTIVE."
                )
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="CITY_READINESS_DECIDED",
                resource_type="city_readiness_check",
                resource_id=check.id,
                market_id=city.market_id,
                city_id=city.id,
                changes={
                    "gate_code": check.gate_code,
                    "status": check.status.value,
                    "evidence_reference_recorded": True,
                    "configuration_version": configuration.optimistic_version,
                },
            )
            await session.flush()
            await session.refresh(configuration)
            response = await configuration_response(session, configuration)
    except (ControlPlaneConflict, OptimisticVersionConflict) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return response
