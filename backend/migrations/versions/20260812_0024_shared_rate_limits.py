"""Store privacy-minimized shared abuse-rate-limit buckets.

Revision ID: 20260812_0024
Revises: 20260812_0023
Create Date: 2026-08-12
"""

import sqlalchemy as sa
from alembic import op


revision = "20260812_0024"
down_revision = "20260812_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_buckets",
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.CheckConstraint("attempts > 0", name="positive_attempts"),
        sa.PrimaryKeyConstraint("key_hash", name=op.f("pk_rate_limit_buckets")),
    )
    op.create_index(
        op.f("ix_rate_limit_buckets_expires_at"),
        "rate_limit_buckets",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_rate_limit_buckets_expires_at"), table_name="rate_limit_buckets")
    op.drop_table("rate_limit_buckets")
