"""Restricted market-scoped security-incident workflow."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.administration.models import (
    AdministrativeGrant,
    AdministrativeRoleTemplate,
    AuditLog,
)
from taximobile_api.domains.administration.operations_dependencies import (
    OperationsSessionIdentity,
    require_operations_permission,
    require_recent_operations_mfa,
)
from taximobile_api.domains.administration.permissions import (
    OperationsPermission,
    OperationsPrincipal,
)
from taximobile_api.domains.administration.service import audit
from taximobile_api.domains.auth.models import User, UserStatus
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.idempotency.service import (
    IdempotencyKeyReuse,
    IdempotentReplay,
    InvalidIdempotencyKey,
    begin_command,
    finish_command,
)
from taximobile_api.domains.markets.models import City, Market
from taximobile_api.domains.security_incidents.models import (
    SecurityIncident,
    SecurityIncidentCategory,
    SecurityIncidentPostmortemOutcome,
    SecurityIncidentResponsibility,
    SecurityIncidentResponsibilityAssignment,
    SecurityIncidentSeverity,
    SecurityIncidentStatus,
    SecurityIncidentTimelineEntry,
    SecurityIncidentTimelineKind,
)
from taximobile_api.domains.security_incidents.schemas import (
    SecurityIncidentCreateRequest,
    SecurityIncidentListResponse,
    SecurityIncidentPostmortemCompleteRequest,
    SecurityIncidentResponsibilityAssignRequest,
    SecurityIncidentResponsibilityListResponse,
    SecurityIncidentResponsibilityResponse,
    SecurityIncidentResponse,
    SecurityIncidentTimelineCreateRequest,
    SecurityIncidentTimelineListResponse,
    SecurityIncidentTimelineResponse,
    SecurityIncidentTransitionRequest,
)
from taximobile_api.domains.security_incidents.service import (
    InvalidSecurityIncidentTransition,
    SecurityIncidentTransition,
    apply_transition,
)


router = APIRouter(
    prefix="/operations/security-incidents",
    tags=["operations-security-incidents"],
)
PERMISSION = OperationsPermission.MANAGE_SECURITY_INCIDENTS


def incident_response(incident: SecurityIncident) -> SecurityIncidentResponse:
    return SecurityIncidentResponse(
        id=incident.id,
        reference=incident.reference,
        market_id=incident.market_id,
        city_id=incident.city_id,
        severity=SecurityIncidentSeverity(incident.severity),
        category=SecurityIncidentCategory(incident.category),
        status=SecurityIncidentStatus(incident.status),
        summary=incident.summary,
        reported_by_user_id=incident.reported_by_user_id,
        lead_user_id=incident.lead_user_id,
        detected_at=incident.detected_at,
        opened_at=incident.opened_at,
        containment_due_at=incident.containment_due_at,
        contained_at=incident.contained_at,
        recovered_at=incident.recovered_at,
        closed_at=incident.closed_at,
        postmortem_due_at=incident.postmortem_due_at,
        postmortem_completed_at=incident.postmortem_completed_at,
        postmortem_completed_by_user_id=incident.postmortem_completed_by_user_id,
        postmortem_outcome=(
            SecurityIncidentPostmortemOutcome(incident.postmortem_outcome)
            if incident.postmortem_outcome is not None
            else None
        ),
        optimistic_version=incident.optimistic_version,
    )


def timeline_response(
    entry: SecurityIncidentTimelineEntry,
) -> SecurityIncidentTimelineResponse:
    return SecurityIncidentTimelineResponse(
        id=entry.id,
        incident_id=entry.incident_id,
        sequence=entry.sequence,
        kind=SecurityIncidentTimelineKind(entry.kind),
        actor_user_id=entry.actor_user_id,
        occurred_at=entry.occurred_at,
        recorded_at=entry.recorded_at,
        summary=entry.summary,
        audit_log_id=entry.audit_log_id,
        external_reference=entry.external_reference,
    )


def responsibility_response(
    assignment: SecurityIncidentResponsibilityAssignment,
    *,
    incident_version: int,
) -> SecurityIncidentResponsibilityResponse:
    return SecurityIncidentResponsibilityResponse(
        id=assignment.id,
        incident_id=assignment.incident_id,
        responsibility=SecurityIncidentResponsibility(assignment.responsibility),
        assigned_user_id=assignment.assigned_user_id,
        assigned_by_user_id=assignment.assigned_by_user_id,
        assignment_reference=assignment.assignment_reference,
        assigned_at=assignment.assigned_at,
        released_at=assignment.released_at,
        released_by_user_id=assignment.released_by_user_id,
        release_reference=assignment.release_reference,
        incident_version=incident_version,
    )


def _authorized_market_ids(principal: OperationsPrincipal) -> frozenset[UUID]:
    market_ids = principal.market_ids_for(PERMISSION)
    if not market_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Market-scoped security-incident authority is required.",
        )
    return market_ids


def _aware_utc(value: datetime, *, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field} must be timezone-aware.",
        )
    return value.astimezone(UTC)


async def _locked_incident(
    session: AsyncSession,
    principal: OperationsPrincipal,
    incident_id: UUID,
) -> SecurityIncident:
    incident = await session.scalar(
        select(SecurityIncident)
        .where(
            SecurityIncident.id == incident_id,
            SecurityIncident.market_id.in_(_authorized_market_ids(principal)),
        )
        .with_for_update()
    )
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security incident not found.",
        )
    return incident


async def _append_timeline_entry(
    session: AsyncSession,
    *,
    incident: SecurityIncident,
    actor_user_id: UUID,
    kind: SecurityIncidentTimelineKind,
    summary: str,
    occurred_at: datetime,
    audit_log_id: UUID | None = None,
    external_reference: str | None = None,
) -> SecurityIncidentTimelineEntry:
    last_sequence = await session.scalar(
        select(func.max(SecurityIncidentTimelineEntry.sequence)).where(
            SecurityIncidentTimelineEntry.incident_id == incident.id
        )
    )
    entry = SecurityIncidentTimelineEntry(
        incident_id=incident.id,
        sequence=(last_sequence or 0) + 1,
        kind=kind,
        actor_user_id=actor_user_id,
        occurred_at=occurred_at,
        recorded_at=datetime.now(UTC),
        summary=summary,
        audit_log_id=audit_log_id,
        external_reference=external_reference,
    )
    session.add(entry)
    await session.flush()
    return entry


async def _require_scoped_audit_reference(
    session: AsyncSession,
    *,
    incident: SecurityIncident,
    audit_log_id: UUID | None,
) -> None:
    if audit_log_id is None:
        return
    audit_filters = [
        AuditLog.id == audit_log_id,
        AuditLog.market_id == incident.market_id,
    ]
    if incident.city_id is not None:
        audit_filters.append(
            or_(
                AuditLog.city_id.is_(None),
                AuditLog.city_id == incident.city_id,
            )
        )
    if await session.scalar(select(AuditLog.id).where(*audit_filters)) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scoped audit record not found.",
        )


def _command_error(error: Exception) -> HTTPException:
    if isinstance(error, InvalidIdempotencyKey):
        code = status.HTTP_400_BAD_REQUEST
    else:
        code = status.HTTP_409_CONFLICT
    return HTTPException(status_code=code, detail=str(error))


@router.get("", response_model=SecurityIncidentListResponse)
async def list_security_incidents(
    market_id: UUID | None = Query(default=None),
    city_id: UUID | None = Query(default=None),
    incident_status: SecurityIncidentStatus | None = Query(default=None, alias="status"),
    severity: SecurityIncidentSeverity | None = Query(default=None),
    category: SecurityIncidentCategory | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> SecurityIncidentListResponse:
    authorized_markets = _authorized_market_ids(principal)
    if market_id is not None and market_id not in authorized_markets:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found.")
    filters = [SecurityIncident.market_id.in_(authorized_markets)]
    if market_id is not None:
        filters.append(SecurityIncident.market_id == market_id)
    if city_id is not None:
        filters.append(SecurityIncident.city_id == city_id)
    if incident_status is not None:
        filters.append(SecurityIncident.status == incident_status)
    if severity is not None:
        filters.append(SecurityIncident.severity == severity)
    if category is not None:
        filters.append(SecurityIncident.category == category)
    incidents = list(
        await session.scalars(
            select(SecurityIncident)
            .where(*filters)
            .order_by(
                SecurityIncident.closed_at.asc().nullsfirst(),
                SecurityIncident.severity.asc(),
                SecurityIncident.opened_at.desc(),
                SecurityIncident.id.desc(),
            )
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    total = await session.scalar(
        select(func.count()).select_from(SecurityIncident).where(*filters)
    )
    return SecurityIncidentListResponse(
        items=[incident_response(item) for item in incidents],
        page=page,
        limit=limit,
        total=total or 0,
    )


@router.post(
    "",
    response_model=SecurityIncidentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_security_incident(
    payload: SecurityIncidentCreateRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> SecurityIncidentResponse:
    now = datetime.now(UTC)
    detected_at = _aware_utc(payload.detected_at, field="detected_at")
    containment_due_at = _aware_utc(
        payload.containment_due_at,
        field="containment_due_at",
    )
    if detected_at > now or detected_at < now - timedelta(days=366):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="detected_at must be within the last 366 days and not in the future.",
        )
    if containment_due_at <= now or containment_due_at > now + timedelta(days=31):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="containment_due_at must be within the next 31 days.",
        )
    if payload.market_id not in _authorized_market_ids(principal):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found.")
    try:
        async with session.begin():
            market = await session.get(Market, payload.market_id)
            if market is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Market not found.",
                )
            if payload.city_id is not None:
                city = await session.scalar(
                    select(City).where(
                        City.id == payload.city_id,
                        City.market_id == payload.market_id,
                    )
                )
                if city is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="City not found.",
                    )
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="operations.security_incident.create",
                key=idempotency_key,
                payload=payload.model_dump(mode="json"),
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            incident_id = uuid4()
            incident = SecurityIncident(
                id=incident_id,
                reference=f"SEC-{incident_id.hex.upper()}",
                market_id=payload.market_id,
                city_id=payload.city_id,
                severity=payload.severity,
                category=payload.category,
                status=SecurityIncidentStatus.OPEN,
                summary=payload.summary,
                reported_by_user_id=principal.user_id,
                lead_user_id=principal.user_id,
                detected_at=detected_at,
                opened_at=now,
                containment_due_at=containment_due_at,
                optimistic_version=1,
                created_at=now,
                updated_at=now,
            )
            session.add(incident)
            await session.flush()
            session.add(
                SecurityIncidentResponsibilityAssignment(
                    incident_id=incident.id,
                    responsibility=(
                        SecurityIncidentResponsibility.SECURITY_RESPONSE_LEAD
                    ),
                    assigned_user_id=principal.user_id,
                    assigned_by_user_id=principal.user_id,
                    assignment_reference="INCIDENT-OPENED",
                    assigned_at=now,
                )
            )
            await _append_timeline_entry(
                session,
                incident=incident,
                actor_user_id=principal.user_id,
                kind=SecurityIncidentTimelineKind.INCIDENT_OPENED,
                summary="Security incident opened and assigned to the reporting lead.",
                occurred_at=now,
            )
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="SECURITY_INCIDENT_CREATED",
                resource_type="security_incident",
                resource_id=incident.id,
                market_id=incident.market_id,
                city_id=incident.city_id,
                changes={
                    "severity": payload.severity.value,
                    "category": payload.category.value,
                    "summary_recorded": True,
                    "containment_due_at": containment_due_at.isoformat(),
                },
            )
            response = incident_response(incident)
            await finish_command(
                session,
                command,
                status_code=status.HTTP_201_CREATED,
                payload=response.model_dump(mode="json"),
            )
    except (InvalidIdempotencyKey, IdempotencyKeyReuse) as error:
        raise _command_error(error) from error
    except IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The security incident could not be created safely.",
        ) from error
    return response


@router.get("/{incident_id}", response_model=SecurityIncidentResponse)
async def get_security_incident(
    incident_id: UUID,
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> SecurityIncidentResponse:
    incident = await session.scalar(
        select(SecurityIncident).where(
            SecurityIncident.id == incident_id,
            SecurityIncident.market_id.in_(_authorized_market_ids(principal)),
        )
    )
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security incident not found.",
        )
    return incident_response(incident)


@router.get(
    "/{incident_id}/timeline",
    response_model=SecurityIncidentTimelineListResponse,
)
async def list_security_incident_timeline(
    incident_id: UUID,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> SecurityIncidentTimelineListResponse:
    incident = await session.scalar(
        select(SecurityIncident.id).where(
            SecurityIncident.id == incident_id,
            SecurityIncident.market_id.in_(_authorized_market_ids(principal)),
        )
    )
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security incident not found.",
        )
    filters = [SecurityIncidentTimelineEntry.incident_id == incident_id]
    entries = list(
        await session.scalars(
            select(SecurityIncidentTimelineEntry)
            .where(*filters)
            .order_by(SecurityIncidentTimelineEntry.sequence.asc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    total = await session.scalar(
        select(func.count()).select_from(SecurityIncidentTimelineEntry).where(*filters)
    )
    return SecurityIncidentTimelineListResponse(
        items=[timeline_response(item) for item in entries],
        page=page,
        limit=limit,
        total=total or 0,
    )


@router.get(
    "/{incident_id}/responsibilities",
    response_model=SecurityIncidentResponsibilityListResponse,
)
async def list_security_incident_responsibilities(
    incident_id: UUID,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> SecurityIncidentResponsibilityListResponse:
    incident = await session.scalar(
        select(SecurityIncident).where(
            SecurityIncident.id == incident_id,
            SecurityIncident.market_id.in_(_authorized_market_ids(principal)),
        )
    )
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security incident not found.",
        )
    filters = [SecurityIncidentResponsibilityAssignment.incident_id == incident_id]
    assignments = list(
        await session.scalars(
            select(SecurityIncidentResponsibilityAssignment)
            .where(*filters)
            .order_by(
                SecurityIncidentResponsibilityAssignment.released_at.asc().nullsfirst(),
                SecurityIncidentResponsibilityAssignment.responsibility.asc(),
                SecurityIncidentResponsibilityAssignment.assigned_at.desc(),
                SecurityIncidentResponsibilityAssignment.id.desc(),
            )
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    total = await session.scalar(
        select(func.count())
        .select_from(SecurityIncidentResponsibilityAssignment)
        .where(*filters)
    )
    return SecurityIncidentResponsibilityListResponse(
        items=[
            responsibility_response(
                assignment,
                incident_version=incident.optimistic_version,
            )
            for assignment in assignments
        ],
        page=page,
        limit=limit,
        total=total or 0,
    )


@router.post(
    "/{incident_id}/responsibilities/{responsibility}/assign",
    response_model=SecurityIncidentResponsibilityResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_security_incident_responsibility(
    incident_id: UUID,
    responsibility: SecurityIncidentResponsibility,
    payload: SecurityIncidentResponsibilityAssignRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> SecurityIncidentResponsibilityResponse:
    occurred_at = _aware_utc(payload.occurred_at, field="occurred_at")
    now = datetime.now(UTC)
    if occurred_at > now:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="occurred_at cannot be in the future.",
        )
    try:
        async with session.begin():
            incident = await _locked_incident(session, principal, incident_id)
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="operations.security_incident.responsibility.assign",
                key=idempotency_key,
                payload={
                    "incident_id": str(incident_id),
                    "responsibility": responsibility.value,
                    **payload.model_dump(mode="json"),
                },
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(
                    status_code=command.status_code,
                    content=command.payload,
                )
            if incident.optimistic_version != payload.expected_version:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "The incident changed; reload it before assigning "
                        "responsibility."
                    ),
                )
            if incident.postmortem_completed_at is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Completed incidents cannot receive new responsibilities.",
                )
            if occurred_at < incident.opened_at:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="occurred_at cannot precede incident opening.",
                )
            eligible_responder = await session.scalar(
                select(User.id)
                .join(
                    AdministrativeGrant,
                    AdministrativeGrant.user_id == User.id,
                )
                .where(
                    User.id == payload.assigned_user_id,
                    User.status == UserStatus.ACTIVE,
                    AdministrativeGrant.role_template
                    == AdministrativeRoleTemplate.PLATFORM_ADMIN,
                    AdministrativeGrant.market_id == incident.market_id,
                    AdministrativeGrant.operator_id.is_(None),
                    AdministrativeGrant.city_id.is_(None),
                    AdministrativeGrant.revoked_at.is_(None),
                    or_(
                        AdministrativeGrant.expires_at.is_(None),
                        AdministrativeGrant.expires_at > now,
                    ),
                )
                .limit(1)
            )
            if eligible_responder is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Responder is not currently eligible for this incident "
                        "market."
                    ),
                )
            active_assignment = await session.scalar(
                select(SecurityIncidentResponsibilityAssignment)
                .where(
                    SecurityIncidentResponsibilityAssignment.incident_id
                    == incident.id,
                    SecurityIncidentResponsibilityAssignment.responsibility
                    == responsibility,
                    SecurityIncidentResponsibilityAssignment.released_at.is_(None),
                )
                .with_for_update()
            )
            if (
                active_assignment is not None
                and active_assignment.assigned_user_id == payload.assigned_user_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="That responder already holds this responsibility.",
                )
            if active_assignment is not None:
                if occurred_at < active_assignment.assigned_at:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="occurred_at cannot precede the active assignment.",
                    )
                active_assignment.released_at = occurred_at
                active_assignment.released_by_user_id = principal.user_id
                active_assignment.release_reference = payload.external_reference
            assignment = SecurityIncidentResponsibilityAssignment(
                incident_id=incident.id,
                responsibility=responsibility,
                assigned_user_id=payload.assigned_user_id,
                assigned_by_user_id=principal.user_id,
                assignment_reference=payload.external_reference,
                assigned_at=occurred_at,
            )
            session.add(assignment)
            if responsibility == SecurityIncidentResponsibility.SECURITY_RESPONSE_LEAD:
                incident.lead_user_id = payload.assigned_user_id
            incident.optimistic_version += 1
            incident.updated_at = now
            await session.flush()
            timeline_entry = await _append_timeline_entry(
                session,
                incident=incident,
                actor_user_id=principal.user_id,
                kind=SecurityIncidentTimelineKind.RESPONSIBILITY_CHANGED,
                summary=(
                    f"{responsibility.value} responsibility assigned under an "
                    "approved roster reference."
                ),
                occurred_at=occurred_at,
                external_reference=payload.external_reference,
            )
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="SECURITY_INCIDENT_RESPONSIBILITY_ASSIGNED",
                resource_type="security_incident",
                resource_id=incident.id,
                market_id=incident.market_id,
                city_id=incident.city_id,
                changes={
                    "responsibility": responsibility.value,
                    "reassigned": active_assignment is not None,
                    "external_reference_recorded": True,
                    "timeline_sequence": timeline_entry.sequence,
                    "optimistic_version": incident.optimistic_version,
                },
            )
            response = responsibility_response(
                assignment,
                incident_version=incident.optimistic_version,
            )
            await finish_command(
                session,
                command,
                status_code=status.HTTP_201_CREATED,
                payload=response.model_dump(mode="json"),
            )
    except (InvalidIdempotencyKey, IdempotencyKeyReuse) as error:
        raise _command_error(error) from error
    except IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The responsibility changed concurrently; reload and retry.",
        ) from error
    return response


@router.post(
    "/{incident_id}/timeline",
    response_model=SecurityIncidentTimelineResponse,
    status_code=status.HTTP_201_CREATED,
)
async def append_security_incident_timeline(
    incident_id: UUID,
    payload: SecurityIncidentTimelineCreateRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> SecurityIncidentTimelineResponse:
    occurred_at = _aware_utc(payload.occurred_at, field="occurred_at")
    now = datetime.now(UTC)
    if occurred_at > now:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="occurred_at cannot be in the future.",
        )
    try:
        async with session.begin():
            incident = await _locked_incident(session, principal, incident_id)
            if occurred_at < incident.detected_at:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="occurred_at cannot precede incident detection.",
                )
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="operations.security_incident.timeline.append",
                key=idempotency_key,
                payload={
                    "incident_id": str(incident_id),
                    **payload.model_dump(mode="json"),
                },
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            await _require_scoped_audit_reference(
                session,
                incident=incident,
                audit_log_id=payload.audit_log_id,
            )
            entry = await _append_timeline_entry(
                session,
                incident=incident,
                actor_user_id=principal.user_id,
                kind=payload.kind,
                summary=payload.summary,
                occurred_at=occurred_at,
                audit_log_id=payload.audit_log_id,
                external_reference=payload.external_reference,
            )
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="SECURITY_INCIDENT_TIMELINE_APPENDED",
                resource_type="security_incident",
                resource_id=incident.id,
                market_id=incident.market_id,
                city_id=incident.city_id,
                changes={
                    "kind": payload.kind.value,
                    "sequence": entry.sequence,
                    "audit_log_linked": payload.audit_log_id is not None,
                    "external_reference_recorded": payload.external_reference is not None,
                    "summary_recorded": True,
                },
            )
            response = timeline_response(entry)
            await finish_command(
                session,
                command,
                status_code=status.HTTP_201_CREATED,
                payload=response.model_dump(mode="json"),
            )
    except (InvalidIdempotencyKey, IdempotencyKeyReuse) as error:
        raise _command_error(error) from error
    except IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The timeline changed concurrently; retry with a new idempotency key.",
        ) from error
    return response


@router.post("/{incident_id}/transitions", response_model=SecurityIncidentResponse)
async def transition_security_incident(
    incident_id: UUID,
    payload: SecurityIncidentTransitionRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> SecurityIncidentResponse:
    occurred_at = _aware_utc(payload.occurred_at, field="occurred_at")
    now = datetime.now(UTC)
    if occurred_at > now:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="occurred_at cannot be in the future.",
        )
    postmortem_due_at = None
    if payload.postmortem_due_at is not None:
        postmortem_due_at = _aware_utc(
            payload.postmortem_due_at,
            field="postmortem_due_at",
        )
        if postmortem_due_at <= occurred_at or postmortem_due_at > now + timedelta(days=90):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="postmortem_due_at must be after closure and within 90 days.",
            )
    try:
        async with session.begin():
            incident = await _locked_incident(session, principal, incident_id)
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="operations.security_incident.transition",
                key=idempotency_key,
                payload={
                    "incident_id": str(incident_id),
                    **payload.model_dump(mode="json"),
                },
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            if incident.optimistic_version != payload.expected_version:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="The incident changed; reload it before deciding the next action.",
                )
            if occurred_at < incident.detected_at:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="occurred_at cannot precede incident detection.",
                )
            lifecycle_floor = max(
                timestamp
                for timestamp in (
                    incident.opened_at,
                    incident.contained_at,
                    incident.recovered_at,
                    incident.closed_at,
                )
                if timestamp is not None
            )
            if occurred_at < lifecycle_floor:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="occurred_at cannot precede the latest lifecycle milestone.",
                )
            old_status = SecurityIncidentStatus(incident.status)
            try:
                result = apply_transition(
                    current_status=old_status,
                    transition=payload.transition,
                    changed_at=occurred_at,
                    contained_at=incident.contained_at,
                    recovered_at=incident.recovered_at,
                    closed_at=incident.closed_at,
                )
            except InvalidSecurityIncidentTransition as error:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=str(error),
                ) from error
            incident.status = result.status
            incident.contained_at = result.contained_at
            incident.recovered_at = result.recovered_at
            incident.closed_at = result.closed_at
            incident.postmortem_due_at = postmortem_due_at
            incident.optimistic_version += 1
            incident.updated_at = now
            await _append_timeline_entry(
                session,
                incident=incident,
                actor_user_id=principal.user_id,
                kind=SecurityIncidentTimelineKind.STATUS_TRANSITION,
                summary=payload.summary,
                occurred_at=occurred_at,
            )
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="SECURITY_INCIDENT_STATUS_CHANGED",
                resource_type="security_incident",
                resource_id=incident.id,
                market_id=incident.market_id,
                city_id=incident.city_id,
                changes={
                    "from_status": old_status.value,
                    "to_status": result.status.value,
                    "transition": payload.transition.value,
                    "optimistic_version": incident.optimistic_version,
                    "summary_recorded": True,
                    "postmortem_due_at": (
                        postmortem_due_at.isoformat()
                        if postmortem_due_at is not None
                        else None
                    ),
                },
            )
            response = incident_response(incident)
            await finish_command(
                session,
                command,
                status_code=status.HTTP_200_OK,
                payload=response.model_dump(mode="json"),
            )
    except (InvalidIdempotencyKey, IdempotencyKeyReuse) as error:
        raise _command_error(error) from error
    except IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The incident changed concurrently; reload and retry.",
        ) from error
    return response


@router.post(
    "/{incident_id}/postmortem/complete",
    response_model=SecurityIncidentResponse,
)
async def complete_security_incident_postmortem(
    incident_id: UUID,
    payload: SecurityIncidentPostmortemCompleteRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> SecurityIncidentResponse:
    occurred_at = _aware_utc(payload.occurred_at, field="occurred_at")
    now = datetime.now(UTC)
    if occurred_at > now:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="occurred_at cannot be in the future.",
        )
    try:
        async with session.begin():
            incident = await _locked_incident(session, principal, incident_id)
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="operations.security_incident.postmortem.complete",
                key=idempotency_key,
                payload={
                    "incident_id": str(incident_id),
                    **payload.model_dump(mode="json"),
                },
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            if incident.optimistic_version != payload.expected_version:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="The incident changed; reload it before completing the postmortem.",
                )
            if SecurityIncidentStatus(incident.status) != SecurityIncidentStatus.CLOSED:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="The incident must be closed before its postmortem can be completed.",
                )
            if incident.postmortem_completed_at is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="The incident postmortem is already complete.",
                )
            if incident.closed_at is None or occurred_at < incident.closed_at:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="occurred_at cannot precede incident closure.",
                )
            await _require_scoped_audit_reference(
                session,
                incident=incident,
                audit_log_id=payload.audit_log_id,
            )
            incident.postmortem_completed_at = occurred_at
            incident.postmortem_completed_by_user_id = principal.user_id
            incident.postmortem_outcome = payload.outcome
            incident.optimistic_version += 1
            incident.updated_at = now
            entry = await _append_timeline_entry(
                session,
                incident=incident,
                actor_user_id=principal.user_id,
                kind=SecurityIncidentTimelineKind.POSTMORTEM_ACTION,
                summary=payload.summary,
                occurred_at=occurred_at,
                audit_log_id=payload.audit_log_id,
                external_reference=payload.external_reference,
            )
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="SECURITY_INCIDENT_POSTMORTEM_COMPLETED",
                resource_type="security_incident",
                resource_id=incident.id,
                market_id=incident.market_id,
                city_id=incident.city_id,
                changes={
                    "outcome": payload.outcome.value,
                    "timeline_sequence": entry.sequence,
                    "audit_log_linked": payload.audit_log_id is not None,
                    "external_reference_recorded": payload.external_reference is not None,
                    "summary_recorded": True,
                    "completed_at": occurred_at.isoformat(),
                    "optimistic_version": incident.optimistic_version,
                },
            )
            response = incident_response(incident)
            await finish_command(
                session,
                command,
                status_code=status.HTTP_200_OK,
                payload=response.model_dump(mode="json"),
            )
    except (InvalidIdempotencyKey, IdempotencyKeyReuse) as error:
        raise _command_error(error) from error
    except IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The incident changed concurrently; reload and retry.",
        ) from error
    return response
