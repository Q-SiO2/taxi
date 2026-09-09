from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, LargeBinary, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from taximobile_api.db.base import Base
from taximobile_api.domains.markets.models import bounded_enum


class AdministrativeRoleTemplate(StrEnum):
    """Reviewed staff templates; permissions remain server-owned mappings."""

    PLATFORM_ADMIN = "PLATFORM_ADMIN"
    OPERATOR_ADMIN = "OPERATOR_ADMIN"
    CITY_MANAGER = "CITY_MANAGER"
    DRIVER_REVIEWER = "DRIVER_REVIEWER"
    PRICING_MANAGER = "PRICING_MANAGER"
    PAYMENT_RECONCILER = "PAYMENT_RECONCILER"
    SUPPORT_AGENT = "SUPPORT_AGENT"
    SAFETY_RESPONDER = "SAFETY_RESPONDER"
    ANALYST = "ANALYST"


class AdministrativeGrantRequestAction(StrEnum):
    CREATE = "CREATE"
    REVOKE = "REVOKE"


class AdministrativeGrantRequestStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


CITY_SCOPED_ROLE_TEMPLATES = frozenset(
    {
        AdministrativeRoleTemplate.CITY_MANAGER,
        AdministrativeRoleTemplate.DRIVER_REVIEWER,
        AdministrativeRoleTemplate.PRICING_MANAGER,
        AdministrativeRoleTemplate.PAYMENT_RECONCILER,
        AdministrativeRoleTemplate.SUPPORT_AGENT,
        AdministrativeRoleTemplate.SAFETY_RESPONDER,
        AdministrativeRoleTemplate.ANALYST,
    }
)


class AdministrativeGrant(Base):
    """Append-visible operations authority with exactly one validated scope."""

    __tablename__ = "administrative_grants"
    __table_args__ = (
        CheckConstraint(
            "(role_template = 'PLATFORM_ADMIN' AND market_id IS NOT NULL "
            "AND operator_id IS NULL AND city_id IS NULL) OR "
            "(role_template = 'OPERATOR_ADMIN' AND market_id IS NULL "
            "AND operator_id IS NOT NULL AND city_id IS NULL) OR "
            "(role_template IN ('CITY_MANAGER', 'DRIVER_REVIEWER', 'PRICING_MANAGER', "
            "'PAYMENT_RECONCILER', 'SUPPORT_AGENT', 'SAFETY_RESPONDER', 'ANALYST') "
            "AND market_id IS NULL AND operator_id IS NULL AND city_id IS NOT NULL)",
            name="administrative_grant_template_scope",
        ),
        CheckConstraint(
            "expires_at IS NULL OR expires_at > granted_at",
            name="expiry_after_grant",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_template: Mapped[AdministrativeRoleTemplate] = mapped_column(
        bounded_enum(AdministrativeRoleTemplate, "administrative_role_template", 32),
        nullable=False,
        index=True,
    )
    market_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("markets.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    operator_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("operators.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    city_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("cities.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    granted_by_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    grant_reason: Mapped[str] = mapped_column(String(240), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    revocation_reason: Mapped[str | None] = mapped_column(String(240), nullable=True)


class AdministrativeGrantChangeRequest(Base):
    """Append-visible maker-checker request carrying an immutable grant snapshot."""

    __tablename__ = "administrative_grant_change_requests"
    __table_args__ = (
        CheckConstraint(
            "(role_template = 'PLATFORM_ADMIN' AND market_id IS NOT NULL "
            "AND operator_id IS NULL AND city_id IS NULL) OR "
            "(role_template = 'OPERATOR_ADMIN' AND market_id IS NULL "
            "AND operator_id IS NOT NULL AND city_id IS NULL) OR "
            "(role_template IN ('CITY_MANAGER', 'DRIVER_REVIEWER', 'PRICING_MANAGER', "
            "'PAYMENT_RECONCILER', 'SUPPORT_AGENT', 'SAFETY_RESPONDER', 'ANALYST') "
            "AND market_id IS NULL AND operator_id IS NULL AND city_id IS NOT NULL)",
            name="administrative_grant_request_template_scope",
        ),
        CheckConstraint(
            "(action = 'CREATE' AND source_grant_id IS NULL) OR "
            "(action = 'REVOKE' AND source_grant_id IS NOT NULL)",
            name="administrative_grant_request_action_source",
        ),
        CheckConstraint(
            "requester_user_id <> target_user_id",
            name="administrative_grant_request_no_self_request",
        ),
        CheckConstraint(
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
            name="administrative_grant_request_decision_state",
        ),
        CheckConstraint(
            "requested_grant_expires_at IS NULL "
            "OR requested_grant_expires_at > requested_at",
            name="administrative_grant_request_expiry_after_request",
        ),
        CheckConstraint("optimistic_version > 0", name="administrative_grant_request_version_positive"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    action: Mapped[AdministrativeGrantRequestAction] = mapped_column(
        bounded_enum(AdministrativeGrantRequestAction, "administrative_grant_request_action", 16),
        nullable=False,
        index=True,
    )
    status: Mapped[AdministrativeGrantRequestStatus] = mapped_column(
        bounded_enum(AdministrativeGrantRequestStatus, "administrative_grant_request_status", 16),
        nullable=False,
        default=AdministrativeGrantRequestStatus.PENDING,
        server_default=AdministrativeGrantRequestStatus.PENDING.value,
        index=True,
    )
    requester_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    decided_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    target_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    role_template: Mapped[AdministrativeRoleTemplate] = mapped_column(
        bounded_enum(AdministrativeRoleTemplate, "administrative_role_template", 32),
        nullable=False,
    )
    market_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("markets.id", ondelete="RESTRICT"), nullable=True
    )
    operator_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("operators.id", ondelete="RESTRICT"), nullable=True
    )
    city_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("cities.id", ondelete="RESTRICT"), nullable=True
    )
    source_grant_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("administrative_grants.id", ondelete="RESTRICT"),
        nullable=True,
    )
    resulting_grant_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("administrative_grants.id", ondelete="RESTRICT"),
        nullable=True,
        unique=True,
    )
    reason: Mapped[str] = mapped_column(String(240), nullable=False)
    decision_reason: Mapped[str | None] = mapped_column(String(240), nullable=True)
    requested_grant_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    optimistic_version: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=1, server_default="1"
    )


class OperationsSession(Base):
    """Browser operations session, isolated from ordinary mobile refresh tokens."""

    __tablename__ = "operations_sessions"
    __table_args__ = (
        CheckConstraint(
            "(mfa_verified_at IS NULL AND mfa_method IS NULL) OR "
            "(mfa_verified_at IS NOT NULL AND mfa_method IN ('TOTP', 'RECOVERY_CODE'))",
            name="operations_session_mfa_state",
        ),
        CheckConstraint(
            "csrf_token_hash IS NULL OR csrf_token_hash ~ '^[0-9a-f]{64}$'",
            name="operations_session_csrf_hash",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    refresh_token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    csrf_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    refresh_family_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refresh_rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mfa_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mfa_method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    device_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class OperationsMfaCredential(Base):
    """One encrypted RFC 6238 seed per operations account."""

    __tablename__ = "operations_mfa_credentials"
    __table_args__ = (
        CheckConstraint("octet_length(secret_nonce) = 12", name="operations_mfa_credential_nonce_length"),
        CheckConstraint("octet_length(encrypted_secret) >= 36", name="operations_mfa_credential_ciphertext_length"),
        CheckConstraint(
            "last_accepted_counter IS NULL OR last_accepted_counter >= 0",
            name="operations_mfa_credential_counter",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    encrypted_secret: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    secret_nonce: Mapped[bytes] = mapped_column(LargeBinary(12), nullable=False)
    last_accepted_counter: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    enabled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class OperationsMfaRecoveryCode(Base):
    """A high-entropy lookup secret stored only as a SHA-256 digest."""

    __tablename__ = "operations_mfa_recovery_codes"
    __table_args__ = (
        CheckConstraint("code_hash ~ '^[0-9a-f]{64}$'", name="operations_mfa_recovery_code_hash"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    credential_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("operations_mfa_credentials.id", ondelete="CASCADE"),
        nullable=False,
    )
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class OperationsMfaChallenge(Base):
    """Short-lived password-verified pre-session challenge."""

    __tablename__ = "operations_mfa_challenges"
    __table_args__ = (
        CheckConstraint("attempt_count BETWEEN 0 AND 5", name="operations_mfa_challenge_attempt_count"),
        CheckConstraint("expires_at > created_at", name="operations_mfa_challenge_expiry"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempt_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    device_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    actor_user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False, index=True)
    market_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("markets.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    operator_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("operators.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    city_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("cities.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    changes: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
