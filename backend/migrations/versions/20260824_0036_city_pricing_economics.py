"""Add scoped city tariffs, operator economics, and immutable ride snapshots.

Revision ID: 20260824_0036
Revises: 20260824_0035
Create Date: 2026-08-24
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260824_0036"
down_revision = "20260824_0035"
branch_labels = None
depends_on = None


LEGACY_OPERATOR_ID = "10000000-0000-4000-8000-000000000002"
LEGACY_CITY_ID = "10000000-0000-4000-8000-000000000003"
LEGACY_CONFIGURATION_ID = "10000000-0000-4000-8000-000000000006"
LEGACY_ZERO_FEE_POLICY_ID = "10000000-0000-4000-8000-000000000009"


def constrained_values(name: str, column: str, values: tuple[str, ...]) -> sa.CheckConstraint:
    allowed = ", ".join(f"'{value}'" for value in values)
    return sa.CheckConstraint(f"{column} IN ({allowed})", name=name)


def upgrade() -> None:
    # Preserve the original native enum and compatibility value while adding the
    # reviewed national lifecycle. New values are not used inside this migration
    # transaction; API writes begin only after the migration commits.
    for value in ("DRAFT", "IN_REVIEW", "REPLACED"):
        op.execute(f"ALTER TYPE pricing_rule_status ADD VALUE IF NOT EXISTS '{value}'")

    op.add_column("pricing_rules", sa.Column("operator_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("pricing_rules", sa.Column("service_type", sa.String(length=20), nullable=True))
    op.add_column("pricing_rules", sa.Column("booking_type", sa.String(length=16), nullable=True))
    op.add_column("pricing_rules", sa.Column("optimistic_version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("pricing_rules", sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("pricing_rules", sa.Column("submitted_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("pricing_rules", sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("pricing_rules", sa.Column("activated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("pricing_rules", sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "pricing_rules",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.execute(
        sa.text(
            "UPDATE pricing_rules SET operator_id = CAST(:operator_id AS uuid), "
            "service_type = 'ON_DEMAND', booking_type = 'IMMEDIATE'"
        ).bindparams(operator_id=LEGACY_OPERATOR_ID)
    )
    op.alter_column("pricing_rules", "operator_id", nullable=False)
    op.alter_column("pricing_rules", "service_type", nullable=False)
    op.alter_column("pricing_rules", "booking_type", nullable=False)
    op.create_foreign_key(
        "fk_pricing_rules_operator_id_operators",
        "pricing_rules",
        "operators",
        ["operator_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    for column, constraint in (
        ("created_by_user_id", "fk_pricing_rules_created_by_user_id_users"),
        ("submitted_by_user_id", "fk_pricing_rules_submitted_by_user_id_users"),
        ("activated_by_user_id", "fk_pricing_rules_activated_by_user_id_users"),
    ):
        op.create_foreign_key(
            constraint,
            "pricing_rules",
            "users",
            [column],
            ["id"],
            ondelete="RESTRICT",
        )
    op.create_check_constraint(
        "ck_pricing_rules_service_type",
        "pricing_rules",
        "service_type IN ('ON_DEMAND', 'FIXED_ROUTE', 'SCHEDULED')",
    )
    op.create_check_constraint(
        "ck_pricing_rules_booking_type",
        "pricing_rules",
        "booking_type IN ('IMMEDIATE', 'SCHEDULED')",
    )
    # Legacy API activation already closed earlier schedules, but direct local
    # fixtures may have produced overlaps. Normalize only policy ranges/status;
    # immutable ride quotes and fare/payment records remain untouched.
    op.execute(
        """
        WITH duplicate_starts AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY city_id, operator_id, service_type, booking_type, effective_from
                       ORDER BY created_at DESC, id DESC
                   ) AS position
            FROM pricing_rules
            WHERE status = 'ACTIVE'
        )
        UPDATE pricing_rules AS rule
        SET status = 'INACTIVE'
        FROM duplicate_starts AS duplicate
        WHERE rule.id = duplicate.id AND duplicate.position > 1
        """
    )
    op.execute(
        """
        WITH ordered AS (
            SELECT id,
                   lead(effective_from) OVER (
                       PARTITION BY city_id, operator_id, service_type, booking_type
                       ORDER BY effective_from, id
                   ) AS next_effective_from
            FROM pricing_rules
            WHERE status = 'ACTIVE'
        )
        UPDATE pricing_rules AS rule
        SET effective_until = ordered.next_effective_from
        FROM ordered
        WHERE rule.id = ordered.id
          AND ordered.next_effective_from IS NOT NULL
          AND (rule.effective_until IS NULL OR rule.effective_until > ordered.next_effective_from)
        """
    )
    op.create_check_constraint(
        "ck_pricing_rule_effective_range",
        "pricing_rules",
        "effective_until IS NULL OR effective_until > effective_from",
    )
    op.create_check_constraint(
        "ck_pricing_rule_optimistic_version",
        "pricing_rules",
        "optimistic_version >= 1",
    )
    # The project-wide SQLAlchemy naming convention names the original
    # column-level unique constraint ``uq_pricing_rules_version``.
    op.drop_constraint("uq_pricing_rules_version", "pricing_rules", type_="unique")
    op.create_unique_constraint(
        "uq_pricing_rule_scope_version",
        "pricing_rules",
        ["city_id", "operator_id", "service_type", "booking_type", "version"],
    )
    op.create_index("ix_pricing_rules_operator_id", "pricing_rules", ["operator_id"])
    op.create_index(
        "ix_pricing_rules_scope_status_effective",
        "pricing_rules",
        ["city_id", "operator_id", "service_type", "booking_type", "status", "effective_from"],
    )
    op.execute(
        "ALTER TABLE pricing_rules ADD CONSTRAINT ex_pricing_rules_active_scope_overlap "
        "EXCLUDE USING gist (city_id WITH =, operator_id WITH =, service_type WITH =, "
        "booking_type WITH =, tstzrange(effective_from, "
        "COALESCE(effective_until, 'infinity'::timestamptz), '[)') WITH &&) "
        "WHERE (status = 'ACTIVE')"
    )

    op.create_table(
        "operator_fee_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_type", sa.String(length=20), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("calculation_mode", sa.String(length=40), nullable=False),
        sa.Column("funding_mode", sa.String(length=32), nullable=False),
        sa.Column("eligible_base_code", sa.String(length=40), nullable=False),
        sa.Column("percentage_rate", sa.Numeric(7, 4), nullable=True),
        sa.Column("flat_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("rounding_rule", sa.String(length=20), nullable=False),
        sa.Column("minimum_driver_net", sa.Numeric(12, 2), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("optimistic_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("submitted_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        constrained_values(
            "ck_operator_fee_policies_service_type",
            "service_type",
            ("ON_DEMAND", "FIXED_ROUTE", "SCHEDULED"),
        ),
        constrained_values(
            "ck_operator_fee_policies_status",
            "status",
            ("DRAFT", "IN_REVIEW", "ACTIVE", "REPLACED"),
        ),
        constrained_values(
            "ck_operator_fee_policies_calculation_mode",
            "calculation_mode",
            ("PERCENTAGE_OF_TRANSPORT_FARE", "FLAT_PER_COMPLETED_BOOKING"),
        ),
        constrained_values(
            "ck_operator_fee_policies_funding_mode",
            "funding_mode",
            ("DRIVER_SETTLEMENT_DEDUCTION", "PASSENGER_SURCHARGE"),
        ),
        constrained_values(
            "ck_operator_fee_policies_rounding_rule",
            "rounding_rule",
            ("HALF_UP_0_01",),
        ),
        sa.CheckConstraint(
            "effective_until IS NULL OR effective_until > effective_from",
            name="ck_operator_fee_policy_effective_range",
        ),
        sa.CheckConstraint(
            "(calculation_mode = 'PERCENTAGE_OF_TRANSPORT_FARE' AND percentage_rate IS NOT NULL "
            "AND percentage_rate >= 0 AND percentage_rate < 100 AND flat_amount IS NULL) OR "
            "(calculation_mode = 'FLAT_PER_COMPLETED_BOOKING' AND flat_amount IS NOT NULL "
            "AND flat_amount >= 0 AND percentage_rate IS NULL)",
            name="ck_operator_fee_policy_mode_values",
        ),
        sa.CheckConstraint("minimum_driver_net >= 0", name="ck_operator_fee_policy_minimum_driver_net"),
        sa.CheckConstraint("optimistic_version >= 1", name="ck_operator_fee_policy_optimistic_version"),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["operator_id"], ["operators.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["submitted_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["activated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_operator_fee_policies"),
        sa.UniqueConstraint(
            "city_id",
            "operator_id",
            "service_type",
            "version",
            name="uq_operator_fee_policy_scope_version",
        ),
    )
    op.create_index("ix_operator_fee_policies_city_id", "operator_fee_policies", ["city_id"])
    op.create_index("ix_operator_fee_policies_operator_id", "operator_fee_policies", ["operator_id"])
    op.create_index("ix_operator_fee_policies_status", "operator_fee_policies", ["status"])
    op.execute(
        "ALTER TABLE operator_fee_policies ADD CONSTRAINT ex_operator_fee_policies_active_scope_overlap "
        "EXCLUDE USING gist (city_id WITH =, operator_id WITH =, service_type WITH =, "
        "tstzrange(effective_from, COALESCE(effective_until, 'infinity'::timestamptz), '[)') WITH &&) "
        "WHERE (status = 'ACTIVE')"
    )

    op.create_table(
        "scheduling_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_type", sa.String(length=20), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("surcharge_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("beneficiary", sa.String(length=16), nullable=False),
        sa.Column("collection_timing_code", sa.String(length=40), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("optimistic_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("submitted_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        constrained_values(
            "ck_scheduling_policies_service_type",
            "service_type",
            ("ON_DEMAND", "FIXED_ROUTE", "SCHEDULED"),
        ),
        constrained_values(
            "ck_scheduling_policies_status",
            "status",
            ("DRAFT", "IN_REVIEW", "ACTIVE", "REPLACED"),
        ),
        constrained_values(
            "ck_scheduling_policies_beneficiary",
            "beneficiary",
            ("OPERATOR", "DRIVER"),
        ),
        sa.CheckConstraint(
            "effective_until IS NULL OR effective_until > effective_from",
            name="ck_scheduling_policy_effective_range",
        ),
        sa.CheckConstraint("surcharge_amount >= 0", name="ck_scheduling_policy_surcharge_nonnegative"),
        sa.CheckConstraint("optimistic_version >= 1", name="ck_scheduling_policy_optimistic_version"),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["operator_id"], ["operators.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["submitted_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["activated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_scheduling_policies"),
        sa.UniqueConstraint(
            "city_id",
            "operator_id",
            "service_type",
            "version",
            name="uq_scheduling_policy_scope_version",
        ),
    )
    op.create_index("ix_scheduling_policies_city_id", "scheduling_policies", ["city_id"])
    op.create_index("ix_scheduling_policies_operator_id", "scheduling_policies", ["operator_id"])
    op.create_index("ix_scheduling_policies_status", "scheduling_policies", ["status"])
    op.execute(
        "ALTER TABLE scheduling_policies ADD CONSTRAINT ex_scheduling_policies_active_scope_overlap "
        "EXCLUDE USING gist (city_id WITH =, operator_id WITH =, service_type WITH =, "
        "tstzrange(effective_from, COALESCE(effective_until, 'infinity'::timestamptz), '[)') WITH &&) "
        "WHERE (status = 'ACTIVE')"
    )

    # Explicit zero fee preserves existing passenger totals and driver earnings.
    op.execute(
        sa.text(
            """
            INSERT INTO operator_fee_policies (
                id, city_id, operator_id, service_type, version, status,
                calculation_mode, funding_mode, eligible_base_code,
                percentage_rate, flat_amount, currency, rounding_rule,
                minimum_driver_net, effective_from, activated_at
            ) VALUES (
                CAST(:policy_id AS uuid), CAST(:city_id AS uuid), CAST(:operator_id AS uuid),
                'ON_DEMAND', 'legacy-zero-fee-v1', 'ACTIVE',
                'FLAT_PER_COMPLETED_BOOKING', 'DRIVER_SETTLEMENT_DEDUCTION',
                'TRANSPORT_FARE', NULL, 0.00, 'MAD', 'HALF_UP_0_01', 0.00,
                '2000-01-01 00:00:00+00', now()
            )
            """
        ).bindparams(
            policy_id=LEGACY_ZERO_FEE_POLICY_ID,
            city_id=LEGACY_CITY_ID,
            operator_id=LEGACY_OPERATOR_ID,
        )
    )

    op.add_column(
        "city_configuration_services",
        sa.Column("operator_fee_policy_version_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "city_configuration_services",
        sa.Column("scheduling_policy_version_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_config_service_operator_fee_policy",
        "city_configuration_services",
        "operator_fee_policies",
        ["operator_fee_policy_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_config_service_scheduling_policy",
        "city_configuration_services",
        "scheduling_policies",
        ["scheduling_policy_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.execute(
        sa.text(
            "UPDATE city_configuration_services SET operator_fee_policy_version_id = CAST(:policy_id AS uuid) "
            "WHERE configuration_version_id = CAST(:configuration_id AS uuid) AND service_type = 'ON_DEMAND'"
        ).bindparams(policy_id=LEGACY_ZERO_FEE_POLICY_ID, configuration_id=LEGACY_CONFIGURATION_ID)
    )

    op.create_table(
        "ride_financial_snapshots",
        sa.Column("ride_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pricing_rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operator_fee_policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scheduling_policy_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("booking_type", sa.String(length=16), nullable=False),
        sa.Column("operator_fee_calculation_mode", sa.String(length=40), nullable=False),
        sa.Column("operator_fee_funding_mode", sa.String(length=32), nullable=False),
        sa.Column("scheduling_surcharge_beneficiary", sa.String(length=16), nullable=True),
        sa.Column("transport_fare_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("scheduling_surcharge_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("operator_fee_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("passenger_total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("driver_gross_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("driver_fee_deduction_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("driver_net_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("operator_allocation_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        constrained_values(
            "ck_ride_financial_snapshots_booking_type",
            "booking_type",
            ("IMMEDIATE", "SCHEDULED"),
        ),
        constrained_values(
            "ck_ride_financial_snapshots_fee_calculation_mode",
            "operator_fee_calculation_mode",
            ("PERCENTAGE_OF_TRANSPORT_FARE", "FLAT_PER_COMPLETED_BOOKING"),
        ),
        constrained_values(
            "ck_ride_financial_snapshots_fee_funding_mode",
            "operator_fee_funding_mode",
            ("DRIVER_SETTLEMENT_DEDUCTION", "PASSENGER_SURCHARGE"),
        ),
        constrained_values(
            "ck_ride_financial_snapshots_scheduling_beneficiary",
            "scheduling_surcharge_beneficiary",
            ("OPERATOR", "DRIVER"),
        ),
        sa.CheckConstraint(
            "transport_fare_amount >= 0 AND scheduling_surcharge_amount >= 0 "
            "AND operator_fee_amount >= 0 AND passenger_total_amount >= 0 "
            "AND driver_gross_amount >= 0 AND driver_fee_deduction_amount >= 0 "
            "AND driver_net_amount >= 0 AND operator_allocation_amount >= 0",
            name="ck_ride_financial_snapshot_nonnegative",
        ),
        sa.CheckConstraint(
            "driver_net_amount = driver_gross_amount - driver_fee_deduction_amount",
            name="ck_ride_financial_snapshot_driver_reconciles",
        ),
        sa.CheckConstraint(
            "(booking_type = 'IMMEDIATE' AND scheduling_policy_id IS NULL "
            "AND scheduling_surcharge_beneficiary IS NULL AND scheduling_surcharge_amount = 0) "
            "OR (booking_type = 'SCHEDULED' AND scheduling_policy_id IS NOT NULL "
            "AND scheduling_surcharge_beneficiary IS NOT NULL)",
            name="ck_ride_financial_snapshot_booking_consistent",
        ),
        sa.CheckConstraint(
            "passenger_total_amount = transport_fare_amount + scheduling_surcharge_amount + "
            "CASE WHEN operator_fee_funding_mode = 'PASSENGER_SURCHARGE' "
            "THEN operator_fee_amount ELSE 0 END",
            name="ck_ride_financial_snapshot_passenger_reconciles",
        ),
        sa.CheckConstraint(
            "driver_gross_amount = transport_fare_amount + "
            "CASE WHEN scheduling_surcharge_beneficiary = 'DRIVER' "
            "THEN scheduling_surcharge_amount ELSE 0 END",
            name="ck_ride_financial_snapshot_driver_gross_reconciles",
        ),
        sa.CheckConstraint(
            "driver_fee_deduction_amount = CASE WHEN operator_fee_funding_mode = "
            "'DRIVER_SETTLEMENT_DEDUCTION' THEN operator_fee_amount ELSE 0 END",
            name="ck_ride_financial_snapshot_driver_fee_reconciles",
        ),
        sa.CheckConstraint(
            "operator_allocation_amount = operator_fee_amount + "
            "CASE WHEN scheduling_surcharge_beneficiary = 'OPERATOR' "
            "THEN scheduling_surcharge_amount ELSE 0 END",
            name="ck_ride_financial_snapshot_operator_reconciles",
        ),
        sa.ForeignKeyConstraint(["ride_id"], ["rides.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pricing_rule_id"], ["pricing_rules.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["operator_fee_policy_id"], ["operator_fee_policies.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["scheduling_policy_id"], ["scheduling_policies.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("ride_id", name="pk_ride_financial_snapshots"),
    )

    op.add_column("driver_earnings", sa.Column("transport_fare_amount", sa.Numeric(12, 2), nullable=True))
    op.add_column(
        "driver_earnings",
        sa.Column("scheduling_surcharge_amount", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
    )
    op.add_column(
        "driver_earnings",
        sa.Column("operator_fee_amount", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
    )
    op.add_column(
        "driver_earnings",
        sa.Column("operator_allocation_amount", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
    )
    op.add_column(
        "driver_earnings",
        sa.Column("operator_fee_policy_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "driver_earnings",
        sa.Column("scheduling_policy_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "driver_earnings",
        sa.Column("operator_fee_funding_mode", sa.String(length=32), nullable=True),
    )
    op.execute("UPDATE driver_earnings SET transport_fare_amount = gross_amount")
    op.alter_column("driver_earnings", "transport_fare_amount", nullable=False)
    op.create_foreign_key(
        "fk_driver_earnings_operator_fee_policy",
        "driver_earnings",
        "operator_fee_policies",
        ["operator_fee_policy_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_driver_earnings_scheduling_policy",
        "driver_earnings",
        "scheduling_policies",
        ["scheduling_policy_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_driver_earnings_operator_fee_funding_mode",
        "driver_earnings",
        "operator_fee_funding_mode IS NULL OR operator_fee_funding_mode IN "
        "('DRIVER_SETTLEMENT_DEDUCTION', 'PASSENGER_SURCHARGE')",
    )
    op.create_check_constraint(
        "ck_driver_earning_components_nonnegative",
        "driver_earnings",
        "transport_fare_amount >= 0 AND scheduling_surcharge_amount >= 0 "
        "AND operator_fee_amount >= 0 AND operator_allocation_amount >= 0",
    )
    op.create_check_constraint(
        "ck_driver_earning_net_reconciles",
        "driver_earnings",
        "net_amount = gross_amount - fee_amount + adjustment_amount",
    )
    op.create_check_constraint(
        "ck_driver_earning_fee_reconciles",
        "driver_earnings",
        "operator_fee_funding_mode IS NULL OR "
        "(operator_fee_funding_mode = 'DRIVER_SETTLEMENT_DEDUCTION' "
        "AND fee_amount = operator_fee_amount) OR "
        "(operator_fee_funding_mode = 'PASSENGER_SURCHARGE' AND fee_amount = 0)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_driver_earning_fee_reconciles", "driver_earnings", type_="check")
    op.drop_constraint("ck_driver_earning_net_reconciles", "driver_earnings", type_="check")
    op.drop_constraint("ck_driver_earning_components_nonnegative", "driver_earnings", type_="check")
    op.drop_constraint("ck_driver_earnings_operator_fee_funding_mode", "driver_earnings", type_="check")
    op.drop_constraint("fk_driver_earnings_scheduling_policy", "driver_earnings", type_="foreignkey")
    op.drop_constraint("fk_driver_earnings_operator_fee_policy", "driver_earnings", type_="foreignkey")
    for column in (
        "operator_fee_funding_mode",
        "scheduling_policy_id",
        "operator_fee_policy_id",
        "operator_allocation_amount",
        "operator_fee_amount",
        "scheduling_surcharge_amount",
        "transport_fare_amount",
    ):
        op.drop_column("driver_earnings", column)

    op.drop_table("ride_financial_snapshots")
    op.drop_constraint("fk_config_service_scheduling_policy", "city_configuration_services", type_="foreignkey")
    op.drop_constraint("fk_config_service_operator_fee_policy", "city_configuration_services", type_="foreignkey")
    op.drop_column("city_configuration_services", "scheduling_policy_version_id")
    op.drop_column("city_configuration_services", "operator_fee_policy_version_id")
    op.drop_table("scheduling_policies")
    op.drop_table("operator_fee_policies")

    op.execute("ALTER TABLE pricing_rules DROP CONSTRAINT ex_pricing_rules_active_scope_overlap")
    op.drop_index("ix_pricing_rules_scope_status_effective", table_name="pricing_rules")
    op.drop_index("ix_pricing_rules_operator_id", table_name="pricing_rules")
    op.drop_constraint("uq_pricing_rule_scope_version", "pricing_rules", type_="unique")
    op.create_unique_constraint("uq_pricing_rules_version", "pricing_rules", ["version"])
    op.drop_constraint("ck_pricing_rule_optimistic_version", "pricing_rules", type_="check")
    op.drop_constraint("ck_pricing_rule_effective_range", "pricing_rules", type_="check")
    op.drop_constraint("ck_pricing_rules_booking_type", "pricing_rules", type_="check")
    op.drop_constraint("ck_pricing_rules_service_type", "pricing_rules", type_="check")
    for constraint in (
        "fk_pricing_rules_activated_by_user_id_users",
        "fk_pricing_rules_submitted_by_user_id_users",
        "fk_pricing_rules_created_by_user_id_users",
        "fk_pricing_rules_operator_id_operators",
    ):
        op.drop_constraint(constraint, "pricing_rules", type_="foreignkey")
    for column in (
        "updated_at",
        "activated_at",
        "activated_by_user_id",
        "submitted_at",
        "submitted_by_user_id",
        "created_by_user_id",
        "optimistic_version",
        "booking_type",
        "service_type",
        "operator_id",
    ):
        op.drop_column("pricing_rules", column)
