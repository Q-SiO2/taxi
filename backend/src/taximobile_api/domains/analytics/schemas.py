from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class MetricDefinitionResponse(BaseModel):
    code: str
    family: str
    title: str
    unit: str
    source: str
    purpose: str
    owner: str
    definition_version: str
    retention_days: int
    late_event_policy: str
    minimum_cell_size: int


class MetricDefinitionListResponse(BaseModel):
    items: list[MetricDefinitionResponse]


class OperationalMetricFactResponse(BaseModel):
    bucket_start: datetime
    city_id: UUID
    operator_id: UUID | None
    service_type: str | None
    booking_type: str | None
    fixed_route_direction_version_id: UUID | None
    pricing_rule_version_id: UUID | None
    operator_fee_policy_version_id: UUID | None
    scheduling_policy_version_id: UUID | None
    matching_algorithm_version: str | None
    metric_code: str
    metric_family: str
    outcome_code: str | None
    category_code: str | None
    currency: str | None
    sample_count: int | None
    integer_value: int | None
    average_duration_seconds: Decimal | None
    average_distance_meters: Decimal | None
    amount_sum: Decimal | None
    average_numeric_value: Decimal | None
    average_per_entity: Decimal | None
    minimum_per_entity: int | None
    maximum_per_entity: int | None
    distribution_gini: Decimal | None
    suppressed: bool
    source_watermark: datetime
    computed_at: datetime


class OperationalMetricFactListResponse(BaseModel):
    items: list[OperationalMetricFactResponse]
    from_time: datetime
    to_time: datetime
    bucket: str
    definition_version: str
    minimum_cell_size: int
    late_event_policy: str
    retention_days: int
