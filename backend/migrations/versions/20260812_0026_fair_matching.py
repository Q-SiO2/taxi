"""Add deterministic fairness-aware matching state and offer evidence.

Revision ID: 20260812_0026
Revises: 20260812_0025
Create Date: 2026-08-12
"""

import sqlalchemy as sa
from alembic import op


revision = "20260812_0026"
down_revision = "20260812_0025"
branch_labels = None
depends_on = None


OLD_RIDE_STATUSES = (
    "REQUESTED",
    "MATCHING",
    "ACCEPTED",
    "DRIVER_EN_ROUTE",
    "DRIVER_ARRIVED",
    "IN_PROGRESS",
    "COMPLETED",
    "CANCELLED",
)
OLD_EVENT_TYPES = ("CREATED", "STATUS_CHANGED", "CANCELLED")
OLD_OFFER_STATUSES = ("PENDING", "ACCEPTED", "DECLINED", "EXPIRED")


def upgrade() -> None:
    op.execute("ALTER TYPE ride_status ADD VALUE IF NOT EXISTS 'UNMATCHED'")
    for value in ("OFFER_CREATED", "OFFER_DECLINED", "OFFER_EXPIRED", "MATCHING_FAILED"):
        op.execute(f"ALTER TYPE ride_event_type ADD VALUE IF NOT EXISTS '{value}'")
    op.execute("ALTER TYPE ride_offer_status ADD VALUE IF NOT EXISTS 'CANCELLED'")

    op.add_column("driver_profiles", sa.Column("available_since", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_driver_profiles_available_since", "driver_profiles", ["available_since"])
    # Existing online drivers were already waiting from at least their latest
    # profile transition. This is a conservative historical backfill; only new
    # transitions have exact availability timestamps.
    op.execute(
        "UPDATE driver_profiles SET available_since = updated_at "
        "WHERE availability_status IN ('AVAILABLE', 'OFFERED_RIDE') AND available_since IS NULL"
    )

    op.add_column("ride_offers", sa.Column("estimated_pickup_distance_meters", sa.Integer(), nullable=True))
    op.add_column("ride_offers", sa.Column("estimated_pickup_time_seconds", sa.Integer(), nullable=True))
    op.add_column("ride_offers", sa.Column("idle_seconds_at_offer", sa.Integer(), nullable=True))
    op.add_column("ride_offers", sa.Column("recent_assignment_count", sa.Integer(), nullable=True))
    op.add_column("ride_offers", sa.Column("proximity_score", sa.Float(), nullable=True))
    op.add_column("ride_offers", sa.Column("idle_score", sa.Float(), nullable=True))
    op.add_column("ride_offers", sa.Column("fairness_score", sa.Float(), nullable=True))
    op.add_column("ride_offers", sa.Column("ranking_score", sa.Float(), nullable=True))
    op.add_column("ride_offers", sa.Column("matching_algorithm_version", sa.String(length=32), nullable=True))


def downgrade() -> None:
    for column_name in (
        "matching_algorithm_version",
        "ranking_score",
        "fairness_score",
        "idle_score",
        "proximity_score",
        "recent_assignment_count",
        "idle_seconds_at_offer",
        "estimated_pickup_time_seconds",
        "estimated_pickup_distance_meters",
    ):
        op.drop_column("ride_offers", column_name)
    op.drop_index("ix_driver_profiles_available_since", table_name="driver_profiles")
    op.drop_column("driver_profiles", "available_since")

    # Map forward-only business outcomes to the closest legacy terminal/event
    # values before recreating PostgreSQL enums without the added labels.
    op.execute("UPDATE rides SET status = 'CANCELLED' WHERE status = 'UNMATCHED'")
    op.execute("UPDATE ride_events SET previous_status = 'CANCELLED' WHERE previous_status = 'UNMATCHED'")
    op.execute("UPDATE ride_events SET new_status = 'CANCELLED' WHERE new_status = 'UNMATCHED'")
    op.execute(
        "UPDATE ride_events SET event_type = 'STATUS_CHANGED' "
        "WHERE event_type IN ('OFFER_CREATED', 'OFFER_DECLINED', 'OFFER_EXPIRED', 'MATCHING_FAILED')"
    )
    op.execute("UPDATE ride_offers SET status = 'EXPIRED' WHERE status = 'CANCELLED'")

    _recreate_ride_status()
    _recreate_event_type()
    _recreate_offer_status()


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _recreate_ride_status() -> None:
    op.execute("ALTER TABLE rides ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TYPE ride_status RENAME TO ride_status_with_unmatched")
    op.execute(f"CREATE TYPE ride_status AS ENUM ({_quoted(OLD_RIDE_STATUSES)})")
    op.execute("ALTER TABLE rides ALTER COLUMN status TYPE ride_status USING status::text::ride_status")
    op.execute(
        "ALTER TABLE ride_events ALTER COLUMN previous_status TYPE ride_status "
        "USING previous_status::text::ride_status"
    )
    op.execute(
        "ALTER TABLE ride_events ALTER COLUMN new_status TYPE ride_status "
        "USING new_status::text::ride_status"
    )
    op.execute("ALTER TABLE rides ALTER COLUMN status SET DEFAULT 'REQUESTED'::ride_status")
    op.execute("DROP TYPE ride_status_with_unmatched")


def _recreate_event_type() -> None:
    op.execute("ALTER TYPE ride_event_type RENAME TO ride_event_type_with_matching_events")
    op.execute(f"CREATE TYPE ride_event_type AS ENUM ({_quoted(OLD_EVENT_TYPES)})")
    op.execute(
        "ALTER TABLE ride_events ALTER COLUMN event_type TYPE ride_event_type "
        "USING event_type::text::ride_event_type"
    )
    op.execute("DROP TYPE ride_event_type_with_matching_events")


def _recreate_offer_status() -> None:
    op.execute("ALTER TABLE ride_offers ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TYPE ride_offer_status RENAME TO ride_offer_status_with_cancelled")
    op.execute(f"CREATE TYPE ride_offer_status AS ENUM ({_quoted(OLD_OFFER_STATUSES)})")
    op.execute(
        "ALTER TABLE ride_offers ALTER COLUMN status TYPE ride_offer_status "
        "USING status::text::ride_offer_status"
    )
    op.execute("ALTER TABLE ride_offers ALTER COLUMN status SET DEFAULT 'PENDING'::ride_offer_status")
    op.execute("DROP TYPE ride_offer_status_with_cancelled")
