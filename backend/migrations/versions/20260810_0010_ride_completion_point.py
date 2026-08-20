"""Store the backend-recorded point at ride completion.

Revision ID: 20260810_0010
Revises: 20260810_0009
Create Date: 2026-08-10
"""
import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geography

revision = "20260810_0010"
down_revision = "20260810_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("rides", sa.Column("completed_point", Geography(geometry_type="POINT", srid=4326), nullable=True))


def downgrade() -> None:
    op.drop_column("rides", "completed_point")
