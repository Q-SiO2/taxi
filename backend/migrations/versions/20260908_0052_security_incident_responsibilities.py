"""Add versioned security-incident responsibility history.

Revision ID: 20260908_0052
Revises: 20260907_0051
Create Date: 2026-09-08
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260908_0052"
down_revision = "20260907_0051"
branch_labels = None
depends_on = None


RESPONSIBILITIES = (
    "SECURITY_RESPONSE_LEAD",
    "COMMUNICATIONS_LEAD",
    "OPERATIONS_LIAISON",
    "POSTMORTEM_OWNER",
)


def upgrade() -> None:
    op.drop_constraint(
        "ck_security_incident_timeline_entries_kind",
        "security_incident_timeline_entries",
        type_="check",
    )
    op.create_check_constraint(
        "ck_security_incident_timeline_entries_kind",
        "security_incident_timeline_entries",
        "kind IN ('INCIDENT_OPENED', 'EVIDENCE_LINKED', 'CONTAINMENT_ACTION', "
        "'COMMUNICATION_DECISION', 'RECOVERY_ACTION', 'POSTMORTEM_ACTION', "
        "'RESPONSIBILITY_CHANGED', 'STATUS_TRANSITION')",
    )
    op.create_table(
        "security_incident_responsibility_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("responsibility", sa.String(length=32), nullable=False),
        sa.Column("assigned_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assignment_reference", sa.String(length=160), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("release_reference", sa.String(length=160), nullable=True),
        sa.CheckConstraint(
            "responsibility IN "
            "('SECURITY_RESPONSE_LEAD', 'COMMUNICATIONS_LEAD', "
            "'OPERATIONS_LIAISON', 'POSTMORTEM_OWNER')",
            name="ck_security_incident_responsibility_assignments_role",
        ),
        sa.CheckConstraint(
            "(released_at IS NULL AND released_by_user_id IS NULL "
            "AND release_reference IS NULL) OR "
            "(released_at IS NOT NULL AND released_by_user_id IS NOT NULL "
            "AND release_reference IS NOT NULL)",
            name="ck_security_incident_responsibility_assignments_release_shape",
        ),
        sa.CheckConstraint(
            "released_at IS NULL OR released_at >= assigned_at",
            name="ck_security_incident_responsibility_assignments_release_after_assign",
        ),
        sa.ForeignKeyConstraint(
            ["incident_id"], ["security_incidents.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["assigned_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["assigned_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["released_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_security_incident_responsibilities_incident",
        "security_incident_responsibility_assignments",
        ["incident_id", "assigned_at"],
    )
    op.create_index(
        "ix_security_incident_responsibilities_assignee",
        "security_incident_responsibility_assignments",
        ["assigned_user_id", "released_at"],
    )
    op.create_index(
        "uq_security_incident_responsibilities_active_role",
        "security_incident_responsibility_assignments",
        ["incident_id", "responsibility"],
        unique=True,
        postgresql_where=sa.text("released_at IS NULL"),
    )
    op.execute(
        """
        INSERT INTO security_incident_responsibility_assignments (
            id,
            incident_id,
            responsibility,
            assigned_user_id,
            assigned_by_user_id,
            assignment_reference,
            assigned_at
        )
        SELECT
            md5('security-response-lead:' || id::text)::uuid,
            id,
            'SECURITY_RESPONSE_LEAD',
            lead_user_id,
            reported_by_user_id,
            'MIGRATION-0052-INITIAL-LEAD',
            opened_at
        FROM security_incidents
        """
    )
    op.execute(
        """
        CREATE FUNCTION guard_security_incident_responsibility_history()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'security incident responsibility history cannot be deleted'
                    USING ERRCODE = '55000';
            END IF;
            IF OLD.released_at IS NOT NULL
               OR NEW.id IS DISTINCT FROM OLD.id
               OR NEW.incident_id IS DISTINCT FROM OLD.incident_id
               OR NEW.responsibility IS DISTINCT FROM OLD.responsibility
               OR NEW.assigned_user_id IS DISTINCT FROM OLD.assigned_user_id
               OR NEW.assigned_by_user_id IS DISTINCT FROM OLD.assigned_by_user_id
               OR NEW.assignment_reference IS DISTINCT FROM OLD.assignment_reference
               OR NEW.assigned_at IS DISTINCT FROM OLD.assigned_at
               OR NEW.released_at IS NULL
               OR NEW.released_by_user_id IS NULL
               OR NEW.release_reference IS NULL THEN
                RAISE EXCEPTION 'security incident responsibility history is append-visible'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER security_incident_responsibility_history_guard
        BEFORE UPDATE OR DELETE ON security_incident_responsibility_assignments
        FOR EACH ROW EXECUTE FUNCTION guard_security_incident_responsibility_history()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS security_incident_responsibility_history_guard "
        "ON security_incident_responsibility_assignments"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS guard_security_incident_responsibility_history()"
    )
    op.drop_table("security_incident_responsibility_assignments")
    op.drop_constraint(
        "ck_security_incident_timeline_entries_kind",
        "security_incident_timeline_entries",
        type_="check",
    )
    op.create_check_constraint(
        "ck_security_incident_timeline_entries_kind",
        "security_incident_timeline_entries",
        "kind IN ('INCIDENT_OPENED', 'EVIDENCE_LINKED', 'CONTAINMENT_ACTION', "
        "'COMMUNICATION_DECISION', 'RECOVERY_ACTION', 'POSTMORTEM_ACTION', "
        "'STATUS_TRANSITION')",
    )
