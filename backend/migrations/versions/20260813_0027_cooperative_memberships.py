"""Add cooperatives and independent cooperative memberships.

Revision ID: 20260813_0027
Revises: 20260812_0026
Create Date: 2026-08-13
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260813_0027"
down_revision = "20260812_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    cooperative_status = postgresql.ENUM("ACTIVE", "INACTIVE", name="cooperative_status", create_type=False)
    membership_status = postgresql.ENUM(
        "PENDING", "ACTIVE", "SUSPENDED", "ENDED", name="cooperative_membership_status", create_type=False
    )
    cooperative_status.create(op.get_bind(), checkfirst=True)
    membership_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "cooperatives",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("legal_identifier", sa.String(length=120), nullable=True),
        sa.Column("status", cooperative_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("legal_identifier", name="uq_cooperatives_legal_identifier"),
    )
    op.create_table(
        "cooperative_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cooperative_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("membership_status", membership_status, nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("membership_number", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "ended_at IS NULL OR joined_at IS NULL OR ended_at >= joined_at",
            name="ck_cooperative_memberships_membership_dates_ordered",
        ),
        sa.ForeignKeyConstraint(["cooperative_id"], ["cooperatives.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "cooperative_id", "membership_number", name="uq_cooperative_memberships_cooperative_membership_number"
        ),
        sa.UniqueConstraint("cooperative_id", "user_id", name="uq_cooperative_memberships_cooperative_user"),
    )
    op.create_index(
        "ix_cooperative_memberships_cooperative_id", "cooperative_memberships", ["cooperative_id"]
    )
    op.create_index(
        "ix_cooperative_memberships_membership_status", "cooperative_memberships", ["membership_status"]
    )
    op.create_index("ix_cooperative_memberships_user_id", "cooperative_memberships", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_cooperative_memberships_user_id", table_name="cooperative_memberships")
    op.drop_index("ix_cooperative_memberships_membership_status", table_name="cooperative_memberships")
    op.drop_index("ix_cooperative_memberships_cooperative_id", table_name="cooperative_memberships")
    op.drop_table("cooperative_memberships")
    op.drop_table("cooperatives")
    postgresql.ENUM(name="cooperative_membership_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="cooperative_status").drop(op.get_bind(), checkfirst=True)
