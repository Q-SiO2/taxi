"""Record sensitive administrative actions.

Revision ID: 20260810_0011
Revises: 20260810_0010
Create Date: 2026-08-10
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260810_0011"
down_revision = "20260810_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False), sa.Column("resource_type", sa.String(length=80), nullable=False), sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("changes", postgresql.JSONB(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"]); op.create_index("ix_audit_logs_resource_id", "audit_logs", ["resource_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_resource_id", table_name="audit_logs"); op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs"); op.drop_table("audit_logs")
