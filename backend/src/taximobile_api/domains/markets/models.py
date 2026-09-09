"""Persistent national control-plane records.

Only foundation-owned component references live here.  Driver requirements,
financial policies, fixed routes, and scheduling add their foreign keys in the
roadmap phase that owns and validates those records; this module never stores an
unvalidated configuration JSON blob as a substitute.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from taximobile_api.db.base import Base


def bounded_enum(enum_type: type[StrEnum], name: str, length: int) -> Enum:
    """Persist new control-plane enums as constrained text.

    Existing product enums are native PostgreSQL types.  Constrained text is
    deliberate for this administrative domain: role/lifecycle additions still
    require a reviewed migration, while range/exclusion indexes and managed
    PostgreSQL upgrades remain straightforward.
    """

    return Enum(
        enum_type,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        length=length,
    )


class MarketStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class OperatorType(StrEnum):
    PLATFORM = "PLATFORM"
    COOPERATIVE = "COOPERATIVE"
    LOCAL_ENTITY = "LOCAL_ENTITY"


class OperatorStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class CityLifecycleStatus(StrEnum):
    DRAFT = "DRAFT"
    CONFIGURING = "CONFIGURING"
    PILOT = "PILOT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    RETIRED = "RETIRED"


class ServiceType(StrEnum):
    ON_DEMAND = "ON_DEMAND"
    FIXED_ROUTE = "FIXED_ROUTE"
    SCHEDULED = "SCHEDULED"


class AssignmentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class ConfigurationStatus(StrEnum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    REPLACED = "REPLACED"


class ServiceAreaStatus(StrEnum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    REPLACED = "REPLACED"


class ReadinessStatus(StrEnum):
    PENDING = "PENDING"
    PASSED = "PASSED"
    FAILED = "FAILED"


class Market(Base):
    __tablename__ = "markets"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(8), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    default_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[MarketStatus] = mapped_column(
        bounded_enum(MarketStatus, "market_status", 16),
        nullable=False,
        default=MarketStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Operator(Base):
    __tablename__ = "operators"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    market_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("markets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    cooperative_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("cooperatives.id", ondelete="RESTRICT"),
        nullable=True,
        unique=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    operator_type: Mapped[OperatorType] = mapped_column(
        bounded_enum(OperatorType, "operator_type", 24), nullable=False
    )
    status: Mapped[OperatorStatus] = mapped_column(
        bounded_enum(OperatorStatus, "operator_status", 16),
        nullable=False,
        default=OperatorStatus.DRAFT,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class City(Base):
    __tablename__ = "cities"
    __table_args__ = (
        UniqueConstraint("market_id", "code", name="uq_cities_market_code"),
        CheckConstraint("optimistic_version >= 1", name="city_optimistic_version_positive"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    market_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("markets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    localized_name: Mapped[dict] = mapped_column(JSONB, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    presentation_centroid: Mapped[object] = mapped_column(
        Geography(geometry_type="POINT", srid=4326), nullable=False
    )
    lifecycle_status: Mapped[CityLifecycleStatus] = mapped_column(
        bounded_enum(CityLifecycleStatus, "city_lifecycle_status", 20),
        nullable=False,
        default=CityLifecycleStatus.DRAFT,
        index=True,
    )
    active_configuration_version_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "city_configuration_versions.id",
            name="fk_city_active_configuration",
            use_alter=True,
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    # Only the deterministic pre-national city has this flag.  It allows the
    # existing pilot to keep operating while new cities remain fail-closed until
    # all later configuration domains and readiness gates exist.
    is_legacy_compatibility: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    optimistic_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class OperatorCityAssignment(Base):
    __tablename__ = "operator_city_assignments"
    __table_args__ = (
        CheckConstraint(
            "effective_until IS NULL OR effective_until > effective_from",
            name="assignment_effective_range",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    operator_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("operators.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    city_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    service_type: Mapped[ServiceType] = mapped_column(
        bounded_enum(ServiceType, "city_service_type", 20), nullable=False, index=True
    )
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[AssignmentStatus] = mapped_column(
        bounded_enum(AssignmentStatus, "operator_assignment_status", 16),
        nullable=False,
        default=AssignmentStatus.ACTIVE,
        index=True,
    )
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    retired_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CityServiceAreaVersion(Base):
    __tablename__ = "city_service_area_versions"
    __table_args__ = (
        UniqueConstraint("city_id", "version", name="uq_city_service_area_versions_city_version"),
        CheckConstraint(
            "effective_until IS NULL OR effective_until > effective_from",
            name="effective_range",
        ),
        CheckConstraint("optimistic_version >= 1", name="optimistic_version_positive"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    city_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    boundary: Mapped[object] = mapped_column(
        Geography(geometry_type="MULTIPOLYGON", srid=4326), nullable=False
    )
    status: Mapped[ServiceAreaStatus] = mapped_column(
        bounded_enum(ServiceAreaStatus, "service_area_status", 16),
        nullable=False,
        default=ServiceAreaStatus.DRAFT,
        index=True,
    )
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    optimistic_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class CityConfigurationVersion(Base):
    __tablename__ = "city_configuration_versions"
    __table_args__ = (
        UniqueConstraint("city_id", "version", name="uq_city_configuration_versions_city_version"),
        CheckConstraint("optimistic_version >= 1", name="optimistic_version_positive"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    city_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[ConfigurationStatus] = mapped_column(
        bounded_enum(ConfigurationStatus, "city_configuration_status", 16),
        nullable=False,
        default=ConfigurationStatus.DRAFT,
        index=True,
    )
    service_area_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("city_service_area_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    driver_requirement_version_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("driver_requirement_versions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    optimistic_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    submitted_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class CityConfigurationService(Base):
    __tablename__ = "city_configuration_services"

    configuration_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("city_configuration_versions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    service_type: Mapped[ServiceType] = mapped_column(
        bounded_enum(ServiceType, "city_service_type", 20), primary_key=True
    )
    operator_city_assignment_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("operator_city_assignments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # The current PricingRule is the only component already owned by an
    # implemented domain.  Phase 14 replaces this compatibility reference with
    # the complete tariff/fee policy bundle without rewriting old rides.
    tariff_version_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("pricing_rules.id", ondelete="RESTRICT"), nullable=True
    )
    operator_fee_policy_version_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("operator_fee_policies.id", ondelete="RESTRICT"),
        nullable=True,
    )
    scheduling_policy_version_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("scheduling_policies.id", ondelete="RESTRICT"),
        nullable=True,
    )
    payment_capability_version_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("payment_capability_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CityReadinessCheck(Base):
    __tablename__ = "city_readiness_checks"
    __table_args__ = (
        UniqueConstraint(
            "configuration_version_id",
            "gate_code",
            name="uq_city_readiness_checks_configuration_gate",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    configuration_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("city_configuration_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gate_code: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[ReadinessStatus] = mapped_column(
        bounded_enum(ReadinessStatus, "city_readiness_status", 16),
        nullable=False,
        default=ReadinessStatus.PENDING,
        index=True,
    )
    non_secret_evidence_reference: Mapped[str | None] = mapped_column(String(240), nullable=True)
    decided_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
