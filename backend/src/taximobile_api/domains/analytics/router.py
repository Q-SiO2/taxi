from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.administration.operations_dependencies import require_operations_permission
from taximobile_api.domains.administration.permissions import OperationsPermission, OperationsPrincipal
from taximobile_api.domains.analytics.definitions import (
    LATE_EVENT_POLICY,
    METRIC_DEFINITION_VERSION,
    METRIC_DEFINITIONS,
    MINIMUM_CELL_SIZE,
    RETENTION_DAYS,
)
from taximobile_api.domains.analytics.schemas import (
    MetricDefinitionListResponse,
    MetricDefinitionResponse,
    OperationalMetricFactListResponse,
)
from taximobile_api.domains.analytics.service import present_fact
from taximobile_api.domains.auth.router import database_session


router = APIRouter(prefix="/operations/analytics", tags=["operations-analytics"])
VIEW_ANALYTICS = OperationsPermission.VIEW_SCOPED_OPERATIONAL_AGGREGATES


@router.get("/definitions", response_model=MetricDefinitionListResponse)
async def metric_definitions(
    principal: OperationsPrincipal = Depends(require_operations_permission(VIEW_ANALYTICS)),
) -> MetricDefinitionListResponse:
    del principal
    return MetricDefinitionListResponse(
        items=[
            MetricDefinitionResponse(
                **asdict(definition),
                definition_version=METRIC_DEFINITION_VERSION,
                retention_days=RETENTION_DAYS,
                late_event_policy=LATE_EVENT_POLICY,
                minimum_cell_size=MINIMUM_CELL_SIZE,
            )
            for definition in METRIC_DEFINITIONS
        ]
    )


@router.get("/facts", response_model=OperationalMetricFactListResponse)
async def operational_facts(
    city_id: UUID,
    from_time: datetime | None = Query(default=None, alias="from"),
    to_time: datetime | None = Query(default=None, alias="to"),
    service_type: str | None = Query(default=None, pattern="^(ON_DEMAND|FIXED_ROUTE)$"),
    metric_code: str | None = Query(default=None, min_length=1, max_length=48),
    principal: OperationsPrincipal = Depends(require_operations_permission(VIEW_ANALYTICS)),
    session: AsyncSession = Depends(database_session),
) -> OperationalMetricFactListResponse:
    if city_id not in principal.city_ids_for(VIEW_ANALYTICS):
        raise HTTPException(status_code=404, detail="City scope not found.")
    end = to_time or datetime.now(UTC)
    start = from_time or end - timedelta(days=30)
    if start.tzinfo is None or end.tzinfo is None:
        raise HTTPException(status_code=422, detail="Analytics time bounds must include a timezone.")
    if start >= end or end - start > timedelta(days=31):
        raise HTTPException(status_code=422, detail="Choose a positive analytics window of at most 31 days.")
    filters = ["city_id = :city_id", "bucket_start >= :from_time", "bucket_start < :to_time"]
    params: dict[str, object] = {"city_id": city_id, "from_time": start, "to_time": end}
    if service_type is not None:
        filters.append("service_type = :service_type")
        params["service_type"] = service_type
    if metric_code is not None:
        filters.append("metric_code = :metric_code")
        params["metric_code"] = metric_code
    rows = (
        await session.execute(
            text(
                "SELECT * FROM operational_metric_facts_hourly_v1 WHERE "
                + " AND ".join(filters)
                + " ORDER BY bucket_start, metric_code, outcome_code NULLS FIRST"
            ),
            params,
        )
    ).all()
    return OperationalMetricFactListResponse(
        items=[present_fact(row) for row in rows],
        from_time=start,
        to_time=end,
        bucket="HOUR",
        definition_version=METRIC_DEFINITION_VERSION,
        minimum_cell_size=MINIMUM_CELL_SIZE,
        late_event_policy=LATE_EVENT_POLICY,
        retention_days=RETENTION_DAYS,
    )
