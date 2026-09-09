"""Add durable maker-checker requests for scoped staff grants.

Revision ID: 20260907_0049
Revises: 20260903_0048
Create Date: 2026-09-07
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260907_0049"
down_revision = "20260903_0048"
branch_labels = None
depends_on = None


ROLE_SCOPE_CHECK = (
    "(role_template = 'PLATFORM_ADMIN' AND market_id IS NOT NULL "
    "AND operator_id IS NULL AND city_id IS NULL) OR "
    "(role_template = 'OPERATOR_ADMIN' AND market_id IS NULL "
    "AND operator_id IS NOT NULL AND city_id IS NULL) OR "
    "(role_template IN ('CITY_MANAGER', 'DRIVER_REVIEWER', 'PRICING_MANAGER', "
    "'PAYMENT_RECONCILER', 'SUPPORT_AGENT', 'SAFETY_RESPONDER', 'ANALYST') "
    "AND market_id IS NULL AND operator_id IS NULL AND city_id IS NOT NULL)"
)


def upgrade() -> None:
    op.create_table(
        "administrative_grant_change_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="PENDING", nullable=False),
        sa.Column("requester_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decided_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_template", sa.String(length=32), nullable=False),
        sa.Column("market_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("operator_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_grant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resulting_grant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.String(length=240), nullable=False),
        sa.Column("decision_reason", sa.String(length=240), nullable=True),
        sa.Column("requested_grant_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("optimistic_version", sa.SmallInteger(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "action IN ('CREATE', 'REVOKE')",
            name="ck_administrative_grant_change_requests_action",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED')",
            name="ck_administrative_grant_change_requests_status",
        ),
        sa.CheckConstraint(
            ROLE_SCOPE_CHECK,
            name="ck_administrative_grant_change_requests_template_scope",
        ),
        sa.CheckConstraint(
            "(action = 'CREATE' AND source_grant_id IS NULL) OR "
            "(action = 'REVOKE' AND source_grant_id IS NOT NULL)",
            name="ck_administrative_grant_change_requests_action_source",
        ),
        sa.CheckConstraint(
            "requester_user_id <> target_user_id",
            name="ck_administrative_grant_change_requests_no_self_request",
        ),
        sa.CheckConstraint(
            "(status = 'PENDING' AND decided_by_user_id IS NULL "
            "AND decided_at IS NULL AND decision_reason IS NULL "
            "AND resulting_grant_id IS NULL) OR "
            "(status IN ('APPROVED', 'REJECTED') "
            "AND decided_by_user_id IS NOT NULL AND decided_at IS NOT NULL "
            "AND decision_reason IS NOT NULL "
            "AND decided_by_user_id <> requester_user_id "
            "AND decided_by_user_id <> target_user_id "
            "AND ((status = 'APPROVED' AND action = 'CREATE' "
            "AND resulting_grant_id IS NOT NULL) OR "
            "(status = 'APPROVED' AND action = 'REVOKE' "
            "AND resulting_grant_id IS NULL) OR "
            "(status = 'REJECTED' AND resulting_grant_id IS NULL))) OR "
            "(status = 'CANCELLED' AND decided_by_user_id = requester_user_id "
            "AND decided_at IS NOT NULL AND decision_reason IS NOT NULL "
            "AND resulting_grant_id IS NULL)",
            name="ck_administrative_grant_change_requests_decision_state",
        ),
        sa.CheckConstraint(
            "requested_grant_expires_at IS NULL "
            "OR requested_grant_expires_at > requested_at",
            name="ck_administrative_grant_change_requests_expiry_after_request",
        ),
        sa.CheckConstraint(
            "optimistic_version > 0",
            name="ck_administrative_grant_change_requests_version_positive",
        ),
        sa.ForeignKeyConstraint(
            ["requester_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["decided_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["operator_id"], ["operators.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["city_id"], ["cities.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["source_grant_id"], ["administrative_grants.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["resulting_grant_id"], ["administrative_grants.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resulting_grant_id"),
    )
    for column in (
        "action",
        "status",
        "requester_user_id",
        "target_user_id",
        "market_id",
        "operator_id",
        "city_id",
    ):
        op.create_index(
            f"ix_administrative_grant_change_requests_{column}",
            "administrative_grant_change_requests",
            [column],
        )
    op.create_index(
        "uq_administrative_grant_requests_pending_create_market",
        "administrative_grant_change_requests",
        ["target_user_id", "role_template", "market_id"],
        unique=True,
        postgresql_where=sa.text("status = 'PENDING' AND action = 'CREATE' AND market_id IS NOT NULL"),
    )
    op.create_index(
        "uq_administrative_grant_requests_pending_create_operator",
        "administrative_grant_change_requests",
        ["target_user_id", "role_template", "operator_id"],
        unique=True,
        postgresql_where=sa.text("status = 'PENDING' AND action = 'CREATE' AND operator_id IS NOT NULL"),
    )
    op.create_index(
        "uq_administrative_grant_requests_pending_create_city",
        "administrative_grant_change_requests",
        ["target_user_id", "role_template", "city_id"],
        unique=True,
        postgresql_where=sa.text("status = 'PENDING' AND action = 'CREATE' AND city_id IS NOT NULL"),
    )
    op.create_index(
        "uq_administrative_grant_requests_pending_revoke",
        "administrative_grant_change_requests",
        ["source_grant_id"],
        unique=True,
        postgresql_where=sa.text("status = 'PENDING' AND action = 'REVOKE'"),
    )


def downgrade() -> None:
    op.drop_table("administrative_grant_change_requests")
