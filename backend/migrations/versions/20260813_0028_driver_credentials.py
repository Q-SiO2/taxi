"""Add privacy-minimized professional driver credentials.

Revision ID: 20260813_0028
Revises: 20260813_0027
Create Date: 2026-08-13
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260813_0028"
down_revision = "20260813_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    credential_status = postgresql.ENUM(
        "PENDING", "VERIFIED", "REJECTED", "EXPIRED",
        name="credential_verification_status",
        create_type=False,
    )
    credential_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "driver_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("credential_type", sa.String(length=64), nullable=False),
        sa.Column("verification_status", credential_status, nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["driver_id"], ["driver_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_driver_credentials_driver_id", "driver_credentials", ["driver_id"])
    op.create_index("ix_driver_credentials_expires_at", "driver_credentials", ["expires_at"])
    op.create_index(
        "ix_driver_credentials_verification_status", "driver_credentials", ["verification_status"]
    )


def downgrade() -> None:
    op.drop_index("ix_driver_credentials_verification_status", table_name="driver_credentials")
    op.drop_index("ix_driver_credentials_expires_at", table_name="driver_credentials")
    op.drop_index("ix_driver_credentials_driver_id", table_name="driver_credentials")
    op.drop_table("driver_credentials")
    postgresql.ENUM(name="credential_verification_status").drop(op.get_bind(), checkfirst=True)
