"""Give each push provider token one current account owner.

Revision ID: 20260812_0025
Revises: 20260812_0024
Create Date: 2026-08-12
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260812_0025"
down_revision = "20260812_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("one_device_token_per_user", "device_tokens", type_="unique")
    op.execute(
        "CREATE TYPE device_registration_kind AS ENUM "
        "('FIREBASE_INSTALLATION_ID', 'LEGACY_FCM_TOKEN')"
    )
    op.add_column(
        "device_tokens",
        sa.Column(
            "registration_kind",
            postgresql.ENUM(
                "FIREBASE_INSTALLATION_ID",
                "LEGACY_FCM_TOKEN",
                name="device_registration_kind",
                create_type=False,
            ),
            server_default="LEGACY_FCM_TOKEN",
            nullable=False,
        ),
    )
    op.add_column(
        "device_tokens",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_device_tokens_session_id_sessions",
        "device_tokens",
        "sessions",
        ["session_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_device_tokens_session_id", "device_tokens", ["session_id"])
    # Historical versions allowed one Firebase token to be active for several
    # accounts. Keep only the row most recently seen by this app installation
    # before enforcing atomic ownership transfer for all future registrations.
    op.execute(
        sa.text(
            """
            WITH ranked_tokens AS (
                SELECT
                    id,
                    row_number() OVER (
                        PARTITION BY registration_kind, token
                        ORDER BY last_seen_at DESC, created_at DESC, id DESC
                    ) AS ownership_rank
                FROM device_tokens
            )
            DELETE FROM device_tokens AS duplicate
            USING ranked_tokens
            WHERE duplicate.id = ranked_tokens.id
              AND ranked_tokens.ownership_rank > 1
            """
        )
    )
    op.create_unique_constraint(
        "one_owner_per_push_registration",
        "device_tokens",
        ["registration_kind", "token"],
    )


def downgrade() -> None:
    op.drop_constraint("one_owner_per_push_registration", "device_tokens", type_="unique")
    op.drop_index("ix_device_tokens_session_id", table_name="device_tokens")
    op.drop_constraint("fk_device_tokens_session_id_sessions", "device_tokens", type_="foreignkey")
    op.drop_column("device_tokens", "session_id")
    op.drop_column("device_tokens", "registration_kind")
    op.execute("DROP TYPE device_registration_kind")
    op.create_unique_constraint("one_device_token_per_user", "device_tokens", ["user_id", "token"])
