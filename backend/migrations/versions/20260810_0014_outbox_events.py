"""Persist transactional notification work with the ride mutation.

Revision ID: 20260810_0014
Revises: 20260810_0013
Create Date: 2026-08-10
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260810_0014"
down_revision = "20260810_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("topic", sa.String(length=120), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("attempts >= 0", name="outbox_non_negative_attempts"),
    )
    op.create_index("ix_outbox_events_topic", "outbox_events", ["topic"])
    op.create_index("ix_outbox_events_pending", "outbox_events", ["available_at"], postgresql_where=sa.text("delivered_at IS NULL"))


def downgrade() -> None:
    op.drop_index("ix_outbox_events_pending", table_name="outbox_events")
    op.drop_index("ix_outbox_events_topic", table_name="outbox_events")
    op.drop_table("outbox_events")
