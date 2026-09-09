"""Persistent city driver requirements, applications, and authorizations.

The applicant owns the editable application data.  Requirement publication,
review decisions, and operating authorization remain server-authoritative and
are represented separately so a completed form can never grant dispatch access.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from taximobile_api.db.base import Base
from taximobile_api.domains.markets.models import ServiceType, bounded_enum


class RequirementVersionStatus(StrEnum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    ACTIVE = "ACTIVE"
    REPLACED = "REPLACED"


class RequirementEvidenceType(StrEnum):
    PROFILE = "PROFILE"
    VEHICLE = "VEHICLE"
    CREDENTIAL = "CREDENTIAL"
    DOCUMENT = "DOCUMENT"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    TEXT = "TEXT"


class RequirementValidityRule(StrEnum):
    PROFILE_OWNED = "PROFILE_OWNED"
    VEHICLE_OWNED = "VEHICLE_OWNED"
    VEHICLE_VERIFIED = "VEHICLE_VERIFIED"
    CREDENTIAL_OWNED = "CREDENTIAL_OWNED"
    CREDENTIAL_VERIFIED = "CREDENTIAL_VERIFIED"
    CREDENTIAL_UNEXPIRED = "CREDENTIAL_UNEXPIRED"
    DOCUMENT_SCANNED_CLEAN = "DOCUMENT_SCANNED_CLEAN"
    BOOLEAN_TRUE = "BOOLEAN_TRUE"
    DATE_NOT_FUTURE = "DATE_NOT_FUTURE"
    TEXT_PRESENT = "TEXT_PRESENT"


class CityApplicationStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ADDITIONAL_INFORMATION_REQUIRED = "ADDITIONAL_INFORMATION_REQUIRED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    SUSPENDED = "SUSPENDED"
    EXPIRED = "EXPIRED"


class ApplicationEvidenceStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class ApplicationAnswerType(StrEnum):
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    TEXT = "TEXT"


class DocumentScanStatus(StrEnum):
    QUARANTINED = "QUARANTINED"
    PENDING = "PENDING"
    CLEAN = "CLEAN"
    REJECTED = "REJECTED"
    ERROR = "ERROR"


class DocumentErasureReason(StrEnum):
    APPLICANT_DELETED = "APPLICANT_DELETED"
    RETENTION_EXPIRED = "RETENTION_EXPIRED"


class ApplicationDecisionType(StrEnum):
    START_REVIEW = "START_REVIEW"
    REQUEST_ADDITIONAL_INFORMATION = "REQUEST_ADDITIONAL_INFORMATION"
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class CityAuthorizationStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class DriverRequirementVersion(Base):
    __tablename__ = "driver_requirement_versions"
    __table_args__ = (
        UniqueConstraint("city_id", "version", name="driver_requirement_city_version"),
        CheckConstraint(
            "effective_until IS NULL OR effective_until > effective_from",
            name="driver_requirement_effective_range",
        ),
        CheckConstraint("optimistic_version >= 1", name="driver_requirement_version_positive"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    city_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[RequirementVersionStatus] = mapped_column(
        bounded_enum(RequirementVersionStatus, "driver_requirement_version_status", 16),
        nullable=False,
        default=RequirementVersionStatus.DRAFT,
        index=True,
    )
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    optimistic_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    submitted_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DriverRequirementItem(Base):
    __tablename__ = "driver_requirement_items"
    __table_args__ = (
        UniqueConstraint(
            "requirement_version_id",
            "requirement_code",
            name="driver_requirement_item_code",
        ),
        CheckConstraint("display_order >= 0", name="driver_requirement_display_order_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    requirement_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("driver_requirement_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requirement_code: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_type: Mapped[RequirementEvidenceType] = mapped_column(
        bounded_enum(RequirementEvidenceType, "driver_requirement_evidence_type", 16),
        nullable=False,
    )
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    validity_rule_code: Mapped[RequirementValidityRule] = mapped_column(
        bounded_enum(RequirementValidityRule, "driver_requirement_validity_rule", 32),
        nullable=False,
    )
    # For credentials this is the reviewed credential_type policy value.  It is
    # never a credential number or a document/storage identifier.
    reference_type_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    localized_copy_key: Mapped[str] = mapped_column(String(120), nullable=False)
    localized_label: Mapped[dict] = mapped_column(JSONB, nullable=False)
    localized_description: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class DriverCityApplication(Base):
    __tablename__ = "driver_city_applications"
    __table_args__ = (
        CheckConstraint("optimistic_version >= 1", name="driver_city_application_version_positive"),
        CheckConstraint("submission_revision >= 0", name="driver_city_application_revision_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    driver_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("driver_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    city_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    requirement_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("driver_requirement_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[CityApplicationStatus] = mapped_column(
        bounded_enum(CityApplicationStatus, "driver_city_application_status", 40),
        nullable=False,
        default=CityApplicationStatus.NOT_STARTED,
        index=True,
    )
    optimistic_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    submission_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latest_decision_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "driver_application_decisions.id",
            name="fk_driver_city_applications_latest_decision",
            use_alter=True,
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DriverApplicationAnswer(Base):
    __tablename__ = "driver_application_answers"
    __table_args__ = (
        UniqueConstraint("application_id", "requirement_item_id", name="driver_application_answer_item"),
        CheckConstraint(
            "(answer_type = 'BOOLEAN' AND boolean_value IS NOT NULL AND date_value IS NULL "
            "AND bounded_text_value IS NULL) OR "
            "(answer_type = 'DATE' AND boolean_value IS NULL AND date_value IS NOT NULL "
            "AND bounded_text_value IS NULL) OR "
            "(answer_type = 'TEXT' AND boolean_value IS NULL AND date_value IS NULL "
            "AND bounded_text_value IS NOT NULL)",
            name="driver_application_answer_exact_value",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    application_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("driver_city_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requirement_item_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("driver_requirement_items.id", ondelete="RESTRICT"),
        nullable=False,
    )
    answer_type: Mapped[ApplicationAnswerType] = mapped_column(
        bounded_enum(ApplicationAnswerType, "driver_application_answer_type", 16), nullable=False
    )
    boolean_value: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    date_value: Mapped[date | None] = mapped_column(Date, nullable=True)
    bounded_text_value: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DriverApplicationDocument(Base):
    __tablename__ = "driver_application_documents"
    __table_args__ = (
        CheckConstraint("byte_size > 0", name="driver_application_document_positive_size"),
        CheckConstraint(
            "retention_deadline > uploaded_at",
            name="driver_application_document_retention_after_upload",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    application_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("driver_city_applications.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    requirement_item_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("driver_requirement_items.id", ondelete="RESTRICT"),
        nullable=False,
    )
    opaque_storage_key: Mapped[str] = mapped_column(String(240), nullable=False, unique=True)
    media_type: Mapped[str] = mapped_column(String(120), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    malware_scan_status: Mapped[DocumentScanStatus] = mapped_column(
        bounded_enum(DocumentScanStatus, "driver_document_scan_status", 16), nullable=False
    )
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retention_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DriverDocumentRetentionAction(Base):
    """Immutable non-personal evidence that protected bytes were erased."""

    __tablename__ = "driver_document_retention_actions"
    __table_args__ = (
        CheckConstraint(
            "reason IN ('APPLICANT_DELETED', 'RETENTION_EXPIRED')",
            name="driver_document_retention_reason",
        ),
        UniqueConstraint("document_id", name="uq_driver_document_retention_document"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    document_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    application_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("driver_city_applications.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    city_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("cities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    reason: Mapped[DocumentErasureReason] = mapped_column(
        bounded_enum(DocumentErasureReason, "driver_document_erasure_reason", 24),
        nullable=False,
    )
    retention_policy_version: Mapped[str] = mapped_column(String(40), nullable=False)
    retention_due_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DriverApplicationEvidence(Base):
    __tablename__ = "driver_application_evidence"
    __table_args__ = (
        UniqueConstraint("application_id", "requirement_item_id", name="driver_application_evidence_item"),
        CheckConstraint(
            "num_nonnulls(profile_id, vehicle_id, credential_id, document_id) = 1",
            name="driver_application_evidence_exact_reference",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    application_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("driver_city_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requirement_item_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("driver_requirement_items.id", ondelete="RESTRICT"),
        nullable=False,
    )
    profile_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("driver_profiles.id", ondelete="RESTRICT"), nullable=True
    )
    vehicle_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=True
    )
    credential_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("driver_credentials.id", ondelete="RESTRICT"), nullable=True
    )
    document_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("driver_application_documents.id", ondelete="RESTRICT"),
        nullable=True,
    )
    status: Mapped[ApplicationEvidenceStatus] = mapped_column(
        bounded_enum(ApplicationEvidenceStatus, "driver_application_evidence_status", 16),
        nullable=False,
        default=ApplicationEvidenceStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DriverApplicationDecision(Base):
    __tablename__ = "driver_application_decisions"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    application_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("driver_city_applications.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    requirement_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("driver_requirement_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reviewer_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    decision: Mapped[ApplicationDecisionType] = mapped_column(
        bounded_enum(ApplicationDecisionType, "driver_application_decision_type", 40), nullable=False
    )
    bounded_reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    applicant_safe_message: Mapped[str] = mapped_column(String(500), nullable=False)
    application_version: Mapped[int] = mapped_column(Integer, nullable=False)
    submission_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class DriverCityAuthorization(Base):
    __tablename__ = "driver_city_authorizations"
    __table_args__ = (
        UniqueConstraint("application_id", name="driver_city_authorization_application"),
        CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from",
            name="driver_city_authorization_valid_range",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    driver_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("driver_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    city_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    application_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("driver_city_applications.id", ondelete="RESTRICT"),
        nullable=False,
    )
    vehicle_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=True
    )
    status: Mapped[CityAuthorizationStatus] = mapped_column(
        bounded_enum(CityAuthorizationStatus, "driver_city_authorization_status", 16),
        nullable=False,
        default=CityAuthorizationStatus.ACTIVE,
        index=True,
    )
    scheduled_offers_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DriverCityAuthorizationService(Base):
    __tablename__ = "driver_city_authorization_services"

    authorization_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("driver_city_authorizations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    service_type: Mapped[ServiceType] = mapped_column(
        bounded_enum(ServiceType, "driver_authorization_service_type", 20), primary_key=True
    )
