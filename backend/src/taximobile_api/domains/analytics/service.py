from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.analytics.definitions import (
    LATE_EVENT_POLICY,
    METRIC_DEFINITION_BY_CODE,
    MINIMUM_CELL_SIZE,
    RETENTION_DAYS,
)
from taximobile_api.domains.analytics.schemas import OperationalMetricFactResponse


ANALYTICS_REFRESH_LOCK = 8_417_033_917


def hour_bucket(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        raise ValueError("Analytics timestamps must include a timezone.")
    return moment.astimezone(UTC).replace(minute=0, second=0, microsecond=0)


async def refresh_operational_analytics(
    session: AsyncSession,
    *,
    now: datetime | None = None,
) -> int:
    """Snapshot coarse supply and rebuild source-derived facts under one DB lock."""
    observed_at = now or datetime.now(UTC)
    bucket_start = hour_bucket(observed_at)
    retention_until = bucket_start + timedelta(days=RETENTION_DAYS)
    await session.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": ANALYTICS_REFRESH_LOCK},
    )
    await session.execute(
        text("DELETE FROM operational_supply_snapshots_hourly WHERE retention_until <= :now"),
        {"now": observed_at},
    )
    result = await session.execute(
        text(
            """
            WITH active_assignments AS (
              SELECT city_id, operator_id, service_type::text AS service_type
              FROM operator_city_assignments
              WHERE status::text = 'ACTIVE'
                AND effective_from <= :observed_at
                AND (effective_until IS NULL OR effective_until > :observed_at)
            )
            SELECT
              aa.city_id,
              aa.operator_id,
              aa.service_type,
              count(DISTINCT auth.driver_id) FILTER (
                WHERE auth.status::text = 'ACTIVE'
                  AND auth.valid_from <= :observed_at
                  AND (auth.valid_until IS NULL OR auth.valid_until > :observed_at)
                  AND dp.verification_status::text = 'APPROVED'
                  AND dp.account_status::text = 'ACTIVE'
                  AND v.status::text = 'ACTIVE'
                  AND v.verification_status::text = 'VERIFIED'
              )::integer AS eligible_count,
              count(DISTINCT auth.driver_id) FILTER (
                WHERE auth.status::text = 'ACTIVE'
                  AND auth.valid_from <= :observed_at
                  AND (auth.valid_until IS NULL OR auth.valid_until > :observed_at)
                  AND dp.verification_status::text = 'APPROVED'
                  AND dp.account_status::text = 'ACTIVE'
                  AND dp.availability_status::text = 'AVAILABLE'
                  AND dp.online_city_id = aa.city_id
                  AND dp.online_service_type::text = aa.service_type
                  AND v.status::text = 'ACTIVE'
                  AND v.verification_status::text = 'VERIFIED'
              )::integer AS available_count
            FROM active_assignments aa
            LEFT JOIN driver_city_authorizations auth ON auth.city_id = aa.city_id
            LEFT JOIN driver_city_authorization_services auth_service
              ON auth_service.authorization_id = auth.id
             AND auth_service.service_type::text = aa.service_type
            LEFT JOIN driver_profiles dp ON dp.id = auth.driver_id
            LEFT JOIN vehicles v ON v.id = dp.active_vehicle_id
            WHERE auth.id IS NULL OR auth_service.authorization_id IS NOT NULL
            GROUP BY aa.city_id, aa.operator_id, aa.service_type
            """
        ),
        {"observed_at": observed_at},
    )
    rows = result.mappings().all()
    for row in rows:
        await session.execute(
            text(
                """
                INSERT INTO operational_supply_snapshots_hourly (
                  id, city_id, operator_id, service_type, zone_code, bucket_start,
                  available_driver_count, eligible_driver_count, observed_at, retention_until
                ) VALUES (
                  gen_random_uuid(), :city_id, :operator_id, :service_type, 'CITY_WIDE',
                  :bucket_start, :available_count, :eligible_count, :observed_at, :retention_until
                )
                ON CONFLICT (city_id, operator_id, service_type, zone_code, bucket_start)
                DO UPDATE SET
                  available_driver_count = EXCLUDED.available_driver_count,
                  eligible_driver_count = EXCLUDED.eligible_driver_count,
                  observed_at = EXCLUDED.observed_at,
                  retention_until = EXCLUDED.retention_until
                """
            ),
            {
                **row,
                "bucket_start": bucket_start,
                "observed_at": observed_at,
                "retention_until": retention_until,
            },
        )
    await session.execute(text("REFRESH MATERIALIZED VIEW operational_metric_facts_hourly_v1"))
    return len(rows)


def _average(total: int | Decimal | None, samples: int) -> Decimal | None:
    if total is None or samples <= 0:
        return None
    return (Decimal(total) / Decimal(samples)).quantize(Decimal("0.01"))


def present_fact(row) -> OperationalMetricFactResponse:
    raw_samples = int(row.sample_count)
    suppressed = raw_samples < MINIMUM_CELL_SIZE
    definition = METRIC_DEFINITION_BY_CODE.get(row.metric_code)
    family = definition.family if definition is not None else "other"
    return OperationalMetricFactResponse(
        bucket_start=row.bucket_start,
        city_id=row.city_id,
        operator_id=row.operator_id,
        service_type=row.service_type,
        booking_type=row.booking_type,
        fixed_route_direction_version_id=row.fixed_route_direction_id,
        pricing_rule_version_id=row.pricing_rule_id,
        operator_fee_policy_version_id=row.operator_fee_policy_id,
        scheduling_policy_version_id=row.scheduling_policy_id,
        matching_algorithm_version=row.matching_algorithm_version,
        metric_code=row.metric_code,
        metric_family=family,
        outcome_code=row.outcome_code,
        category_code=row.category_code,
        currency=row.currency,
        sample_count=None if suppressed else raw_samples,
        integer_value=None if suppressed else int(row.integer_value),
        average_duration_seconds=None
        if suppressed
        else _average(row.duration_seconds_sum, raw_samples),
        average_distance_meters=None
        if suppressed
        else _average(row.distance_meters_sum, raw_samples),
        amount_sum=None if suppressed else row.amount_sum,
        average_numeric_value=None
        if suppressed
        else _average(row.numeric_value_sum, raw_samples),
        average_per_entity=None
        if suppressed
        else _average(row.integer_value, raw_samples),
        minimum_per_entity=None
        if suppressed or row.minimum_per_entity is None
        else int(row.minimum_per_entity),
        maximum_per_entity=None
        if suppressed or row.maximum_per_entity is None
        else int(row.maximum_per_entity),
        distribution_gini=None if suppressed else row.distribution_gini,
        suppressed=suppressed,
        source_watermark=row.source_watermark,
        computed_at=row.computed_at,
    )
