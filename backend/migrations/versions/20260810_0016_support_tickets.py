"""Create participant-owned support tickets.

Revision ID: 20260810_0016
Revises: 20260810_0015
Create Date: 2026-08-10
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260810_0016"
down_revision = "20260810_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    category = postgresql.ENUM(
        "RIDE_PROBLEM", "FARE_DISPUTE", "ACCOUNT_ACCESS", "OTHER", name="support_ticket_category", create_type=False
    )
    ticket_status = postgresql.ENUM("OPEN", name="support_ticket_status", create_type=False)
    category.create(op.get_bind(), checkfirst=False)
    ticket_status.create(op.get_bind(), checkfirst=False)
    op.create_table(
        "support_tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ride_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rides.id")),
        sa.Column("category", category, nullable=False),
        sa.Column("subject", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", ticket_status, nullable=False, server_default="OPEN"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_support_tickets_user_id", "support_tickets", ["user_id"])
    op.create_index("ix_support_tickets_ride_id", "support_tickets", ["ride_id"])


def downgrade() -> None:
    op.drop_index("ix_support_tickets_ride_id", table_name="support_tickets")
    op.drop_index("ix_support_tickets_user_id", table_name="support_tickets")
    op.drop_table("support_tickets")
    postgresql.ENUM(name="support_ticket_status").drop(op.get_bind(), checkfirst=False)
    postgresql.ENUM(name="support_ticket_category").drop(op.get_bind(), checkfirst=False)
