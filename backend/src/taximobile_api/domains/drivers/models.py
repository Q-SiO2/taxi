"""Persistent driver state. Verification and availability are intentionally distinct."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from taximobile_api.db.base import Base
from taximobile_api.domains.markets.models import ServiceType, bounded_enum


class VerificationStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ADDITIONAL_INFORMATION_REQUIRED = "ADDITIONAL_INFORMATION_REQUIRED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"
    EXPIRED = "EXPIRED"


class DriverAccountStatus(StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DEACTIVATED = "DEACTIVATED"


class AvailabilityStatus(StrEnum):
    OFFLINE = "OFFLINE"
    AVAILABLE = "AVAILABLE"
    PAUSED = "PAUSED"
    OFFERED_RIDE = "OFFERED_RIDE"
    EN_ROUTE = "EN_ROUTE"
    AT_PICKUP = "AT_PICKUP"
    ON_RIDE = "ON_RIDE"


class VehicleStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class VehicleVerificationStatus(StrEnum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class CredentialVerificationStatus(StrEnum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class DriverProfile(Base):
    __tablename__ = "driver_profiles"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="driver_verification_status"),
        nullable=False,
        default=VerificationStatus.NOT_STARTED,
    )
    account_status: Mapped[DriverAccountStatus] = mapped_column(
        Enum(DriverAccountStatus, name="driver_account_status"),
        nullable=False,
        default=DriverAccountStatus.PENDING,
    )
    availability_status: Mapped[AvailabilityStatus] = mapped_column(
        Enum(AvailabilityStatus, name="driver_availability_status"),
        nullable=False,
        default=AvailabilityStatus.OFFLINE,
    )
    active_vehicle_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    # The selected operational scope is explicit.  A driver may hold several
    # city authorizations but can be online in only this one city/service at a
    # time; OFFLINE clears both fields.
    online_city_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("cities.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    online_service_type: Mapped[ServiceType | None] = mapped_column(
        bounded_enum(ServiceType, "driver_authorization_service_type", 20),
        nullable=True,
    )
    # The beginning of the current uninterrupted waiting period. It is set
    # when an eligible driver explicitly becomes available, preserved across
    # declined/expired offers, and cleared whenever the driver leaves the
    # available/offer states.
    available_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DriverVerification(Base):
    __tablename__ = "driver_verifications"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    driver_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("driver_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="driver_verification_status"), nullable=False
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class DriverCredential(Base):
    """A professional credential fact; sensitive numbers/documents are separate and not exposed here."""

    __tablename__ = "driver_credentials"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    driver_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("driver_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Requirements vary by jurisdiction, so the type remains validated policy
    # data rather than a permanently hard-coded database enum.
    credential_type: Mapped[str] = mapped_column(String(64), nullable=False)
    verification_status: Mapped[CredentialVerificationStatus] = mapped_column(
        Enum(CredentialVerificationStatus, name="credential_verification_status"),
        nullable=False,
        default=CredentialVerificationStatus.PENDING,
        index=True,
    )
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    expiry_warning_sent_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    driver_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("driver_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    make: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    color: Mapped[str] = mapped_column(String(60), nullable=False)
    registration_number: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    taxi_identifier: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    passenger_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[VehicleStatus] = mapped_column(
        Enum(VehicleStatus, name="vehicle_status"), nullable=False, default=VehicleStatus.ACTIVE
    )
    verification_status: Mapped[VehicleVerificationStatus] = mapped_column(
        Enum(VehicleVerificationStatus, name="vehicle_verification_status"),
        nullable=False,
        default=VehicleVerificationStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DriverLocation(Base):
    __tablename__ = "driver_locations"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    driver_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("driver_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    point: Mapped[object] = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    accuracy_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    heading_degrees: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed_meters_per_second: Mapped[float | None] = mapped_column(Float, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
