"""Add immutable protected driver-document erasure evidence.

Revision ID: 20260831_0045
Revises: 20260831_0044
Create Date: 2026-08-31
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260831_0045"
down_revision = "20260831_0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "driver_document_retention_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.String(length=24), nullable=False),
        sa.Column("retention_policy_version", sa.String(length=40), nullable=False),
        sa.Column("retention_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "reason IN ('APPLICANT_DELETED', 'RETENTION_EXPIRED')",
            name="driver_document_retention_reason",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["driver_city_applications.id"],
            name="fk_driver_document_retention_application",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["city_id"],
            ["cities.id"],
            name="fk_driver_document_retention_city",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_driver_document_retention_actions"),
        sa.UniqueConstraint(
            "document_id",
            name="uq_driver_document_retention_document",
        ),
    )
    op.create_index(
        "ix_driver_document_retention_application",
        "driver_document_retention_actions",
        ["application_id"],
    )
    op.create_index(
        "ix_driver_document_retention_city",
        "driver_document_retention_actions",
        ["city_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_driver_document_retention_city",
        table_name="driver_document_retention_actions",
    )
    op.drop_index(
        "ix_driver_document_retention_application",
        table_name="driver_document_retention_actions",
    )
    op.drop_table("driver_document_retention_actions")
