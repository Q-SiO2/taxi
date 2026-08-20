"""Create pending driver application and vehicle foundations.

Revision ID: 20260810_0003
Revises: 20260810_0002
Create Date: 2026-08-10
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260810_0003"
down_revision = "20260810_0002"
branch_labels = None
depends_on = None

verification_status = sa.Enum(
    "NOT_STARTED", "SUBMITTED", "UNDER_REVIEW", "ADDITIONAL_INFORMATION_REQUIRED", "APPROVED", "REJECTED", "SUSPENDED", "EXPIRED", name="driver_verification_status"
)
account_status = sa.Enum("PENDING", "ACTIVE", "SUSPENDED", "DEACTIVATED", name="driver_account_status")
availability_status = sa.Enum("OFFLINE", "AVAILABLE", "PAUSED", "OFFERED_RIDE", "EN_ROUTE", "AT_PICKUP", "ON_RIDE", name="driver_availability_status")
vehicle_status = sa.Enum("ACTIVE", "INACTIVE", name="vehicle_status")
vehicle_verification_status = sa.Enum("PENDING", "VERIFIED", "REJECTED", "EXPIRED", name="vehicle_verification_status")


def upgrade() -> None:
    op.create_table(
        "driver_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("verification_status", verification_status, nullable=False, server_default="NOT_STARTED"),
        sa.Column("account_status", account_status, nullable=False, server_default="PENDING"),
        sa.Column("availability_status", availability_status, nullable=False, server_default="OFFLINE"),
        sa.Column("active_vehicle_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_table(
        "driver_verifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("driver_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", verification_status, nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("rejection_reason", sa.String(length=500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_driver_verifications_driver_id", "driver_verifications", ["driver_id"])
    op.create_table(
        "vehicles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("driver_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("make", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("color", sa.String(length=60), nullable=False),
        sa.Column("registration_number", sa.String(length=64), nullable=False, unique=True),
        sa.Column("taxi_identifier", sa.String(length=64), unique=True),
        sa.Column("passenger_capacity", sa.Integer()),
        sa.Column("status", vehicle_status, nullable=False, server_default="ACTIVE"),
        sa.Column("verification_status", vehicle_verification_status, nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_vehicles_driver_id", "vehicles", ["driver_id"])
    op.create_foreign_key("fk_driver_profiles_active_vehicle_id_vehicles", "driver_profiles", "vehicles", ["active_vehicle_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_driver_profiles_active_vehicle_id_vehicles", "driver_profiles", type_="foreignkey")
    op.drop_index("ix_vehicles_driver_id", table_name="vehicles")
    op.drop_table("vehicles")
    op.drop_index("ix_driver_verifications_driver_id", table_name="driver_verifications")
    op.drop_table("driver_verifications")
    op.drop_table("driver_profiles")
    vehicle_verification_status.drop(op.get_bind(), checkfirst=True)
    vehicle_status.drop(op.get_bind(), checkfirst=True)
    availability_status.drop(op.get_bind(), checkfirst=True)
    account_status.drop(op.get_bind(), checkfirst=True)
    verification_status.drop(op.get_bind(), checkfirst=True)
