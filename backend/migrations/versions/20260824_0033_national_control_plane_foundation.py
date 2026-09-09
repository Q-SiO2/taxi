"""Add national market/city configuration and deterministic pilot ownership.

Revision ID: 20260824_0033
Revises: 20260824_0032
Create Date: 2026-08-24
"""

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql


revision = "20260824_0033"
down_revision = "20260824_0032"
branch_labels = None
depends_on = None


MARKET_ID = "10000000-0000-4000-8000-000000000001"
OPERATOR_ID = "10000000-0000-4000-8000-000000000002"
CITY_ID = "10000000-0000-4000-8000-000000000003"
SERVICE_AREA_ID = "10000000-0000-4000-8000-000000000004"
ASSIGNMENT_ID = "10000000-0000-4000-8000-000000000005"
CONFIGURATION_ID = "10000000-0000-4000-8000-000000000006"


def text_enum(name: str, *values: str, length: int = 32) -> sa.Enum:
    return sa.Enum(
        *values,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=length,
    )


def upgrade() -> None:
    market_status = text_enum("market_status", "ACTIVE", "INACTIVE", length=16)
    operator_type = text_enum(
        "operator_type", "PLATFORM", "COOPERATIVE", "LOCAL_ENTITY", length=24
    )
    operator_status = text_enum("operator_status", "DRAFT", "ACTIVE", "INACTIVE", length=16)
    city_lifecycle = text_enum(
        "city_lifecycle_status",
        "DRAFT",
        "CONFIGURING",
        "PILOT",
        "ACTIVE",
        "PAUSED",
        "RETIRED",
        length=20,
    )
    service_type = text_enum(
        "city_service_type", "ON_DEMAND", "FIXED_ROUTE", "SCHEDULED", length=20
    )
    assignment_status = text_enum(
        "operator_assignment_status", "ACTIVE", "RETIRED", length=16
    )
    service_area_status = text_enum(
        "service_area_status",
        "DRAFT",
        "IN_REVIEW",
        "APPROVED",
        "ACTIVE",
        "REPLACED",
        length=16,
    )
    configuration_status = text_enum(
        "city_configuration_status",
        "DRAFT",
        "IN_REVIEW",
        "APPROVED",
        "ACTIVE",
        "REPLACED",
        length=16,
    )
    readiness_status = text_enum(
        "city_readiness_status", "PENDING", "PASSED", "FAILED", length=16
    )

    op.create_table(
        "markets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=8), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("default_currency", sa.String(length=3), nullable=False),
        sa.Column("status", market_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", name="pk_markets"),
        sa.UniqueConstraint("code", name="uq_markets_code"),
    )
    op.create_table(
        "operators",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("market_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cooperative_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("operator_type", operator_type, nullable=False),
        sa.Column("status", operator_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_operators_market_id_markets", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["cooperative_id"],
            ["cooperatives.id"],
            name="fk_operators_cooperative_id_cooperatives",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_operators"),
        sa.UniqueConstraint("cooperative_id", name="uq_operators_cooperative_id"),
    )
    op.create_index("ix_operators_market_id", "operators", ["market_id"])
    op.create_index("ix_operators_status", "operators", ["status"])

    # The active configuration FK is added after the version table to avoid a
    # circular create-order dependency.
    op.create_table(
        "cities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("market_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("localized_name", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("presentation_centroid", Geography(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("lifecycle_status", city_lifecycle, nullable=False),
        sa.Column("active_configuration_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_legacy_compatibility", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("optimistic_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("optimistic_version >= 1", name="ck_cities_city_optimistic_version_positive"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_cities_market_id_markets", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_cities"),
        sa.UniqueConstraint("market_id", "code", name="uq_cities_market_code"),
    )
    op.create_index("ix_cities_market_id", "cities", ["market_id"])
    op.create_index("ix_cities_lifecycle_status", "cities", ["lifecycle_status"])
    op.create_index(
        "ix_cities_presentation_centroid",
        "cities",
        ["presentation_centroid"],
        postgresql_using="gist",
    )

    op.create_table(
        "operator_city_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_type", service_type, nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", assignment_status, nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("retired_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "effective_until IS NULL OR effective_until > effective_from",
            name="ck_operator_assignment_effective_range",
        ),
        sa.ForeignKeyConstraint(
            ["operator_id"],
            ["operators.id"],
            name="fk_operator_city_assignments_operator_id_operators",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["city_id"],
            ["cities.id"],
            name="fk_operator_city_assignments_city_id_cities",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_operator_city_assignments_created_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["retired_by_user_id"],
            ["users.id"],
            name="fk_operator_city_assignments_retired_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_operator_city_assignments"),
    )
    op.create_index("ix_operator_city_assignments_operator_id", "operator_city_assignments", ["operator_id"])
    op.create_index("ix_operator_city_assignments_city_id", "operator_city_assignments", ["city_id"])
    op.create_index("ix_operator_city_assignments_service_type", "operator_city_assignments", ["service_type"])
    op.create_index("ix_operator_city_assignments_status", "operator_city_assignments", ["status"])

    # This database constraint is the final concurrency arbiter.  The service
    # also takes a scope advisory lock so conflicts return a stable 409 instead
    # of exposing a driver/constraint message.
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute(
        "ALTER TABLE operator_city_assignments ADD CONSTRAINT "
        "ex_operator_city_assignments_authority_overlap EXCLUDE USING gist "
        "(city_id WITH =, service_type WITH =, "
        "tstzrange(effective_from, COALESCE(effective_until, 'infinity'::timestamptz), '[)') WITH &&) "
        "WHERE (status = 'ACTIVE')"
    )

    op.create_table(
        "city_service_area_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("boundary", Geography(geometry_type="MULTIPOLYGON", srid=4326), nullable=False),
        sa.Column("status", service_area_status, nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("optimistic_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "effective_until IS NULL OR effective_until > effective_from",
            name="ck_service_area_effective_range",
        ),
        sa.CheckConstraint(
            "optimistic_version >= 1",
            name="ck_service_area_optimistic_version",
        ),
        sa.ForeignKeyConstraint(
            ["city_id"],
            ["cities.id"],
            name="fk_city_service_area_versions_city_id_cities",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_city_service_area_versions_created_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"],
            ["users.id"],
            name="fk_city_service_area_versions_reviewed_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_city_service_area_versions"),
        sa.UniqueConstraint("city_id", "version", name="uq_city_service_area_versions_city_version"),
    )
    op.create_index("ix_city_service_area_versions_city_id", "city_service_area_versions", ["city_id"])
    op.create_index("ix_city_service_area_versions_status", "city_service_area_versions", ["status"])
    op.create_index(
        "ix_city_service_area_versions_boundary",
        "city_service_area_versions",
        ["boundary"],
        postgresql_using="gist",
    )

    op.create_table(
        "city_configuration_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("status", configuration_status, nullable=False),
        sa.Column("service_area_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("optimistic_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("submitted_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "optimistic_version >= 1",
            name="ck_city_configuration_optimistic_version",
        ),
        sa.ForeignKeyConstraint(
            ["city_id"],
            ["cities.id"],
            name="fk_city_configuration_versions_city_id_cities",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["service_area_version_id"],
            ["city_service_area_versions.id"],
            name="fk_city_config_service_area",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_city_configuration_versions_created_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by_user_id"],
            ["users.id"],
            name="fk_city_configuration_versions_submitted_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_user_id"],
            ["users.id"],
            name="fk_city_configuration_versions_approved_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["activated_by_user_id"],
            ["users.id"],
            name="fk_city_configuration_versions_activated_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_city_configuration_versions"),
        sa.UniqueConstraint("city_id", "version", name="uq_city_configuration_versions_city_version"),
    )
    op.create_index("ix_city_configuration_versions_city_id", "city_configuration_versions", ["city_id"])
    op.create_index("ix_city_configuration_versions_status", "city_configuration_versions", ["status"])

    op.create_foreign_key(
        "fk_city_active_configuration",
        "cities",
        "city_configuration_versions",
        ["active_configuration_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_table(
        "city_configuration_services",
        sa.Column("configuration_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_type", service_type, nullable=False),
        sa.Column("operator_city_assignment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tariff_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(
            ["configuration_version_id"],
            ["city_configuration_versions.id"],
            name="fk_config_service_configuration",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["operator_city_assignment_id"],
            ["operator_city_assignments.id"],
            name="fk_config_service_assignment",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tariff_version_id"],
            ["pricing_rules.id"],
            name="fk_city_configuration_services_tariff_version_id_pricing_rules",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "configuration_version_id", "service_type", name="pk_city_configuration_services"
        ),
    )

    op.create_table(
        "city_readiness_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("configuration_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gate_code", sa.String(length=64), nullable=False),
        sa.Column("status", readiness_status, nullable=False),
        sa.Column("non_secret_evidence_reference", sa.String(length=240), nullable=True),
        sa.Column("decided_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["configuration_version_id"],
            ["city_configuration_versions.id"],
            name="fk_readiness_configuration",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["decided_by_user_id"],
            ["users.id"],
            name="fk_city_readiness_checks_decided_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_city_readiness_checks"),
        sa.UniqueConstraint(
            "configuration_version_id",
            "gate_code",
            name="uq_city_readiness_checks_configuration_gate",
        ),
    )
    op.create_index("ix_city_readiness_checks_configuration_version_id", "city_readiness_checks", ["configuration_version_id"])
    op.create_index("ix_city_readiness_checks_status", "city_readiness_checks", ["status"])

    # Deterministic, explicit compatibility scope.  No city is inferred from a
    # historical coordinate and no existing fare or ride amount is rewritten.
    op.execute(
        f"""
        INSERT INTO markets (id, code, name, default_currency, status)
        VALUES ('{MARKET_ID}', 'MA', 'Morocco', 'MAD', 'ACTIVE')
        """
    )
    op.execute(
        f"""
        INSERT INTO operators (id, market_id, name, operator_type, status)
        VALUES ('{OPERATOR_ID}', '{MARKET_ID}', 'TaxiMobile legacy pilot operator', 'PLATFORM', 'ACTIVE')
        """
    )
    op.execute(
        f"""
        INSERT INTO cities (
            id, market_id, code, localized_name, timezone,
            presentation_centroid, lifecycle_status, is_legacy_compatibility
        ) VALUES (
            '{CITY_ID}', '{MARKET_ID}', 'casablanca',
            '{{"en":"Casablanca","fr":"Casablanca","ar":"الدار البيضاء"}}'::jsonb,
            'Africa/Casablanca',
            ST_GeogFromText('SRID=4326;POINT(-7.5898 33.5731)'),
            'ACTIVE', true
        )
        """
    )
    op.execute(
        f"""
        INSERT INTO city_service_area_versions (
            id, city_id, version, boundary, status, effective_from
        ) VALUES (
            '{SERVICE_AREA_ID}', '{CITY_ID}', 'legacy-casablanca-v1',
            ST_GeogFromText(
                'SRID=4326;MULTIPOLYGON(((-7.9000 33.3000,-7.2000 33.3000,-7.2000 33.9000,-7.9000 33.9000,-7.9000 33.3000)))'
            ),
            'ACTIVE', '2000-01-01 00:00:00+00'
        )
        """
    )
    op.execute(
        f"""
        INSERT INTO operator_city_assignments (
            id, operator_id, city_id, service_type, effective_from, status
        ) VALUES (
            '{ASSIGNMENT_ID}', '{OPERATOR_ID}', '{CITY_ID}', 'ON_DEMAND',
            '2000-01-01 00:00:00+00', 'ACTIVE'
        )
        """
    )
    op.execute(
        f"""
        INSERT INTO city_configuration_versions (
            id, city_id, version, status, service_area_version_id, activated_at
        ) VALUES (
            '{CONFIGURATION_ID}', '{CITY_ID}', 'legacy-single-city-v1', 'ACTIVE',
            '{SERVICE_AREA_ID}', now()
        )
        """
    )
    op.execute(
        f"""
        INSERT INTO city_configuration_services (
            configuration_version_id, service_type, operator_city_assignment_id, enabled
        ) VALUES ('{CONFIGURATION_ID}', 'ON_DEMAND', '{ASSIGNMENT_ID}', true)
        """
    )
    op.execute(
        f"UPDATE cities SET active_configuration_version_id = '{CONFIGURATION_ID}' WHERE id = '{CITY_ID}'"
    )

    # Preserve every cooperative as a distinct draft operator candidate.  This
    # does not make it authoritative for Casablanca and does not grant any staff
    # access or cooperative membership.
    op.execute(
        f"""
        INSERT INTO operators (id, market_id, cooperative_id, name, operator_type, status)
        SELECT
            md5('taximobile-cooperative-operator:' || id::text)::uuid,
            '{MARKET_ID}'::uuid,
            id,
            name,
            'COOPERATIVE',
            'DRAFT'
        FROM cooperatives
        ON CONFLICT (cooperative_id) DO NOTHING
        """
    )

    op.add_column("pricing_rules", sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute(f"UPDATE pricing_rules SET city_id = '{CITY_ID}' WHERE city_id IS NULL")
    op.alter_column("pricing_rules", "city_id", nullable=False)
    op.create_foreign_key(
        "fk_pricing_rules_city_id_cities",
        "pricing_rules",
        "cities",
        ["city_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_pricing_rules_city_id", "pricing_rules", ["city_id"])

    op.add_column("rides", sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("rides", sa.Column("operator_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute(
        f"UPDATE rides SET city_id = '{CITY_ID}', operator_id = '{OPERATOR_ID}' "
        "WHERE city_id IS NULL OR operator_id IS NULL"
    )
    op.alter_column("rides", "city_id", nullable=False)
    op.alter_column("rides", "operator_id", nullable=False)
    op.create_foreign_key(
        "fk_rides_city_id_cities",
        "rides",
        "cities",
        ["city_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_rides_operator_id_operators",
        "rides",
        "operators",
        ["operator_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_rides_city_id", "rides", ["city_id"])
    op.create_index("ix_rides_operator_id", "rides", ["operator_id"])
    op.create_index("ix_rides_city_status_created_at", "rides", ["city_id", "status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_rides_city_status_created_at", table_name="rides")
    op.drop_index("ix_rides_operator_id", table_name="rides")
    op.drop_index("ix_rides_city_id", table_name="rides")
    op.drop_constraint("fk_rides_operator_id_operators", "rides", type_="foreignkey")
    op.drop_constraint("fk_rides_city_id_cities", "rides", type_="foreignkey")
    op.drop_column("rides", "operator_id")
    op.drop_column("rides", "city_id")

    op.drop_index("ix_pricing_rules_city_id", table_name="pricing_rules")
    op.drop_constraint("fk_pricing_rules_city_id_cities", "pricing_rules", type_="foreignkey")
    op.drop_column("pricing_rules", "city_id")

    op.drop_table("city_readiness_checks")
    op.drop_table("city_configuration_services")
    op.drop_constraint(
        "fk_city_active_configuration",
        "cities",
        type_="foreignkey",
    )
    op.drop_table("city_configuration_versions")
    op.drop_table("city_service_area_versions")
    op.drop_table("operator_city_assignments")
    op.drop_table("cities")
    op.drop_table("operators")
    op.drop_table("markets")
