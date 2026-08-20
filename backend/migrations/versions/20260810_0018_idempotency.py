"""Record completed sensitive commands for retry-safe responses.

Revision ID: 20260810_0018
Revises: 20260810_0017
Create Date: 2026-08-10
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260810_0018"
down_revision = "20260810_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "idempotency_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("operation", sa.String(length=120), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("response_status", sa.Integer()),
        sa.Column("response_payload", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("user_id", "operation", "key", name="idempotency_user_operation_key"),
    )
    op.create_index("ix_idempotency_records_user_id", "idempotency_records", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_idempotency_records_user_id", table_name="idempotency_records")
    op.drop_table("idempotency_records")
