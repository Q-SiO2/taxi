"""Add restricted support triage and separate safety reports.

Revision ID: 20260824_0032
Revises: 20260824_0031
Create Date: 2026-08-24
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260824_0032"
down_revision = "20260824_0031"
branch_labels = None
depends_on = None


support_priority = postgresql.ENUM(
    "LOW", "NORMAL", "HIGH", "URGENT", name="support_priority", create_type=False
)
support_resolution = postgresql.ENUM(
    "INFORMATION_PROVIDED",
    "ACTION_TAKEN",
    "REFUND_RECORDED",
    "DUPLICATE",
    "OUT_OF_SCOPE",
    "NO_ACTION",
    name="support_resolution_code",
    create_type=False,
)
case_note_visibility = postgresql.ENUM(
    "INTERNAL", "PARTICIPANT", name="case_note_visibility", create_type=False
)
safety_category = postgresql.ENUM(
    "IMMEDIATE_DANGER",
    "HARASSMENT",
    "ASSAULT",
    "UNSAFE_DRIVING",
    "DISCRIMINATION",
    "VEHICLE_SAFETY",
    "OTHER_SAFETY",
    name="safety_report_category",
    create_type=False,
)
safety_status = postgresql.ENUM(
    "SUBMITTED",
    "ACKNOWLEDGED",
    "ESCALATED",
    "RESOLVED",
    "CLOSED",
    name="safety_report_status",
    create_type=False,
)
safety_resolution = postgresql.ENUM(
    "SAFETY_ACTION_TAKEN",
    "REFERRED_TO_AUTHORITIES",
    "INFORMATION_PROVIDED",
    "DUPLICATE",
    "NO_PLATFORM_ACTION",
    name="safety_resolution_code",
    create_type=False,
)


def upgrade() -> None:
    op.execute("ALTER TYPE support_ticket_status ADD VALUE IF NOT EXISTS 'IN_PROGRESS'")
    op.execute("ALTER TYPE support_ticket_status ADD VALUE IF NOT EXISTS 'RESOLVED'")
    op.execute("ALTER TYPE support_ticket_status ADD VALUE IF NOT EXISTS 'CLOSED'")
    support_priority.create(op.get_bind(), checkfirst=True)
    support_resolution.create(op.get_bind(), checkfirst=True)
    case_note_visibility.create(op.get_bind(), checkfirst=True)
    safety_category.create(op.get_bind(), checkfirst=True)
    safety_status.create(op.get_bind(), checkfirst=True)
    safety_resolution.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "support_tickets",
        sa.Column(
            "priority",
            support_priority,
            nullable=False,
            server_default=sa.text("'NORMAL'::support_priority"),
        ),
    )
    op.alter_column("support_tickets", "priority", server_default=None)
    op.add_column(
        "support_tickets",
        sa.Column("assigned_to_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "support_tickets",
        sa.Column("response_due_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE support_tickets SET response_due_at = created_at + interval '24 hours' "
        "WHERE response_due_at IS NULL"
    )
    op.alter_column("support_tickets", "response_due_at", nullable=False)
    op.add_column(
        "support_tickets",
        sa.Column("first_responded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "support_tickets",
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "support_tickets",
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "support_tickets",
        sa.Column("resolution_code", support_resolution, nullable=True),
    )
    op.add_column("support_tickets", sa.Column("latest_public_message", sa.Text(), nullable=True))
    op.add_column(
        "support_tickets",
        sa.Column("latest_public_message_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "support_tickets",
        sa.Column(
            "retention_policy_version",
            sa.String(length=40),
            nullable=False,
            server_default="support-launch-v1",
        ),
    )
    op.alter_column("support_tickets", "retention_policy_version", server_default=None)
    op.add_column(
        "support_tickets",
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_support_tickets_assigned_to_user_id_users",
        "support_tickets",
        "users",
        ["assigned_to_user_id"],
        ["id"],
    )
    op.create_index("ix_support_tickets_priority", "support_tickets", ["priority"])
    op.create_index(
        "ix_support_tickets_assigned_to_user_id",
        "support_tickets",
        ["assigned_to_user_id"],
    )
    op.create_index(
        "ix_support_tickets_status_response_due_at",
        "support_tickets",
        ["status", "response_due_at"],
    )

    op.create_table(
        "support_ticket_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visibility", case_note_visibility, nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["support_tickets.id"],
            name="fk_support_ticket_notes_ticket_id_support_tickets",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["author_user_id"],
            ["users.id"],
            name="fk_support_ticket_notes_author_user_id_users",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_support_ticket_notes"),
    )
    op.create_index(
        "ix_support_ticket_notes_ticket_id",
        "support_ticket_notes",
        ["ticket_id"],
    )
    op.create_index(
        "ix_support_ticket_notes_author_user_id",
        "support_ticket_notes",
        ["author_user_id"],
    )

    op.create_table(
        "safety_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ride_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reporter_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reported_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_support_ticket_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category", safety_category, nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "status",
            safety_status,
            nullable=False,
            server_default=sa.text("'SUBMITTED'::safety_report_status"),
        ),
        sa.Column("priority", support_priority, nullable=False),
        sa.Column("assigned_to_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("response_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_code", safety_resolution, nullable=True),
        sa.Column("latest_public_message", sa.Text(), nullable=True),
        sa.Column("latest_public_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "retention_policy_version",
            sa.String(length=40),
            nullable=False,
            server_default="safety-launch-v1",
        ),
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["ride_id"], ["rides.id"], name="fk_safety_reports_ride_id_rides"
        ),
        sa.ForeignKeyConstraint(
            ["reporter_user_id"],
            ["users.id"],
            name="fk_safety_reports_reporter_user_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["reported_user_id"],
            ["users.id"],
            name="fk_safety_reports_reported_user_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["source_support_ticket_id"],
            ["support_tickets.id"],
            name="fk_safety_reports_source_support_ticket_id_support_tickets",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_to_user_id"],
            ["users.id"],
            name="fk_safety_reports_assigned_to_user_id_users",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_safety_reports"),
        sa.UniqueConstraint(
            "source_support_ticket_id",
            name="uq_safety_reports_source_support_ticket_id",
        ),
    )
    for column in (
        "ride_id",
        "reporter_user_id",
        "reported_user_id",
        "priority",
        "assigned_to_user_id",
    ):
        op.create_index(f"ix_safety_reports_{column}", "safety_reports", [column])
    op.create_index(
        "ix_safety_reports_status_response_due_at",
        "safety_reports",
        ["status", "response_due_at"],
    )

    op.create_table(
        "safety_report_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visibility", case_note_visibility, nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["safety_reports.id"],
            name="fk_safety_report_notes_report_id_safety_reports",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["author_user_id"],
            ["users.id"],
            name="fk_safety_report_notes_author_user_id_users",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_safety_report_notes"),
    )
    op.create_index(
        "ix_safety_report_notes_report_id",
        "safety_report_notes",
        ["report_id"],
    )
    op.create_index(
        "ix_safety_report_notes_author_user_id",
        "safety_report_notes",
        ["author_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_safety_report_notes_author_user_id", table_name="safety_report_notes")
    op.drop_index("ix_safety_report_notes_report_id", table_name="safety_report_notes")
    op.drop_table("safety_report_notes")
    op.drop_index("ix_safety_reports_status_response_due_at", table_name="safety_reports")
    for column in reversed(
        ("ride_id", "reporter_user_id", "reported_user_id", "priority", "assigned_to_user_id")
    ):
        op.drop_index(f"ix_safety_reports_{column}", table_name="safety_reports")
    op.drop_table("safety_reports")

    op.drop_index("ix_support_ticket_notes_author_user_id", table_name="support_ticket_notes")
    op.drop_index("ix_support_ticket_notes_ticket_id", table_name="support_ticket_notes")
    op.drop_table("support_ticket_notes")
    op.drop_index("ix_support_tickets_status_response_due_at", table_name="support_tickets")
    op.drop_index("ix_support_tickets_assigned_to_user_id", table_name="support_tickets")
    op.drop_index("ix_support_tickets_priority", table_name="support_tickets")
    op.drop_constraint(
        "fk_support_tickets_assigned_to_user_id_users",
        "support_tickets",
        type_="foreignkey",
    )
    for column in (
        "retention_until",
        "retention_policy_version",
        "latest_public_message_at",
        "latest_public_message",
        "resolution_code",
        "closed_at",
        "resolved_at",
        "first_responded_at",
        "response_due_at",
        "assigned_to_user_id",
        "priority",
    ):
        op.drop_column("support_tickets", column)

    safety_resolution.drop(op.get_bind(), checkfirst=True)
    safety_status.drop(op.get_bind(), checkfirst=True)
    safety_category.drop(op.get_bind(), checkfirst=True)
    case_note_visibility.drop(op.get_bind(), checkfirst=True)
    support_resolution.drop(op.get_bind(), checkfirst=True)
    support_priority.drop(op.get_bind(), checkfirst=True)

    # Removing enum values is impossible in place. The cast intentionally fails
    # if non-OPEN support tickets still exist, avoiding a destructive downgrade.
    op.execute("CREATE TYPE support_ticket_status_open_only AS ENUM ('OPEN')")
    op.execute(
        "ALTER TABLE support_tickets ALTER COLUMN status DROP DEFAULT"
    )
    op.execute(
        "ALTER TABLE support_tickets ALTER COLUMN status TYPE support_ticket_status_open_only "
        "USING status::text::support_ticket_status_open_only"
    )
    op.execute("DROP TYPE support_ticket_status")
    op.execute("ALTER TYPE support_ticket_status_open_only RENAME TO support_ticket_status")
    op.execute("ALTER TABLE support_tickets ALTER COLUMN status SET DEFAULT 'OPEN'")
