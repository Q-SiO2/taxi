"""Create authoritative rides and append-only lifecycle events.

Revision ID: 20260810_0005
Revises: 20260810_0004
Create Date: 2026-08-10
"""
import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql

revision = "20260810_0005"
down_revision = "20260810_0004"
branch_labels = None
depends_on = None

ride_status = sa.Enum("REQUESTED", "MATCHING", "ACCEPTED", "DRIVER_EN_ROUTE", "DRIVER_ARRIVED", "IN_PROGRESS", "COMPLETED", "CANCELLED", name="ride_status")
event_type = sa.Enum("CREATED", "STATUS_CHANGED", "CANCELLED", name="ride_event_type")


def upgrade() -> None:
    op.create_table(
        "rides",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("passenger_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("driver_profiles.id")),
        sa.Column("status", ride_status, nullable=False, server_default="REQUESTED"),
        sa.Column("pickup_point", Geography(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("destination_point", Geography(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("pickup_address", sa.String(length=500)), sa.Column("destination_address", sa.String(length=500)),
        sa.Column("passenger_note", sa.Text()), sa.Column("cancellation_reason", sa.String(length=120)),
        sa.Column("cancelled_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("accepted_at", sa.DateTime(timezone=True)), sa.Column("arrived_at", sa.DateTime(timezone=True)),
        sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_rides_passenger_id", "rides", ["passenger_id"]); op.create_index("ix_rides_driver_id", "rides", ["driver_id"]); op.create_index("ix_rides_status", "rides", ["status"])
    op.create_table(
        "ride_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ride_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rides.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", event_type, nullable=False), sa.Column("previous_status", ride_status), sa.Column("new_status", ride_status, nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")), sa.Column("reason", sa.String(length=120)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    ); op.create_index("ix_ride_events_ride_id", "ride_events", ["ride_id"])


def downgrade() -> None:
    op.drop_index("ix_ride_events_ride_id", table_name="ride_events"); op.drop_table("ride_events")
    op.drop_index("ix_rides_status", table_name="rides"); op.drop_index("ix_rides_driver_id", table_name="rides"); op.drop_index("ix_rides_passenger_id", table_name="rides"); op.drop_table("rides")
    event_type.drop(op.get_bind(), checkfirst=True); ride_status.drop(op.get_bind(), checkfirst=True)
