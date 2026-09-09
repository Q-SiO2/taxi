"""PostGIS authority for place-search city focus and pickup eligibility."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from geoalchemy2 import Geometry
from sqlalchemy import Float, Integer, column, func, or_, select, true, values
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.markets.models import (
    AssignmentStatus,
    City,
    CityConfigurationService,
    CityConfigurationVersion,
    CityLifecycleStatus,
    CityServiceAreaVersion,
    ConfigurationStatus,
    OperatorCityAssignment,
    ServiceAreaStatus,
    ServiceType,
)
from taximobile_api.integrations.geocoding.models import GeoCoordinate, SearchViewbox


class PlaceCityUnavailable(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PlaceCityContext:
    city_id: UUID
    service_area_version_id: UUID
    viewbox: SearchViewbox


async def active_place_city_context(
    session: AsyncSession,
    city_id: UUID,
    *,
    at: datetime | None = None,
) -> PlaceCityContext:
    applicable_at = at or datetime.now(UTC)
    boundary_geometry = CityServiceAreaVersion.boundary.cast(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326)
    )
    envelope = func.ST_Envelope(boundary_geometry)
    row = (
        await session.execute(
            select(
                City.id,
                CityServiceAreaVersion.id,
                func.ST_XMin(envelope),
                func.ST_YMin(envelope),
                func.ST_XMax(envelope),
                func.ST_YMax(envelope),
            )
            .join(
                CityConfigurationVersion,
                CityConfigurationVersion.id == City.active_configuration_version_id,
            )
            .join(
                CityServiceAreaVersion,
                CityServiceAreaVersion.id == CityConfigurationVersion.service_area_version_id,
            )
            .join(
                CityConfigurationService,
                CityConfigurationService.configuration_version_id
                == CityConfigurationVersion.id,
            )
            .join(
                OperatorCityAssignment,
                OperatorCityAssignment.id
                == CityConfigurationService.operator_city_assignment_id,
            )
            .where(
                City.id == city_id,
                City.lifecycle_status.in_({CityLifecycleStatus.PILOT, CityLifecycleStatus.ACTIVE}),
                CityConfigurationVersion.status == ConfigurationStatus.ACTIVE,
                CityConfigurationService.service_type == ServiceType.ON_DEMAND,
                CityConfigurationService.enabled.is_(True),
                CityServiceAreaVersion.status == ServiceAreaStatus.ACTIVE,
                CityServiceAreaVersion.effective_from <= applicable_at,
                or_(
                    CityServiceAreaVersion.effective_until.is_(None),
                    CityServiceAreaVersion.effective_until > applicable_at,
                ),
                OperatorCityAssignment.city_id == City.id,
                OperatorCityAssignment.service_type == ServiceType.ON_DEMAND,
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
        raise PlaceCityUnavailable("Place discovery is unavailable for this city.")
    resolved_city_id, area_id, west, south, east, north = row
    return PlaceCityContext(
        city_id=resolved_city_id,
        service_area_version_id=area_id,
        viewbox=SearchViewbox(
            west=float(west),
            south=float(south),
            east=float(east),
            north=float(north),
        ),
    )


async def pickup_serviceability(
    session: AsyncSession,
    context: PlaceCityContext,
    coordinates: list[GeoCoordinate],
) -> list[bool]:
    """Evaluate exact active polygon coverage; provider locality text is irrelevant."""
    if not coordinates:
        return []
    coordinate_rows = values(
        column("ordinal", Integer),
        column("longitude", Float),
        column("latitude", Float),
        name="place_coordinates",
    ).data(
        [
            (index, coordinate.longitude, coordinate.latitude)
            for index, coordinate in enumerate(coordinates)
        ]
    )
    point = func.ST_SetSRID(
        func.ST_MakePoint(coordinate_rows.c.longitude, coordinate_rows.c.latitude),
        4326,
    )
    rows = (
        await session.execute(
            select(
                coordinate_rows.c.ordinal,
                func.ST_Covers(CityServiceAreaVersion.boundary, point),
            )
            .select_from(CityServiceAreaVersion)
            .join(coordinate_rows, true())
            .where(CityServiceAreaVersion.id == context.service_area_version_id)
            .order_by(coordinate_rows.c.ordinal)
        )
    ).all()
    if len(rows) != len(coordinates):
        raise PlaceCityUnavailable("The active city service area is unavailable.")
    return [bool(covered) for _, covered in rows]
