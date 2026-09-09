"""Add authoritative security-incident postmortem completion.

Revision ID: 20260907_0051
Revises: 20260907_0050
Create Date: 2026-09-07
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260907_0051"
down_revision = "20260907_0050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "security_incidents",
        sa.Column("postmortem_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "security_incidents",
        sa.Column(
            "postmortem_completed_by_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "security_incidents",
        sa.Column("postmortem_outcome", sa.String(length=32), nullable=True),
    )
    op.create_foreign_key(
        "fk_security_incidents_postmortem_completed_by",
        "security_incidents",
        "users",
        ["postmortem_completed_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_security_incidents_postmortem_outcome",
        "security_incidents",
        "postmortem_outcome IS NULL OR postmortem_outcome IN "
        "('CONTROL_CHANGED', 'FOLLOW_UP_REQUIRED', 'NO_FURTHER_ACTION')",
    )
    op.create_check_constraint(
        "ck_security_incidents_postmortem_completion_shape",
        "security_incidents",
        "(postmortem_completed_at IS NULL "
        "AND postmortem_completed_by_user_id IS NULL "
        "AND postmortem_outcome IS NULL) OR "
        "(status = 'CLOSED' AND postmortem_completed_at IS NOT NULL "
        "AND postmortem_completed_by_user_id IS NOT NULL "
        "AND postmortem_outcome IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_security_incidents_postmortem_completed_after_close",
        "security_incidents",
        "postmortem_completed_at IS NULL OR postmortem_completed_at >= closed_at",
    )
    op.create_index(
        "ix_security_incidents_containment_due_open",
        "security_incidents",
        ["containment_due_at"],
        postgresql_where=sa.text("status IN ('OPEN', 'CONTAINING')"),
    )
    op.create_index(
        "ix_security_incidents_postmortem_due_pending",
        "security_incidents",
        ["postmortem_due_at"],
        postgresql_where=sa.text(
            "status = 'CLOSED' AND postmortem_completed_at IS NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_security_incidents_postmortem_due_pending",
        table_name="security_incidents",
    )
    op.drop_index(
        "ix_security_incidents_containment_due_open",
        table_name="security_incidents",
    )
    op.drop_constraint(
        "ck_security_incidents_postmortem_completed_after_close",
        "security_incidents",
        type_="check",
    )
    op.drop_constraint(
        "ck_security_incidents_postmortem_completion_shape",
        "security_incidents",
        type_="check",
    )
    op.drop_constraint(
        "ck_security_incidents_postmortem_outcome",
        "security_incidents",
        type_="check",
    )
    op.drop_constraint(
        "fk_security_incidents_postmortem_completed_by",
        "security_incidents",
        type_="foreignkey",
    )
    op.drop_column("security_incidents", "postmortem_outcome")
    op.drop_column("security_incidents", "postmortem_completed_by_user_id")
    op.drop_column("security_incidents", "postmortem_completed_at")
