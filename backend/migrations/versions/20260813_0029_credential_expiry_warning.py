"""Track idempotent professional credential expiry warnings.

Revision ID: 20260813_0029
Revises: 20260813_0028
Create Date: 2026-08-13
"""

import sqlalchemy as sa
from alembic import op


revision = "20260813_0029"
down_revision = "20260813_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "driver_credentials",
        sa.Column("expiry_warning_sent_for", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("driver_credentials", "expiry_warning_sent_for")
