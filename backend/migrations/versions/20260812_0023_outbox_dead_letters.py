"""Bound failed outbox delivery with an inspectable dead-letter state.

Revision ID: 20260812_0023
Revises: 20260812_0022
Create Date: 2026-08-12
"""

import sqlalchemy as sa
from alembic import op


revision = "20260812_0023"
down_revision = "20260812_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("outbox_events", sa.Column("dead_lettered_at", sa.DateTime(timezone=True), nullable=True))
    op.drop_index("ix_outbox_events_pending", table_name="outbox_events")
    op.create_index(
        "ix_outbox_events_pending",
        "outbox_events",
        ["available_at"],
        postgresql_where=sa.text("delivered_at IS NULL AND dead_lettered_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_outbox_events_pending", table_name="outbox_events")
    op.create_index(
        "ix_outbox_events_pending",
        "outbox_events",
        ["available_at"],
        postgresql_where=sa.text("delivered_at IS NULL"),
    )
    op.drop_column("outbox_events", "dead_lettered_at")
