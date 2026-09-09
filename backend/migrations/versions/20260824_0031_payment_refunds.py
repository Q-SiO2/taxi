"""Add append-only, operator-funded payment refund records.

Revision ID: 20260824_0031
Revises: 20260820_0030
Create Date: 2026-08-24
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260824_0031"
down_revision = "20260820_0030"
branch_labels = None
depends_on = None


refund_reason = postgresql.ENUM(
    "FARE_CORRECTION",
    "DUPLICATE_PAYMENT",
    "SERVICE_RECOVERY",
    "OTHER_APPROVED",
    name="refund_reason",
    create_type=False,
)
refund_settlement_method = postgresql.ENUM(
    "CASH",
    "EXTERNAL_TRANSFER",
    name="refund_settlement_method",
    create_type=False,
)


def upgrade() -> None:
    refund_reason.create(op.get_bind(), checkfirst=True)
    refund_settlement_method.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "payment_refunds",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("reason", refund_reason, nullable=False),
        sa.Column("settlement_method", refund_settlement_method, nullable=False),
        sa.Column("settlement_reference", sa.String(length=120), nullable=False),
        sa.Column("operator_note", sa.String(length=500), nullable=False),
        sa.Column(
            "driver_recovery_amount",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column("operator_funded_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("authorized_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "refunded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("amount > 0", name="payment_refund_positive_amount"),
        sa.CheckConstraint(
            "driver_recovery_amount = 0 AND operator_funded_amount = amount",
            name="payment_refund_launch_funding_reconciles",
        ),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
            name="fk_payment_refunds_payment_id_payments",
        ),
        sa.ForeignKeyConstraint(
            ["authorized_by_user_id"],
            ["users.id"],
            name="fk_payment_refunds_authorized_by_user_id_users",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payment_refunds"),
        sa.UniqueConstraint(
            "settlement_reference",
            name="uq_payment_refunds_settlement_reference",
        ),
    )
    op.create_index(
        "ix_payment_refunds_payment_id",
        "payment_refunds",
        ["payment_id"],
    )
    op.create_index(
        "ix_payment_refunds_authorized_by_user_id",
        "payment_refunds",
        ["authorized_by_user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_payment_refunds_authorized_by_user_id",
        table_name="payment_refunds",
    )
    op.drop_index("ix_payment_refunds_payment_id", table_name="payment_refunds")
    op.drop_table("payment_refunds")
    refund_settlement_method.drop(op.get_bind(), checkfirst=True)
    refund_reason.drop(op.get_bind(), checkfirst=True)
