from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from sqlalchemy import CheckConstraint, DateTime, Enum, Float, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from taximobile_api.db.base import Base
from taximobile_api.domains.markets.models import ServiceType, bounded_enum
from taximobile_api.domains.payments.models import PaymentMethod


class RideStatus(StrEnum):
    REQUESTED = "REQUESTED"
    MATCHING = "MATCHING"
    ACCEPTED = "ACCEPTED"
    DRIVER_EN_ROUTE = "DRIVER_EN_ROUTE"
    DRIVER_ARRIVED = "DRIVER_ARRIVED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    UNMATCHED = "UNMATCHED"


class RideEventType(StrEnum):
    CREATED = "CREATED"
    STATUS_CHANGED = "STATUS_CHANGED"
    CANCELLED = "CANCELLED"
    OFFER_CREATED = "OFFER_CREATED"
    OFFER_DECLINED = "OFFER_DECLINED"
    OFFER_EXPIRED = "OFFER_EXPIRED"
    MATCHING_FAILED = "MATCHING_FAILED"


class RideOfferStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class Ride(Base):
    __tablename__ = "rides"
    __table_args__ = (
        CheckConstraint(
            "(service_type = 'ON_DEMAND' AND fixed_route_direction_id IS NULL) OR "
            "(service_type = 'FIXED_ROUTE' AND fixed_route_direction_id IS NOT NULL)",
            name="ride_fixed_route_consistency",
        ),
        Index(
            "uq_rides_one_active_per_driver", "driver_id", unique=True,
            postgresql_where=text(
                "driver_id IS NOT NULL AND status IN "
                "('ACCEPTED', 'DRIVER_EN_ROUTE', 'DRIVER_ARRIVED', 'IN_PROGRESS')"
            ),
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
        bounded_enum(ServiceType, "ride_service_type", 20),
        nullable=False,
        default=ServiceType.ON_DEMAND,
        index=True,
    )
    fixed_route_direction_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("fixed_route_directions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    scheduled_booking_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("scheduled_bookings.id", name="fk_rides_scheduled_booking", use_alter=True, ondelete="RESTRICT"),
        nullable=True,
        unique=True,
    )
    passenger_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    driver_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("driver_profiles.id"), nullable=True, index=True)
    vehicle_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=True, index=True)
    assigned_driver_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    assigned_vehicle_make: Mapped[str | None] = mapped_column(String(80), nullable=True)
    assigned_vehicle_model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    assigned_vehicle_color: Mapped[str | None] = mapped_column(String(60), nullable=True)
    assigned_taxi_identifier: Mapped[str | None] = mapped_column(String(64), nullable=True)
    quoted_pricing_rule_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("pricing_rules.id"), nullable=True)
    quoted_amount: Mapped[object | None] = mapped_column(Numeric(12, 2), nullable=True)
    quoted_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method"), nullable=False, default=PaymentMethod.CASH
    )
    payment_capability_version_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("payment_capability_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    payment_recipient_account_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("payment_recipient_accounts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    transfer_recipient_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    transfer_bank_account: Mapped[str | None] = mapped_column(String(120), nullable=True)
    transfer_wallet_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[RideStatus] = mapped_column(Enum(RideStatus, name="ride_status"), nullable=False, default=RideStatus.REQUESTED, index=True)
    pickup_point: Mapped[object] = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    destination_point: Mapped[object] = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    completed_point: Mapped[object | None] = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    pickup_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    destination_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    passenger_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cancelled_by_user_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    en_route_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class RideEvent(Base):
    __tablename__ = "ride_events"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    ride_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("rides.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[RideEventType] = mapped_column(Enum(RideEventType, name="ride_event_type"), nullable=False)
    previous_status: Mapped[RideStatus | None] = mapped_column(Enum(RideStatus, name="ride_status"), nullable=True)
    new_status: Mapped[RideStatus] = mapped_column(Enum(RideStatus, name="ride_status"), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class RideOffer(Base):
    __tablename__ = "ride_offers"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    ride_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("rides.id", ondelete="CASCADE"), nullable=False, index=True)
    driver_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("driver_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[RideOfferStatus] = mapped_column(Enum(RideOfferStatus, name="ride_offer_status"), nullable=False, default=RideOfferStatus.PENDING, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decline_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    estimated_pickup_distance_meters: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_pickup_time_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    idle_seconds_at_offer: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recent_assignment_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    proximity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    idle_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    fairness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ranking_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    matching_algorithm_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class RideRating(Base):
    """Immutable passenger feedback for a completed assigned ride.

    Ordinary feedback deliberately has its own table. It must not be used for
    safety reports or to alter dispatch/driver eligibility without a separately
    documented policy.
    """

    __tablename__ = "ride_ratings"
    __table_args__ = (
        CheckConstraint("score BETWEEN 1 AND 5", name="ride_rating_score_range"),
        UniqueConstraint("ride_id", "reviewer_id", name="one_rating_per_reviewer_per_ride"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    ride_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("rides.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reviewer_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reviewed_user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
