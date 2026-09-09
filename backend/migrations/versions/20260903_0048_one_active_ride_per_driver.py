"""Enforce one active live ride per driver across all booking origins.

Revision ID: 20260903_0048
Revises: 20260903_0047
Create Date: 2026-09-03
"""

import sqlalchemy as sa
from alembic import op


revision = "20260903_0048"
down_revision = "20260903_0047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Freeze writes before checking; otherwise a bypassing writer could add a
    # conflict between the preflight and index creation. Never repair ride
    # history implicitly, and do not put driver identifiers in the diagnostic.
    op.execute("LOCK TABLE rides IN SHARE MODE")
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT driver_id FROM rides
                WHERE driver_id IS NOT NULL AND status IN
                    ('ACCEPTED', 'DRIVER_EN_ROUTE', 'DRIVER_ARRIVED', 'IN_PROGRESS')
                GROUP BY driver_id HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION 'Active ride conflicts require operator investigation before migration';
            END IF;
        END $$;
    """)
    op.create_index(
        "uq_rides_one_active_per_driver", "rides", ["driver_id"], unique=True,
        postgresql_where=sa.text(
            "driver_id IS NOT NULL AND status IN "
            "('ACCEPTED', 'DRIVER_EN_ROUTE', 'DRIVER_ARRIVED', 'IN_PROGRESS')"
        ),
    )


def downgrade() -> None:
    op.drop_index("uq_rides_one_active_per_driver", table_name="rides")
