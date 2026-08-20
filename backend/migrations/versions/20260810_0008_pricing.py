"""Create versioned pricing rules and immutable fare records.

Revision ID: 20260810_0008
Revises: 20260810_0007
Create Date: 2026-08-10
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260810_0008"
down_revision = "20260810_0007"
branch_labels = None
depends_on = None

pricing_model = sa.Enum("FIXED", "METERED", "ESTIMATED", name="pricing_model")
rule_status = sa.Enum("ACTIVE", "INACTIVE", name="pricing_rule_status")


def upgrade() -> None:
    op.create_table(
        "pricing_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("name", sa.String(length=120), nullable=False), sa.Column("version", sa.String(length=64), nullable=False, unique=True),
        sa.Column("model", pricing_model, nullable=False), sa.Column("fixed_amount", sa.Numeric(12, 2)), sa.Column("currency", sa.String(length=3), nullable=False, server_default="MAD"),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False), sa.Column("effective_until", sa.DateTime(timezone=True)), sa.Column("status", rule_status, nullable=False, server_default="INACTIVE"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("fixed_amount IS NULL OR fixed_amount >= 0", name="pricing_rule_non_negative_fixed_amount"),
    )
    op.create_table(
        "fare_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("ride_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rides.id"), nullable=False, unique=True), sa.Column("pricing_rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pricing_rules.id"), nullable=False),
        sa.Column("base_amount", sa.Numeric(12, 2), nullable=False), sa.Column("total_amount", sa.Numeric(12, 2), nullable=False), sa.Column("currency", sa.String(length=3), nullable=False), sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("base_amount >= 0 AND total_amount >= 0", name="fare_record_non_negative_amounts"),
    )


def downgrade() -> None:
    op.drop_table("fare_records"); op.drop_table("pricing_rules"); rule_status.drop(op.get_bind(), checkfirst=True); pricing_model.drop(op.get_bind(), checkfirst=True)
