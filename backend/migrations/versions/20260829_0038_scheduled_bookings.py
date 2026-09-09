"""Add the scheduled-booking reservation lifecycle.

Revision ID: 20260829_0038
Revises: 20260827_0037
Create Date: 2026-08-29
"""

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql


revision = "20260829_0038"
down_revision = "20260827_0037"
branch_labels = None
depends_on = None


def constrained_values(name: str, column: str, values: tuple[str, ...]) -> sa.CheckConstraint:
    allowed = ", ".join(f"'{value}'" for value in values)
    return sa.CheckConstraint(f"{column} IN ({allowed})", name=name)


def upgrade() -> None:
    # Phase 14 delivered the monetary allocation. Phase 16 makes this a complete
    # dispatch/cancellation policy. Defaults make already-authored draft rows
    # explicit and safe; an operator must still review/activate a version before
    # scheduled booking is enabled by a city configuration.
    policy_columns = (
        sa.Column("minimum_lead_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("maximum_horizon_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("offer_open_minutes_before", sa.Integer(), nullable=False, server_default="1440"),
        sa.Column("offer_response_seconds", sa.Integer(), nullable=False, server_default="120"),
        sa.Column("commitment_deadline_minutes_before", sa.Integer(), nullable=False, server_default="180"),
        sa.Column("handoff_minutes_before", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("protected_duration_minutes", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("conflict_buffer_before_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("conflict_buffer_after_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("passenger_cancel_cutoff_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("driver_cancel_cutoff_minutes", sa.Integer(), nullable=False, server_default="120"),
        sa.Column("surcharge_refund_mode", sa.String(length=40), nullable=False, server_default="FULL_BEFORE_CUTOFF"),
        sa.Column("fallback_matching_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    for column in policy_columns:
        op.add_column("scheduling_policies", column)
    op.create_check_constraint(
        "scheduling_policy_timing_bounds",
        "scheduling_policies",
        "minimum_lead_minutes >= 15 AND maximum_horizon_days BETWEEN 1 AND 365 "
        "AND offer_open_minutes_before > commitment_deadline_minutes_before "
        "AND commitment_deadline_minutes_before >= handoff_minutes_before "
        "AND handoff_minutes_before >= 5 AND offer_response_seconds BETWEEN 15 AND 3600 "
        "AND protected_duration_minutes BETWEEN 15 AND 1440 "
        "AND conflict_buffer_before_minutes BETWEEN 0 AND 1440 "
        "AND conflict_buffer_after_minutes BETWEEN 0 AND 1440 "
        "AND passenger_cancel_cutoff_minutes BETWEEN 0 AND 10080 "
        "AND driver_cancel_cutoff_minutes BETWEEN 0 AND 10080",
    )
    op.create_check_constraint(
        "scheduling_policy_refund_mode",
        "scheduling_policies",
        "surcharge_refund_mode IN ('ALWAYS_FULL', 'FULL_BEFORE_CUTOFF', 'NON_REFUNDABLE')",
    )

    op.create_table(
        "scheduled_bookings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("passenger_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_type", sa.String(length=20), nullable=False),
        sa.Column("fixed_route_direction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("city_timezone", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("pickup_point", Geography(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("destination_point", Geography(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("pickup_address", sa.String(length=500), nullable=True),
        sa.Column("destination_address", sa.String(length=500), nullable=True),
        sa.Column("passenger_note", sa.Text(), nullable=True),
        sa.Column("payment_method", sa.String(length=32), nullable=False),
        sa.Column("pricing_rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operator_fee_policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scheduling_policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transport_fare_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("scheduling_surcharge_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("operator_fee_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("passenger_total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("driver_gross_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("driver_fee_deduction_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("driver_net_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("operator_allocation_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("quote_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("policy_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("current_commitment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("live_ride_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("offering_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("handoff_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("live_ride_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unfulfilled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.String(length=120), nullable=True),
        sa.Column("cancellation_financial_outcome", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        constrained_values(
            "scheduled_booking_service_type", "service_type", ("ON_DEMAND", "FIXED_ROUTE")
        ),
        constrained_values(
            "scheduled_booking_status",
            "status",
            (
                "SCHEDULED", "OFFERING", "DRIVER_COMMITTED", "DISPATCH_HANDOFF",
                "LIVE_RIDE_CREATED", "UNFULFILLED", "CANCELLED",
            ),
        ),
        constrained_values(
            "scheduled_booking_payment_method",
            "payment_method",
            ("CASH", "MANUAL_TRANSFER", "CARD", "MOBILE_PAYMENT"),
        ),
        sa.CheckConstraint(
            "(service_type = 'ON_DEMAND' AND fixed_route_direction_id IS NULL) OR "
            "(service_type = 'FIXED_ROUTE' AND fixed_route_direction_id IS NOT NULL)",
            name="scheduled_booking_service_consistency",
        ),
        sa.CheckConstraint(
            "transport_fare_amount >= 0 AND scheduling_surcharge_amount >= 0 "
            "AND operator_fee_amount >= 0 AND passenger_total_amount >= 0 "
            "AND driver_gross_amount >= 0 AND driver_fee_deduction_amount >= 0 "
            "AND driver_net_amount >= 0 AND operator_allocation_amount >= 0",
            name="scheduled_booking_money_nonnegative",
        ),
        sa.CheckConstraint(
            "driver_net_amount = driver_gross_amount - driver_fee_deduction_amount",
            name="scheduled_booking_driver_reconciles",
        ),
        sa.CheckConstraint(
            "live_ride_id IS NULL OR status = 'LIVE_RIDE_CREATED'",
            name="scheduled_booking_live_ride_state",
        ),
        sa.CheckConstraint(
            "cancellation_financial_outcome IS NULL OR cancellation_financial_outcome IN "
            "('NO_CHARGE', 'SURCHARGE_RETAINED', 'REFUND_PENDING', 'REFUNDED')",
            name="scheduled_booking_cancellation_outcome",
        ),
        sa.ForeignKeyConstraint(["passenger_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["operator_id"], ["operators.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["fixed_route_direction_id"], ["fixed_route_directions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["pricing_rule_id"], ["pricing_rules.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["operator_fee_policy_id"], ["operator_fee_policies.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["scheduling_policy_id"], ["scheduling_policies.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_scheduled_bookings"),
        sa.UniqueConstraint("live_ride_id", name="uq_scheduled_bookings_live_ride"),
    )
    op.create_index("ix_scheduled_bookings_passenger_id", "scheduled_bookings", ["passenger_id"])
    op.create_index("ix_scheduled_bookings_city_status_time", "scheduled_bookings", ["city_id", "status", "scheduled_for"])

    op.create_table(
        "scheduled_booking_offers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("offered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decline_reason", sa.String(length=120), nullable=True),
        sa.Column("conflict_policy_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        constrained_values("scheduled_offer_status", "status", ("PENDING", "ACCEPTED", "DECLINED", "EXPIRED", "CANCELLED")),
        sa.CheckConstraint("expires_at > offered_at", name="scheduled_offer_expiry_after_offer"),
        sa.ForeignKeyConstraint(["booking_id"], ["scheduled_bookings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["driver_id"], ["driver_profiles.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_scheduled_booking_offers"),
        sa.UniqueConstraint("booking_id", "driver_id", name="uq_scheduled_offer_booking_driver"),
    )
    op.create_index("ix_scheduled_booking_offers_driver_status", "scheduled_booking_offers", ["driver_id", "status", "expires_at"])

    op.create_table(
        "scheduled_booking_commitments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("offer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("protected_window", postgresql.TSTZRANGE(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("release_reason", sa.String(length=120), nullable=True),
        constrained_values("scheduled_commitment_status", "status", ("ACTIVE", "RELEASED", "CANCELLED", "FULFILLED")),
        sa.ForeignKeyConstraint(["booking_id"], ["scheduled_bookings.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["offer_id"], ["scheduled_booking_offers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["driver_id"], ["driver_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_scheduled_booking_commitments"),
        sa.UniqueConstraint("booking_id", name="uq_scheduled_commitment_booking"),
        sa.UniqueConstraint("offer_id", name="uq_scheduled_commitment_offer"),
    )
    op.execute(
        "ALTER TABLE scheduled_booking_commitments ADD CONSTRAINT "
        "ex_scheduled_commitments_driver_window EXCLUDE USING gist "
        "(driver_id WITH =, protected_window WITH &&) WHERE (status = 'ACTIVE')"
    )
    op.create_index("ix_scheduled_commitments_driver_status", "scheduled_booking_commitments", ["driver_id", "status"])
    op.create_foreign_key(
        "fk_scheduled_bookings_current_commitment",
        "scheduled_bookings", "scheduled_booking_commitments",
        ["current_commitment_id"], ["id"], ondelete="RESTRICT",
    )

    op.create_table(
        "scheduled_booking_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("previous_status", sa.String(length=24), nullable=True),
        sa.Column("new_status", sa.String(length=24), nullable=False),
        sa.Column("controlled_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["booking_id"], ["scheduled_bookings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_scheduled_booking_events"),
    )
    op.create_index("ix_scheduled_booking_events_booking_created", "scheduled_booking_events", ["booking_id", "created_at"])

    op.create_table(
        "driver_scheduled_offer_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["driver_id"], ["driver_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_driver_scheduled_offer_preferences"),
        sa.UniqueConstraint("driver_id", "city_id", name="uq_driver_scheduled_preference_city"),
    )
    op.create_index("ix_driver_scheduled_preferences_city_enabled", "driver_scheduled_offer_preferences", ["city_id", "enabled"])

    op.add_column("rides", sa.Column("scheduled_booking_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_rides_scheduled_booking", "rides", "scheduled_bookings",
        ["scheduled_booking_id"], ["id"], ondelete="RESTRICT",
    )
    op.create_unique_constraint("uq_rides_scheduled_booking", "rides", ["scheduled_booking_id"])
    op.create_foreign_key(
        "fk_scheduled_bookings_live_ride",
        "scheduled_bookings", "rides", ["live_ride_id"], ["id"], ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_scheduled_bookings_live_ride", "scheduled_bookings", type_="foreignkey")
    op.drop_constraint("uq_rides_scheduled_booking", "rides", type_="unique")
    op.drop_constraint("fk_rides_scheduled_booking", "rides", type_="foreignkey")
    op.drop_column("rides", "scheduled_booking_id")
    op.drop_table("driver_scheduled_offer_preferences")
    op.drop_table("scheduled_booking_events")
    op.drop_constraint("fk_scheduled_bookings_current_commitment", "scheduled_bookings", type_="foreignkey")
    op.drop_table("scheduled_booking_commitments")
    op.drop_table("scheduled_booking_offers")
    op.drop_table("scheduled_bookings")
    # Raw SQL is deliberate: passing these convention-expanded names back to
    # op.drop_constraint would apply the naming convention a second time.
    op.execute(
        "ALTER TABLE scheduling_policies DROP CONSTRAINT "
        "ck_scheduling_policies_scheduling_policy_refund_mode"
    )
    op.execute(
        "ALTER TABLE scheduling_policies DROP CONSTRAINT "
        "ck_scheduling_policies_scheduling_policy_timing_bounds"
    )
    for column in (
        "fallback_matching_enabled", "surcharge_refund_mode", "driver_cancel_cutoff_minutes",
        "passenger_cancel_cutoff_minutes", "conflict_buffer_after_minutes",
        "conflict_buffer_before_minutes", "protected_duration_minutes", "handoff_minutes_before",
        "commitment_deadline_minutes_before", "offer_response_seconds",
        "offer_open_minutes_before", "maximum_horizon_days", "minimum_lead_minutes",
    ):
        op.drop_column("scheduling_policies", column)
