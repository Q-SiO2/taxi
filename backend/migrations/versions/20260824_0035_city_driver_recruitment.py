"""Add city driver requirements, applications, and authorizations.

Revision ID: 20260824_0035
Revises: 20260824_0034
Create Date: 2026-08-24
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260824_0035"
down_revision = "20260824_0034"
branch_labels = None
depends_on = None


LEGACY_CITY_ID = "10000000-0000-4000-8000-000000000003"
LEGACY_REQUIREMENT_VERSION_ID = "10000000-0000-4000-8000-000000000007"
LEGACY_PROFILE_REQUIREMENT_ITEM_ID = "10000000-0000-4000-8000-000000000008"


def text_enum(name: str, length: int, *values: str) -> sa.Enum:
    return sa.Enum(
        *values,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=length,
    )


def upgrade() -> None:
    requirement_status = text_enum(
        "driver_requirement_version_status",
        16,
        "DRAFT",
        "IN_REVIEW",
        "ACTIVE",
        "REPLACED",
    )
    evidence_type = text_enum(
        "driver_requirement_evidence_type",
        16,
        "PROFILE",
        "VEHICLE",
        "CREDENTIAL",
        "DOCUMENT",
        "BOOLEAN",
        "DATE",
        "TEXT",
    )
    validity_rule = text_enum(
        "driver_requirement_validity_rule",
        32,
        "PROFILE_OWNED",
        "VEHICLE_OWNED",
        "VEHICLE_VERIFIED",
        "CREDENTIAL_OWNED",
        "CREDENTIAL_VERIFIED",
        "CREDENTIAL_UNEXPIRED",
        "DOCUMENT_SCANNED_CLEAN",
        "BOOLEAN_TRUE",
        "DATE_NOT_FUTURE",
        "TEXT_PRESENT",
    )
    application_status = text_enum(
        "driver_city_application_status",
        40,
        "NOT_STARTED",
        "SUBMITTED",
        "UNDER_REVIEW",
        "ADDITIONAL_INFORMATION_REQUIRED",
        "APPROVED",
        "REJECTED",
        "WITHDRAWN",
        "SUSPENDED",
        "EXPIRED",
    )
    answer_type = text_enum(
        "driver_application_answer_type",
        16,
        "BOOLEAN",
        "DATE",
        "TEXT",
    )
    document_scan_status = text_enum(
        "driver_document_scan_status",
        16,
        "QUARANTINED",
        "PENDING",
        "CLEAN",
        "REJECTED",
        "ERROR",
    )
    application_evidence_status = text_enum(
        "driver_application_evidence_status",
        16,
        "PENDING",
        "ACCEPTED",
        "REJECTED",
        "EXPIRED",
    )
    decision_type = text_enum(
        "driver_application_decision_type",
        40,
        "START_REVIEW",
        "REQUEST_ADDITIONAL_INFORMATION",
        "APPROVE",
        "REJECT",
    )
    authorization_status = text_enum(
        "driver_city_authorization_status",
        16,
        "ACTIVE",
        "SUSPENDED",
        "EXPIRED",
        "REVOKED",
    )
    authorization_service_type = text_enum(
        "driver_authorization_service_type",
        20,
        "ON_DEMAND",
        "FIXED_ROUTE",
        "SCHEDULED",
    )

    op.create_table(
        "driver_requirement_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("status", requirement_status, nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("optimistic_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("submitted_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "effective_until IS NULL OR effective_until > effective_from",
            name="ck_drv_req_effective_range",
        ),
        sa.CheckConstraint(
            "optimistic_version >= 1",
            name="ck_drv_req_version_positive",
        ),
        sa.ForeignKeyConstraint(
            ["city_id"], ["cities.id"], name="fk_driver_requirement_versions_city_id_cities", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_driver_requirement_versions_created_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by_user_id"],
            ["users.id"],
            name="fk_driver_requirement_versions_submitted_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["activated_by_user_id"],
            ["users.id"],
            name="fk_driver_requirement_versions_activated_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_driver_requirement_versions"),
        sa.UniqueConstraint("city_id", "version", name="uq_driver_requirement_city_version"),
    )
    op.create_index("ix_driver_requirement_versions_city_id", "driver_requirement_versions", ["city_id"])
    op.create_index("ix_driver_requirement_versions_status", "driver_requirement_versions", ["status"])
    op.create_index(
        "uq_driver_requirement_versions_active_city",
        "driver_requirement_versions",
        ["city_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    op.create_table(
        "driver_requirement_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requirement_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requirement_code", sa.String(length=64), nullable=False),
        sa.Column("evidence_type", evidence_type, nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("validity_rule_code", validity_rule, nullable=False),
        sa.Column("reference_type_code", sa.String(length=64), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("localized_copy_key", sa.String(length=120), nullable=False),
        sa.Column("localized_label", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("localized_description", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "display_order >= 0",
            name="ck_drv_req_item_order_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_version_id"],
            ["driver_requirement_versions.id"],
            name="fk_drv_req_item_version",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_driver_requirement_items"),
        sa.UniqueConstraint(
            "requirement_version_id",
            "requirement_code",
            name="uq_driver_requirement_item_code",
        ),
    )
    op.create_index(
        "ix_driver_requirement_items_requirement_version_id",
        "driver_requirement_items",
        ["requirement_version_id"],
    )

    op.create_table(
        "driver_city_applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requirement_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", application_status, nullable=False),
        sa.Column("optimistic_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("submission_revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latest_decision_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "optimistic_version >= 1",
            name="ck_drv_city_app_version_positive",
        ),
        sa.CheckConstraint(
            "submission_revision >= 0",
            name="ck_drv_city_app_revision_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["driver_id"],
            ["driver_profiles.id"],
            name="fk_driver_city_applications_driver_id_driver_profiles",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["city_id"], ["cities.id"], name="fk_driver_city_applications_city_id_cities", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["requirement_version_id"],
            ["driver_requirement_versions.id"],
            name="fk_drv_city_app_requirement_version",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_driver_city_applications"),
    )
    op.create_index("ix_driver_city_applications_driver_id", "driver_city_applications", ["driver_id"])
    op.create_index("ix_driver_city_applications_city_id", "driver_city_applications", ["city_id"])
    op.create_index(
        "ix_driver_city_applications_requirement_version_id",
        "driver_city_applications",
        ["requirement_version_id"],
    )
    op.create_index("ix_driver_city_applications_status", "driver_city_applications", ["status"])
    op.create_index(
        "ix_driver_city_applications_city_status_submitted",
        "driver_city_applications",
        ["city_id", "status", "submitted_at", "id"],
    )
    op.create_index(
        "uq_driver_city_applications_open_driver_city",
        "driver_city_applications",
        ["driver_id", "city_id"],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('NOT_STARTED', 'SUBMITTED', 'UNDER_REVIEW', "
            "'ADDITIONAL_INFORMATION_REQUIRED')"
        ),
    )

    op.create_table(
        "driver_application_answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requirement_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("answer_type", answer_type, nullable=False),
        sa.Column("boolean_value", sa.Boolean(), nullable=True),
        sa.Column("date_value", sa.Date(), nullable=True),
        sa.Column("bounded_text_value", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "(answer_type = 'BOOLEAN' AND boolean_value IS NOT NULL AND date_value IS NULL "
            "AND bounded_text_value IS NULL) OR "
            "(answer_type = 'DATE' AND boolean_value IS NULL AND date_value IS NOT NULL "
            "AND bounded_text_value IS NULL) OR "
            "(answer_type = 'TEXT' AND boolean_value IS NULL AND date_value IS NULL "
            "AND bounded_text_value IS NOT NULL)",
            name="ck_drv_app_answer_exact_value",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["driver_city_applications.id"],
            name="fk_drv_app_answer_application",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_item_id"],
            ["driver_requirement_items.id"],
            name="fk_drv_app_answer_requirement_item",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_driver_application_answers"),
        sa.UniqueConstraint(
            "application_id", "requirement_item_id", name="uq_driver_application_answer_item"
        ),
    )
    op.create_index(
        "ix_driver_application_answers_application_id", "driver_application_answers", ["application_id"]
    )

    op.create_table(
        "driver_application_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requirement_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opaque_storage_key", sa.String(length=240), nullable=False),
        sa.Column("media_type", sa.String(length=120), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("malware_scan_status", document_scan_status, nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retention_deadline", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "byte_size > 0",
            name="ck_drv_app_document_positive_size",
        ),
        sa.CheckConstraint(
            "retention_deadline > uploaded_at",
            name="ck_drv_app_document_retention_after_upload",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["driver_city_applications.id"],
            name="fk_drv_app_document_application",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_item_id"],
            ["driver_requirement_items.id"],
            name="fk_drv_app_document_requirement_item",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_driver_application_documents"),
        sa.UniqueConstraint("opaque_storage_key", name="uq_driver_application_documents_opaque_storage_key"),
    )
    op.create_index(
        "ix_driver_application_documents_application_id",
        "driver_application_documents",
        ["application_id"],
    )

    op.create_table(
        "driver_application_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requirement_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("credential_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", application_evidence_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "num_nonnulls(profile_id, vehicle_id, credential_id, document_id) = 1",
            name="ck_drv_app_evidence_exact_reference",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["driver_city_applications.id"],
            name="fk_drv_app_evidence_application",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_item_id"],
            ["driver_requirement_items.id"],
            name="fk_drv_app_evidence_requirement_item",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["driver_profiles.id"], name="fk_driver_application_evidence_profile_id_driver_profiles", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["vehicle_id"], ["vehicles.id"], name="fk_driver_application_evidence_vehicle_id_vehicles", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["credential_id"],
            ["driver_credentials.id"],
            name="fk_driver_application_evidence_credential_id_driver_credentials",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["driver_application_documents.id"],
            name="fk_drv_app_evidence_document",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_driver_application_evidence"),
        sa.UniqueConstraint(
            "application_id", "requirement_item_id", name="uq_driver_application_evidence_item"
        ),
    )
    op.create_index(
        "ix_driver_application_evidence_application_id", "driver_application_evidence", ["application_id"]
    )

    op.create_table(
        "driver_application_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requirement_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision", decision_type, nullable=False),
        sa.Column("bounded_reason_code", sa.String(length=64), nullable=False),
        sa.Column("applicant_safe_message", sa.String(length=500), nullable=False),
        sa.Column("application_version", sa.Integer(), nullable=False),
        sa.Column("submission_revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["driver_city_applications.id"],
            name="fk_drv_app_decision_application",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_version_id"],
            ["driver_requirement_versions.id"],
            name="fk_drv_app_decision_requirement_version",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_user_id"],
            ["users.id"],
            name="fk_driver_application_decisions_reviewer_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_driver_application_decisions"),
    )
    op.create_index(
        "ix_driver_application_decisions_application_id", "driver_application_decisions", ["application_id"]
    )
    op.create_foreign_key(
        "fk_driver_city_applications_latest_decision",
        "driver_city_applications",
        "driver_application_decisions",
        ["latest_decision_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_table(
        "driver_city_authorizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", authorization_status, nullable=False),
        sa.Column("scheduled_offers_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from",
            name="ck_drv_city_authorization_valid_range",
        ),
        sa.ForeignKeyConstraint(
            ["driver_id"],
            ["driver_profiles.id"],
            name="fk_driver_city_authorizations_driver_id_driver_profiles",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["city_id"], ["cities.id"], name="fk_driver_city_authorizations_city_id_cities", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["driver_city_applications.id"],
            name="fk_drv_city_authorization_application",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["vehicle_id"], ["vehicles.id"], name="fk_driver_city_authorizations_vehicle_id_vehicles", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_driver_city_authorizations"),
        sa.UniqueConstraint("application_id", name="uq_driver_city_authorization_application"),
    )
    op.create_index("ix_driver_city_authorizations_driver_id", "driver_city_authorizations", ["driver_id"])
    op.create_index("ix_driver_city_authorizations_city_id", "driver_city_authorizations", ["city_id"])
    op.create_index("ix_driver_city_authorizations_status", "driver_city_authorizations", ["status"])
    op.create_index(
        "uq_driver_city_authorizations_active_driver_city",
        "driver_city_authorizations",
        ["driver_id", "city_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    op.create_table(
        "driver_city_authorization_services",
        sa.Column("authorization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_type", authorization_service_type, nullable=False),
        sa.ForeignKeyConstraint(
            ["authorization_id"],
            ["driver_city_authorizations.id"],
            name="fk_drv_city_auth_service_authorization",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "authorization_id", "service_type", name="pk_driver_city_authorization_services"
        ),
    )

    op.add_column(
        "city_configuration_versions",
        sa.Column("driver_requirement_version_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_city_config_driver_requirement_version",
        "city_configuration_versions",
        "driver_requirement_versions",
        ["driver_requirement_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_city_configuration_versions_driver_requirement_version_id",
        "city_configuration_versions",
        ["driver_requirement_version_id"],
    )

    op.add_column(
        "driver_profiles",
        sa.Column("online_city_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "driver_profiles",
        sa.Column("online_service_type", authorization_service_type, nullable=True),
    )
    op.create_foreign_key(
        "fk_driver_profiles_online_city_id_cities",
        "driver_profiles",
        "cities",
        ["online_city_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_driver_profiles_online_city_id", "driver_profiles", ["online_city_id"])

    # The pre-national Casablanca pilot receives one transparent compatibility
    # requirement and application per existing profile.  No identity/document
    # value is invented: the only requirement references the already-owned
    # profile.  Approved drivers receive the corresponding ON_DEMAND authority.
    op.execute(
        sa.text(
            """
            INSERT INTO driver_requirement_versions (
                id, city_id, version, status, effective_from, optimistic_version,
                submitted_at, activated_at, created_at, updated_at
            ) VALUES (
                CAST(:requirement_version_id AS uuid), CAST(:city_id AS uuid),
                'legacy-compatibility-v1', 'ACTIVE', TIMESTAMPTZ '2020-01-01 00:00:00+00',
                1, now(), now(), now(), now()
            )
            """
        ).bindparams(
            requirement_version_id=LEGACY_REQUIREMENT_VERSION_ID,
            city_id=LEGACY_CITY_ID,
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO driver_requirement_items (
                id, requirement_version_id, requirement_code, evidence_type,
                required, validity_rule_code, display_order, localized_copy_key,
                localized_label, localized_description, created_at
            ) VALUES (
                CAST(:item_id AS uuid), CAST(:requirement_version_id AS uuid),
                'DRIVER_PROFILE', 'PROFILE', true, 'PROFILE_OWNED', 0,
                'driver.requirement.profile',
                CAST(:label AS jsonb), CAST(:description AS jsonb), now()
            )
            """
        ).bindparams(
            item_id=LEGACY_PROFILE_REQUIREMENT_ITEM_ID,
            requirement_version_id=LEGACY_REQUIREMENT_VERSION_ID,
            label='{"en":"Driver profile","fr":"Profil chauffeur","ar":"ملف السائق"}',
            description='{"en":"Confirm the driver profile owned by this account.","fr":"Confirmez le profil chauffeur appartenant à ce compte.","ar":"أكد ملف السائق المملوك لهذا الحساب."}',
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO driver_city_applications (
                id, driver_id, city_id, requirement_version_id, status,
                optimistic_version, submission_revision, submitted_at, reviewed_at,
                created_at, updated_at
            )
            SELECT
                CAST(md5(dp.id::text || :application_suffix) AS uuid),
                dp.id,
                CAST(:city_id AS uuid),
                CAST(:requirement_version_id AS uuid),
                dp.verification_status::text,
                1,
                CASE WHEN dp.verification_status::text = 'NOT_STARTED' THEN 0 ELSE 1 END,
                CASE WHEN dp.verification_status::text = 'NOT_STARTED' THEN NULL ELSE dp.created_at END,
                CASE WHEN dp.verification_status::text IN ('APPROVED', 'REJECTED', 'SUSPENDED', 'EXPIRED')
                     THEN dp.updated_at ELSE NULL END,
                dp.created_at,
                dp.updated_at
            FROM driver_profiles dp
            """
        ).bindparams(
            city_id=LEGACY_CITY_ID,
            requirement_version_id=LEGACY_REQUIREMENT_VERSION_ID,
            application_suffix=":legacy-city-application",
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO driver_application_evidence (
                id, application_id, requirement_item_id, profile_id, status,
                created_at, updated_at
            )
            SELECT
                CAST(md5(dp.id::text || :evidence_suffix) AS uuid),
                CAST(md5(dp.id::text || :application_suffix) AS uuid),
                CAST(:item_id AS uuid),
                dp.id,
                CASE WHEN dp.verification_status::text = 'APPROVED' THEN 'ACCEPTED' ELSE 'PENDING' END,
                dp.created_at,
                dp.updated_at
            FROM driver_profiles dp
            """
        ).bindparams(
            item_id=LEGACY_PROFILE_REQUIREMENT_ITEM_ID,
            evidence_suffix=":legacy-profile-evidence",
            application_suffix=":legacy-city-application",
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO driver_city_authorizations (
                id, driver_id, city_id, application_id, status,
                scheduled_offers_enabled, valid_from, created_at, updated_at
            )
            SELECT
                CAST(md5(dp.id::text || :authorization_suffix) AS uuid),
                dp.id,
                CAST(:city_id AS uuid),
                CAST(md5(dp.id::text || :application_suffix) AS uuid),
                'ACTIVE', false, dp.updated_at, dp.updated_at, dp.updated_at
            FROM driver_profiles dp
            WHERE dp.verification_status::text = 'APPROVED'
              AND dp.account_status::text = 'ACTIVE'
            """
        ).bindparams(
            city_id=LEGACY_CITY_ID,
            authorization_suffix=":legacy-city-authorization",
            application_suffix=":legacy-city-application",
        )
    )
    op.execute(
        """
        INSERT INTO driver_city_authorization_services (authorization_id, service_type)
        SELECT id, 'ON_DEMAND'
        FROM driver_city_authorizations
        WHERE city_id = CAST('10000000-0000-4000-8000-000000000003' AS uuid)
        """
    )
    op.execute(
        sa.text(
            """
            UPDATE city_configuration_versions
            SET driver_requirement_version_id = CAST(:requirement_version_id AS uuid)
            WHERE city_id = CAST(:city_id AS uuid)
            """
        ).bindparams(
            requirement_version_id=LEGACY_REQUIREMENT_VERSION_ID,
            city_id=LEGACY_CITY_ID,
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE driver_profiles
            SET online_city_id = CAST(:city_id AS uuid),
                online_service_type = 'ON_DEMAND'
            WHERE availability_status::text <> 'OFFLINE'
              AND verification_status::text = 'APPROVED'
              AND account_status::text = 'ACTIVE'
            """
        ).bindparams(city_id=LEGACY_CITY_ID)
    )


def downgrade() -> None:
    op.drop_index("ix_driver_profiles_online_city_id", table_name="driver_profiles")
    op.drop_constraint("fk_driver_profiles_online_city_id_cities", "driver_profiles", type_="foreignkey")
    op.drop_column("driver_profiles", "online_service_type")
    op.drop_column("driver_profiles", "online_city_id")

    op.drop_index(
        "ix_city_configuration_versions_driver_requirement_version_id",
        table_name="city_configuration_versions",
    )
    op.drop_constraint(
        "fk_city_config_driver_requirement_version",
        "city_configuration_versions",
        type_="foreignkey",
    )
    op.drop_column("city_configuration_versions", "driver_requirement_version_id")

    op.drop_table("driver_city_authorization_services")
    op.drop_index("uq_driver_city_authorizations_active_driver_city", table_name="driver_city_authorizations")
    op.drop_index("ix_driver_city_authorizations_status", table_name="driver_city_authorizations")
    op.drop_index("ix_driver_city_authorizations_city_id", table_name="driver_city_authorizations")
    op.drop_index("ix_driver_city_authorizations_driver_id", table_name="driver_city_authorizations")
    op.drop_table("driver_city_authorizations")
    op.drop_constraint(
        "fk_driver_city_applications_latest_decision",
        "driver_city_applications",
        type_="foreignkey",
    )
    op.drop_index("ix_driver_application_decisions_application_id", table_name="driver_application_decisions")
    op.drop_table("driver_application_decisions")
    op.drop_index("ix_driver_application_evidence_application_id", table_name="driver_application_evidence")
    op.drop_table("driver_application_evidence")
    op.drop_index("ix_driver_application_documents_application_id", table_name="driver_application_documents")
    op.drop_table("driver_application_documents")
    op.drop_index("ix_driver_application_answers_application_id", table_name="driver_application_answers")
    op.drop_table("driver_application_answers")
    op.drop_index("uq_driver_city_applications_open_driver_city", table_name="driver_city_applications")
    op.drop_index("ix_driver_city_applications_city_status_submitted", table_name="driver_city_applications")
    op.drop_index("ix_driver_city_applications_status", table_name="driver_city_applications")
    op.drop_index("ix_driver_city_applications_requirement_version_id", table_name="driver_city_applications")
    op.drop_index("ix_driver_city_applications_city_id", table_name="driver_city_applications")
    op.drop_index("ix_driver_city_applications_driver_id", table_name="driver_city_applications")
    op.drop_table("driver_city_applications")
    op.drop_index("ix_driver_requirement_items_requirement_version_id", table_name="driver_requirement_items")
    op.drop_table("driver_requirement_items")
    op.drop_index("uq_driver_requirement_versions_active_city", table_name="driver_requirement_versions")
    op.drop_index("ix_driver_requirement_versions_status", table_name="driver_requirement_versions")
    op.drop_index("ix_driver_requirement_versions_city_id", table_name="driver_requirement_versions")
    op.drop_table("driver_requirement_versions")
