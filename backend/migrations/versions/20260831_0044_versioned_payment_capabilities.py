"""Add scoped, versioned payment capabilities and financial provenance.

Revision ID: 20260831_0044
Revises: 20260830_0043
Create Date: 2026-08-31
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260831_0044"
down_revision = "20260830_0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_recipient_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(length=80), nullable=False),
        sa.Column("recipient_name", sa.String(length=120), nullable=False),
        sa.Column("bank_account", sa.String(length=120), nullable=True),
        sa.Column("wallet_id", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("optimistic_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("verified_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("retired_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("bank_account IS NOT NULL OR wallet_id IS NOT NULL", name="payment_recipient_has_destination"),
        sa.CheckConstraint("optimistic_version >= 1", name="payment_recipient_optimistic_version_positive"),
        sa.CheckConstraint("status IN ('DRAFT', 'VERIFIED', 'RETIRED')", name="payment_recipient_status_valid"),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], name="fk_payment_recipient_city", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["operator_id"], ["operators.id"], name="fk_payment_recipient_operator", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], name="fk_payment_recipient_creator", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["verified_by_user_id"], ["users.id"], name="fk_payment_recipient_verifier", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["retired_by_user_id"], ["users.id"], name="fk_payment_recipient_retirer", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_payment_recipient_accounts"),
        sa.UniqueConstraint("city_id", "operator_id", "label", name="uq_payment_recipient_scope_label"),
    )
    op.create_index("ix_payment_recipient_city", "payment_recipient_accounts", ["city_id"])
    op.create_index("ix_payment_recipient_operator", "payment_recipient_accounts", ["operator_id"])
    op.create_index("ix_payment_recipient_status", "payment_recipient_accounts", ["status"])

    op.create_table(
        "payment_capability_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_type", sa.String(length=20), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("cash_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("manual_transfer_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("recipient_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("optimistic_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submitted_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("activated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("cash_enabled", name="payment_capability_cash_required"),
        sa.CheckConstraint(
            "service_type IN ('ON_DEMAND', 'FIXED_ROUTE', 'SCHEDULED')",
            name="payment_capability_service_type_valid",
        ),
        sa.CheckConstraint(
            "(manual_transfer_enabled AND recipient_account_id IS NOT NULL) OR "
            "(NOT manual_transfer_enabled AND recipient_account_id IS NULL)",
            name="payment_capability_transfer_recipient_consistency",
        ),
        sa.CheckConstraint("effective_until IS NULL OR effective_until > effective_from", name="payment_capability_effective_range"),
        sa.CheckConstraint("optimistic_version >= 1", name="payment_capability_optimistic_version_positive"),
        sa.CheckConstraint("status IN ('DRAFT', 'IN_REVIEW', 'APPROVED', 'ACTIVE', 'REPLACED')", name="payment_capability_status_valid"),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], name="fk_payment_capability_city", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["operator_id"], ["operators.id"], name="fk_payment_capability_operator", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recipient_account_id"], ["payment_recipient_accounts.id"], name="fk_payment_capability_recipient", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], name="fk_payment_capability_creator", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["submitted_by_user_id"], ["users.id"], name="fk_payment_capability_submitter", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], name="fk_payment_capability_approver", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["activated_by_user_id"], ["users.id"], name="fk_payment_capability_activator", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_payment_capability_versions"),
        sa.UniqueConstraint("city_id", "operator_id", "service_type", "version", name="uq_payment_capability_scope_version"),
    )
    op.create_index("ix_payment_capability_city", "payment_capability_versions", ["city_id"])
    op.create_index("ix_payment_capability_operator", "payment_capability_versions", ["operator_id"])
    op.create_index("ix_payment_capability_status", "payment_capability_versions", ["status"])
    op.create_index(
        "ix_payment_capability_active_scope",
        "payment_capability_versions",
        ["city_id", "operator_id", "service_type"],
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    op.add_column(
        "city_configuration_services",
        sa.Column("payment_capability_version_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_city_configuration_service_payment_capability",
        "city_configuration_services",
        "payment_capability_versions",
        ["payment_capability_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    for table_name in ("rides", "payments"):
        op.add_column(table_name, sa.Column("payment_capability_version_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.add_column(table_name, sa.Column("payment_recipient_account_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(
            f"fk_{table_name}_payment_capability",
            table_name,
            "payment_capability_versions",
            ["payment_capability_version_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_foreign_key(
            f"fk_{table_name}_payment_recipient",
            table_name,
            "payment_recipient_accounts",
            ["payment_recipient_account_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    op.add_column("payments", sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("payments", sa.Column("operator_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute(
        "UPDATE payments AS p SET city_id = r.city_id, operator_id = r.operator_id "
        "FROM rides AS r WHERE r.id = p.ride_id"
    )
    op.alter_column("payments", "city_id", nullable=False)
    op.alter_column("payments", "operator_id", nullable=False)
    op.create_foreign_key("fk_payments_city", "payments", "cities", ["city_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_payments_operator", "payments", "operators", ["operator_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_payments_city_status", "payments", ["city_id", "status"])
    op.create_index("ix_payments_operator", "payments", ["operator_id"])

    op.add_column("payment_refunds", sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("payment_refunds", sa.Column("operator_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute(
        "UPDATE payment_refunds AS pr SET city_id = p.city_id, operator_id = p.operator_id "
        "FROM payments AS p WHERE p.id = pr.payment_id"
    )
    op.alter_column("payment_refunds", "city_id", nullable=False)
    op.alter_column("payment_refunds", "operator_id", nullable=False)
    op.create_foreign_key("fk_payment_refunds_city", "payment_refunds", "cities", ["city_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_payment_refunds_operator", "payment_refunds", "operators", ["operator_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_payment_refunds_city", "payment_refunds", ["city_id"])
    op.create_index("ix_payment_refunds_operator", "payment_refunds", ["operator_id"])


def downgrade() -> None:
    op.drop_index("ix_payment_refunds_operator", table_name="payment_refunds")
    op.drop_index("ix_payment_refunds_city", table_name="payment_refunds")
    op.drop_constraint("fk_payment_refunds_operator", "payment_refunds", type_="foreignkey")
    op.drop_constraint("fk_payment_refunds_city", "payment_refunds", type_="foreignkey")
    op.drop_column("payment_refunds", "operator_id")
    op.drop_column("payment_refunds", "city_id")

    op.drop_index("ix_payments_operator", table_name="payments")
    op.drop_index("ix_payments_city_status", table_name="payments")
    op.drop_constraint("fk_payments_operator", "payments", type_="foreignkey")
    op.drop_constraint("fk_payments_city", "payments", type_="foreignkey")
    op.drop_column("payments", "operator_id")
    op.drop_column("payments", "city_id")
    for table_name in ("payments", "rides"):
        op.drop_constraint(f"fk_{table_name}_payment_recipient", table_name, type_="foreignkey")
        op.drop_constraint(f"fk_{table_name}_payment_capability", table_name, type_="foreignkey")
        op.drop_column(table_name, "payment_recipient_account_id")
        op.drop_column(table_name, "payment_capability_version_id")

    op.drop_constraint("fk_city_configuration_service_payment_capability", "city_configuration_services", type_="foreignkey")
    op.drop_column("city_configuration_services", "payment_capability_version_id")
    op.drop_index("ix_payment_capability_active_scope", table_name="payment_capability_versions")
    op.drop_index("ix_payment_capability_status", table_name="payment_capability_versions")
    op.drop_index("ix_payment_capability_operator", table_name="payment_capability_versions")
    op.drop_index("ix_payment_capability_city", table_name="payment_capability_versions")
    op.drop_table("payment_capability_versions")
    op.drop_index("ix_payment_recipient_status", table_name="payment_recipient_accounts")
    op.drop_index("ix_payment_recipient_operator", table_name="payment_recipient_accounts")
    op.drop_index("ix_payment_recipient_city", table_name="payment_recipient_accounts")
    op.drop_table("payment_recipient_accounts")
