"""Scoped market, operator, city, assignment, and rollout endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2 import Geometry
from geoalchemy2.elements import WKTElement
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
from taximobile_api.domains.cooperatives.models import Cooperative
from taximobile_api.domains.markets.constants import (
    PILOT_ENTRY_CITY_READINESS_GATES,
    PUBLIC_ACTIVATION_CITY_READINESS_GATES,
)
from taximobile_api.domains.markets.models import (
    AssignmentStatus,
    City,
    CityConfigurationVersion,
    CityLifecycleStatus,
    CityReadinessCheck,
    Market,
    Operator,
    OperatorCityAssignment,
    OperatorStatus,
    OperatorType,
    ReadinessStatus,
)
from taximobile_api.domains.markets.schemas import (
    CityCreateRequest,
    CityLifecycleTransitionRequest,
    CityListResponse,
    CityResponse,
    CityUpdateRequest,
    Coordinate,
    LocalizedName,
    MarketListResponse,
    MarketResponse,
    OperatorCityAssignmentCreateRequest,
    OperatorCityAssignmentListResponse,
    OperatorCityAssignmentResponse,
    OperatorCityAssignmentRetireRequest,
    OperatorCreateRequest,
    OperatorListResponse,
    OperatorResponse,
    OperatorUpdateRequest,
    RolloutCitySummary,
    RolloutOverviewResponse,
)
from taximobile_api.domains.markets.service import (
    ControlPlaneConflict,
    OptimisticVersionConflict,
    ensure_assignment_does_not_overlap,
    missing_readiness_gates,
    require_expected_version,
    same_market_operator_and_city,
    validate_city_lifecycle_transition,
)


router = APIRouter(prefix="/operations", tags=["operations-control-plane"])


VIEW = OperationsPermission.VIEW_CONTROL_PLANE


def _forbidden() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="The resource is outside the granted operations scope.",
    )


def _city_scope_condition(principal: OperationsPrincipal, permission: OperationsPermission):
    city_ids = principal.city_ids_for(permission)
    if not city_ids:
        return City.id.in_([])
    return City.id.in_(city_ids)


def _operator_scope_condition(principal: OperationsPrincipal, permission: OperationsPermission):
    operator_ids = principal.operator_ids_for(permission)
    if not operator_ids:
        return Operator.id.in_([])
    return Operator.id.in_(operator_ids)


def market_response(market: Market) -> MarketResponse:
    return MarketResponse(
        id=market.id,
        code=market.code,
        name=market.name,
        default_currency=market.default_currency,
        status=market.status.value,
    )


def operator_response(operator: Operator) -> OperatorResponse:
    return OperatorResponse(
        id=operator.id,
        market_id=operator.market_id,
        cooperative_id=operator.cooperative_id,
        name=operator.name,
        operator_type=operator.operator_type.value,
        status=operator.status.value,
        created_at=operator.created_at,
        updated_at=operator.updated_at,
    )


def assignment_response(assignment: OperatorCityAssignment) -> OperatorCityAssignmentResponse:
    return OperatorCityAssignmentResponse(
        id=assignment.id,
        operator_id=assignment.operator_id,
        city_id=assignment.city_id,
        service_type=assignment.service_type.value,
        effective_from=assignment.effective_from,
        effective_until=assignment.effective_until,
        status=assignment.status.value,
        created_at=assignment.created_at,
        retired_at=assignment.retired_at,
    )


async def city_response(session: AsyncSession, city: City) -> CityResponse:
    latitude, longitude = (
        await session.execute(
            select(
                func.ST_Y(
                    City.presentation_centroid.cast(Geometry(geometry_type="POINT", srid=4326))
                ),
                func.ST_X(
                    City.presentation_centroid.cast(Geometry(geometry_type="POINT", srid=4326))
                ),
            ).where(City.id == city.id)
        )
    ).one()
    return CityResponse(
        id=city.id,
        market_id=city.market_id,
        code=city.code,
        localized_name=LocalizedName.model_validate(city.localized_name),
        timezone=city.timezone,
        presentation_centroid=Coordinate(latitude=latitude, longitude=longitude),
        lifecycle_status=city.lifecycle_status.value,
        active_configuration_version_id=city.active_configuration_version_id,
        optimistic_version=city.optimistic_version,
        is_legacy_compatibility=city.is_legacy_compatibility,
        created_at=city.created_at,
        updated_at=city.updated_at,
    )


async def scoped_city_or_404(
    session: AsyncSession,
    principal: OperationsPrincipal,
    city_id: UUID,
    permission: OperationsPermission,
    *,
    lock: bool = False,
) -> City:
    statement = select(City).where(
        City.id == city_id,
        _city_scope_condition(principal, permission),
    )
    if lock:
        statement = statement.with_for_update()
    city = await session.scalar(statement)
    if city is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="City not found.")
    return city


async def scoped_operator_or_404(
    session: AsyncSession,
    principal: OperationsPrincipal,
    operator_id: UUID,
    permission: OperationsPermission,
    *,
    lock: bool = False,
) -> Operator:
    statement = select(Operator).where(
        Operator.id == operator_id,
        _operator_scope_condition(principal, permission),
    )
    if lock:
        statement = statement.with_for_update()
    operator = await session.scalar(statement)
    if operator is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator not found.")
    return operator


async def _require_database_timezone(session: AsyncSession, timezone: str) -> None:
    exists = await session.scalar(
        text("SELECT EXISTS (SELECT 1 FROM pg_timezone_names WHERE name = :timezone)"),
        {"timezone": timezone},
    )
    if not exists:
        raise HTTPException(status_code=422, detail="Timezone is not a known IANA timezone.")


@router.get("/markets", response_model=MarketListResponse)
async def list_markets(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: OperationsPrincipal = Depends(require_operations_permission(VIEW)),
    session: AsyncSession = Depends(database_session),
) -> MarketListResponse:
    market_ids = principal.market_ids_for(VIEW)
    filters = [Market.id.in_(market_ids)]
    items = list(
        await session.scalars(
            select(Market)
            .where(*filters)
            .order_by(Market.code, Market.id)
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    total = await session.scalar(select(func.count()).select_from(Market).where(*filters))
    return MarketListResponse(
        items=[market_response(item) for item in items],
        page=page,
        limit=limit,
        total=total or 0,
    )


@router.get("/cities", response_model=CityListResponse)
async def list_cities(
    market_id: UUID | None = Query(default=None),
    lifecycle_status: CityLifecycleStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: OperationsPrincipal = Depends(require_operations_permission(VIEW)),
    session: AsyncSession = Depends(database_session),
) -> CityListResponse:
    filters = [_city_scope_condition(principal, VIEW)]
    if market_id is not None:
        filters.append(City.market_id == market_id)
    if lifecycle_status is not None:
        filters.append(City.lifecycle_status == lifecycle_status)
    items = list(
        await session.scalars(
            select(City)
            .where(*filters)
            .order_by(City.code, City.id)
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    total = await session.scalar(select(func.count()).select_from(City).where(*filters))
    return CityListResponse(
        items=[await city_response(session, item) for item in items],
        page=page,
        limit=limit,
        total=total or 0,
    )


@router.post("/cities", response_model=CityResponse, status_code=status.HTTP_201_CREATED)
async def create_city(
    payload: CityCreateRequest,
    principal: OperationsPrincipal = Depends(
        require_operations_permission(OperationsPermission.MANAGE_CITY_LIFECYCLE)
    ),
    session: AsyncSession = Depends(database_session),
) -> CityResponse:
    if not principal.allows(
        OperationsPermission.MANAGE_CITY_LIFECYCLE,
        market_id=payload.market_id,
    ):
        raise _forbidden()
    city = City(
        market_id=payload.market_id,
        code=payload.code,
        localized_name=payload.localized_name.model_dump(),
        timezone=payload.timezone,
        presentation_centroid=WKTElement(
            f"POINT({payload.presentation_centroid.longitude} {payload.presentation_centroid.latitude})",
            srid=4326,
        ),
        lifecycle_status=CityLifecycleStatus.DRAFT,
    )
    try:
        async with session.begin():
            await _require_database_timezone(session, payload.timezone)
            if await session.get(Market, payload.market_id) is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found.")
            session.add(city)
            await session.flush()
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="CITY_CREATED",
                resource_type="city",
                resource_id=city.id,
                market_id=city.market_id,
                city_id=city.id,
                changes={"code": city.code, "lifecycle_status": city.lifecycle_status.value},
            )
    except IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A city with that code already exists in the market.",
        ) from error
    return await city_response(session, city)


@router.get("/cities/{city_id}", response_model=CityResponse)
async def get_city(
    city_id: UUID,
    principal: OperationsPrincipal = Depends(require_operations_permission(VIEW)),
    session: AsyncSession = Depends(database_session),
) -> CityResponse:
    return await city_response(session, await scoped_city_or_404(session, principal, city_id, VIEW))


@router.patch("/cities/{city_id}", response_model=CityResponse)
async def update_city(
    city_id: UUID,
    payload: CityUpdateRequest,
    principal: OperationsPrincipal = Depends(
        require_operations_permission(OperationsPermission.MANAGE_CITY_LIFECYCLE)
    ),
    session: AsyncSession = Depends(database_session),
) -> CityResponse:
    try:
        async with session.begin():
            city = await scoped_city_or_404(
                session,
                principal,
                city_id,
                OperationsPermission.MANAGE_CITY_LIFECYCLE,
                lock=True,
            )
            require_expected_version(city.optimistic_version, payload.expected_version)
            if city.lifecycle_status not in {
                CityLifecycleStatus.DRAFT,
                CityLifecycleStatus.CONFIGURING,
            }:
                raise ControlPlaneConflict(
                    "Active lifecycle city metadata changes require a new reviewed configuration."
                )
            changes: dict[str, object] = {"expected_version": payload.expected_version}
            if payload.localized_name is not None:
                city.localized_name = payload.localized_name.model_dump()
                changes["localized_name_updated"] = True
            if payload.timezone is not None:
                await _require_database_timezone(session, payload.timezone)
                city.timezone = payload.timezone
                changes["timezone"] = city.timezone
            if payload.presentation_centroid is not None:
                city.presentation_centroid = WKTElement(
                    f"POINT({payload.presentation_centroid.longitude} {payload.presentation_centroid.latitude})",
                    srid=4326,
                )
                changes["presentation_centroid_updated"] = True
            city.optimistic_version += 1
            city.updated_at = datetime.now(UTC)
            changes["current_version"] = city.optimistic_version
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="CITY_UPDATED",
                resource_type="city",
                resource_id=city.id,
                market_id=city.market_id,
                city_id=city.id,
                changes=changes,
            )
    except OptimisticVersionConflict as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ControlPlaneConflict as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return await city_response(session, city)


@router.post("/cities/{city_id}/lifecycle-transitions", response_model=CityResponse)
async def transition_city_lifecycle(
    city_id: UUID,
    payload: CityLifecycleTransitionRequest,
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(
        require_operations_permission(OperationsPermission.MANAGE_CITY_LIFECYCLE)
    ),
    session: AsyncSession = Depends(database_session),
) -> CityResponse:
    try:
        async with session.begin():
            city = await scoped_city_or_404(
                session,
                principal,
                city_id,
                OperationsPermission.MANAGE_CITY_LIFECYCLE,
                lock=True,
            )
            require_expected_version(city.optimistic_version, payload.expected_version)
            previous = city.lifecycle_status
            await validate_city_lifecycle_transition(session, city, payload.target_status)
            city.lifecycle_status = payload.target_status
            city.optimistic_version += 1
            city.updated_at = datetime.now(UTC)
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="CITY_LIFECYCLE_TRANSITIONED",
                resource_type="city",
                resource_id=city.id,
                market_id=city.market_id,
                city_id=city.id,
                changes={
                    "previous_status": previous.value,
                    "current_status": city.lifecycle_status.value,
                    "reason": payload.reason,
                    "expected_version": payload.expected_version,
                    "current_version": city.optimistic_version,
                },
            )
    except (ControlPlaneConflict, OptimisticVersionConflict) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return await city_response(session, city)


@router.get("/operators", response_model=OperatorListResponse)
async def list_operators(
    market_id: UUID | None = Query(default=None),
    operator_status: OperatorStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: OperationsPrincipal = Depends(require_operations_permission(VIEW)),
    session: AsyncSession = Depends(database_session),
) -> OperatorListResponse:
    filters = [_operator_scope_condition(principal, VIEW)]
    if market_id is not None:
        filters.append(Operator.market_id == market_id)
    if operator_status is not None:
        filters.append(Operator.status == operator_status)
    items = list(
        await session.scalars(
            select(Operator)
            .where(*filters)
            .order_by(Operator.name, Operator.id)
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    total = await session.scalar(select(func.count()).select_from(Operator).where(*filters))
    return OperatorListResponse(
        items=[operator_response(item) for item in items],
        page=page,
        limit=limit,
        total=total or 0,
    )


@router.post("/operators", response_model=OperatorResponse, status_code=status.HTTP_201_CREATED)
async def create_operator(
    payload: OperatorCreateRequest,
    principal: OperationsPrincipal = Depends(
        require_operations_permission(OperationsPermission.MANAGE_OPERATORS)
    ),
    session: AsyncSession = Depends(database_session),
) -> OperatorResponse:
    if not principal.allows(OperationsPermission.MANAGE_OPERATORS, market_id=payload.market_id):
        raise _forbidden()
    if (payload.operator_type == OperatorType.COOPERATIVE) != (payload.cooperative_id is not None):
        raise HTTPException(
            status_code=422,
            detail="A cooperative operator must reference one cooperative, and other operator types must not.",
        )
    operator = Operator(
        market_id=payload.market_id,
        cooperative_id=payload.cooperative_id,
        name=payload.name,
        operator_type=payload.operator_type,
        status=OperatorStatus.DRAFT,
    )
    try:
        async with session.begin():
            if await session.get(Market, payload.market_id) is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found.")
            if payload.cooperative_id is not None and await session.get(Cooperative, payload.cooperative_id) is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cooperative not found.")
            session.add(operator)
            await session.flush()
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="OPERATOR_CREATED",
                resource_type="operator",
                resource_id=operator.id,
                market_id=operator.market_id,
                operator_id=operator.id,
                changes={
                    "operator_type": operator.operator_type.value,
                    "status": operator.status.value,
                    "cooperative_linked": operator.cooperative_id is not None,
                },
            )
    except IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That cooperative is already linked to an operator.",
        ) from error
    return operator_response(operator)


@router.get("/operators/{operator_id}", response_model=OperatorResponse)
async def get_operator(
    operator_id: UUID,
    principal: OperationsPrincipal = Depends(require_operations_permission(VIEW)),
    session: AsyncSession = Depends(database_session),
) -> OperatorResponse:
    return operator_response(
        await scoped_operator_or_404(session, principal, operator_id, VIEW)
    )


@router.patch("/operators/{operator_id}", response_model=OperatorResponse)
async def update_operator(
    operator_id: UUID,
    payload: OperatorUpdateRequest,
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(
        require_operations_permission(OperationsPermission.MANAGE_OPERATORS)
    ),
    session: AsyncSession = Depends(database_session),
) -> OperatorResponse:
    try:
        async with session.begin():
            operator = await scoped_operator_or_404(
                session,
                principal,
                operator_id,
                OperationsPermission.MANAGE_OPERATORS,
                lock=True,
            )
            previous = {"name": operator.name, "status": operator.status.value}
            if payload.name is not None:
                operator.name = payload.name
            if payload.status is not None:
                operator.status = payload.status
            operator.updated_at = datetime.now(UTC)
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="OPERATOR_UPDATED",
                resource_type="operator",
                resource_id=operator.id,
                market_id=operator.market_id,
                operator_id=operator.id,
                changes={
                    "previous": previous,
                    "current": {"name": operator.name, "status": operator.status.value},
                },
            )
    except IntegrityError as error:
        raise HTTPException(status_code=409, detail="An operator with that name already exists.") from error
    return operator_response(operator)


@router.get("/operator-city-assignments", response_model=OperatorCityAssignmentListResponse)
async def list_operator_city_assignments(
    city_id: UUID | None = Query(default=None),
    operator_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: OperationsPrincipal = Depends(require_operations_permission(VIEW)),
    session: AsyncSession = Depends(database_session),
) -> OperatorCityAssignmentListResponse:
    allowed_cities = principal.city_ids_for(VIEW)
    allowed_operators = principal.operator_ids_for(VIEW)
    filters = [
        OperatorCityAssignment.city_id.in_(allowed_cities),
        OperatorCityAssignment.operator_id.in_(allowed_operators),
    ]
    if city_id is not None:
        filters.append(OperatorCityAssignment.city_id == city_id)
    if operator_id is not None:
        filters.append(OperatorCityAssignment.operator_id == operator_id)
    items = list(
        await session.scalars(
            select(OperatorCityAssignment)
            .where(*filters)
            .order_by(OperatorCityAssignment.effective_from.desc(), OperatorCityAssignment.id)
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    total = await session.scalar(
        select(func.count()).select_from(OperatorCityAssignment).where(*filters)
    )
    return OperatorCityAssignmentListResponse(
        items=[assignment_response(item) for item in items],
        page=page,
        limit=limit,
        total=total or 0,
    )


@router.post(
    "/operator-city-assignments",
    response_model=OperatorCityAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_operator_city_assignment(
    payload: OperatorCityAssignmentCreateRequest,
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(
        require_operations_permission(OperationsPermission.MANAGE_OPERATOR_ASSIGNMENTS)
    ),
    session: AsyncSession = Depends(database_session),
) -> OperatorCityAssignmentResponse:
    try:
        async with session.begin():
            operator, city = await same_market_operator_and_city(
                session,
                payload.operator_id,
                payload.city_id,
            )
            if not principal.allows(
                OperationsPermission.MANAGE_OPERATOR_ASSIGNMENTS,
                market_id=city.market_id,
            ):
                raise _forbidden()
            if operator.status != OperatorStatus.ACTIVE:
                raise ControlPlaneConflict("Only an active operator can receive city authority.")
            if city.lifecycle_status == CityLifecycleStatus.RETIRED:
                raise ControlPlaneConflict("A retired city cannot receive a new operator assignment.")
            await ensure_assignment_does_not_overlap(
                session,
                city_id=city.id,
                service_type=payload.service_type,
                effective_from=payload.effective_from,
                effective_until=payload.effective_until,
            )
            assignment = OperatorCityAssignment(
                operator_id=operator.id,
                city_id=city.id,
                service_type=payload.service_type,
                effective_from=payload.effective_from,
                effective_until=payload.effective_until,
                status=AssignmentStatus.ACTIVE,
                created_by_user_id=principal.user_id,
            )
            session.add(assignment)
            await session.flush()
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="OPERATOR_CITY_ASSIGNMENT_CREATED",
                resource_type="operator_city_assignment",
                resource_id=assignment.id,
                market_id=city.market_id,
                operator_id=operator.id,
                city_id=city.id,
                changes={
                    "service_type": assignment.service_type.value,
                    "effective_from": assignment.effective_from.isoformat(),
                    "effective_until": assignment.effective_until.isoformat()
                    if assignment.effective_until
                    else None,
                },
            )
    except ControlPlaneConflict as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active operator assignment already covers that city, service, and time range.",
        ) from error
    return assignment_response(assignment)


@router.post(
    "/operator-city-assignments/{assignment_id}/retire",
    response_model=OperatorCityAssignmentResponse,
)
async def retire_operator_city_assignment(
    assignment_id: UUID,
    payload: OperatorCityAssignmentRetireRequest,
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(
        require_operations_permission(OperationsPermission.MANAGE_OPERATOR_ASSIGNMENTS)
    ),
    session: AsyncSession = Depends(database_session),
) -> OperatorCityAssignmentResponse:
    async with session.begin():
        assignment = await session.scalar(
            select(OperatorCityAssignment)
            .where(OperatorCityAssignment.id == assignment_id)
            .with_for_update()
        )
        if assignment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")
        city = await session.get(City, assignment.city_id)
        assert city is not None
        if not principal.allows(
            OperationsPermission.MANAGE_OPERATOR_ASSIGNMENTS,
            market_id=city.market_id,
        ):
            # Treat a cross-market identifier as absent to avoid enumeration.
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")
        if assignment.status == AssignmentStatus.RETIRED:
            return assignment_response(assignment)
        now = datetime.now(UTC)
        assignment.status = AssignmentStatus.RETIRED
        assignment.effective_until = min(assignment.effective_until, now) if assignment.effective_until else now
        assignment.retired_at = now
        assignment.retired_by_user_id = principal.user_id
        await audit(
            session,
            actor_user_id=principal.user_id,
            action="OPERATOR_CITY_ASSIGNMENT_RETIRED",
            resource_type="operator_city_assignment",
            resource_id=assignment.id,
            market_id=city.market_id,
            operator_id=assignment.operator_id,
            city_id=assignment.city_id,
            changes={"reason": payload.reason, "retired_at": now.isoformat()},
        )
    return assignment_response(assignment)


@router.get("/rollout-overview", response_model=RolloutOverviewResponse)
async def rollout_overview(
    principal: OperationsPrincipal = Depends(require_operations_permission(VIEW)),
    session: AsyncSession = Depends(database_session),
) -> RolloutOverviewResponse:
    allowed_city_ids = principal.city_ids_for(VIEW)
    allowed_operator_ids = principal.operator_ids_for(VIEW)
    cities = list(
        await session.scalars(
            select(City).where(City.id.in_(allowed_city_ids)).order_by(City.code, City.id)
        )
    )
    summaries: list[RolloutCitySummary] = []
    for city in cities:
        if city.active_configuration_version_id is None:
            missing_pilot = sorted(PILOT_ENTRY_CITY_READINESS_GATES)
            missing_public = sorted(PUBLIC_ACTIVATION_CITY_READINESS_GATES)
            post_launch_status = ReadinessStatus.PENDING.value
        else:
            missing_pilot = await missing_readiness_gates(
                session,
                city.active_configuration_version_id,
                PILOT_ENTRY_CITY_READINESS_GATES,
            )
            missing_public = await missing_readiness_gates(
                session,
                city.active_configuration_version_id,
                PUBLIC_ACTIVATION_CITY_READINESS_GATES,
            )
            post_launch_status = await session.scalar(
                select(CityReadinessCheck.status).where(
                    CityReadinessCheck.configuration_version_id
                    == city.active_configuration_version_id,
                    CityReadinessCheck.gate_code == "POST_LAUNCH_REVIEW",
                )
            )
            post_launch_status = (
                post_launch_status.value
                if post_launch_status is not None
                else ReadinessStatus.PENDING.value
            )
        summaries.append(
            RolloutCitySummary(
                city_id=city.id,
                code=city.code,
                localized_name=LocalizedName.model_validate(city.localized_name),
                lifecycle_status=city.lifecycle_status.value,
                active_configuration_version_id=city.active_configuration_version_id,
                readiness_passed=len(PUBLIC_ACTIVATION_CITY_READINESS_GATES)
                - len(missing_public),
                readiness_required=len(PUBLIC_ACTIVATION_CITY_READINESS_GATES),
                missing_readiness_gates=missing_public,
                pilot_entry_passed=len(PILOT_ENTRY_CITY_READINESS_GATES)
                - len(missing_pilot),
                pilot_entry_required=len(PILOT_ENTRY_CITY_READINESS_GATES),
                missing_pilot_entry_gates=missing_pilot,
                public_activation_passed=len(PUBLIC_ACTIVATION_CITY_READINESS_GATES)
                - len(missing_public),
                public_activation_required=len(PUBLIC_ACTIVATION_CITY_READINESS_GATES),
                missing_public_activation_gates=missing_public,
                post_launch_review_status=post_launch_status,
            )
        )
    visible_market_count = await session.scalar(
        select(func.count()).select_from(Market).where(Market.id.in_(principal.market_ids_for(VIEW)))
    )
    visible_operator_count = await session.scalar(
        select(func.count()).select_from(Operator).where(Operator.id.in_(allowed_operator_ids))
    )
    return RolloutOverviewResponse(
        visible_market_count=visible_market_count or 0,
        visible_operator_count=visible_operator_count or 0,
        visible_city_count=len(cities),
        cities=summaries,
    )
