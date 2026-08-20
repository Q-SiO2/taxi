"""Enable PostGIS as the migration baseline.

Revision ID: 20260810_0001
Revises:
Create Date: 2026-08-10
"""

from alembic import op


revision = "20260810_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")


def downgrade() -> None:
    # Extensions may be shared by later migrations; do not drop PostGIS automatically.
    pass
