"""Preserve passenger-facing assignment details at offer acceptance.

Revision ID: 20260810_0020
Revises: 20260810_0019
Create Date: 2026-08-10
"""

import sqlalchemy as sa
from alembic import op


revision = "20260810_0020"
down_revision = "20260810_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("rides", sa.Column("assigned_driver_name", sa.String(length=120), nullable=True))
    op.add_column("rides", sa.Column("assigned_vehicle_make", sa.String(length=80), nullable=True))
    op.add_column("rides", sa.Column("assigned_vehicle_model", sa.String(length=80), nullable=True))
    op.add_column("rides", sa.Column("assigned_vehicle_color", sa.String(length=60), nullable=True))
    op.add_column("rides", sa.Column("assigned_taxi_identifier", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("rides", "assigned_taxi_identifier")
    op.drop_column("rides", "assigned_vehicle_color")
    op.drop_column("rides", "assigned_vehicle_model")
    op.drop_column("rides", "assigned_vehicle_make")
    op.drop_column("rides", "assigned_driver_name")
