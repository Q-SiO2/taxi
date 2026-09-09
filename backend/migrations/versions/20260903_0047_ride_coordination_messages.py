"""Add closed-code ride-participant coordination messages.

Revision ID: 20260903_0047
Revises: 20260902_0046
Create Date: 2026-09-03
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260903_0047"
down_revision = "20260902_0046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ride_coordination_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ride_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "code IN ("
            "'PASSENGER_AT_PICKUP', "
            "'PASSENGER_NEEDS_MORE_TIME', "
            "'PASSENGER_CANNOT_FIND_DRIVER', "
            "'DRIVER_ON_MY_WAY', "
            "'DRIVER_AT_PICKUP', "
            "'DRIVER_CANNOT_FIND_PASSENGER'"
            ")",
            name="ride_coordination_code",
        ),
        sa.ForeignKeyConstraint(
            ["ride_id"],
            ["rides.id"],
            name="fk_ride_coordination_messages_ride_id_rides",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sender_user_id"],
            ["users.id"],
            name="fk_ride_coordination_messages_sender_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ride_coordination_messages"),
    )
    op.create_index(
        "ix_ride_coordination_messages_ride_created",
        "ride_coordination_messages",
        ["ride_id", "created_at"],
    )
    op.create_index(
        "ix_ride_coordination_messages_sender_ride",
        "ride_coordination_messages",
        ["sender_user_id", "ride_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ride_coordination_messages_sender_ride",
        table_name="ride_coordination_messages",
    )
    op.drop_index(
        "ix_ride_coordination_messages_ride_created",
        table_name="ride_coordination_messages",
    )
    op.drop_table("ride_coordination_messages")
