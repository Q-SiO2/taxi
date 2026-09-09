"""Add durable, privacy-minimized overdue case alerts.

Revision ID: 20260830_0041
Revises: 20260830_0040
Create Date: 2026-08-30
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260830_0041"
down_revision = "20260830_0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "case_overdue_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "city_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "support_ticket_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("support_tickets.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "safety_report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("safety_reports.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("response_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivery_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_delivery_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "acknowledged_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(support_ticket_id IS NOT NULL)::integer + "
            "(safety_report_id IS NOT NULL)::integer = 1",
            name="case_overdue_alert_exactly_one_case",
        ),
        sa.CheckConstraint(
            "severity IN ('HIGH', 'URGENT')",
            name="case_overdue_alert_severity",
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'ACKNOWLEDGED', 'RESOLVED')",
            name="case_overdue_alert_status",
        ),
        sa.CheckConstraint(
            "delivery_attempts >= 0",
            name="case_overdue_alert_delivery_attempts",
        ),
        sa.UniqueConstraint("support_ticket_id", name="uq_case_overdue_alert_support_ticket"),
        sa.UniqueConstraint("safety_report_id", name="uq_case_overdue_alert_safety_report"),
    )
    op.create_index("ix_case_overdue_alerts_city_id", "case_overdue_alerts", ["city_id"])
    op.create_index(
        "ix_case_overdue_alerts_delivery",
        "case_overdue_alerts",
        ["status", "next_delivery_at"],
    )
    op.create_index(
        "ix_case_overdue_alerts_unresolved",
        "case_overdue_alerts",
        ["city_id", "status", "first_detected_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_case_overdue_alerts_unresolved", table_name="case_overdue_alerts")
    op.drop_index("ix_case_overdue_alerts_delivery", table_name="case_overdue_alerts")
    op.drop_index("ix_case_overdue_alerts_city_id", table_name="case_overdue_alerts")
    op.drop_table("case_overdue_alerts")
