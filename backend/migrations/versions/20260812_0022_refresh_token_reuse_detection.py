"""Track refresh-token families and rotated tokens for reuse detection.

Revision ID: 20260812_0022
Revises: 20260811_0021
Create Date: 2026-08-12
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260812_0022"
down_revision = "20260811_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("refresh_family_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("sessions", sa.Column("refresh_rotated_at", sa.DateTime(timezone=True), nullable=True))
    # Existing sessions each form an independent family; no token or user data
    # is copied into the new columns.
    op.execute("UPDATE sessions SET refresh_family_id = id WHERE refresh_family_id IS NULL")
    op.alter_column("sessions", "refresh_family_id", nullable=False)
    op.create_index("ix_sessions_refresh_family_id", "sessions", ["refresh_family_id"])


def downgrade() -> None:
    op.drop_index("ix_sessions_refresh_family_id", table_name="sessions")
    op.drop_column("sessions", "refresh_rotated_at")
    op.drop_column("sessions", "refresh_family_id")
