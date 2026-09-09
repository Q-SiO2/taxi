"""Add restricted security-incident operations records.

Revision ID: 20260907_0050
Revises: 20260907_0049
Create Date: 2026-09-07
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260907_0050"
down_revision = "20260907_0049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "security_incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reference", sa.String(length=40), nullable=False),
        sa.Column("market_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("severity", sa.String(length=8), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="OPEN", nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("reported_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lead_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("containment_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("contained_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recovered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("postmortem_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("optimistic_version", sa.SmallInteger(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "severity IN ('SEV1', 'SEV2', 'SEV3', 'SEV4')",
            name="ck_security_incidents_severity",
        ),
        sa.CheckConstraint(
            "category IN ('ACCOUNT_COMPROMISE', 'PROVIDER_CREDENTIAL_EXPOSURE', "
            "'DATA_EXPOSURE', 'MALICIOUS_ACCESS', 'SERVICE_ABUSE', 'OTHER')",
            name="ck_security_incidents_category",
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'CONTAINING', 'CONTAINED', 'RECOVERING', "
            "'RECOVERED', 'CLOSED')",
            name="ck_security_incidents_status",
        ),
        sa.CheckConstraint(
            "containment_due_at > opened_at",
            name="ck_security_incidents_containment_due_after_open",
        ),
        sa.CheckConstraint(
            "detected_at <= opened_at",
            name="ck_security_incidents_detected_before_open",
        ),
        sa.CheckConstraint(
            "optimistic_version > 0",
            name="ck_security_incidents_version_positive",
        ),
        sa.CheckConstraint(
            "(status IN ('OPEN', 'CONTAINING') AND contained_at IS NULL "
            "AND recovered_at IS NULL AND closed_at IS NULL "
            "AND postmortem_due_at IS NULL) OR "
            "(status IN ('CONTAINED', 'RECOVERING') AND contained_at IS NOT NULL "
            "AND recovered_at IS NULL AND closed_at IS NULL "
            "AND postmortem_due_at IS NULL) OR "
            "(status = 'RECOVERED' AND contained_at IS NOT NULL "
            "AND recovered_at IS NOT NULL AND closed_at IS NULL "
            "AND postmortem_due_at IS NULL) OR "
            "(status = 'CLOSED' AND contained_at IS NOT NULL "
            "AND recovered_at IS NOT NULL AND closed_at IS NOT NULL "
            "AND postmortem_due_at IS NOT NULL)",
            name="ck_security_incidents_lifecycle_timestamps",
        ),
        sa.CheckConstraint(
            "contained_at IS NULL OR contained_at >= opened_at",
            name="ck_security_incidents_contained_after_open",
        ),
        sa.CheckConstraint(
            "recovered_at IS NULL OR recovered_at >= contained_at",
            name="ck_security_incidents_recovered_after_contained",
        ),
        sa.CheckConstraint(
            "closed_at IS NULL OR closed_at >= recovered_at",
            name="ck_security_incidents_closed_after_recovered",
        ),
        sa.CheckConstraint(
            "postmortem_due_at IS NULL OR postmortem_due_at > closed_at",
            name="ck_security_incidents_postmortem_after_close",
        ),
        sa.ForeignKeyConstraint(["market_id"], ["markets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["reported_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["lead_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference", name="uq_security_incidents_reference"),
    )
    for column in (
        "market_id",
        "city_id",
        "severity",
        "category",
        "status",
        "containment_due_at",
    ):
        op.create_index(
            f"ix_security_incidents_{column}",
            "security_incidents",
            [column],
        )

    op.create_table(
        "security_incident_timeline_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("audit_log_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("external_reference", sa.String(length=160), nullable=True),
        sa.CheckConstraint(
            "kind IN ('INCIDENT_OPENED', 'EVIDENCE_LINKED', 'CONTAINMENT_ACTION', "
            "'COMMUNICATION_DECISION', 'RECOVERY_ACTION', 'POSTMORTEM_ACTION', "
            "'STATUS_TRANSITION')",
            name="ck_security_incident_timeline_entries_kind",
        ),
        sa.CheckConstraint(
            "sequence > 0",
            name="ck_security_incident_timeline_entries_sequence_positive",
        ),
        sa.ForeignKeyConstraint(
            ["incident_id"], ["security_incidents.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["audit_log_id"], ["audit_logs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "incident_id",
            "sequence",
            name="uq_security_incident_timeline_incident_sequence",
        ),
    )
    op.create_index(
        "ix_security_incident_timeline_entries_incident_id",
        "security_incident_timeline_entries",
        ["incident_id"],
    )
    op.create_index(
        "ix_security_incident_timeline_entries_kind",
        "security_incident_timeline_entries",
        ["kind"],
    )
    op.execute(
        """
        CREATE FUNCTION prevent_security_incident_timeline_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'security incident timeline entries are append-only'
                USING ERRCODE = '55000';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER security_incident_timeline_append_only
        BEFORE UPDATE OR DELETE ON security_incident_timeline_entries
        FOR EACH ROW EXECUTE FUNCTION prevent_security_incident_timeline_mutation()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS security_incident_timeline_append_only "
        "ON security_incident_timeline_entries"
    )
    op.execute("DROP FUNCTION IF EXISTS prevent_security_incident_timeline_mutation()")
    op.drop_table("security_incident_timeline_entries")
    op.drop_table("security_incidents")
