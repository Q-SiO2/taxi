"""Public city and published fixed-route catalog without live-supply data."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.auth.dependencies import CurrentPrincipal, authenticated_principal
from taximobile_api.domains.scheduled_bookings.local_time import (
    TimeZoneRulesUnavailable, local_pickup_time_options, packaged_rules_version,
)
from taximobile_api.domains.scheduled_bookings.schemas import (
    ScheduledLocalTimeOption, ScheduledLocalTimeRequest, ScheduledLocalTimeResponse,
)
from taximobile_api.domains.fixed_routes.models import (
    FixedRoute,
    FixedRouteDirection,
    FixedRoutePublicationStatus,
    FixedRouteStatus,
    FixedRouteVersion,
)
from taximobile_api.domains.fixed_routes.schemas import (
    FixedRouteVersionResponse,
    PublicCityListResponse,
    PublicCityResponse,
    PublicFixedRouteListResponse,
)
from taximobile_api.domains.fixed_routes.service import (
    active_route_booking_flags,
    public_city_booking_available,
    published_versions_for_city,
    route_response,
    route_version_response,
)
from taximobile_api.domains.markets.models import City, CityLifecycleStatus


router = APIRouter(tags=["public-city-catalog"])
PUBLIC_CITY_STATUSES = (CityLifecycleStatus.ACTIVE, CityLifecycleStatus.PAUSED)


def _city_response(city: City) -> PublicCityResponse:
    return PublicCityResponse(
        id=city.id,
        code=city.code,
        localized_name=city.localized_name,
        timezone=city.timezone,
        lifecycle_status=city.lifecycle_status.value,
        booking_available=public_city_booking_available(city),
    )


async def _public_city_or_404(session: AsyncSession, city_id: UUID) -> City:
    city = await session.scalar(
        select(City).where(
            City.id == city_id,
            City.lifecycle_status.in_(PUBLIC_CITY_STATUSES),
        )
    )
    if city is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="City not found.")
    return city


@router.get("/cities", response_model=PublicCityListResponse)
async def list_public_cities(
    response: Response,
    session: AsyncSession = Depends(database_session),
) -> PublicCityListResponse:
    """List public service jurisdictions, never live taxi supply."""

    cities = list(
        await session.scalars(
            select(City)
            .where(City.lifecycle_status.in_(PUBLIC_CITY_STATUSES))
            .order_by(City.code, City.id)
            .limit(200)
        )
    )
    response.headers["Cache-Control"] = "public, max-age=60"
    return PublicCityListResponse(items=[_city_response(city) for city in cities])


@router.post("/cities/{city_id}/scheduled-time-options", response_model=ScheduledLocalTimeResponse)
async def scheduled_time_options(
    city_id: UUID,
    payload: ScheduledLocalTimeRequest,
    response: Response,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> ScheduledLocalTimeResponse:
    del principal
    city = await _public_city_or_404(session, city_id)
    try:
        options = local_pickup_time_options(
            datetime.fromisoformat(f"{payload.local_date}T{payload.local_time}"), city.timezone,
        )
        version = packaged_rules_version()
    except TimeZoneRulesUnavailable as error:
        raise HTTPException(status_code=503, detail="City time rules are unavailable. Try again later.") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail="The clock selection is outside the supported date range.") from error
    response.headers["Cache-Control"] = "no-store"
    return ScheduledLocalTimeResponse(
        city_id=city.id, city_timezone=city.timezone, local_date=payload.local_date,
        local_time=payload.local_time, booking_available=public_city_booking_available(city),
        rules_version=version,
        options=[ScheduledLocalTimeOption(scheduled_for=instant, utc_offset_seconds=offset)
                 for instant, offset in options],
    )


@router.get("/cities/{city_id}", response_model=PublicCityResponse)
async def get_public_city(
    city_id: UUID,
    response: Response,
    session: AsyncSession = Depends(database_session),
) -> PublicCityResponse:
    city = await _public_city_or_404(session, city_id)
    response.headers["Cache-Control"] = "public, max-age=60"
    return _city_response(city)


@router.get(
    "/cities/{city_id}/fixed-routes",
    response_model=PublicFixedRouteListResponse,
    response_model_exclude_none=True,
)
async def list_public_fixed_routes(
    city_id: UUID,
    response: Response,
    session: AsyncSession = Depends(database_session),
) -> PublicFixedRouteListResponse:
    city = await _public_city_or_404(session, city_id)
    pairs = await published_versions_for_city(session, city.id)
    version_ids = [version.id for _, version in pairs]
    flags = await active_route_booking_flags(session, city, version_ids)
    routes = [
        await route_response(
            session,
            route,
            versions=[version],
            include_audit=False,
            booking_flags=flags,
        )
        for route, version in pairs
    ]
    response.headers["Cache-Control"] = "public, max-age=60"
    return PublicFixedRouteListResponse(city=_city_response(city), routes=routes)


@router.get(
    "/fixed-route-directions/{direction_version_id}",
    response_model=FixedRouteVersionResponse,
    response_model_exclude_none=True,
)
async def get_public_fixed_route_direction(
    direction_version_id: UUID,
    response: Response,
    session: AsyncSession = Depends(database_session),
) -> FixedRouteVersionResponse:
    """Return the published parent version containing one direction."""

    now = datetime.now(UTC)
    row = (
        await session.execute(
            select(FixedRouteDirection, FixedRouteVersion, FixedRoute, City)
            .join(
                FixedRouteVersion,
                FixedRouteVersion.id == FixedRouteDirection.route_version_id,
            )
            .join(FixedRoute, FixedRoute.id == FixedRouteVersion.fixed_route_id)
            .join(City, City.id == FixedRoute.city_id)
            .where(
                FixedRouteDirection.id == direction_version_id,
                FixedRoute.status == FixedRouteStatus.ACTIVE,
                FixedRouteVersion.status == FixedRoutePublicationStatus.PUBLISHED,
                FixedRouteVersion.effective_from <= now,
                or_(
                    FixedRouteVersion.effective_until.is_(None),
                    FixedRouteVersion.effective_until > now,
                ),
                City.lifecycle_status.in_(PUBLIC_CITY_STATUSES),
            )
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Published fixed-route direction not found.",
        )
    direction, version, _, city = row
    flags = await active_route_booking_flags(session, city, [version.id])
    result = await route_version_response(
        session,
        version,
        include_audit=False,
        immediate_booking_enabled=flags.get(version.id, (False, False))[0],
        scheduled_booking_enabled=flags.get(version.id, (False, False))[1],
    )
    result.directions = [item for item in result.directions if item.id == direction.id]
    # Route content is immutable after publication, but booking availability is
    # derived from the active city configuration and can change independently.
    response.headers["Cache-Control"] = "public, max-age=60"
    return result
