"""Add scoped administrative grants and isolated operations sessions.

Revision ID: 20260824_0034
Revises: 20260824_0033
Create Date: 2026-08-24
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260824_0034"
down_revision = "20260824_0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    role_template = sa.Enum(
        "PLATFORM_ADMIN",
        "OPERATOR_ADMIN",
        "CITY_MANAGER",
        "DRIVER_REVIEWER",
        "PRICING_MANAGER",
        "PAYMENT_RECONCILER",
        "SUPPORT_AGENT",
        "SAFETY_RESPONDER",
        "ANALYST",
        name="administrative_role_template",
        native_enum=False,
        create_constraint=True,
        length=32,
    )
    op.create_table(
        "administrative_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_template", role_template, nullable=False),
        sa.Column("market_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("operator_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("granted_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("grant_reason", sa.String(length=240), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("revocation_reason", sa.String(length=240), nullable=True),
        sa.CheckConstraint(
            "(role_template = 'PLATFORM_ADMIN' AND market_id IS NOT NULL "
            "AND operator_id IS NULL AND city_id IS NULL) OR "
            "(role_template = 'OPERATOR_ADMIN' AND market_id IS NULL "
            "AND operator_id IS NOT NULL AND city_id IS NULL) OR "
            "(role_template IN ('CITY_MANAGER', 'DRIVER_REVIEWER', 'PRICING_MANAGER', "
            "'PAYMENT_RECONCILER', 'SUPPORT_AGENT', 'SAFETY_RESPONDER', 'ANALYST') "
            "AND market_id IS NULL AND operator_id IS NULL AND city_id IS NOT NULL)",
            name="ck_administrative_grants_administrative_grant_template_scope",
        ),
        sa.CheckConstraint(
            "expires_at IS NULL OR expires_at > granted_at",
            name="ck_admin_grant_expiry_after_grant",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_administrative_grants_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["market_id"],
            ["markets.id"],
            name="fk_administrative_grants_market_id_markets",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["operator_id"],
            ["operators.id"],
            name="fk_administrative_grants_operator_id_operators",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["city_id"],
            ["cities.id"],
            name="fk_administrative_grants_city_id_cities",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["granted_by_user_id"],
            ["users.id"],
            name="fk_administrative_grants_granted_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["revoked_by_user_id"],
            ["users.id"],
            name="fk_administrative_grants_revoked_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_administrative_grants"),
    )
    op.create_index("ix_administrative_grants_user_id", "administrative_grants", ["user_id"])
    op.create_index("ix_administrative_grants_role_template", "administrative_grants", ["role_template"])
    op.create_index("ix_administrative_grants_market_id", "administrative_grants", ["market_id"])
    op.create_index("ix_administrative_grants_operator_id", "administrative_grants", ["operator_id"])
    op.create_index("ix_administrative_grants_city_id", "administrative_grants", ["city_id"])
    op.create_index(
        "uq_administrative_grants_active_market_scope",
        "administrative_grants",
        ["user_id", "role_template", "market_id"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL AND market_id IS NOT NULL"),
    )
    op.create_index(
        "uq_administrative_grants_active_operator_scope",
        "administrative_grants",
        ["user_id", "role_template", "operator_id"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL AND operator_id IS NOT NULL"),
    )
    op.create_index(
        "uq_administrative_grants_active_city_scope",
        "administrative_grants",
        ["user_id", "role_template", "city_id"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL AND city_id IS NOT NULL"),
    )

    op.create_table(
        "operations_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=False),
        sa.Column("refresh_family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refresh_rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mfa_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("device_label", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_operations_sessions_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_operations_sessions"),
        sa.UniqueConstraint("refresh_token_hash", name="uq_operations_sessions_refresh_token_hash"),
    )
    op.create_index("ix_operations_sessions_user_id", "operations_sessions", ["user_id"])
    op.create_index("ix_operations_sessions_refresh_family_id", "operations_sessions", ["refresh_family_id"])

    op.add_column("audit_logs", sa.Column("market_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("audit_logs", sa.Column("operator_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("audit_logs", sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_audit_logs_market_id_markets",
        "audit_logs",
        "markets",
        ["market_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_audit_logs_operator_id_operators",
        "audit_logs",
        "operators",
        ["operator_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_audit_logs_city_id_cities",
        "audit_logs",
        "cities",
        ["city_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_audit_logs_market_id", "audit_logs", ["market_id"])
    op.create_index("ix_audit_logs_operator_id", "audit_logs", ["operator_id"])
    op.create_index("ix_audit_logs_city_id", "audit_logs", ["city_id"])
    op.create_index(
        "ix_audit_logs_city_created_at_id",
        "audit_logs",
        ["city_id", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_city_created_at_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_city_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_operator_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_market_id", table_name="audit_logs")
    op.drop_constraint("fk_audit_logs_city_id_cities", "audit_logs", type_="foreignkey")
    op.drop_constraint("fk_audit_logs_operator_id_operators", "audit_logs", type_="foreignkey")
    op.drop_constraint("fk_audit_logs_market_id_markets", "audit_logs", type_="foreignkey")
    op.drop_column("audit_logs", "city_id")
    op.drop_column("audit_logs", "operator_id")
    op.drop_column("audit_logs", "market_id")

    op.drop_table("operations_sessions")
    op.drop_index("uq_administrative_grants_active_city_scope", table_name="administrative_grants")
    op.drop_index("uq_administrative_grants_active_operator_scope", table_name="administrative_grants")
    op.drop_index("uq_administrative_grants_active_market_scope", table_name="administrative_grants")
    op.drop_table("administrative_grants")
