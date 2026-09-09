from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from taximobile_api.db.base import Base
from taximobile_api.domains.markets.models import bounded_enum
from taximobile_api.domains.markets.models import ServiceType
from taximobile_api.domains.pricing.models import OperatorFeeFundingMode


class PaymentMethod(StrEnum):
    CASH = "CASH"
    MANUAL_TRANSFER = "MANUAL_TRANSFER"
    CARD = "CARD"
    MOBILE_PAYMENT = "MOBILE_PAYMENT"


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    DISPUTED = "DISPUTED"
    REFUNDED = "REFUNDED"


class ManualTransferClaimStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class RefundReason(StrEnum):
    FARE_CORRECTION = "FARE_CORRECTION"
    DUPLICATE_PAYMENT = "DUPLICATE_PAYMENT"
    SERVICE_RECOVERY = "SERVICE_RECOVERY"
    OTHER_APPROVED = "OTHER_APPROVED"


class RefundSettlementMethod(StrEnum):
    CASH = "CASH"
    EXTERNAL_TRANSFER = "EXTERNAL_TRANSFER"


class PaymentRecipientStatus(StrEnum):
    DRAFT = "DRAFT"
    VERIFIED = "VERIFIED"
    RETIRED = "RETIRED"


class PaymentCapabilityStatus(StrEnum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    REPLACED = "REPLACED"


class PaymentRecipientAccount(Base):
    """Immutable-after-verification destination used for passenger instructions."""

    __tablename__ = "payment_recipient_accounts"
    __table_args__ = (
        CheckConstraint(
            "bank_account IS NOT NULL OR wallet_id IS NOT NULL",
            name="payment_recipient_has_destination",
        ),
        CheckConstraint(
            "optimistic_version >= 1",
            name="payment_recipient_optimistic_version_positive",
        ),
        UniqueConstraint(
            "city_id", "operator_id", "label", name="uq_payment_recipient_scope_label"
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    city_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    operator_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("operators.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    recipient_name: Mapped[str] = mapped_column(String(120), nullable=False)
    bank_account: Mapped[str | None] = mapped_column(String(120), nullable=True)
    wallet_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[PaymentRecipientStatus] = mapped_column(
        bounded_enum(PaymentRecipientStatus, "payment_recipient_status", 16),
        nullable=False,
        default=PaymentRecipientStatus.DRAFT,
        index=True,
    )
    optimistic_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    verified_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    retired_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class PaymentCapabilityVersion(Base):
    """Versioned methods allowed for exactly one city/operator/service scope."""

    __tablename__ = "payment_capability_versions"
    __table_args__ = (
        CheckConstraint("cash_enabled", name="payment_capability_cash_required"),
        CheckConstraint(
            "(manual_transfer_enabled AND recipient_account_id IS NOT NULL) OR "
            "(NOT manual_transfer_enabled AND recipient_account_id IS NULL)",
            name="payment_capability_transfer_recipient_consistency",
        ),
        CheckConstraint(
            "effective_until IS NULL OR effective_until > effective_from",
            name="payment_capability_effective_range",
        ),
        CheckConstraint(
            "optimistic_version >= 1",
            name="payment_capability_optimistic_version_positive",
        ),
        UniqueConstraint(
            "city_id", "operator_id", "service_type", "version",
            name="uq_payment_capability_scope_version",
        ),
        Index(
            "ix_payment_capability_active_scope",
            "city_id", "operator_id", "service_type",
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    city_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    operator_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("operators.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    service_type: Mapped[ServiceType] = mapped_column(
        bounded_enum(ServiceType, "payment_capability_service_type", 20), nullable=False
    )
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[PaymentCapabilityStatus] = mapped_column(
        bounded_enum(PaymentCapabilityStatus, "payment_capability_status", 16),
        nullable=False,
        default=PaymentCapabilityStatus.DRAFT,
        index=True,
    )
    cash_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    manual_transfer_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recipient_account_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("payment_recipient_accounts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    optimistic_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    submitted_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    approved_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    activated_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    ride_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("rides.id"), nullable=False, unique=True)
    payer_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    city_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    operator_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("operators.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    payment_capability_version_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("payment_capability_versions.id", ondelete="RESTRICT"), nullable=True
    )
    payment_recipient_account_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("payment_recipient_accounts.id", ondelete="RESTRICT"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod, name="payment_method"), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus, name="payment_status"), nullable=False, default=PaymentStatus.PENDING)
    provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    provider_reference: Mapped[str | None] = mapped_column(String(160), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ManualTransferClaim(Base):
    """A passenger assertion awaiting settlement-statement reconciliation.

    A claim is deliberately separate from the payment. Creating one never
    proves that money moved and therefore never completes the payment.
    """

    __tablename__ = "manual_transfer_claims"
    __table_args__ = (
        Index(
            "uq_manual_transfer_claims_submitted_payment",
            "payment_id",
            unique=True,
            postgresql_where=text("status = 'SUBMITTED'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    payment_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    claimant_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    payer_reference: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[ManualTransferClaimStatus] = mapped_column(
        Enum(ManualTransferClaimStatus, name="manual_transfer_claim_status"),
        nullable=False,
        default=ManualTransferClaimStatus.SUBMITTED,
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    review_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    settlement_reference: Mapped[str | None] = mapped_column(String(120), nullable=True, unique=True)


class PaymentRefund(Base):
    """An append-only fact that money was returned to the passenger.

    Refund requests and disputes live in support. A row is created only after an
    authorized operator has independently confirmed the cash handover or outbound
    transfer represented by ``settlement_reference``.
    """

    __tablename__ = "payment_refunds"
    __table_args__ = (
        CheckConstraint("amount > 0", name="payment_refund_positive_amount"),
        CheckConstraint(
            "driver_recovery_amount = 0 AND operator_funded_amount = amount",
            name="payment_refund_launch_funding_reconciles",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    payment_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("payments.id"),
        nullable=False,
        index=True,
    )
    city_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    operator_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("operators.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    reason: Mapped[RefundReason] = mapped_column(
        Enum(RefundReason, name="refund_reason"),
        nullable=False,
    )
    settlement_method: Mapped[RefundSettlementMethod] = mapped_column(
        Enum(RefundSettlementMethod, name="refund_settlement_method"),
        nullable=False,
    )
    settlement_reference: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    operator_note: Mapped[str] = mapped_column(String(500), nullable=False)
    driver_recovery_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    operator_funded_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    authorized_by_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    refunded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DriverEarning(Base):
    """A settled accounting fact, separate from the passenger's payment record."""

    __tablename__ = "driver_earnings"
    __table_args__ = (
        CheckConstraint(
            "transport_fare_amount >= 0 AND scheduling_surcharge_amount >= 0 "
            "AND operator_fee_amount >= 0 AND operator_allocation_amount >= 0",
            name="ck_driver_earning_components_nonnegative",
        ),
        CheckConstraint(
            "net_amount = gross_amount - fee_amount + adjustment_amount",
            name="ck_driver_earning_net_reconciles",
        ),
        CheckConstraint(
            "operator_fee_funding_mode IS NULL OR "
            "(operator_fee_funding_mode = 'DRIVER_SETTLEMENT_DEDUCTION' "
            "AND fee_amount = operator_fee_amount) OR "
            "(operator_fee_funding_mode = 'PASSENGER_SURCHARGE' AND fee_amount = 0)",
            name="ck_driver_earning_fee_reconciles",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    driver_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("driver_profiles.id"), nullable=False, index=True
    )
    ride_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("rides.id"), nullable=False, unique=True
    )
    payment_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("payments.id"), nullable=False, unique=True
    )
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fee_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    adjustment_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    transport_fare_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    scheduling_surcharge_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    operator_fee_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    operator_allocation_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    operator_fee_policy_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("operator_fee_policies.id", ondelete="RESTRICT"),
        nullable=True,
    )
    scheduling_policy_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("scheduling_policies.id", ondelete="RESTRICT"),
        nullable=True,
    )
    operator_fee_funding_mode: Mapped[OperatorFeeFundingMode | None] = mapped_column(
        bounded_enum(OperatorFeeFundingMode, "earning_operator_fee_funding_mode", 32),
        nullable=True,
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    settled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
