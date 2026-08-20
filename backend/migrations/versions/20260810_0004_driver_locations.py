"""Store validated operational driver locations using PostGIS geography.

Revision ID: 20260810_0004
Revises: 20260810_0003
Create Date: 2026-08-10
"""

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql


revision = "20260810_0004"
down_revision = "20260810_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "driver_locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("driver_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("point", Geography(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accuracy_meters", sa.Float()),
        sa.Column("heading_degrees", sa.Float()),
        sa.Column("speed_meters_per_second", sa.Float()),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_driver_locations_driver_id", "driver_locations", ["driver_id"])
    op.create_index("ix_driver_locations_observed_at", "driver_locations", ["observed_at"])


def downgrade() -> None:
    op.drop_index("ix_driver_locations_observed_at", table_name="driver_locations")
    op.drop_index("ix_driver_locations_driver_id", table_name="driver_locations")
    op.drop_table("driver_locations")
