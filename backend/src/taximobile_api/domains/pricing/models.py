from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from taximobile_api.db.base import Base
from taximobile_api.domains.markets.models import ServiceType, bounded_enum


class PricingModel(StrEnum):
    FIXED = "FIXED"
    METERED = "METERED"
    ESTIMATED = "ESTIMATED"


class PricingRuleStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    REPLACED = "REPLACED"


class BookingType(StrEnum):
    IMMEDIATE = "IMMEDIATE"
    SCHEDULED = "SCHEDULED"


class FinancialPolicyStatus(StrEnum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    ACTIVE = "ACTIVE"
    REPLACED = "REPLACED"


class OperatorFeeCalculationMode(StrEnum):
    PERCENTAGE_OF_TRANSPORT_FARE = "PERCENTAGE_OF_TRANSPORT_FARE"
    FLAT_PER_COMPLETED_BOOKING = "FLAT_PER_COMPLETED_BOOKING"


class OperatorFeeFundingMode(StrEnum):
    DRIVER_SETTLEMENT_DEDUCTION = "DRIVER_SETTLEMENT_DEDUCTION"
    PASSENGER_SURCHARGE = "PASSENGER_SURCHARGE"


class PricingRoundingRule(StrEnum):
    HALF_UP_0_01 = "HALF_UP_0_01"


class SchedulingSurchargeBeneficiary(StrEnum):
    OPERATOR = "OPERATOR"
    DRIVER = "DRIVER"


class SchedulingRefundMode(StrEnum):
    ALWAYS_FULL = "ALWAYS_FULL"
    FULL_BEFORE_CUTOFF = "FULL_BEFORE_CUTOFF"
    NON_REFUNDABLE = "NON_REFUNDABLE"


class PricingRule(Base):
    __tablename__ = "pricing_rules"
    __table_args__ = (
        UniqueConstraint(
            "city_id",
            "operator_id",
            "service_type",
            "booking_type",
            "version",
            name="uq_pricing_rule_scope_version",
        ),
        UniqueConstraint(
            "fixed_route_direction_id",
            name="uq_pricing_rule_fixed_route_direction",
        ),
        CheckConstraint(
            "effective_until IS NULL OR effective_until > effective_from",
            name="ck_pricing_rule_effective_range",
        ),
        CheckConstraint(
            "(service_type = 'ON_DEMAND' AND fixed_route_direction_id IS NULL) OR "
            "(service_type = 'FIXED_ROUTE' AND (fixed_route_direction_id IS NOT NULL "
            "OR status IN ('DRAFT', 'IN_REVIEW')))",
            name="ck_pricing_rule_fixed_route_scope",
        ),
        CheckConstraint("optimistic_version >= 1", name="ck_pricing_rule_optimistic_version"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    city_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    operator_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("operators.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    service_type: Mapped[ServiceType] = mapped_column(
        bounded_enum(ServiceType, "pricing_service_type", 20), nullable=False, default=ServiceType.ON_DEMAND
    )
    booking_type: Mapped[BookingType] = mapped_column(
        bounded_enum(BookingType, "pricing_booking_type", 16), nullable=False, default=BookingType.IMMEDIATE
    )
    fixed_route_direction_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("fixed_route_directions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[PricingModel] = mapped_column(Enum(PricingModel, name="pricing_model"), nullable=False)
    fixed_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="MAD")
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[PricingRuleStatus] = mapped_column(Enum(PricingRuleStatus, name="pricing_rule_status"), nullable=False, default=PricingRuleStatus.INACTIVE)
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


class OperatorFeePolicy(Base):
    __tablename__ = "operator_fee_policies"
    __table_args__ = (
        UniqueConstraint(
            "city_id",
            "operator_id",
            "service_type",
            "version",
            name="uq_operator_fee_policy_scope_version",
        ),
        CheckConstraint(
            "effective_until IS NULL OR effective_until > effective_from",
            name="ck_operator_fee_policy_effective_range",
        ),
        CheckConstraint(
            "(calculation_mode = 'PERCENTAGE_OF_TRANSPORT_FARE' AND percentage_rate IS NOT NULL "
            "AND percentage_rate >= 0 AND percentage_rate < 100 AND flat_amount IS NULL) OR "
            "(calculation_mode = 'FLAT_PER_COMPLETED_BOOKING' AND flat_amount IS NOT NULL "
            "AND flat_amount >= 0 AND percentage_rate IS NULL)",
            name="ck_operator_fee_policy_mode_values",
        ),
        CheckConstraint("minimum_driver_net >= 0", name="ck_operator_fee_policy_minimum_driver_net"),
        CheckConstraint("optimistic_version >= 1", name="ck_operator_fee_policy_optimistic_version"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    city_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    operator_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("operators.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    service_type: Mapped[ServiceType] = mapped_column(
        bounded_enum(ServiceType, "operator_fee_service_type", 20), nullable=False
    )
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[FinancialPolicyStatus] = mapped_column(
        bounded_enum(FinancialPolicyStatus, "operator_fee_policy_status", 16),
        nullable=False,
        default=FinancialPolicyStatus.DRAFT,
        index=True,
    )
    calculation_mode: Mapped[OperatorFeeCalculationMode] = mapped_column(
        bounded_enum(OperatorFeeCalculationMode, "operator_fee_calculation_mode", 40), nullable=False
    )
    funding_mode: Mapped[OperatorFeeFundingMode] = mapped_column(
        bounded_enum(OperatorFeeFundingMode, "operator_fee_funding_mode", 32), nullable=False
    )
    eligible_base_code: Mapped[str] = mapped_column(
        String(40), nullable=False, default="TRANSPORT_FARE"
    )
    percentage_rate: Mapped[Decimal | None] = mapped_column(Numeric(7, 4), nullable=True)
    flat_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rounding_rule: Mapped[PricingRoundingRule] = mapped_column(
        bounded_enum(PricingRoundingRule, "operator_fee_rounding_rule", 20),
        nullable=False,
        default=PricingRoundingRule.HALF_UP_0_01,
    )
    minimum_driver_net: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class SchedulingPolicy(Base):
    """Versioned monetary, timing, conflict, cancellation, and handoff policy."""

    __tablename__ = "scheduling_policies"
    __table_args__ = (
        UniqueConstraint(
            "city_id",
            "operator_id",
            "service_type",
            "version",
            name="uq_scheduling_policy_scope_version",
        ),
        CheckConstraint(
            "effective_until IS NULL OR effective_until > effective_from",
            name="ck_scheduling_policy_effective_range",
        ),
        CheckConstraint("surcharge_amount >= 0", name="ck_scheduling_policy_surcharge_nonnegative"),
        CheckConstraint(
            "minimum_lead_minutes >= 15 AND maximum_horizon_days BETWEEN 1 AND 365 "
            "AND offer_open_minutes_before > commitment_deadline_minutes_before "
            "AND commitment_deadline_minutes_before >= handoff_minutes_before "
            "AND handoff_minutes_before >= 5 AND offer_response_seconds BETWEEN 15 AND 3600 "
            "AND protected_duration_minutes BETWEEN 15 AND 1440 "
            "AND conflict_buffer_before_minutes BETWEEN 0 AND 1440 "
            "AND conflict_buffer_after_minutes BETWEEN 0 AND 1440 "
            "AND passenger_cancel_cutoff_minutes BETWEEN 0 AND 10080 "
            "AND driver_cancel_cutoff_minutes BETWEEN 0 AND 10080",
            name="scheduling_policy_timing_bounds",
        ),
        CheckConstraint("optimistic_version >= 1", name="ck_scheduling_policy_optimistic_version"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    city_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    operator_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("operators.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    service_type: Mapped[ServiceType] = mapped_column(
        bounded_enum(ServiceType, "scheduling_policy_service_type", 20), nullable=False
    )
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[FinancialPolicyStatus] = mapped_column(
        bounded_enum(FinancialPolicyStatus, "scheduling_policy_status", 16),
        nullable=False,
        default=FinancialPolicyStatus.DRAFT,
        index=True,
    )
    surcharge_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    beneficiary: Mapped[SchedulingSurchargeBeneficiary] = mapped_column(
        bounded_enum(SchedulingSurchargeBeneficiary, "scheduling_surcharge_beneficiary", 16),
        nullable=False,
    )
    collection_timing_code: Mapped[str] = mapped_column(
        String(40), nullable=False, default="AT_RIDE_SETTLEMENT"
    )
    minimum_lead_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    maximum_horizon_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    offer_open_minutes_before: Mapped[int] = mapped_column(Integer, nullable=False, default=1440)
    offer_response_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=120)
    commitment_deadline_minutes_before: Mapped[int] = mapped_column(Integer, nullable=False, default=180)
    handoff_minutes_before: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    protected_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    conflict_buffer_before_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    conflict_buffer_after_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    passenger_cancel_cutoff_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    driver_cancel_cutoff_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=120)
    surcharge_refund_mode: Mapped[SchedulingRefundMode] = mapped_column(
        bounded_enum(SchedulingRefundMode, "scheduling_refund_mode", 40),
        nullable=False,
        default=SchedulingRefundMode.FULL_BEFORE_CUTOFF,
    )
    fallback_matching_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class RideFinancialSnapshot(Base):
    """Immutable quote economics selected before dispatch and reused through settlement."""

    __tablename__ = "ride_financial_snapshots"
    __table_args__ = (
        CheckConstraint(
            "transport_fare_amount >= 0 AND scheduling_surcharge_amount >= 0 "
            "AND operator_fee_amount >= 0 AND passenger_total_amount >= 0 "
            "AND driver_gross_amount >= 0 AND driver_fee_deduction_amount >= 0 "
            "AND driver_net_amount >= 0 AND operator_allocation_amount >= 0",
            name="ck_ride_financial_snapshot_nonnegative",
        ),
        CheckConstraint(
            "driver_net_amount = driver_gross_amount - driver_fee_deduction_amount",
            name="ck_ride_financial_snapshot_driver_reconciles",
        ),
        CheckConstraint(
            "(booking_type = 'IMMEDIATE' AND scheduling_policy_id IS NULL "
            "AND scheduling_surcharge_beneficiary IS NULL AND scheduling_surcharge_amount = 0) "
            "OR (booking_type = 'SCHEDULED' AND scheduling_policy_id IS NOT NULL "
            "AND scheduling_surcharge_beneficiary IS NOT NULL)",
            name="ck_ride_financial_snapshot_booking_consistent",
        ),
        CheckConstraint(
            "passenger_total_amount = transport_fare_amount + scheduling_surcharge_amount + "
            "CASE WHEN operator_fee_funding_mode = 'PASSENGER_SURCHARGE' "
            "THEN operator_fee_amount ELSE 0 END",
            name="ck_ride_financial_snapshot_passenger_reconciles",
        ),
        CheckConstraint(
            "driver_gross_amount = transport_fare_amount + "
            "CASE WHEN scheduling_surcharge_beneficiary = 'DRIVER' "
            "THEN scheduling_surcharge_amount ELSE 0 END",
            name="ck_ride_financial_snapshot_driver_gross_reconciles",
        ),
        CheckConstraint(
            "driver_fee_deduction_amount = CASE WHEN operator_fee_funding_mode = "
            "'DRIVER_SETTLEMENT_DEDUCTION' THEN operator_fee_amount ELSE 0 END",
            name="ck_ride_financial_snapshot_driver_fee_reconciles",
        ),
        CheckConstraint(
            "operator_allocation_amount = operator_fee_amount + "
            "CASE WHEN scheduling_surcharge_beneficiary = 'OPERATOR' "
            "THEN scheduling_surcharge_amount ELSE 0 END",
            name="ck_ride_financial_snapshot_operator_reconciles",
        ),
    )

    ride_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("rides.id", ondelete="CASCADE"), primary_key=True
    )
    pricing_rule_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("pricing_rules.id", ondelete="RESTRICT"), nullable=False
    )
    operator_fee_policy_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("operator_fee_policies.id", ondelete="RESTRICT"), nullable=False
    )
    scheduling_policy_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("scheduling_policies.id", ondelete="RESTRICT"), nullable=True
    )
    booking_type: Mapped[BookingType] = mapped_column(
        bounded_enum(BookingType, "ride_financial_booking_type", 16), nullable=False
    )
    operator_fee_calculation_mode: Mapped[OperatorFeeCalculationMode] = mapped_column(
        bounded_enum(OperatorFeeCalculationMode, "ride_fee_calculation_mode", 40), nullable=False
    )
    operator_fee_funding_mode: Mapped[OperatorFeeFundingMode] = mapped_column(
        bounded_enum(OperatorFeeFundingMode, "ride_fee_funding_mode", 32), nullable=False
    )
    scheduling_surcharge_beneficiary: Mapped[SchedulingSurchargeBeneficiary | None] = mapped_column(
        bounded_enum(SchedulingSurchargeBeneficiary, "ride_scheduling_beneficiary", 16), nullable=True
    )
    transport_fare_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    scheduling_surcharge_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    operator_fee_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    passenger_total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    driver_gross_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    driver_fee_deduction_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    driver_net_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    operator_allocation_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class FareRecord(Base):
    __tablename__ = "fare_records"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    ride_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("rides.id"), nullable=False, unique=True)
    pricing_rule_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("pricing_rules.id"), nullable=False)
    base_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finalized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
