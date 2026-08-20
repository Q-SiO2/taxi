"""Create expiring driver-specific ride offers.

Revision ID: 20260810_0006
Revises: 20260810_0005
Create Date: 2026-08-10
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260810_0006"
down_revision = "20260810_0005"
branch_labels = None
depends_on = None

offer_status = sa.Enum("PENDING", "ACCEPTED", "DECLINED", "EXPIRED", name="ride_offer_status")


def upgrade() -> None:
    op.create_table(
        "ride_offers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ride_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rides.id", ondelete="CASCADE"), nullable=False),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("driver_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", offer_status, nullable=False, server_default="PENDING"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True)), sa.Column("decline_reason", sa.String(length=120)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("ride_id", "driver_id", name="ride_offer_per_driver"),
    )
    op.create_index("ix_ride_offers_ride_id", "ride_offers", ["ride_id"])
    op.create_index("ix_ride_offers_driver_id", "ride_offers", ["driver_id"])
    op.create_index("ix_ride_offers_status", "ride_offers", ["status"])


def downgrade() -> None:
    op.drop_index("ix_ride_offers_status", table_name="ride_offers"); op.drop_index("ix_ride_offers_driver_id", table_name="ride_offers"); op.drop_index("ix_ride_offers_ride_id", table_name="ride_offers")
    op.drop_table("ride_offers"); offer_status.drop(op.get_bind(), checkfirst=True)
