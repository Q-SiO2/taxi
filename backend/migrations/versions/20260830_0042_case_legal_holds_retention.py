"""Add legal holds and auditable case data-erasure processing.

Revision ID: 20260830_0042
Revises: 20260830_0041
Create Date: 2026-08-30
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260830_0042"
down_revision = "20260830_0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "case_legal_holds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("support_ticket_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=True),
        sa.Column("safety_report_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("safety_reports.id", ondelete="CASCADE"), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("reason_code", sa.String(length=40), nullable=False),
        sa.Column("authority_reference", sa.String(length=240), nullable=False),
        sa.Column("placed_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("placed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("review_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("release_reason_code", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(support_ticket_id IS NOT NULL)::integer + (safety_report_id IS NOT NULL)::integer = 1",
            name="case_legal_hold_exactly_one_case",
        ),
        sa.CheckConstraint("status IN ('ACTIVE', 'RELEASED')", name="case_legal_hold_status"),
        sa.CheckConstraint(
            "reason_code IN ('LITIGATION', 'REGULATORY_REQUEST', 'LAW_ENFORCEMENT_REQUEST', "
            "'DISPUTE_PRESERVATION', 'OTHER_LEGAL_OBLIGATION')",
            name="case_legal_hold_reason_code",
        ),
        sa.CheckConstraint("review_due_at > placed_at", name="case_legal_hold_review_after_placement"),
        sa.CheckConstraint(
            "(status = 'ACTIVE' AND released_by_user_id IS NULL AND released_at IS NULL AND release_reason_code IS NULL) OR "
            "(status = 'RELEASED' AND released_by_user_id IS NOT NULL AND released_at IS NOT NULL AND "
            "release_reason_code IN ('OBLIGATION_ENDED', 'REQUEST_WITHDRAWN', 'SUPERSEDED', 'PLACED_IN_ERROR'))",
            name="case_legal_hold_release_state",
        ),
    )
    op.create_index("ix_case_legal_holds_city_status", "case_legal_holds", ["city_id", "status", "review_due_at"])
    op.create_index(
        "uq_case_legal_holds_active_support",
        "case_legal_holds",
        ["support_ticket_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE' AND support_ticket_id IS NOT NULL"),
    )
    op.create_index(
        "uq_case_legal_holds_active_safety",
        "case_legal_holds",
        ["safety_report_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE' AND safety_report_id IS NOT NULL"),
    )

    for table_name in ("support_tickets", "safety_reports"):
        op.add_column(table_name, sa.Column("retention_action", sa.String(length=32), nullable=True))
        op.add_column(table_name, sa.Column("retention_processed_at", sa.DateTime(timezone=True), nullable=True))
        op.create_check_constraint(
            f"{table_name}_retention_state",
            table_name,
            "(retention_action IS NULL AND retention_processed_at IS NULL) OR "
            "(retention_action = 'PERSONAL_DATA_ERASED' AND retention_processed_at IS NOT NULL)",
        )
        op.create_index(
            f"ix_{table_name}_retention_due",
            table_name,
            ["retention_processed_at", "retention_until"],
        )

    op.alter_column("support_tickets", "user_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    op.alter_column("safety_reports", "ride_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    op.alter_column("safety_reports", "reporter_user_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)

    op.create_table(
        "case_retention_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("support_ticket_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("support_tickets.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("safety_report_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("safety_reports.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("retention_policy_version", sa.String(length=40), nullable=False),
        sa.Column("retention_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("erased_note_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(support_ticket_id IS NOT NULL)::integer + (safety_report_id IS NOT NULL)::integer = 1",
            name="case_retention_action_exactly_one_case",
        ),
        sa.CheckConstraint("action = 'PERSONAL_DATA_ERASED'", name="case_retention_action_code"),
        sa.CheckConstraint("erased_note_count >= 0", name="case_retention_action_note_count"),
        sa.UniqueConstraint("support_ticket_id", name="uq_case_retention_actions_support_ticket"),
        sa.UniqueConstraint("safety_report_id", name="uq_case_retention_actions_safety_report"),
    )
    op.create_index("ix_case_retention_actions_city_executed", "case_retention_actions", ["city_id", "executed_at"])


def downgrade() -> None:
    op.drop_index("ix_case_retention_actions_city_executed", table_name="case_retention_actions")
    op.drop_table("case_retention_actions")
    op.alter_column("safety_reports", "reporter_user_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
    op.alter_column("safety_reports", "ride_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
    op.alter_column("support_tickets", "user_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
    for table_name in ("safety_reports", "support_tickets"):
        op.drop_index(f"ix_{table_name}_retention_due", table_name=table_name)
        op.drop_constraint(f"ck_{table_name}_{table_name}_retention_state", table_name, type_="check")
        op.drop_column(table_name, "retention_processed_at")
        op.drop_column(table_name, "retention_action")
    op.drop_index("uq_case_legal_holds_active_safety", table_name="case_legal_holds")
    op.drop_index("uq_case_legal_holds_active_support", table_name="case_legal_holds")
    op.drop_index("ix_case_legal_holds_city_status", table_name="case_legal_holds")
    op.drop_table("case_legal_holds")
