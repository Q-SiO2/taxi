from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, TSTZRANGE, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from taximobile_api.db.base import Base
from taximobile_api.domains.markets.models import ServiceType, bounded_enum
from taximobile_api.domains.payments.models import PaymentMethod


class ScheduledBookingStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    OFFERING = "OFFERING"
    DRIVER_COMMITTED = "DRIVER_COMMITTED"
    DISPATCH_HANDOFF = "DISPATCH_HANDOFF"
    LIVE_RIDE_CREATED = "LIVE_RIDE_CREATED"
    UNFULFILLED = "UNFULFILLED"
    CANCELLED = "CANCELLED"


class ScheduledOfferStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class ScheduledCommitmentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    CANCELLED = "CANCELLED"
    FULFILLED = "FULFILLED"


class CancellationFinancialOutcome(StrEnum):
    NO_CHARGE = "NO_CHARGE"
    SURCHARGE_RETAINED = "SURCHARGE_RETAINED"
    REFUND_PENDING = "REFUND_PENDING"
    REFUNDED = "REFUNDED"


class ScheduledBookingEventType(StrEnum):
    CREATED = "CREATED"
    OFFERING_STARTED = "OFFERING_STARTED"
    OFFER_CREATED = "OFFER_CREATED"
    OFFER_DECLINED = "OFFER_DECLINED"
    DRIVER_COMMITTED = "DRIVER_COMMITTED"
    HANDOFF_STARTED = "HANDOFF_STARTED"
    LIVE_RIDE_CREATED = "LIVE_RIDE_CREATED"
    CANCELLED = "CANCELLED"
    UNFULFILLED = "UNFULFILLED"


class ScheduledBooking(Base):
    __tablename__ = "scheduled_bookings"
    __table_args__ = (
        CheckConstraint(
            "(service_type = 'ON_DEMAND' AND fixed_route_direction_id IS NULL) OR "
            "(service_type = 'FIXED_ROUTE' AND fixed_route_direction_id IS NOT NULL)",
            name="scheduled_booking_service_consistency",
        ),
        CheckConstraint(
            "transport_fare_amount >= 0 AND scheduling_surcharge_amount >= 0 "
            "AND operator_fee_amount >= 0 AND passenger_total_amount >= 0 "
            "AND driver_gross_amount >= 0 AND driver_fee_deduction_amount >= 0 "
            "AND driver_net_amount >= 0 AND operator_allocation_amount >= 0",
            name="scheduled_booking_money_nonnegative",
        ),
        CheckConstraint(
            "driver_net_amount = driver_gross_amount - driver_fee_deduction_amount",
            name="scheduled_booking_driver_reconciles",
        ),
        CheckConstraint(
            "live_ride_id IS NULL OR status = 'LIVE_RIDE_CREATED'",
            name="scheduled_booking_live_ride_state",
        ),
        UniqueConstraint("live_ride_id", name="uq_scheduled_bookings_live_ride"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    passenger_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    city_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    operator_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("operators.id", ondelete="RESTRICT"), nullable=False
    )
    service_type: Mapped[ServiceType] = mapped_column(
        bounded_enum(ServiceType, "scheduled_booking_service_type", 20), nullable=False
    )
    fixed_route_direction_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("fixed_route_directions.id", ondelete="RESTRICT"), nullable=True
    )
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    city_timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[ScheduledBookingStatus] = mapped_column(
        bounded_enum(ScheduledBookingStatus, "scheduled_booking_status", 24),
        nullable=False,
        default=ScheduledBookingStatus.SCHEDULED,
        index=True,
    )
    pickup_point: Mapped[object] = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    destination_point: Mapped[object] = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    pickup_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    destination_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    passenger_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_method: Mapped[PaymentMethod] = mapped_column(
        bounded_enum(PaymentMethod, "scheduled_booking_payment_method", 32), nullable=False
    )
    pricing_rule_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("pricing_rules.id", ondelete="RESTRICT"), nullable=False
    )
    operator_fee_policy_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("operator_fee_policies.id", ondelete="RESTRICT"), nullable=False
    )
    scheduling_policy_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("scheduling_policies.id", ondelete="RESTRICT"), nullable=False
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
    quote_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    policy_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    current_commitment_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "scheduled_booking_commitments.id",
            name="fk_scheduled_bookings_current_commitment",
            use_alter=True,
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    live_ride_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("rides.id", name="fk_scheduled_bookings_live_ride", use_alter=True, ondelete="RESTRICT"),
        nullable=True,
    )
    offering_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    handoff_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    live_ride_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    unfulfilled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cancellation_financial_outcome: Mapped[CancellationFinancialOutcome | None] = mapped_column(
        bounded_enum(CancellationFinancialOutcome, "scheduled_cancellation_outcome", 32), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ScheduledBookingOffer(Base):
    __tablename__ = "scheduled_booking_offers"
    __table_args__ = (
        UniqueConstraint("booking_id", "driver_id", name="uq_scheduled_offer_booking_driver"),
        CheckConstraint("expires_at > offered_at", name="scheduled_offer_expiry_after_offer"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("scheduled_bookings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    driver_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("driver_profiles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[ScheduledOfferStatus] = mapped_column(
        bounded_enum(ScheduledOfferStatus, "scheduled_offer_status", 16), nullable=False, default=ScheduledOfferStatus.PENDING
    )
    offered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decline_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    conflict_policy_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)


class ScheduledBookingCommitment(Base):
    __tablename__ = "scheduled_booking_commitments"
    __table_args__ = (
        UniqueConstraint("booking_id", name="uq_scheduled_commitment_booking"),
        UniqueConstraint("offer_id", name="uq_scheduled_commitment_offer"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("scheduled_bookings.id", ondelete="RESTRICT"), nullable=False
    )
    offer_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("scheduled_booking_offers.id", ondelete="RESTRICT"), nullable=False
    )
    driver_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("driver_profiles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    vehicle_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=False
    )
    protected_window: Mapped[object] = mapped_column(TSTZRANGE, nullable=False)
    status: Mapped[ScheduledCommitmentStatus] = mapped_column(
        bounded_enum(ScheduledCommitmentStatus, "scheduled_commitment_status", 16),
        nullable=False,
        default=ScheduledCommitmentStatus.ACTIVE,
    )
    committed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    release_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)


class ScheduledBookingEvent(Base):
    __tablename__ = "scheduled_booking_events"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("scheduled_bookings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[ScheduledBookingEventType] = mapped_column(
        bounded_enum(ScheduledBookingEventType, "scheduled_booking_event_type", 32), nullable=False
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    previous_status: Mapped[ScheduledBookingStatus | None] = mapped_column(
        bounded_enum(ScheduledBookingStatus, "scheduled_booking_status", 24), nullable=True
    )
    new_status: Mapped[ScheduledBookingStatus] = mapped_column(
        bounded_enum(ScheduledBookingStatus, "scheduled_booking_status", 24), nullable=False
    )
    controlled_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class DriverScheduledOfferPreference(Base):
    __tablename__ = "driver_scheduled_offer_preferences"
    __table_args__ = (
        UniqueConstraint("driver_id", "city_id", name="uq_driver_scheduled_preference_city"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    driver_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("driver_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    city_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
