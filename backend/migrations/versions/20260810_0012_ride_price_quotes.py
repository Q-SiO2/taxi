"""Persist the tariff quote selected when a passenger confirms a fixed-price ride.

Revision ID: 20260810_0012
Revises: 20260810_0011
Create Date: 2026-08-10
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260810_0012"
down_revision = "20260810_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("rides", sa.Column("quoted_pricing_rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pricing_rules.id")))
    op.add_column("rides", sa.Column("quoted_amount", sa.Numeric(12, 2)))
    op.add_column("rides", sa.Column("quoted_currency", sa.String(length=3)))
    op.create_check_constraint(
        "ride_quote_fields_together",
        "rides",
        "(quoted_pricing_rule_id IS NULL AND quoted_amount IS NULL AND quoted_currency IS NULL) "
        "OR (quoted_pricing_rule_id IS NOT NULL AND quoted_amount IS NOT NULL AND quoted_amount >= 0 AND quoted_currency IS NOT NULL)",
    )
    op.create_index("ix_rides_quoted_pricing_rule_id", "rides", ["quoted_pricing_rule_id"])


def downgrade() -> None:
    op.drop_index("ix_rides_quoted_pricing_rule_id", table_name="rides")
    op.drop_constraint("ck_rides_ride_quote_fields_together", "rides", type_="check")
    op.drop_column("rides", "quoted_currency")
    op.drop_column("rides", "quoted_amount")
    op.drop_column("rides", "quoted_pricing_rule_id")
