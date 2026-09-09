"""Immutable, directional fixed-route publication records."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from taximobile_api.db.base import Base
from taximobile_api.domains.markets.models import bounded_enum


class FixedRouteStatus(StrEnum):
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class FixedRoutePublicationStatus(StrEnum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    PUBLISHED = "PUBLISHED"
    RETIRED = "RETIRED"


class FixedRouteDirectionCode(StrEnum):
    OUTBOUND = "OUTBOUND"
    INBOUND = "INBOUND"


class FixedRoute(Base):
    """Stable route identity; passenger-visible content lives in versions."""

    __tablename__ = "fixed_routes"
    __table_args__ = (
        UniqueConstraint(
            "city_id",
            "operator_id",
            "code",
            name="uq_fixed_route_scope_code",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    city_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("cities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    operator_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("operators.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[FixedRouteStatus] = mapped_column(
        bounded_enum(FixedRouteStatus, "fixed_route_status", 16),
        nullable=False,
        default=FixedRouteStatus.ACTIVE,
        index=True,
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    retired_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    retired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class FixedRouteVersion(Base):
    """Reviewed route content; published rows are never edited in place."""

    __tablename__ = "fixed_route_versions"
    __table_args__ = (
        UniqueConstraint(
            "fixed_route_id",
            "version",
            name="uq_fixed_route_version_route_version",
        ),
        CheckConstraint(
            "effective_until IS NULL OR effective_until > effective_from",
            name="fixed_route_version_effective_range",
        ),
        CheckConstraint(
            "optimistic_version >= 1",
            name="fixed_route_version_optimistic_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    fixed_route_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("fixed_routes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    localized_name: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)
    localized_description: Mapped[dict[str, str]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    status: Mapped[FixedRoutePublicationStatus] = mapped_column(
        bounded_enum(
            FixedRoutePublicationStatus,
            "fixed_route_publication_status",
            16,
        ),
        nullable=False,
        default=FixedRoutePublicationStatus.DRAFT,
        index=True,
    )
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    effective_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    optimistic_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    submitted_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    published_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retired_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    retired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class FixedRouteDirection(Base):
    """One explicit complete direction and its locked flat-fare policy."""

    __tablename__ = "fixed_route_directions"
    __table_args__ = (
        UniqueConstraint(
            "route_version_id",
            "direction_code",
            name="uq_fixed_route_direction_version_code",
        ),
        CheckConstraint(
            "start_location_name <> '{}'::jsonb AND finish_location_name <> '{}'::jsonb",
            name="fixed_route_direction_named_endpoints",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    route_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("fixed_route_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    direction_code: Mapped[FixedRouteDirectionCode] = mapped_column(
        bounded_enum(FixedRouteDirectionCode, "fixed_route_direction_code", 16),
        nullable=False,
    )
    start_location_name: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)
    finish_location_name: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)
    start_point: Mapped[object] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )
    finish_point: Mapped[object] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )
    static_geometry: Mapped[object] = mapped_column(
        Geography(geometry_type="LINESTRING", srid=4326, spatial_index=False), nullable=False
    )
    # Draft geometry may be created before the separately reviewed fare.  The
    # route cannot enter review without an exact bidirectional fare link and
    # cannot be published until that fare is active for the whole route period.
    flat_fare_policy_version_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("pricing_rules.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )


class FixedRouteStop(Base):
    """Optional ordered stop; stops do not imply segment pricing."""

    __tablename__ = "fixed_route_stops"
    __table_args__ = (
        UniqueConstraint(
            "direction_id",
            "sequence",
            name="uq_fixed_route_stop_direction_sequence",
        ),
        CheckConstraint("sequence >= 1", name="fixed_route_stop_positive_sequence"),
        CheckConstraint(
            "localized_name <> '{}'::jsonb",
            name="fixed_route_stop_localized_name",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    direction_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("fixed_route_directions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    localized_name: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)
    point: Mapped[object] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )


class CityConfigurationRoute(Base):
    """A coherent city bundle's explicit route publication/booking allowlist."""

    __tablename__ = "city_configuration_routes"
    __table_args__ = (
        UniqueConstraint(
            "configuration_version_id",
            "fixed_route_version_id",
            name="uq_city_configuration_route_version",
        ),
        CheckConstraint(
            "immediate_booking_enabled OR scheduled_booking_enabled",
            name="city_configuration_route_booking_enabled",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    configuration_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("city_configuration_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fixed_route_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("fixed_route_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    immediate_booking_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    scheduled_booking_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
