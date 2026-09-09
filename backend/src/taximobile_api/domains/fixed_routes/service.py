"""Fixed-route validation, immutable content management, and presentation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from geoalchemy2 import Geometry
from geoalchemy2.elements import WKTElement
from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.fixed_routes.models import (
    CityConfigurationRoute,
    FixedRoute,
    FixedRouteDirection,
    FixedRoutePublicationStatus,
    FixedRouteStatus,
    FixedRouteStop,
    FixedRouteVersion,
)
from taximobile_api.domains.fixed_routes.schemas import (
    FixedRouteDirectionDraft,
    FixedRouteDirectionResponse,
    FixedRouteRideSummary,
    FixedRouteResponse,
    FixedRouteStopResponse,
    FixedRouteVersionResponse,
    LineStringGeometry,
    RouteCoordinate,
)
from taximobile_api.domains.markets.models import (
    AssignmentStatus,
    City,
    CityConfigurationService,
    CityConfigurationVersion,
    CityLifecycleStatus,
    CityServiceAreaVersion,
    ConfigurationStatus,
    Market,
    Operator,
    OperatorCityAssignment,
    OperatorStatus,
    ServiceAreaStatus,
    ServiceType,
)
from taximobile_api.domains.pricing.models import (
    BookingType,
    PricingModel,
    PricingRule,
    PricingRuleStatus,
)
from taximobile_api.domains.pricing.models import (
    FinancialPolicyStatus,
    OperatorFeePolicy,
    SchedulingPolicy,
)
from taximobile_api.domains.pricing.service import (
    FinancialQuote,
    InvalidFinancialPolicy,
    calculate_financial_quote,
)


class FixedRouteConflict(ValueError):
    """Stable conflict safe to return to an operations or passenger client."""


@dataclass(frozen=True, slots=True)
class ResolvedFixedRouteRide:
    city_id: UUID
    operator_id: UUID
    direction: FixedRouteDirection
    route_version: FixedRouteVersion
    route: FixedRoute
    pickup: RouteCoordinate
    destination: RouteCoordinate
    quote: FinancialQuote


def point_wkt(coordinate: RouteCoordinate) -> WKTElement:
    return WKTElement(
        f"POINT({coordinate.longitude} {coordinate.latitude})",
        srid=4326,
    )


async def replace_directions(
    session: AsyncSession,
    version: FixedRouteVersion,
    directions: list[FixedRouteDirectionDraft],
) -> None:
    """Replace child content only while its parent is an editable draft."""

    if version.status != FixedRoutePublicationStatus.DRAFT:
        raise FixedRouteConflict("Only a draft route version can be edited.")
    existing_directions = list(
        await session.scalars(
            select(FixedRouteDirection).where(
                FixedRouteDirection.route_version_id == version.id
            )
        )
    )
    if any(
        direction.flat_fare_policy_version_id is not None
        for direction in existing_directions
    ):
        raise FixedRouteConflict(
            "Directions with linked tariffs cannot be replaced; create a new route version."
        )
    await session.execute(
        delete(FixedRouteDirection).where(
            FixedRouteDirection.route_version_id == version.id
        )
    )
    await session.flush()
    for draft in directions:
        direction = FixedRouteDirection(
            route_version_id=version.id,
            direction_code=draft.direction_code,
            start_location_name=draft.start_location_name.model_dump(),
            finish_location_name=draft.finish_location_name.model_dump(),
            start_point=point_wkt(draft.start),
            finish_point=point_wkt(draft.finish),
            static_geometry=WKTElement(draft.geometry.to_wkt(), srid=4326),
            flat_fare_policy_version_id=draft.flat_fare_policy_version_id,
        )
        session.add(direction)
        await session.flush()
        if draft.flat_fare_policy_version_id is not None:
            fare = await session.get(
                PricingRule,
                draft.flat_fare_policy_version_id,
                with_for_update=True,
            )
            if fare is None:
                raise FixedRouteConflict(
                    "The selected fixed-route tariff version is unavailable."
                )
            if fare.fixed_route_direction_id is not None:
                raise FixedRouteConflict(
                    "The selected tariff is already linked to another route direction."
                )
            if fare.status not in {
                PricingRuleStatus.DRAFT,
                PricingRuleStatus.IN_REVIEW,
            }:
                raise FixedRouteConflict(
                    "Link a draft or in-review tariff before activating it."
                )
            fare.fixed_route_direction_id = direction.id
        for sequence, stop in enumerate(draft.stops, start=1):
            session.add(
                FixedRouteStop(
                    direction_id=direction.id,
                    sequence=sequence,
                    localized_name=stop.localized_name.model_dump(),
                    point=point_wkt(stop.location),
                )
            )
    await session.flush()


async def _point_response(
    session: AsyncSession,
    model,
    model_id: UUID,
    column,
) -> RouteCoordinate:
    latitude, longitude = (
        await session.execute(
            select(
                func.ST_Y(column.cast(Geometry(geometry_type="POINT", srid=4326))),
                func.ST_X(column.cast(Geometry(geometry_type="POINT", srid=4326))),
            ).where(model.id == model_id)
        )
    ).one()
    return RouteCoordinate(latitude=float(latitude), longitude=float(longitude))


async def _direction_response(
    session: AsyncSession,
    direction: FixedRouteDirection,
    *,
    immediate_booking_enabled: bool,
    scheduled_booking_enabled: bool,
) -> FixedRouteDirectionResponse:
    geometry_text = await session.scalar(
        select(
            func.ST_AsGeoJSON(
                FixedRouteDirection.static_geometry.cast(
                    Geometry(geometry_type="LINESTRING", srid=4326)
                )
            )
        ).where(FixedRouteDirection.id == direction.id)
    )
    if geometry_text is None:
        raise FixedRouteConflict("The fixed-route geometry is unavailable.")
    fare = (
        await session.get(PricingRule, direction.flat_fare_policy_version_id)
        if direction.flat_fare_policy_version_id is not None
        else None
    )
    stops = list(
        await session.scalars(
            select(FixedRouteStop)
            .where(FixedRouteStop.direction_id == direction.id)
            .order_by(FixedRouteStop.sequence, FixedRouteStop.id)
        )
    )
    return FixedRouteDirectionResponse(
        id=direction.id,
        direction_code=direction.direction_code.value,
        start_location_name=direction.start_location_name,
        finish_location_name=direction.finish_location_name,
        start=await _point_response(
            session, FixedRouteDirection, direction.id, FixedRouteDirection.start_point
        ),
        finish=await _point_response(
            session, FixedRouteDirection, direction.id, FixedRouteDirection.finish_point
        ),
        geometry=LineStringGeometry.model_validate(json.loads(geometry_text)),
        flat_fare_policy_version_id=fare.id if fare is not None else None,
        flat_fare=(
            f"{fare.fixed_amount:.2f}"
            if fare is not None and fare.fixed_amount is not None
            else None
        ),
        currency=fare.currency if fare is not None else None,
        immediate_booking_enabled=immediate_booking_enabled,
        scheduled_booking_enabled=scheduled_booking_enabled,
        stops=[
            FixedRouteStopResponse(
                id=stop.id,
                sequence=stop.sequence,
                localized_name=stop.localized_name,
                location=await _point_response(
                    session, FixedRouteStop, stop.id, FixedRouteStop.point
                ),
            )
            for stop in stops
        ],
    )


async def route_version_response(
    session: AsyncSession,
    version: FixedRouteVersion,
    *,
    include_audit: bool,
    immediate_booking_enabled: bool = False,
    scheduled_booking_enabled: bool = False,
) -> FixedRouteVersionResponse:
    route = await session.get(FixedRoute, version.fixed_route_id)
    if route is None:
        raise FixedRouteConflict("The fixed-route identity is unavailable.")
    directions = list(
        await session.scalars(
            select(FixedRouteDirection)
            .where(FixedRouteDirection.route_version_id == version.id)
            .order_by(FixedRouteDirection.direction_code, FixedRouteDirection.id)
        )
    )
    return FixedRouteVersionResponse(
        id=version.id,
        fixed_route_id=route.id,
        route_code=route.code,
        city_id=route.city_id,
        operator_id=route.operator_id,
        version=version.version,
        localized_name=version.localized_name,
        localized_description=version.localized_description,
        status=version.status.value,
        effective_from=version.effective_from,
        effective_until=version.effective_until,
        optimistic_version=version.optimistic_version,
        directions=[
            await _direction_response(
                session,
                direction,
                immediate_booking_enabled=immediate_booking_enabled,
                scheduled_booking_enabled=scheduled_booking_enabled,
            )
            for direction in directions
        ],
        created_by_user_id=version.created_by_user_id if include_audit else None,
        submitted_by_user_id=version.submitted_by_user_id if include_audit else None,
        submitted_at=version.submitted_at if include_audit else None,
        published_by_user_id=version.published_by_user_id if include_audit else None,
        published_at=version.published_at if include_audit else None,
        retired_by_user_id=version.retired_by_user_id if include_audit else None,
        retired_at=version.retired_at if include_audit else None,
        created_at=version.created_at if include_audit else None,
        updated_at=version.updated_at if include_audit else None,
    )


async def route_response(
    session: AsyncSession,
    route: FixedRoute,
    *,
    versions: list[FixedRouteVersion] | None = None,
    include_audit: bool,
    booking_flags: dict[UUID, tuple[bool, bool]] | None = None,
) -> FixedRouteResponse:
    if versions is None:
        versions = list(
            await session.scalars(
                select(FixedRouteVersion)
                .where(FixedRouteVersion.fixed_route_id == route.id)
                .order_by(FixedRouteVersion.created_at.desc(), FixedRouteVersion.id)
            )
        )
    flags = booking_flags or {}
    return FixedRouteResponse(
        id=route.id,
        city_id=route.city_id,
        operator_id=route.operator_id,
        code=route.code,
        status=route.status.value,
        versions=[
            await route_version_response(
                session,
                version,
                include_audit=include_audit,
                immediate_booking_enabled=flags.get(version.id, (False, False))[0],
                scheduled_booking_enabled=flags.get(version.id, (False, False))[1],
            )
            for version in versions
        ],
    )


async def validate_route_structure(
    session: AsyncSession,
    version: FixedRouteVersion,
    *,
    require_active_fares: bool,
    allow_unpriced_directions: bool = False,
) -> None:
    route = await session.get(FixedRoute, version.fixed_route_id)
    if route is None or route.status != FixedRouteStatus.ACTIVE:
        raise FixedRouteConflict("The route identity must be active.")
    if version.effective_until is not None and version.effective_until <= version.effective_from:
        raise FixedRouteConflict("effective_until must be after effective_from.")
    directions = list(
        await session.scalars(
            select(FixedRouteDirection).where(
                FixedRouteDirection.route_version_id == version.id
            )
        )
    )
    if not directions:
        raise FixedRouteConflict("A route version requires at least one direction.")
    if len({direction.direction_code for direction in directions}) != len(directions):
        raise FixedRouteConflict("A route version cannot duplicate a direction.")
    market_id = await session.scalar(select(City.market_id).where(City.id == route.city_id))
    market = await session.get(Market, market_id) if market_id is not None else None
    if market is None:
        raise FixedRouteConflict("The route city market is unavailable.")
    for direction in directions:
        fare = (
            await session.get(PricingRule, direction.flat_fare_policy_version_id)
            if direction.flat_fare_policy_version_id is not None
            else None
        )
        if fare is None:
            if not allow_unpriced_directions:
                raise FixedRouteConflict(
                    "Every direction requires a linked fixed-route tariff."
                )
        else:
            if (
                fare.fixed_route_direction_id != direction.id
                or fare.city_id != route.city_id
                or fare.operator_id != route.operator_id
                or fare.service_type != ServiceType.FIXED_ROUTE
                or fare.booking_type != BookingType.IMMEDIATE
                or fare.model != PricingModel.FIXED
                or fare.fixed_amount is None
                or fare.fixed_amount <= 0
                or fare.currency != market.default_currency
            ):
                raise FixedRouteConflict(
                    "Every direction requires an exact positive same-scope fixed-route tariff link."
                )
            if require_active_fares and (
                fare.status != PricingRuleStatus.ACTIVE
                or fare.effective_from > version.effective_from
                or (
                    fare.effective_until is not None
                    and (
                        fare.effective_until <= version.effective_from
                        or version.effective_until is None
                        or fare.effective_until < version.effective_until
                    )
                )
            ):
                raise FixedRouteConflict(
                    "Every direction tariff must be active for the complete route publication period."
                )
        geometry_valid = await session.scalar(
            text(
                "SELECT ST_IsValid(static_geometry::geometry) "
                "AND ST_NPoints(static_geometry::geometry) >= 2 "
                "AND ST_DWithin(start_point, ST_StartPoint(static_geometry::geometry)::geography, 100) "
                "AND ST_DWithin(finish_point, ST_EndPoint(static_geometry::geometry)::geography, 100) "
                "FROM fixed_route_directions WHERE id = :direction_id"
            ),
            {"direction_id": direction.id},
        )
        if not geometry_valid:
            raise FixedRouteConflict(
                "Direction geometry must be valid and begin/end within 100 meters of its named endpoints."
            )
        invalid_stops = await session.scalar(
            text(
                "SELECT count(*) FROM fixed_route_stops "
                "WHERE direction_id = :direction_id "
                "AND NOT ST_DWithin(point, "
                "(SELECT static_geometry FROM fixed_route_directions WHERE id = :direction_id), 500)"
            ),
            {"direction_id": direction.id},
        )
        if invalid_stops:
            raise FixedRouteConflict("Every stop must be within 500 meters of its route line.")


async def validate_publication_scope(
    session: AsyncSession,
    version: FixedRouteVersion,
) -> None:
    """Require active assignment, approved boundary, fare, and spatial coverage."""

    await validate_route_structure(session, version, require_active_fares=True)
    route = await session.get(FixedRoute, version.fixed_route_id)
    assert route is not None
    city = await session.get(City, route.city_id)
    operator = await session.get(Operator, route.operator_id)
    if city is None or operator is None or operator.market_id != city.market_id:
        raise FixedRouteConflict("The route city/operator scope is invalid.")
    if operator.status != OperatorStatus.ACTIVE:
        raise FixedRouteConflict("The route operator must be active before publication.")
    assignment = await session.scalar(
        select(OperatorCityAssignment)
        .where(
            OperatorCityAssignment.city_id == city.id,
            OperatorCityAssignment.operator_id == operator.id,
            OperatorCityAssignment.service_type == ServiceType.FIXED_ROUTE,
            OperatorCityAssignment.status == AssignmentStatus.ACTIVE,
            OperatorCityAssignment.effective_from <= version.effective_from,
            or_(
                OperatorCityAssignment.effective_until.is_(None),
                OperatorCityAssignment.effective_until > version.effective_from,
            ),
        )
        .order_by(OperatorCityAssignment.effective_from.desc())
        .limit(1)
    )
    if assignment is None:
        raise FixedRouteConflict(
            "The operator needs an active fixed-route assignment for this city."
        )
    service_area = await session.scalar(
        select(CityServiceAreaVersion)
        .where(
            CityServiceAreaVersion.city_id == city.id,
            CityServiceAreaVersion.status.in_(
                [ServiceAreaStatus.APPROVED, ServiceAreaStatus.ACTIVE]
            ),
            CityServiceAreaVersion.effective_from <= version.effective_from,
            or_(
                CityServiceAreaVersion.effective_until.is_(None),
                CityServiceAreaVersion.effective_until > version.effective_from,
            ),
        )
        .order_by(CityServiceAreaVersion.effective_from.desc())
        .limit(1)
    )
    if service_area is None:
        raise FixedRouteConflict(
            "An approved effective city service area is required before route publication."
        )
    outside_count = await session.scalar(
        text(
            "SELECT count(*) FROM fixed_route_directions d "
            "WHERE d.route_version_id = :version_id AND ("
            "NOT ST_Covers((SELECT boundary::geometry FROM city_service_area_versions WHERE id = :area_id), d.start_point::geometry) "
            "OR NOT ST_Covers((SELECT boundary::geometry FROM city_service_area_versions WHERE id = :area_id), d.finish_point::geometry) "
            "OR NOT ST_Covers((SELECT boundary::geometry FROM city_service_area_versions WHERE id = :area_id), d.static_geometry::geometry))"
        ),
        {"version_id": version.id, "area_id": service_area.id},
    )
    if outside_count:
        raise FixedRouteConflict(
            "Every route endpoint and geometry must remain inside the approved city service area."
        )


def public_city_booking_available(city: City) -> bool:
    return (
        city.lifecycle_status in {CityLifecycleStatus.PILOT, CityLifecycleStatus.ACTIVE}
        and city.active_configuration_version_id is not None
    )


async def active_route_booking_flags(
    session: AsyncSession,
    city: City,
    version_ids: list[UUID],
) -> dict[UUID, tuple[bool, bool]]:
    if not public_city_booking_available(city) or not version_ids:
        return {}
    rows = (
        await session.execute(
            select(
                CityConfigurationRoute.fixed_route_version_id,
                CityConfigurationRoute.immediate_booking_enabled,
                CityConfigurationRoute.scheduled_booking_enabled,
            ).where(
                CityConfigurationRoute.configuration_version_id
                == city.active_configuration_version_id,
                CityConfigurationRoute.fixed_route_version_id.in_(version_ids),
            )
        )
    ).all()
    return {
        version_id: (bool(immediate), bool(scheduled))
        for version_id, immediate, scheduled in rows
    }


async def published_versions_for_city(
    session: AsyncSession,
    city_id: UUID,
    *,
    now: datetime | None = None,
) -> list[tuple[FixedRoute, FixedRouteVersion]]:
    at = now or datetime.now(UTC)
    return list(
        (
            await session.execute(
                select(FixedRoute, FixedRouteVersion)
                .join(
                    FixedRouteVersion,
                    FixedRouteVersion.fixed_route_id == FixedRoute.id,
                )
                .where(
                    FixedRoute.city_id == city_id,
                    FixedRoute.status == FixedRouteStatus.ACTIVE,
                    FixedRouteVersion.status == FixedRoutePublicationStatus.PUBLISHED,
                    FixedRouteVersion.effective_from <= at,
                    or_(
                        FixedRouteVersion.effective_until.is_(None),
                        FixedRouteVersion.effective_until > at,
                    ),
                )
                .order_by(FixedRoute.code, FixedRouteVersion.version)
            )
        ).all()
    )


async def fixed_route_ride_summary(
    session: AsyncSession,
    direction_id: UUID,
) -> FixedRouteRideSummary | None:
    row = (
        await session.execute(
            select(FixedRouteDirection, FixedRouteVersion, FixedRoute)
            .join(
                FixedRouteVersion,
                FixedRouteVersion.id == FixedRouteDirection.route_version_id,
            )
            .join(FixedRoute, FixedRoute.id == FixedRouteVersion.fixed_route_id)
            .where(FixedRouteDirection.id == direction_id)
        )
    ).one_or_none()
    if row is None:
        return None
    direction, version, route = row
    return FixedRouteRideSummary(
        direction_version_id=direction.id,
        route_version_id=version.id,
        route_code=route.code,
        localized_route_name=version.localized_name,
        direction_code=direction.direction_code.value,
        start_location_name=direction.start_location_name,
        finish_location_name=direction.finish_location_name,
    )


async def resolve_fixed_route_ride(
    session: AsyncSession,
    direction_id: UUID,
    *,
    city_hint: UUID | None,
    at: datetime | None = None,
    booking_type: BookingType = BookingType.IMMEDIATE,
) -> ResolvedFixedRouteRide:
    """Resolve a bookable published direction without consulting live supply."""

    applicable_at = at or datetime.now(UTC)
    booking_enabled_filter = (
        CityConfigurationRoute.immediate_booking_enabled.is_(True)
        if booking_type == BookingType.IMMEDIATE
        else CityConfigurationRoute.scheduled_booking_enabled.is_(True)
    )
    row = (
        await session.execute(
            select(
                FixedRouteDirection,
                FixedRouteVersion,
                FixedRoute,
                City,
                CityConfigurationRoute,
                CityConfigurationService,
                OperatorCityAssignment,
            )
            .join(
                FixedRouteVersion,
                FixedRouteVersion.id == FixedRouteDirection.route_version_id,
            )
            .join(FixedRoute, FixedRoute.id == FixedRouteVersion.fixed_route_id)
            .join(City, City.id == FixedRoute.city_id)
            .join(
                CityConfigurationRoute,
                CityConfigurationRoute.fixed_route_version_id == FixedRouteVersion.id,
            )
            .join(
                CityConfigurationVersion,
                CityConfigurationVersion.id
                == CityConfigurationRoute.configuration_version_id,
            )
            .join(
                CityConfigurationService,
                CityConfigurationService.configuration_version_id
                == CityConfigurationRoute.configuration_version_id,
            )
            .join(
                OperatorCityAssignment,
                OperatorCityAssignment.id
                == CityConfigurationService.operator_city_assignment_id,
            )
            .where(
                FixedRouteDirection.id == direction_id,
                FixedRoute.status == FixedRouteStatus.ACTIVE,
                FixedRouteVersion.status == FixedRoutePublicationStatus.PUBLISHED,
                FixedRouteVersion.effective_from <= applicable_at,
                or_(
                    FixedRouteVersion.effective_until.is_(None),
                    FixedRouteVersion.effective_until > applicable_at,
                ),
                City.lifecycle_status.in_(
                    [CityLifecycleStatus.PILOT, CityLifecycleStatus.ACTIVE]
                ),
                City.active_configuration_version_id
                == CityConfigurationRoute.configuration_version_id,
                CityConfigurationVersion.status == ConfigurationStatus.ACTIVE,
                CityConfigurationService.service_type == ServiceType.FIXED_ROUTE,
                CityConfigurationService.enabled.is_(True),
                booking_enabled_filter,
                OperatorCityAssignment.city_id == City.id,
                OperatorCityAssignment.operator_id == FixedRoute.operator_id,
                OperatorCityAssignment.service_type == ServiceType.FIXED_ROUTE,
                OperatorCityAssignment.status == AssignmentStatus.ACTIVE,
                OperatorCityAssignment.effective_from <= applicable_at,
                or_(
                    OperatorCityAssignment.effective_until.is_(None),
                    OperatorCityAssignment.effective_until > applicable_at,
                ),
            )
        )
    ).one_or_none()
    if row is None:
        raise FixedRouteConflict("The fixed-route direction is not currently bookable.")
    direction, version, route, city, _, service, _ = row
    if city_hint is not None and city_hint != city.id:
        raise FixedRouteConflict("The selected fixed route does not belong to the requested city.")
    fare = await session.get(PricingRule, direction.flat_fare_policy_version_id)
    fee_policy = (
        await session.get(OperatorFeePolicy, service.operator_fee_policy_version_id)
        if service.operator_fee_policy_version_id is not None
        else None
    )
    scheduling_policy = (
        await session.get(SchedulingPolicy, service.scheduling_policy_version_id)
        if booking_type == BookingType.SCHEDULED
        and service.scheduling_policy_version_id is not None
        else None
    )
    if (
        fare is None
        or fee_policy is None
        or fare.fixed_route_direction_id != direction.id
        or fare.city_id != city.id
        or fare.operator_id != route.operator_id
        or fare.service_type != ServiceType.FIXED_ROUTE
        or fare.booking_type != BookingType.IMMEDIATE
        or fare.status != PricingRuleStatus.ACTIVE
        or fare.effective_from > applicable_at
        or (fare.effective_until is not None and fare.effective_until <= applicable_at)
        or fee_policy.city_id != city.id
        or fee_policy.operator_id != route.operator_id
        or fee_policy.service_type != ServiceType.FIXED_ROUTE
        or fee_policy.status != FinancialPolicyStatus.ACTIVE
        or fee_policy.effective_from > applicable_at
        or (
            fee_policy.effective_until is not None
            and fee_policy.effective_until <= applicable_at
        )
        or (
            booking_type == BookingType.SCHEDULED
            and (
                scheduling_policy is None
                or scheduling_policy.city_id != city.id
                or scheduling_policy.operator_id != route.operator_id
                or scheduling_policy.service_type != ServiceType.FIXED_ROUTE
                or scheduling_policy.status != FinancialPolicyStatus.ACTIVE
                or scheduling_policy.effective_from > applicable_at
                or (
                    scheduling_policy.effective_until is not None
                    and scheduling_policy.effective_until <= applicable_at
                )
            )
        )
    ):
        raise FixedRouteConflict("The fixed-route fare bundle is not currently active.")
    try:
        quote = calculate_financial_quote(
            fare,
            fee_policy,
            booking_type=booking_type,
            scheduling_policy=scheduling_policy,
        )
    except InvalidFinancialPolicy as error:
        raise FixedRouteConflict(str(error)) from error
    return ResolvedFixedRouteRide(
        city_id=city.id,
        operator_id=route.operator_id,
        direction=direction,
        route_version=version,
        route=route,
        pickup=await _point_response(
            session, FixedRouteDirection, direction.id, FixedRouteDirection.start_point
        ),
        destination=await _point_response(
            session, FixedRouteDirection, direction.id, FixedRouteDirection.finish_point
        ),
        quote=quote,
    )
