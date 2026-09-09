"""Add immutable published fixed routes and route-scoped rides.

Revision ID: 20260827_0037
Revises: 20260824_0036
Create Date: 2026-08-27
"""

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql


revision = "20260827_0037"
down_revision = "20260824_0036"
branch_labels = None
depends_on = None


def constrained_values(name: str, column: str, values: tuple[str, ...]) -> sa.CheckConstraint:
    allowed = ", ".join(f"'{value}'" for value in values)
    return sa.CheckConstraint(f"{column} IN ({allowed})", name=name)


def upgrade() -> None:
    op.create_table(
        "fixed_routes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("retired_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        constrained_values("fixed_route_status", "status", ("ACTIVE", "RETIRED")),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["operator_id"], ["operators.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["retired_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("city_id", "operator_id", "code", name="uq_fixed_route_scope_code"),
    )
    op.create_index("ix_fixed_routes_city_id", "fixed_routes", ["city_id"])
    op.create_index("ix_fixed_routes_operator_id", "fixed_routes", ["operator_id"])
    op.create_index("ix_fixed_routes_status", "fixed_routes", ["status"])

    op.create_table(
        "fixed_route_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fixed_route_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("localized_name", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "localized_description",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("optimistic_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submitted_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        constrained_values(
            "fixed_route_publication_status",
            "status",
            ("DRAFT", "IN_REVIEW", "PUBLISHED", "RETIRED"),
        ),
        sa.CheckConstraint(
            "effective_until IS NULL OR effective_until > effective_from",
            name="fixed_route_version_effective_range",
        ),
        sa.CheckConstraint("optimistic_version >= 1", name="fixed_route_version_optimistic_version"),
        sa.ForeignKeyConstraint(["fixed_route_id"], ["fixed_routes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["submitted_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["published_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["retired_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fixed_route_id", "version", name="uq_fixed_route_version_route_version"),
    )
    op.create_index("ix_fixed_route_versions_fixed_route_id", "fixed_route_versions", ["fixed_route_id"])
    op.create_index("ix_fixed_route_versions_status", "fixed_route_versions", ["status"])
    op.execute(
        "ALTER TABLE fixed_route_versions ADD CONSTRAINT ex_fixed_route_versions_published_overlap "
        "EXCLUDE USING gist (fixed_route_id WITH =, tstzrange(effective_from, "
        "COALESCE(effective_until, 'infinity'::timestamptz), '[)') WITH &&) "
        "WHERE (status = 'PUBLISHED')"
    )

    op.create_table(
        "fixed_route_directions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("route_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("direction_code", sa.String(length=16), nullable=False),
        sa.Column("start_location_name", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("finish_location_name", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("start_point", Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False),
        sa.Column("finish_point", Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False),
        sa.Column(
            "static_geometry",
            Geography(geometry_type="LINESTRING", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("flat_fare_policy_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        constrained_values("fixed_route_direction_code", "direction_code", ("OUTBOUND", "INBOUND")),
        sa.CheckConstraint(
            "start_location_name <> '{}'::jsonb AND finish_location_name <> '{}'::jsonb",
            name="fixed_route_direction_named_endpoints",
        ),
        sa.ForeignKeyConstraint(["route_version_id"], ["fixed_route_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["flat_fare_policy_version_id"],
            ["pricing_rules.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "route_version_id",
            "direction_code",
            name="uq_fixed_route_direction_version_code",
        ),
    )
    op.create_index("ix_fixed_route_directions_route_version_id", "fixed_route_directions", ["route_version_id"])
    op.create_index(
        "ix_fixed_route_directions_flat_fare_policy_version_id",
        "fixed_route_directions",
        ["flat_fare_policy_version_id"],
    )
    op.create_index(
        "ix_fixed_route_directions_start_point_gist",
        "fixed_route_directions",
        ["start_point"],
        postgresql_using="gist",
    )
    op.create_index(
        "ix_fixed_route_directions_finish_point_gist",
        "fixed_route_directions",
        ["finish_point"],
        postgresql_using="gist",
    )
    op.create_index(
        "ix_fixed_route_directions_static_geometry_gist",
        "fixed_route_directions",
        ["static_geometry"],
        postgresql_using="gist",
    )

    # A complete-direction tariff belongs to one immutable direction version.
    # DRAFT/IN_REVIEW rules may remain temporarily unbound so pricing review and
    # route drafting can happen in either order; activation requires the link.
    op.add_column(
        "pricing_rules",
        sa.Column(
            "fixed_route_direction_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_pricing_rules_fixed_route_direction_id",
        "pricing_rules",
        "fixed_route_directions",
        ["fixed_route_direction_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_pricing_rule_fixed_route_direction",
        "pricing_rules",
        ["fixed_route_direction_id"],
    )
    op.create_index(
        "ix_pricing_rules_fixed_route_direction_id",
        "pricing_rules",
        ["fixed_route_direction_id"],
    )
    op.create_check_constraint(
        "ck_pricing_rule_fixed_route_scope",
        "pricing_rules",
        "(service_type = 'ON_DEMAND' AND fixed_route_direction_id IS NULL) OR "
        "(service_type = 'FIXED_ROUTE' AND (fixed_route_direction_id IS NOT NULL "
        "OR status::text IN ('DRAFT', 'IN_REVIEW')))",
    )
    op.execute(
        "ALTER TABLE pricing_rules DROP CONSTRAINT "
        "ex_pricing_rules_active_scope_overlap"
    )
    op.execute(
        "ALTER TABLE pricing_rules ADD CONSTRAINT ex_pricing_rules_active_scope_overlap "
        "EXCLUDE USING gist (city_id WITH =, operator_id WITH =, service_type WITH =, "
        "booking_type WITH =, (COALESCE(fixed_route_direction_id, "
        "'00000000-0000-0000-0000-000000000000'::uuid)) WITH =, "
        "tstzrange(effective_from, COALESCE(effective_until, "
        "'infinity'::timestamptz), '[)') WITH &&) WHERE (status = 'ACTIVE')"
    )

    op.create_table(
        "fixed_route_stops",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("direction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("localized_name", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("point", Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False),
        sa.CheckConstraint("sequence >= 1", name="fixed_route_stop_positive_sequence"),
        sa.CheckConstraint("localized_name <> '{}'::jsonb", name="fixed_route_stop_localized_name"),
        sa.ForeignKeyConstraint(["direction_id"], ["fixed_route_directions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("direction_id", "sequence", name="uq_fixed_route_stop_direction_sequence"),
    )
    op.create_index("ix_fixed_route_stops_direction_id", "fixed_route_stops", ["direction_id"])
    op.create_index(
        "ix_fixed_route_stops_point_gist",
        "fixed_route_stops",
        ["point"],
        postgresql_using="gist",
    )

    op.create_table(
        "city_configuration_routes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("configuration_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fixed_route_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("immediate_booking_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("scheduled_booking_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.CheckConstraint(
            "immediate_booking_enabled OR scheduled_booking_enabled",
            name="city_configuration_route_booking_enabled",
        ),
        sa.ForeignKeyConstraint(
            ["configuration_version_id"],
            ["city_configuration_versions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["fixed_route_version_id"],
            ["fixed_route_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "configuration_version_id",
            "fixed_route_version_id",
            name="uq_city_configuration_route_version",
        ),
    )
    op.create_index(
        "ix_city_configuration_routes_configuration_version_id",
        "city_configuration_routes",
        ["configuration_version_id"],
    )
    op.create_index(
        "ix_city_configuration_routes_fixed_route_version_id",
        "city_configuration_routes",
        ["fixed_route_version_id"],
    )

    op.add_column(
        "rides",
        sa.Column("service_type", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "rides",
        sa.Column("fixed_route_direction_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute("UPDATE rides SET service_type = 'ON_DEMAND'")
    op.alter_column("rides", "service_type", nullable=False)
    op.create_check_constraint(
        "ride_service_type",
        "rides",
        "service_type IN ('ON_DEMAND', 'FIXED_ROUTE')",
    )
    op.create_check_constraint(
        "ride_fixed_route_consistency",
        "rides",
        "(service_type = 'ON_DEMAND' AND fixed_route_direction_id IS NULL) OR "
        "(service_type = 'FIXED_ROUTE' AND fixed_route_direction_id IS NOT NULL)",
    )
    op.create_foreign_key(
        "fk_rides_fixed_route_direction_id_fixed_route_directions",
        "rides",
        "fixed_route_directions",
        ["fixed_route_direction_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_rides_service_type", "rides", ["service_type"])
    op.create_index("ix_rides_fixed_route_direction_id", "rides", ["fixed_route_direction_id"])


def downgrade() -> None:
    op.drop_index("ix_rides_fixed_route_direction_id", table_name="rides")
    op.drop_index("ix_rides_service_type", table_name="rides")
    op.drop_constraint(
        "fk_rides_fixed_route_direction_id_fixed_route_directions",
        "rides",
        type_="foreignkey",
    )
    op.drop_constraint("ride_fixed_route_consistency", "rides", type_="check")
    op.drop_constraint("ride_service_type", "rides", type_="check")
    op.drop_column("rides", "fixed_route_direction_id")
    op.drop_column("rides", "service_type")

    op.drop_table("city_configuration_routes")
    op.drop_table("fixed_route_stops")
    op.execute(
        "ALTER TABLE pricing_rules DROP CONSTRAINT "
        "ex_pricing_rules_active_scope_overlap"
    )
    op.drop_constraint(
        "ck_pricing_rule_fixed_route_scope",
        "pricing_rules",
        type_="check",
    )
    op.drop_index(
        "ix_pricing_rules_fixed_route_direction_id",
        table_name="pricing_rules",
    )
    op.drop_constraint(
        "uq_pricing_rule_fixed_route_direction",
        "pricing_rules",
        type_="unique",
    )
    op.drop_constraint(
        "fk_pricing_rules_fixed_route_direction_id",
        "pricing_rules",
        type_="foreignkey",
    )
    op.drop_column("pricing_rules", "fixed_route_direction_id")
    op.execute(
        "ALTER TABLE pricing_rules ADD CONSTRAINT ex_pricing_rules_active_scope_overlap "
        "EXCLUDE USING gist (city_id WITH =, operator_id WITH =, service_type WITH =, "
        "booking_type WITH =, tstzrange(effective_from, COALESCE(effective_until, "
        "'infinity'::timestamptz), '[)') WITH &&) WHERE (status = 'ACTIVE')"
    )
    op.drop_table("fixed_route_directions")
    op.execute(
        "ALTER TABLE fixed_route_versions DROP CONSTRAINT "
        "ex_fixed_route_versions_published_overlap"
    )
    op.drop_table("fixed_route_versions")
    op.drop_table("fixed_routes")
