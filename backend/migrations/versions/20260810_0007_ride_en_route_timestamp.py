"""Record the explicit driver en-route transition time.

Revision ID: 20260810_0007
Revises: 20260810_0006
Create Date: 2026-08-10
"""
import sqlalchemy as sa
from alembic import op

revision = "20260810_0007"
down_revision = "20260810_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("rides", sa.Column("en_route_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("rides", "en_route_at")
