"""Bind an assigned verified vehicle to each accepted ride.

Revision ID: 20260810_0019
Revises: 20260810_0018
Create Date: 2026-08-10
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260810_0019"
down_revision = "20260810_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("rides", sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_rides_vehicle_id_vehicles", "rides", "vehicles", ["vehicle_id"], ["id"])
    op.create_index("ix_rides_vehicle_id", "rides", ["vehicle_id"])


def downgrade() -> None:
    op.drop_index("ix_rides_vehicle_id", table_name="rides")
    op.drop_constraint("fk_rides_vehicle_id_vehicles", "rides", type_="foreignkey")
    op.drop_column("rides", "vehicle_id")
