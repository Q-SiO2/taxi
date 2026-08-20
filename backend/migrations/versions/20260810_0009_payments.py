"""Create immutable-per-ride payment ledger entries.

Revision ID: 20260810_0009
Revises: 20260810_0008
Create Date: 2026-08-10
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260810_0009"
down_revision = "20260810_0008"
branch_labels = None
depends_on = None

method = sa.Enum("CASH", "CARD", "MOBILE_PAYMENT", name="payment_method")
payment_status = sa.Enum("PENDING", "PROCESSING", "COMPLETED", "FAILED", "CANCELLED", "DISPUTED", "REFUNDED", name="payment_status")


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("ride_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rides.id"), nullable=False, unique=True), sa.Column("payer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False), sa.Column("currency", sa.String(length=3), nullable=False), sa.Column("method", method, nullable=False), sa.Column("status", payment_status, nullable=False, server_default="PENDING"),
        sa.Column("provider", sa.String(length=80)), sa.Column("provider_reference", sa.String(length=160), unique=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("refunded_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("amount >= 0", name="payment_non_negative_amount"),
    )


def downgrade() -> None:
    op.drop_table("payments"); payment_status.drop(op.get_bind(), checkfirst=True); method.drop(op.get_bind(), checkfirst=True)
