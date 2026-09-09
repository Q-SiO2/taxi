"""Scoped operations queue and acknowledgement for durable overdue alerts."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.administration.operations_dependencies import (
    authenticated_operations_principal,
)
from taximobile_api.domains.administration.permissions import (
    OperationsPermission,
    OperationsPrincipal,
)
from taximobile_api.domains.administration.service import audit
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.case_alerts.models import (
    CaseAlertSeverity,
    CaseAlertStatus,
    CaseOverdueAlert,
)
from taximobile_api.domains.case_alerts.schemas import (
    CaseAlertAcknowledgeRequest,
    CaseAlertListResponse,
    CaseAlertResponse,
)
from taximobile_api.domains.idempotency.service import (
    IdempotencyKeyReuse,
    IdempotentReplay,
    InvalidIdempotencyKey,
    begin_command,
    finish_command,
)


router = APIRouter(prefix="/operations/case-alerts", tags=["operations-case-alerts"])
SUPPORT_PERMISSION = OperationsPermission.MANAGE_SUPPORT_CASES
SAFETY_PERMISSION = OperationsPermission.MANAGE_SAFETY_CASES


def alert_response(alert: CaseOverdueAlert) -> CaseAlertResponse:
    if alert.support_ticket_id is not None:
        case_type = "SUPPORT"
        case_id = alert.support_ticket_id
    else:
        case_type = "SAFETY"
        assert alert.safety_report_id is not None
        case_id = alert.safety_report_id
    return CaseAlertResponse(
        id=alert.id,
        city_id=alert.city_id,
        case_type=case_type,
        case_id=case_id,
        severity=CaseAlertSeverity(alert.severity),
        status=CaseAlertStatus(alert.status),
        response_due_at=alert.response_due_at,
        first_detected_at=alert.first_detected_at,
        last_evaluated_at=alert.last_evaluated_at,
        delivery_attempts=alert.delivery_attempts,
        next_delivery_at=alert.next_delivery_at,
        last_delivered_at=alert.last_delivered_at,
        acknowledged_at=alert.acknowledged_at,
        acknowledged_by_user_id=alert.acknowledged_by_user_id,
        resolved_at=alert.resolved_at,
    )


def _scope_condition(principal: OperationsPrincipal):
    support_city_ids = principal.city_ids_for(SUPPORT_PERMISSION)
    safety_city_ids = principal.city_ids_for(SAFETY_PERMISSION)
    conditions = []
    if support_city_ids:
        conditions.append(
            CaseOverdueAlert.support_ticket_id.is_not(None)
            & CaseOverdueAlert.city_id.in_(support_city_ids)
        )
    if safety_city_ids:
        conditions.append(
            CaseOverdueAlert.safety_report_id.is_not(None)
            & CaseOverdueAlert.city_id.in_(safety_city_ids)
        )
    if not conditions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A scoped support or safety permission is required.",
        )
    return or_(*conditions)


@router.get("", response_model=CaseAlertListResponse)
async def list_case_alerts(
    city_id: UUID | None = Query(default=None),
    alert_status: CaseAlertStatus | None = Query(default=None, alias="status"),
    severity: CaseAlertSeverity | None = Query(default=None),
    case_type: str | None = Query(default=None, pattern="^(SUPPORT|SAFETY)$"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: OperationsPrincipal = Depends(authenticated_operations_principal),
    session: AsyncSession = Depends(database_session),
) -> CaseAlertListResponse:
    filters = [_scope_condition(principal)]
    if city_id is not None:
        allowed_city_ids = (
            principal.city_ids_for(SUPPORT_PERMISSION)
            | principal.city_ids_for(SAFETY_PERMISSION)
        )
        if city_id not in allowed_city_ids:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="City not found.")
        filters.append(CaseOverdueAlert.city_id == city_id)
    if alert_status is not None:
        filters.append(CaseOverdueAlert.status == alert_status.value)
    if severity is not None:
        filters.append(CaseOverdueAlert.severity == severity.value)
    if case_type == "SUPPORT":
        filters.append(CaseOverdueAlert.support_ticket_id.is_not(None))
    elif case_type == "SAFETY":
        filters.append(CaseOverdueAlert.safety_report_id.is_not(None))
    alerts = list(
        await session.scalars(
            select(CaseOverdueAlert)
            .where(*filters)
            .order_by(
                CaseOverdueAlert.status.asc(),
                CaseOverdueAlert.severity.desc(),
                CaseOverdueAlert.first_detected_at.asc(),
                CaseOverdueAlert.id.asc(),
            )
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    total = await session.scalar(
        select(func.count()).select_from(CaseOverdueAlert).where(*filters)
    )
    return CaseAlertListResponse(
        items=[alert_response(alert) for alert in alerts],
        page=page,
        limit=limit,
        total=total or 0,
    )


@router.post("/{alert_id}/acknowledge", response_model=CaseAlertResponse)
async def acknowledge_case_alert(
    alert_id: UUID,
    payload: CaseAlertAcknowledgeRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: OperationsPrincipal = Depends(authenticated_operations_principal),
    session: AsyncSession = Depends(database_session),
) -> CaseAlertResponse:
    try:
        async with session.begin():
            alert = await session.scalar(
                select(CaseOverdueAlert)
                .where(
                    CaseOverdueAlert.id == alert_id,
                    _scope_condition(principal),
                )
                .with_for_update()
            )
            if alert is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Case alert not found.",
                )
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="operations.case_alert.acknowledge",
                key=idempotency_key,
                payload={"alert_id": str(alert_id), "reason": payload.reason},
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            if alert.status == CaseAlertStatus.RESOLVED.value:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A resolved case alert cannot be acknowledged.",
                )
            now = datetime.now(UTC)
            alert.status = CaseAlertStatus.ACKNOWLEDGED.value
            alert.acknowledged_at = now
            alert.acknowledged_by_user_id = principal.user_id
            alert.next_delivery_at = None
            alert.updated_at = now
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="CASE_OVERDUE_ALERT_ACKNOWLEDGED",
                resource_type="case_overdue_alert",
                resource_id=alert.id,
                city_id=alert.city_id,
                changes={
                    "case_type": "SUPPORT" if alert.support_ticket_id else "SAFETY",
                    "severity": alert.severity,
                    "reason_recorded": True,
                },
            )
            response = alert_response(alert)
            await finish_command(
                session,
                command,
                status_code=status.HTTP_200_OK,
                payload=response.model_dump(mode="json"),
            )
    except InvalidIdempotencyKey as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except IdempotencyKeyReuse as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return response
