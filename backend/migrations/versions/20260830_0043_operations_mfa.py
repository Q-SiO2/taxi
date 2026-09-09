"""Add encrypted operations TOTP, recovery codes, and login challenges.

Revision ID: 20260830_0043
Revises: 20260830_0042
Create Date: 2026-08-30
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260830_0043"
down_revision = "20260830_0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "operations_sessions",
        sa.Column("mfa_method", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "operations_sessions",
        sa.Column("csrf_token_hash", sa.String(length=64), nullable=True),
    )
    op.create_check_constraint(
        "operations_session_csrf_hash",
        "operations_sessions",
        "csrf_token_hash IS NULL OR csrf_token_hash ~ '^[0-9a-f]{64}$'",
    )
    op.create_check_constraint(
        "operations_session_mfa_state",
        "operations_sessions",
        "(mfa_verified_at IS NULL AND mfa_method IS NULL) OR "
        "(mfa_verified_at IS NOT NULL AND mfa_method IN ('TOTP', 'RECOVERY_CODE'))",
    )

    op.create_table(
        "operations_mfa_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("encrypted_secret", sa.LargeBinary(), nullable=False),
        sa.Column("secret_nonce", sa.LargeBinary(length=12), nullable=False),
        sa.Column("last_accepted_counter", sa.BigInteger(), nullable=True),
        sa.Column("enabled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "octet_length(secret_nonce) = 12",
            name="operations_mfa_credential_nonce_length",
        ),
        sa.CheckConstraint(
            "octet_length(encrypted_secret) >= 36",
            name="operations_mfa_credential_ciphertext_length",
        ),
        sa.CheckConstraint(
            "last_accepted_counter IS NULL OR last_accepted_counter >= 0",
            name="operations_mfa_credential_counter",
        ),
    )

    op.create_table(
        "operations_mfa_recovery_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "credential_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("operations_mfa_credentials.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "code_hash ~ '^[0-9a-f]{64}$'",
            name="operations_mfa_recovery_code_hash",
        ),
    )
    op.create_index(
        "ix_operations_mfa_recovery_codes_available",
        "operations_mfa_recovery_codes",
        ["credential_id", "used_at"],
    )

    op.create_table(
        "operations_mfa_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_count", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("device_label", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "attempt_count BETWEEN 0 AND 5",
            name="operations_mfa_challenge_attempt_count",
        ),
        sa.CheckConstraint(
            "expires_at > created_at",
            name="operations_mfa_challenge_expiry",
        ),
    )
    op.create_index(
        "ix_operations_mfa_challenges_user_active",
        "operations_mfa_challenges",
        ["user_id", "consumed_at", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_operations_mfa_challenges_user_active",
        table_name="operations_mfa_challenges",
    )
    op.drop_table("operations_mfa_challenges")
    op.drop_index(
        "ix_operations_mfa_recovery_codes_available",
        table_name="operations_mfa_recovery_codes",
    )
    op.drop_table("operations_mfa_recovery_codes")
    op.drop_table("operations_mfa_credentials")
    op.drop_constraint(
        "ck_operations_sessions_operations_session_mfa_state",
        "operations_sessions",
        type_="check",
    )
    op.drop_constraint(
        "ck_operations_sessions_operations_session_csrf_hash",
        "operations_sessions",
        type_="check",
    )
    op.drop_column("operations_sessions", "csrf_token_hash")
    op.drop_column("operations_sessions", "mfa_method")
