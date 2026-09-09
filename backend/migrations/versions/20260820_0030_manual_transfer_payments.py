"""Add no-provider-cost manual bank and M-Wallet transfer reconciliation.

Revision ID: 20260820_0030
Revises: 20260813_0029
Create Date: 2026-08-20
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260820_0030"
down_revision = "20260813_0029"
branch_labels = None
depends_on = None


payment_method = postgresql.ENUM(
    "CASH",
    "MANUAL_TRANSFER",
    "CARD",
    "MOBILE_PAYMENT",
    name="payment_method",
    create_type=False,
)
claim_status = postgresql.ENUM(
    "SUBMITTED",
    "VERIFIED",
    "REJECTED",
    name="manual_transfer_claim_status",
    create_type=False,
)


def upgrade() -> None:
    # Existing cash/card enum values and rows remain untouched. The new value is
    # added before either table can reference it.
    op.execute("ALTER TYPE payment_method ADD VALUE IF NOT EXISTS 'MANUAL_TRANSFER'")
    op.add_column(
        "rides",
        sa.Column(
            "payment_method",
            payment_method,
            nullable=False,
            server_default=sa.text("'CASH'::payment_method"),
        ),
    )
    op.alter_column("rides", "payment_method", server_default=None)
    op.add_column("rides", sa.Column("transfer_recipient_name", sa.String(length=120), nullable=True))
    op.add_column("rides", sa.Column("transfer_bank_account", sa.String(length=120), nullable=True))
    op.add_column("rides", sa.Column("transfer_wallet_id", sa.String(length=120), nullable=True))

    claim_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "manual_transfer_claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claimant_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payer_reference", sa.String(length=80), nullable=True),
        sa.Column(
            "status",
            claim_status,
            nullable=False,
            server_default=sa.text("'SUBMITTED'::manual_transfer_claim_status"),
        ),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("review_reason", sa.String(length=500), nullable=True),
        sa.Column("settlement_reference", sa.String(length=120), nullable=True),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
            name="fk_manual_transfer_claims_payment_id_payments",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["claimant_user_id"],
            ["users.id"],
            name="fk_manual_transfer_claims_claimant_user_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"],
            ["users.id"],
            name="fk_manual_transfer_claims_reviewed_by_user_id_users",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_manual_transfer_claims"),
        sa.UniqueConstraint(
            "settlement_reference",
            name="uq_manual_transfer_claims_settlement_reference",
        ),
    )
    op.create_index(
        "ix_manual_transfer_claims_payment_id",
        "manual_transfer_claims",
        ["payment_id"],
    )
    op.create_index(
        "ix_manual_transfer_claims_claimant_user_id",
        "manual_transfer_claims",
        ["claimant_user_id"],
    )
    op.create_index(
        "uq_manual_transfer_claims_submitted_payment",
        "manual_transfer_claims",
        ["payment_id"],
        unique=True,
        postgresql_where=sa.text("status = 'SUBMITTED'::manual_transfer_claim_status"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_manual_transfer_claims_submitted_payment",
        table_name="manual_transfer_claims",
    )
    op.drop_index("ix_manual_transfer_claims_claimant_user_id", table_name="manual_transfer_claims")
    op.drop_index("ix_manual_transfer_claims_payment_id", table_name="manual_transfer_claims")
    op.drop_table("manual_transfer_claims")
    claim_status.drop(op.get_bind(), checkfirst=True)

    op.drop_column("rides", "transfer_wallet_id")
    op.drop_column("rides", "transfer_bank_account")
    op.drop_column("rides", "transfer_recipient_name")
    op.drop_column("rides", "payment_method")

    # PostgreSQL cannot remove one enum value in place. This conversion is
    # intentionally lossless for pre-feature data and refuses to cast while a
    # MANUAL_TRANSFER payment still exists.
    op.execute("CREATE TYPE payment_method_without_manual_transfer AS ENUM ('CASH', 'CARD', 'MOBILE_PAYMENT')")
    op.execute(
        "ALTER TABLE payments ALTER COLUMN method TYPE payment_method_without_manual_transfer "
        "USING method::text::payment_method_without_manual_transfer"
    )
    op.execute("DROP TYPE payment_method")
    op.execute("ALTER TYPE payment_method_without_manual_transfer RENAME TO payment_method")
