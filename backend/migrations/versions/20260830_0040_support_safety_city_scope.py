"""Give support and safety cases immutable city ownership.

Revision ID: 20260830_0040
Revises: 20260829_0039
Create Date: 2026-08-30
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260830_0040"
down_revision = "20260829_0039"
branch_labels = None
depends_on = None

_LEGACY_CITY_ID = "10000000-0000-4000-8000-000000000003"


def upgrade() -> None:
    for table_name in ("support_tickets", "safety_reports"):
        op.add_column(
            table_name,
            sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=True),
        )

    op.execute(
        sa.schema.DDL(
            "UPDATE support_tickets AS ticket "
            "SET city_id = COALESCE((SELECT ride.city_id FROM rides AS ride "
            "WHERE ride.id = ticket.ride_id), "
            f"'{_LEGACY_CITY_ID}'::uuid)"
        )
    )
    op.execute(
        sa.schema.DDL(
            "UPDATE safety_reports AS report "
            "SET city_id = COALESCE((SELECT ride.city_id FROM rides AS ride "
            "WHERE ride.id = report.ride_id), "
            f"'{_LEGACY_CITY_ID}'::uuid)"
        )
    )

    for table_name in ("support_tickets", "safety_reports"):
        op.alter_column(table_name, "city_id", nullable=False)
        op.create_foreign_key(
            f"fk_{table_name}_city_id_cities",
            table_name,
            "cities",
            ["city_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_index(f"ix_{table_name}_city_id", table_name, ["city_id"])


def downgrade() -> None:
    for table_name in ("safety_reports", "support_tickets"):
        op.drop_index(f"ix_{table_name}_city_id", table_name=table_name)
        op.drop_constraint(
            f"fk_{table_name}_city_id_cities",
            table_name,
            type_="foreignkey",
        )
        op.drop_column(table_name, "city_id")
