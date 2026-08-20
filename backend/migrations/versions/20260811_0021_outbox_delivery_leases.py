"""Add safe leasing and outcome state for transactional outbox delivery.

Revision ID: 20260811_0021
Revises: 20260810_0020
Create Date: 2026-08-11
"""

import sqlalchemy as sa
from alembic import op


revision = "20260811_0021"
down_revision = "20260810_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("outbox_events", sa.Column("locked_by", sa.String(length=64), nullable=True))
    op.add_column("outbox_events", sa.Column("last_error", sa.String(length=96), nullable=True))


def downgrade() -> None:
    op.drop_column("outbox_events", "last_error")
    op.drop_column("outbox_events", "locked_by")
