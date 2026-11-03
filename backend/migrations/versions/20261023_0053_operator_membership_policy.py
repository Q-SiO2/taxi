"""Add explicit closed-shop driver admission policy to operators.

Revision ID: 20261023_0053
Revises: 20260908_0052
"""

import sqlalchemy as sa
from alembic import op

revision = "20261023_0053"
down_revision = "20260908_0052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "operators",
        sa.Column("requires_active_membership", sa.Boolean(), nullable=False,
                  server_default=sa.false()),
    )
    op.create_check_constraint(
        "operator_membership_requires_register",
        "operators",
        "NOT requires_active_membership OR cooperative_id IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint("operator_membership_requires_register", "operators", type_="check")
    op.drop_column("operators", "requires_active_membership")
