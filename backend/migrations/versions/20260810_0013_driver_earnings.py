"""Store driver settlement facts separately from passenger payments.

Revision ID: 20260810_0013
Revises: 20260810_0012
Create Date: 2026-08-10
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260810_0013"
down_revision = "20260810_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "driver_earnings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("driver_profiles.id"), nullable=False),
        sa.Column("ride_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rides.id"), nullable=False, unique=True),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payments.id"), nullable=False, unique=True),
        sa.Column("gross_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("fee_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("adjustment_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("net_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("gross_amount >= 0 AND fee_amount >= 0", name="driver_earning_non_negative_amounts"),
    )
    op.create_index("ix_driver_earnings_driver_id", "driver_earnings", ["driver_id"])


def downgrade() -> None:
    op.drop_index("ix_driver_earnings_driver_id", table_name="driver_earnings")
    op.drop_table("driver_earnings")
