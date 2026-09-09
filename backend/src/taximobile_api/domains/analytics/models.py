from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from taximobile_api.db.base import Base


class OperationalSupplySnapshot(Base):
    __tablename__ = "operational_supply_snapshots_hourly"
    __table_args__ = (
        CheckConstraint(
            "service_type IN ('ON_DEMAND', 'FIXED_ROUTE')",
            name="operational_supply_service_type",
        ),
        CheckConstraint("zone_code = 'CITY_WIDE'", name="operational_supply_coarse_zone"),
        CheckConstraint(
            "available_driver_count >= 0 AND eligible_driver_count >= available_driver_count",
            name="operational_supply_counts_valid",
        ),
        CheckConstraint(
            "retention_until > bucket_start", name="operational_supply_retention_after_bucket"
        ),
        UniqueConstraint(
            "city_id",
            "operator_id",
            "service_type",
            "zone_code",
            "bucket_start",
            name="operational_supply_bucket_scope",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    city_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("cities.id", ondelete="CASCADE"), nullable=False
    )
    operator_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("operators.id", ondelete="CASCADE"), nullable=False
    )
    service_type: Mapped[str] = mapped_column(String(20), nullable=False)
    zone_code: Mapped[str] = mapped_column(String(32), nullable=False, default="CITY_WIDE")
    bucket_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available_driver_count: Mapped[int] = mapped_column(Integer, nullable=False)
    eligible_driver_count: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retention_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
