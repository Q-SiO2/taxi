"""Add expiring one-time mobile account recovery codes.

Revision ID: 20260902_0046
Revises: 20260831_0045
Create Date: 2026-09-02
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260902_0046"
down_revision = "20260831_0045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "account_recovery_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "code_hash ~ '^[0-9a-f]{64}$'",
            name="account_recovery_code_hash",
        ),
        sa.CheckConstraint(
            "expires_at > created_at",
            name="account_recovery_code_expiry",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_account_recovery_codes_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_account_recovery_codes"),
        sa.UniqueConstraint(
            "code_hash",
            name="uq_account_recovery_codes_code_hash",
        ),
    )
    op.create_index(
        "ix_account_recovery_codes_user_expiry",
        "account_recovery_codes",
        ["user_id", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_account_recovery_codes_user_expiry",
        table_name="account_recovery_codes",
    )
    op.drop_table("account_recovery_codes")
