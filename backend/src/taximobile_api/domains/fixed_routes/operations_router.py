"""Scoped operations lifecycle for fixed-route identities and versions."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select, text
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
from taximobile_api.domains.fixed_routes.models import (
    FixedRoute,
    FixedRoutePublicationStatus,
    FixedRouteStatus,
    FixedRouteVersion,
)
from taximobile_api.domains.fixed_routes.schemas import (
    FixedRouteCommandRequest,
    FixedRouteCreateRequest,
    FixedRouteFareOptionListResponse,
    FixedRouteFareOptionResponse,
    FixedRouteListResponse,
    FixedRouteResponse,
    FixedRouteRetireRequest,
    FixedRouteUpdateRequest,
    FixedRouteVersionCreateRequest,
    FixedRouteVersionResponse,
    FixedRouteVersionUpdateRequest,
)
from taximobile_api.domains.fixed_routes.service import (
    FixedRouteConflict,
    replace_directions,
    route_response,
    route_version_response,
    validate_publication_scope,
    validate_route_structure,
)
from taximobile_api.domains.markets.models import (
    AssignmentStatus,
    City,
    Operator,
    OperatorCityAssignment,
    ServiceType,
)
from taximobile_api.domains.pricing.models import (
    BookingType,
    PricingModel,
    PricingRule,
    PricingRuleStatus,
)


router = APIRouter(prefix="/operations", tags=["operations-fixed-routes"])
PERMISSION = OperationsPermission.MANAGE_FIXED_ROUTES


def _scope_allowed(
    principal: OperationsPrincipal,
    *,
    city_id: UUID,
    operator_id: UUID,
) -> bool:
    return any(
        grant.allows(PERMISSION, city_id=city_id)
        and grant.allows(PERMISSION, operator_id=operator_id)
        for grant in principal.grants
    )


def _conflict(error: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


def _expected(actual: int, expected: int) -> None:
    if actual != expected:
        raise FixedRouteConflict(
            f"The resource changed; expected version {expected}, current version {actual}."
        )


async def _advisory_lock(session: AsyncSession, scope: str) -> None:
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))"),
        {"scope": scope},
    )


async def _scope_context(
    session: AsyncSession,
    principal: OperationsPrincipal,
    *,
    city_id: UUID,
    operator_id: UUID,
) -> City:
    if not _scope_allowed(principal, city_id=city_id, operator_id=operator_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route scope not found.")
    city = await session.get(City, city_id)
    operator = await session.get(Operator, operator_id)
    if city is None or operator is None or operator.market_id != city.market_id:
        raise FixedRouteConflict("The route city and operator must share a market.")
    assignment = await session.scalar(
        select(OperatorCityAssignment.id)
        .where(
            OperatorCityAssignment.city_id == city_id,
            OperatorCityAssignment.operator_id == operator_id,
            OperatorCityAssignment.service_type == ServiceType.FIXED_ROUTE,
            OperatorCityAssignment.status == AssignmentStatus.ACTIVE,
        )
        .limit(1)
    )
    if assignment is None:
        raise FixedRouteConflict(
            "The operator needs an active fixed-route assignment before route drafting."
        )
    return city


async def _route_or_404(
    session: AsyncSession,
    principal: OperationsPrincipal,
    route_id: UUID,
    *,
    lock: bool = False,
) -> FixedRoute:
    statement = select(FixedRoute).where(
        FixedRoute.id == route_id,
        FixedRoute.city_id.in_(principal.city_ids_for(PERMISSION)),
        FixedRoute.operator_id.in_(principal.operator_ids_for(PERMISSION)),
    )
    if lock:
        statement = statement.with_for_update()
    route = await session.scalar(statement)
    if route is None or not _scope_allowed(
        principal, city_id=route.city_id, operator_id=route.operator_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fixed route not found.")
    return route


async def _version_or_404(
    session: AsyncSession,
    principal: OperationsPrincipal,
    version_id: UUID,
    *,
    lock: bool = False,
) -> tuple[FixedRouteVersion, FixedRoute]:
    statement = (
        select(FixedRouteVersion, FixedRoute)
        .join(FixedRoute, FixedRoute.id == FixedRouteVersion.fixed_route_id)
        .where(
            FixedRouteVersion.id == version_id,
            FixedRoute.city_id.in_(principal.city_ids_for(PERMISSION)),
            FixedRoute.operator_id.in_(principal.operator_ids_for(PERMISSION)),
        )
    )
    if lock:
        statement = statement.with_for_update(of=FixedRouteVersion)
    row = (await session.execute(statement)).one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fixed-route version not found.",
        )
    version, route = row
    if not _scope_allowed(principal, city_id=route.city_id, operator_id=route.operator_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fixed-route version not found.",
        )
    return version, route


@router.get("/cities/{city_id}/fixed-routes", response_model=FixedRouteListResponse)
async def list_fixed_routes(
    city_id: UUID,
    operator_id: UUID = Query(),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    route_status: FixedRouteStatus | None = Query(default=None, alias="status"),
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> FixedRouteListResponse:
    await _scope_context(
        session, principal, city_id=city_id, operator_id=operator_id
    )
    filters = [FixedRoute.city_id == city_id, FixedRoute.operator_id == operator_id]
    if route_status is not None:
        filters.append(FixedRoute.status == route_status)
    total = await session.scalar(select(func.count(FixedRoute.id)).where(*filters)) or 0
    routes = list(
        await session.scalars(
            select(FixedRoute)
            .where(*filters)
            .order_by(FixedRoute.code, FixedRoute.id)
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    return FixedRouteListResponse(
        items=[
            await route_response(session, route, include_audit=True)
            for route in routes
        ],
        page=page,
        limit=limit,
        total=total,
    )


@router.get(
    "/cities/{city_id}/fixed-route-fare-options",
    response_model=FixedRouteFareOptionListResponse,
)
async def list_fixed_route_fare_options(
    city_id: UUID,
    operator_id: UUID = Query(),
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> FixedRouteFareOptionListResponse:
    """Expose only unbound draft/review fare metadata needed by a route editor.

    Route managers can link a separately owned fare version without receiving
    pricing mutation authority or financial-policy audit fields. Active fares
    are already bound one-to-one and cannot be reassigned to another direction.
    """

    await _scope_context(
        session,
        principal,
        city_id=city_id,
        operator_id=operator_id,
    )
    rules = list(
        await session.scalars(
            select(PricingRule)
            .where(
                PricingRule.city_id == city_id,
                PricingRule.operator_id == operator_id,
                PricingRule.service_type == ServiceType.FIXED_ROUTE,
                PricingRule.booking_type == BookingType.IMMEDIATE,
                PricingRule.model == PricingModel.FIXED,
                PricingRule.status.in_(
                    [PricingRuleStatus.DRAFT, PricingRuleStatus.IN_REVIEW]
                ),
                PricingRule.fixed_route_direction_id.is_(None),
                PricingRule.fixed_amount.is_not(None),
            )
            .order_by(PricingRule.effective_from.desc(), PricingRule.version)
            .limit(100)
        )
    )
    return FixedRouteFareOptionListResponse(
        items=[
            FixedRouteFareOptionResponse(
                id=rule.id,
                version=rule.version,
                name=rule.name,
                status=rule.status.value,
                fixed_amount=f"{rule.fixed_amount:.2f}",
                currency=rule.currency,
                effective_from=rule.effective_from,
                effective_until=rule.effective_until,
            )
            for rule in rules
            if rule.fixed_amount is not None
        ]
    )


@router.post(
    "/cities/{city_id}/fixed-routes",
    response_model=FixedRouteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_fixed_route(
    city_id: UUID,
    payload: FixedRouteCreateRequest,
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> FixedRouteResponse:
    try:
        async with session.begin():
            city = await _scope_context(
                session,
                principal,
                city_id=city_id,
                operator_id=payload.operator_id,
            )
            await _advisory_lock(
                session, f"fixed-route-code:{city_id}:{payload.operator_id}"
            )
            route = FixedRoute(
                city_id=city_id,
                operator_id=payload.operator_id,
                code=payload.code,
                status=FixedRouteStatus.ACTIVE,
                created_by_user_id=principal.user_id,
            )
            session.add(route)
            await session.flush()
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="FIXED_ROUTE_CREATED",
                resource_type="fixed_route",
                resource_id=route.id,
                market_id=city.market_id,
                city_id=city.id,
                operator_id=route.operator_id,
                changes={"code": route.code, "status": route.status.value},
            )
            await session.refresh(route)
            return await route_response(session, route, include_audit=True)
    except IntegrityError as error:
        raise _conflict(FixedRouteConflict("The fixed-route code already exists in this scope.")) from error
    except FixedRouteConflict as error:
        raise _conflict(error) from error


@router.get("/fixed-routes/{route_id}", response_model=FixedRouteResponse)
async def get_fixed_route(
    route_id: UUID,
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> FixedRouteResponse:
    route = await _route_or_404(session, principal, route_id)
    return await route_response(session, route, include_audit=True)


@router.patch("/fixed-routes/{route_id}", response_model=FixedRouteResponse)
async def update_fixed_route(
    route_id: UUID,
    payload: FixedRouteUpdateRequest,
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> FixedRouteResponse:
    try:
        async with session.begin():
            route = await _route_or_404(session, principal, route_id, lock=True)
            published = await session.scalar(
                select(FixedRouteVersion.id).where(
                    FixedRouteVersion.fixed_route_id == route.id,
                    FixedRouteVersion.status.in_(
                        [
                            FixedRoutePublicationStatus.PUBLISHED,
                            FixedRoutePublicationStatus.RETIRED,
                        ]
                    ),
                ).limit(1)
            )
            if published is not None:
                raise FixedRouteConflict(
                    "A route code cannot change after any version has been published."
                )
            previous = route.code
            route.code = payload.code
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="FIXED_ROUTE_UPDATED",
                resource_type="fixed_route",
                resource_id=route.id,
                city_id=route.city_id,
                operator_id=route.operator_id,
                changes={"code": {"from": previous, "to": route.code}, "reason": payload.reason},
            )
            await session.flush()
            await session.refresh(route)
            return await route_response(session, route, include_audit=True)
    except IntegrityError as error:
        raise _conflict(FixedRouteConflict("The fixed-route code already exists in this scope.")) from error
    except FixedRouteConflict as error:
        raise _conflict(error) from error


@router.post("/fixed-routes/{route_id}/retire", response_model=FixedRouteResponse)
async def retire_fixed_route(
    route_id: UUID,
    payload: FixedRouteRetireRequest,
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> FixedRouteResponse:
    async with session.begin():
        route = await _route_or_404(session, principal, route_id, lock=True)
        if route.status != FixedRouteStatus.RETIRED:
            now = datetime.now(UTC)
            route.status = FixedRouteStatus.RETIRED
            route.retired_by_user_id = principal.user_id
            route.retired_at = now
            versions = list(
                await session.scalars(
                    select(FixedRouteVersion)
                    .where(
                        FixedRouteVersion.fixed_route_id == route.id,
                        FixedRouteVersion.status != FixedRoutePublicationStatus.RETIRED,
                    )
                    .with_for_update()
                )
            )
            for version in versions:
                version.status = FixedRoutePublicationStatus.RETIRED
                version.retired_by_user_id = principal.user_id
                version.retired_at = now
                if (
                    version.effective_from < now
                    and (version.effective_until is None or version.effective_until > now)
                ):
                    version.effective_until = now
                version.optimistic_version += 1
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="FIXED_ROUTE_RETIRED",
                resource_type="fixed_route",
                resource_id=route.id,
                city_id=route.city_id,
                operator_id=route.operator_id,
                changes={"reason": payload.reason, "status": route.status.value},
            )
            await session.flush()
        await session.refresh(route)
        return await route_response(session, route, include_audit=True)


@router.post(
    "/fixed-routes/{route_id}/versions",
    response_model=FixedRouteVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_fixed_route_version(
    route_id: UUID,
    payload: FixedRouteVersionCreateRequest,
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> FixedRouteVersionResponse:
    try:
        async with session.begin():
            route = await _route_or_404(session, principal, route_id, lock=True)
            if route.status != FixedRouteStatus.ACTIVE:
                raise FixedRouteConflict("A retired route cannot receive a new version.")
            await _advisory_lock(session, f"fixed-route-version:{route.id}")
            version = FixedRouteVersion(
                fixed_route_id=route.id,
                version=payload.version,
                localized_name=payload.localized_name.model_dump(),
                localized_description=(
                    payload.localized_description.model_dump()
                    if payload.localized_description is not None
                    else {}
                ),
                status=FixedRoutePublicationStatus.DRAFT,
                effective_from=payload.effective_from,
                effective_until=payload.effective_until,
                created_by_user_id=principal.user_id,
            )
            session.add(version)
            await session.flush()
            await replace_directions(session, version, payload.directions)
            await validate_route_structure(
                session,
                version,
                require_active_fares=False,
                allow_unpriced_directions=True,
            )
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="FIXED_ROUTE_VERSION_CREATED",
                resource_type="fixed_route_version",
                resource_id=version.id,
                city_id=route.city_id,
                operator_id=route.operator_id,
                changes={
                    "version": version.version,
                    "status": version.status.value,
                    "direction_count": len(payload.directions),
                },
            )
            await session.refresh(version)
            return await route_version_response(session, version, include_audit=True)
    except IntegrityError as error:
        raise _conflict(FixedRouteConflict("The route version or direction is duplicated.")) from error
    except FixedRouteConflict as error:
        raise _conflict(error) from error


@router.get(
    "/fixed-route-versions/{version_id}",
    response_model=FixedRouteVersionResponse,
)
async def get_fixed_route_version(
    version_id: UUID,
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> FixedRouteVersionResponse:
    version, _ = await _version_or_404(session, principal, version_id)
    return await route_version_response(session, version, include_audit=True)


@router.patch(
    "/fixed-route-versions/{version_id}",
    response_model=FixedRouteVersionResponse,
)
async def update_fixed_route_version(
    version_id: UUID,
    payload: FixedRouteVersionUpdateRequest,
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> FixedRouteVersionResponse:
    try:
        async with session.begin():
            version, route = await _version_or_404(
                session, principal, version_id, lock=True
            )
            _expected(version.optimistic_version, payload.expected_version)
            if version.status != FixedRoutePublicationStatus.DRAFT:
                raise FixedRouteConflict("Only a draft route version can be edited.")
            if payload.localized_name is not None:
                version.localized_name = payload.localized_name.model_dump()
            if payload.localized_description is not None:
                version.localized_description = payload.localized_description.model_dump()
            elif payload.clear_localized_description:
                version.localized_description = {}
            if payload.effective_from is not None:
                version.effective_from = payload.effective_from
            if payload.effective_until is not None:
                version.effective_until = payload.effective_until
            elif payload.clear_effective_until:
                version.effective_until = None
            if (
                version.effective_until is not None
                and version.effective_until <= version.effective_from
            ):
                raise FixedRouteConflict("effective_until must be after effective_from.")
            if payload.directions is not None:
                await replace_directions(session, version, payload.directions)
            await validate_route_structure(
                session,
                version,
                require_active_fares=False,
                allow_unpriced_directions=True,
            )
            version.optimistic_version += 1
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="FIXED_ROUTE_VERSION_UPDATED",
                resource_type="fixed_route_version",
                resource_id=version.id,
                city_id=route.city_id,
                operator_id=route.operator_id,
                changes={
                    "optimistic_version": version.optimistic_version,
                    "fields": sorted(payload.model_fields_set - {"expected_version"}),
                },
            )
            await session.flush()
            await session.refresh(version)
            return await route_version_response(session, version, include_audit=True)
    except IntegrityError as error:
        raise _conflict(FixedRouteConflict("The route version update conflicts with existing content.")) from error
    except FixedRouteConflict as error:
        raise _conflict(error) from error


@router.post(
    "/fixed-route-versions/{version_id}/submit",
    response_model=FixedRouteVersionResponse,
)
async def submit_fixed_route_version(
    version_id: UUID,
    payload: FixedRouteCommandRequest,
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> FixedRouteVersionResponse:
    try:
        async with session.begin():
            version, route = await _version_or_404(
                session, principal, version_id, lock=True
            )
            _expected(version.optimistic_version, payload.expected_version)
            if version.status != FixedRoutePublicationStatus.DRAFT:
                raise FixedRouteConflict("Only a draft route version can be submitted.")
            await validate_route_structure(session, version, require_active_fares=False)
            version.status = FixedRoutePublicationStatus.IN_REVIEW
            version.submitted_by_user_id = principal.user_id
            version.submitted_at = datetime.now(UTC)
            version.optimistic_version += 1
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="FIXED_ROUTE_VERSION_SUBMITTED",
                resource_type="fixed_route_version",
                resource_id=version.id,
                city_id=route.city_id,
                operator_id=route.operator_id,
                changes={"reason": payload.reason, "status": version.status.value},
            )
            await session.flush()
            await session.refresh(version)
            return await route_version_response(session, version, include_audit=True)
    except FixedRouteConflict as error:
        raise _conflict(error) from error


@router.post(
    "/fixed-route-versions/{version_id}/publish",
    response_model=FixedRouteVersionResponse,
)
async def publish_fixed_route_version(
    version_id: UUID,
    payload: FixedRouteCommandRequest,
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> FixedRouteVersionResponse:
    try:
        async with session.begin():
            version, route = await _version_or_404(
                session, principal, version_id, lock=True
            )
            _expected(version.optimistic_version, payload.expected_version)
            if version.status != FixedRoutePublicationStatus.IN_REVIEW:
                raise FixedRouteConflict("Only an in-review route version can be published.")
            await _advisory_lock(session, f"fixed-route-publication:{route.id}")
            await validate_publication_scope(session, version)
            overlapping = list(
                await session.scalars(
                    select(FixedRouteVersion)
                    .where(
                        FixedRouteVersion.fixed_route_id == route.id,
                        FixedRouteVersion.id != version.id,
                        FixedRouteVersion.status == FixedRoutePublicationStatus.PUBLISHED,
                        FixedRouteVersion.effective_from < (
                            version.effective_until
                            if version.effective_until is not None
                            else datetime.max.replace(tzinfo=UTC)
                        ),
                        or_(
                            FixedRouteVersion.effective_until.is_(None),
                            FixedRouteVersion.effective_until > version.effective_from,
                        ),
                    )
                    .with_for_update()
                )
            )
            for previous in overlapping:
                if previous.effective_from >= version.effective_from:
                    raise FixedRouteConflict(
                        "A published same-route version begins at or after this version's effective time."
                    )
                previous.effective_until = version.effective_from
                previous.optimistic_version += 1
            now = datetime.now(UTC)
            version.status = FixedRoutePublicationStatus.PUBLISHED
            version.published_by_user_id = principal.user_id
            version.published_at = now
            version.optimistic_version += 1
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="FIXED_ROUTE_VERSION_PUBLISHED",
                resource_type="fixed_route_version",
                resource_id=version.id,
                city_id=route.city_id,
                operator_id=route.operator_id,
                changes={
                    "reason": payload.reason,
                    "status": version.status.value,
                    "replaced_version_ids": [str(item.id) for item in overlapping],
                },
            )
            await session.flush()
            await session.refresh(version)
            return await route_version_response(session, version, include_audit=True)
    except IntegrityError as error:
        raise _conflict(FixedRouteConflict("The publication overlaps an existing route version.")) from error
    except FixedRouteConflict as error:
        raise _conflict(error) from error


@router.post(
    "/fixed-route-versions/{version_id}/retire",
    response_model=FixedRouteVersionResponse,
)
async def retire_fixed_route_version(
    version_id: UUID,
    payload: FixedRouteCommandRequest,
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> FixedRouteVersionResponse:
    try:
        async with session.begin():
            version, route = await _version_or_404(
                session, principal, version_id, lock=True
            )
            _expected(version.optimistic_version, payload.expected_version)
            if version.status == FixedRoutePublicationStatus.RETIRED:
                return await route_version_response(session, version, include_audit=True)
            if version.status not in {
                FixedRoutePublicationStatus.IN_REVIEW,
                FixedRoutePublicationStatus.PUBLISHED,
            }:
                raise FixedRouteConflict("Only an in-review or published version can be retired.")
            now = datetime.now(UTC)
            version.status = FixedRoutePublicationStatus.RETIRED
            version.retired_by_user_id = principal.user_id
            version.retired_at = now
            if (
                version.effective_from < now
                and (version.effective_until is None or version.effective_until > now)
            ):
                version.effective_until = now
            version.optimistic_version += 1
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="FIXED_ROUTE_VERSION_RETIRED",
                resource_type="fixed_route_version",
                resource_id=version.id,
                city_id=route.city_id,
                operator_id=route.operator_id,
                changes={"reason": payload.reason, "status": version.status.value},
            )
            await session.flush()
            await session.refresh(version)
            return await route_version_response(session, version, include_audit=True)
    except FixedRouteConflict as error:
        raise _conflict(error) from error
