"""Store ordinary passenger ratings independently from safety reporting.

Revision ID: 20260810_0015
Revises: 20260810_0014
Create Date: 2026-08-10
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260810_0015"
down_revision = "20260810_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ride_ratings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ride_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rides.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reviewed_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("score BETWEEN 1 AND 5", name="ride_rating_score_range"),
        sa.UniqueConstraint("ride_id", "reviewer_id", name="one_rating_per_reviewer_per_ride"),
    )
    op.create_index("ix_ride_ratings_ride_id", "ride_ratings", ["ride_id"])


def downgrade() -> None:
    op.drop_index("ix_ride_ratings_ride_id", table_name="ride_ratings")
    op.drop_table("ride_ratings")
