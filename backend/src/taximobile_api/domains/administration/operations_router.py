"""Scoped staff-grant and audit endpoints for the operations namespace."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.administration.grant_changes import (
    GrantChangeConflict,
    GrantChangeError,
    GrantChangeForbidden,
    GrantChangeInvalid,
    GrantChangeNotFound,
    approve_grant_change,
    cancel_grant_change,
    ensure_platform_admin_continuity_before_revoke,
    reject_grant_change,
    request_grant_creation,
    request_grant_revocation,
    resolve_scope_market_id,
)
from taximobile_api.domains.administration.models import (
    AdministrativeGrant,
    AdministrativeGrantChangeRequest,
    AdministrativeGrantRequestAction,
    AdministrativeGrantRequestStatus,
    AuditLog,
)
from taximobile_api.domains.administration.operations_dependencies import (
    OperationsSessionIdentity,
    require_recent_operations_mfa,
    require_operations_permission,
)
from taximobile_api.domains.administration.operations_schemas import (
    AdministrativeGrantCreateRequest,
    AdministrativeGrantChangeRequestListResponse,
    AdministrativeGrantChangeRequestResponse,
    AdministrativeGrantDecisionRequest,
    AdministrativeGrantListResponse,
    AdministrativeGrantRevocationRequest,
    AdministrativeGrantResponse,
    OperationsAccountSecurityActionRequest,
    OperationsAuditLogListResponse,
    OperationsAuditLogResponse,
)
from taximobile_api.domains.administration.permissions import (
    OperationsPermission,
    OperationsPrincipal,
)
from taximobile_api.domains.administration.schemas import AccountSecurityActionResponse
from taximobile_api.domains.administration.service import (
    audit,
    revoke_user_access,
    suspend_locked_user_access,
)
from taximobile_api.domains.auth.authority import lock_user_for_status_change
from taximobile_api.domains.auth.models import User, UserStatus
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.driver_applications.models import (
    DriverCityApplication,
    DriverCityAuthorization,
)
from taximobile_api.domains.drivers.models import DriverProfile
from taximobile_api.domains.idempotency.service import (
    IdempotencyKeyReuse,
    IdempotentReplay,
    InvalidIdempotencyKey,
    begin_command,
    finish_command,
)
from taximobile_api.domains.markets.models import City, Market, Operator
from taximobile_api.domains.rides.models import Ride
from taximobile_api.domains.safety.models import SafetyReport
from taximobile_api.domains.scheduled_bookings.models import ScheduledBooking
from taximobile_api.domains.support.models import SupportTicket


router = APIRouter(prefix="/operations", tags=["operations-administration"])


def grant_response(grant: AdministrativeGrant) -> AdministrativeGrantResponse:
    return AdministrativeGrantResponse(
        id=grant.id,
        user_id=grant.user_id,
        role_template=grant.role_template.value,
        market_id=grant.market_id,
        operator_id=grant.operator_id,
        city_id=grant.city_id,
        granted_by_user_id=grant.granted_by_user_id,
        grant_reason=grant.grant_reason,
        granted_at=grant.granted_at,
        expires_at=grant.expires_at,
        revoked_at=grant.revoked_at,
        revoked_by_user_id=grant.revoked_by_user_id,
        revocation_reason=grant.revocation_reason,
    )


def grant_change_response(
    request: AdministrativeGrantChangeRequest,
) -> AdministrativeGrantChangeRequestResponse:
    return AdministrativeGrantChangeRequestResponse(
        id=request.id,
        action=request.action,
        status=request.status,
        requester_user_id=request.requester_user_id,
        decided_by_user_id=request.decided_by_user_id,
        target_user_id=request.target_user_id,
        role_template=request.role_template,
        market_id=request.market_id,
        operator_id=request.operator_id,
        city_id=request.city_id,
        source_grant_id=request.source_grant_id,
        resulting_grant_id=request.resulting_grant_id,
        reason=request.reason,
        decision_reason=request.decision_reason,
        requested_grant_expires_at=request.requested_grant_expires_at,
        requested_at=request.requested_at,
        decided_at=request.decided_at,
        optimistic_version=request.optimistic_version,
    )


def audit_response(entry: AuditLog) -> OperationsAuditLogResponse:
    return OperationsAuditLogResponse(
        id=entry.id,
        actor_user_id=entry.actor_user_id,
        action=entry.action,
        resource_type=entry.resource_type,
        resource_id=entry.resource_id,
        market_id=entry.market_id,
        operator_id=entry.operator_id,
        city_id=entry.city_id,
        changes=entry.changes,
        created_at=entry.created_at,
    )


async def _target_market_id(
    session: AsyncSession,
    payload: AdministrativeGrantCreateRequest,
) -> UUID:
    if payload.market_id is not None:
        if await session.get(Market, payload.market_id) is None:
            raise HTTPException(status_code=404, detail="Market not found.")
        return payload.market_id
    if payload.operator_id is not None:
        operator = await session.get(Operator, payload.operator_id)
        if operator is None:
            raise HTTPException(status_code=404, detail="Operator not found.")
        return operator.market_id
    assert payload.city_id is not None
    city = await session.get(City, payload.city_id)
    if city is None:
        raise HTTPException(status_code=404, detail="City not found.")
    return city.market_id


def _grant_visibility_filter(principal: OperationsPrincipal):
    market_ids = principal.market_ids_for(OperationsPermission.MANAGE_SCOPED_STAFF_GRANTS)
    # Only market-scoped PLATFORM_ADMIN currently has this permission, so these
    # subqueries are both least-privilege and SQL-before-count filtering.
    operator_ids = select(Operator.id).where(Operator.market_id.in_(market_ids))
    city_ids = select(City.id).where(City.market_id.in_(market_ids))
    return or_(
        AdministrativeGrant.market_id.in_(market_ids),
        AdministrativeGrant.operator_id.in_(operator_ids),
        AdministrativeGrant.city_id.in_(city_ids),
    )


def _grant_request_visibility_filter(principal: OperationsPrincipal):
    market_ids = principal.market_ids_for(
        OperationsPermission.MANAGE_SCOPED_STAFF_GRANTS
    )
    operator_ids = select(Operator.id).where(Operator.market_id.in_(market_ids))
    city_ids = select(City.id).where(City.market_id.in_(market_ids))
    return or_(
        AdministrativeGrantChangeRequest.market_id.in_(market_ids),
        AdministrativeGrantChangeRequest.operator_id.in_(operator_ids),
        AdministrativeGrantChangeRequest.city_id.in_(city_ids),
    )


def _authorized_grant_market_ids(
    principal: OperationsPrincipal,
) -> frozenset[UUID]:
    return principal.market_ids_for(
        OperationsPermission.MANAGE_SCOPED_STAFF_GRANTS
    )


def _raise_grant_change_http(error: GrantChangeError) -> None:
    if isinstance(error, GrantChangeNotFound):
        code = status.HTTP_404_NOT_FOUND
    elif isinstance(error, GrantChangeForbidden):
        code = status.HTTP_403_FORBIDDEN
    elif isinstance(error, GrantChangeInvalid):
        code = status.HTTP_422_UNPROCESSABLE_ENTITY
    else:
        code = status.HTTP_409_CONFLICT
    raise HTTPException(status_code=code, detail=str(error)) from error


def _reject_direct_grant_mutation(http_request: Request) -> None:
    if http_request.app.state.settings.environment in {"staging", "production"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Direct staff-grant mutation is disabled. Submit a maker-checker "
                "administrative grant request."
            ),
        )


@router.get("/administrative-grants", response_model=AdministrativeGrantListResponse)
async def list_administrative_grants(
    user_id: UUID | None = Query(default=None),
    include_revoked: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: OperationsPrincipal = Depends(
        require_operations_permission(OperationsPermission.MANAGE_SCOPED_STAFF_GRANTS)
    ),
    session: AsyncSession = Depends(database_session),
) -> AdministrativeGrantListResponse:
    filters = [_grant_visibility_filter(principal)]
    if user_id is not None:
        filters.append(AdministrativeGrant.user_id == user_id)
    if not include_revoked:
        filters.append(AdministrativeGrant.revoked_at.is_(None))
    grants = list(
        await session.scalars(
            select(AdministrativeGrant)
            .where(*filters)
            .order_by(AdministrativeGrant.granted_at.desc(), AdministrativeGrant.id.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    total = await session.scalar(
        select(func.count()).select_from(AdministrativeGrant).where(*filters)
    )
    return AdministrativeGrantListResponse(
        items=[grant_response(grant) for grant in grants],
        page=page,
        limit=limit,
        total=total or 0,
    )


@router.post(
    "/administrative-grants",
    response_model=AdministrativeGrantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_administrative_grant(
    payload: AdministrativeGrantCreateRequest,
    http_request: Request,
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(
        require_operations_permission(OperationsPermission.MANAGE_SCOPED_STAFF_GRANTS)
    ),
    session: AsyncSession = Depends(database_session),
) -> AdministrativeGrantResponse:
    now = datetime.now(UTC)
    if payload.user_id == principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "An operations user cannot create or extend a grant for their "
                "own account. A different authorized administrator is required."
            ),
        )
    if payload.expires_at is not None and payload.expires_at <= now:
        raise HTTPException(status_code=422, detail="expires_at must be in the future.")
    _reject_direct_grant_mutation(http_request)
    try:
        async with session.begin():
            target_market_id = await _target_market_id(session, payload)
            if not principal.allows(
                OperationsPermission.MANAGE_SCOPED_STAFF_GRANTS,
                market_id=target_market_id,
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="The requested grant is outside the caller's market scope.",
                )
            user = await session.get(User, payload.user_id)
            if user is None or user.status != UserStatus.ACTIVE:
                raise HTTPException(status_code=404, detail="Active user account not found.")
            grant = AdministrativeGrant(
                user_id=user.id,
                role_template=payload.role_template,
                market_id=payload.market_id,
                operator_id=payload.operator_id,
                city_id=payload.city_id,
                granted_by_user_id=principal.user_id,
                grant_reason=payload.reason,
                expires_at=payload.expires_at,
            )
            session.add(grant)
            await session.flush()
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="ADMINISTRATIVE_GRANT_CREATED",
                resource_type="administrative_grant",
                resource_id=grant.id,
                market_id=target_market_id,
                operator_id=grant.operator_id,
                city_id=grant.city_id,
                changes={
                    "target_user_id": str(grant.user_id),
                    "role_template": grant.role_template.value,
                    "scope_type": "MARKET"
                    if grant.market_id
                    else "OPERATOR"
                    if grant.operator_id
                    else "CITY",
                    "expires_at": grant.expires_at.isoformat() if grant.expires_at else None,
                },
            )
    except IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That active role template and scope grant already exists for the user.",
        ) from error
    return grant_response(grant)


@router.delete("/administrative-grants/{grant_id}", response_model=AdministrativeGrantResponse)
async def revoke_administrative_grant(
    grant_id: UUID,
    http_request: Request,
    reason: str = Query(min_length=3, max_length=240),
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(
        require_operations_permission(OperationsPermission.MANAGE_SCOPED_STAFF_GRANTS)
    ),
    session: AsyncSession = Depends(database_session),
) -> AdministrativeGrantResponse:
    _reject_direct_grant_mutation(http_request)
    async with session.begin():
        grant = await session.scalar(
            select(AdministrativeGrant)
            .where(AdministrativeGrant.id == grant_id, _grant_visibility_filter(principal))
            .with_for_update()
        )
        if grant is None:
            raise HTTPException(status_code=404, detail="Administrative grant not found.")
        if grant.revoked_at is not None:
            return grant_response(grant)
        if grant.user_id == principal.user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An operations user cannot revoke their own active grant.",
            )
        target_market_id = grant.market_id
        if target_market_id is None and grant.operator_id is not None:
            operator = await session.get(Operator, grant.operator_id)
            assert operator is not None
            target_market_id = operator.market_id
        if target_market_id is None and grant.city_id is not None:
            city = await session.get(City, grant.city_id)
            assert city is not None
            target_market_id = city.market_id
        assert target_market_id is not None
        revoked_at = datetime.now(UTC)
        try:
            await ensure_platform_admin_continuity_before_revoke(
                session,
                grant=grant,
                market_id=target_market_id,
                now=revoked_at,
            )
        except GrantChangeError as error:
            _raise_grant_change_http(error)
        grant.revoked_at = revoked_at
        grant.revoked_by_user_id = principal.user_id
        grant.revocation_reason = reason
        await audit(
            session,
            actor_user_id=principal.user_id,
            action="ADMINISTRATIVE_GRANT_REVOKED",
            resource_type="administrative_grant",
            resource_id=grant.id,
            market_id=target_market_id,
            operator_id=grant.operator_id,
            city_id=grant.city_id,
            changes={
                "target_user_id": str(grant.user_id),
                "role_template": grant.role_template.value,
                "reason": reason,
            },
        )
    return grant_response(grant)


@router.get(
    "/administrative-grant-requests",
    response_model=AdministrativeGrantChangeRequestListResponse,
)
async def list_administrative_grant_requests(
    request_status: AdministrativeGrantRequestStatus | None = Query(
        default=None,
        alias="status",
    ),
    action: AdministrativeGrantRequestAction | None = Query(default=None),
    target_user_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: OperationsPrincipal = Depends(
        require_operations_permission(
            OperationsPermission.MANAGE_SCOPED_STAFF_GRANTS
        )
    ),
    session: AsyncSession = Depends(database_session),
) -> AdministrativeGrantChangeRequestListResponse:
    filters = [_grant_request_visibility_filter(principal)]
    if request_status is not None:
        filters.append(AdministrativeGrantChangeRequest.status == request_status)
    if action is not None:
        filters.append(AdministrativeGrantChangeRequest.action == action)
    if target_user_id is not None:
        filters.append(
            AdministrativeGrantChangeRequest.target_user_id == target_user_id
        )
    requests = list(
        await session.scalars(
            select(AdministrativeGrantChangeRequest)
            .where(*filters)
            .order_by(
                AdministrativeGrantChangeRequest.requested_at.desc(),
                AdministrativeGrantChangeRequest.id.desc(),
            )
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    total = await session.scalar(
        select(func.count())
        .select_from(AdministrativeGrantChangeRequest)
        .where(*filters)
    )
    return AdministrativeGrantChangeRequestListResponse(
        items=[grant_change_response(item) for item in requests],
        page=page,
        limit=limit,
        total=total or 0,
    )


@router.post(
    "/administrative-grant-requests/create",
    response_model=AdministrativeGrantChangeRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_administrative_grant_request(
    payload: AdministrativeGrantCreateRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(
        require_operations_permission(
            OperationsPermission.MANAGE_SCOPED_STAFF_GRANTS
        )
    ),
    session: AsyncSession = Depends(database_session),
) -> AdministrativeGrantChangeRequestResponse | JSONResponse:
    try:
        async with session.begin():
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="operations-administrative-grant-request:create",
                key=idempotency_key,
                payload=payload.model_dump(mode="json"),
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(
                    status_code=command.status_code,
                    content=command.payload,
                )
            request = await request_grant_creation(
                session,
                payload=payload,
                requester_user_id=principal.user_id,
                authorized_market_ids=_authorized_grant_market_ids(principal),
            )
            result = grant_change_response(request)
            await finish_command(
                session,
                command,
                status_code=status.HTTP_201_CREATED,
                payload=result.model_dump(mode="json"),
            )
        return result
    except (InvalidIdempotencyKey, GrantChangeInvalid) as error:
        if isinstance(error, GrantChangeError):
            _raise_grant_change_http(error)
        raise HTTPException(status_code=400, detail=str(error)) from error
    except (IdempotencyKeyReuse, GrantChangeError) as error:
        if isinstance(error, GrantChangeError):
            _raise_grant_change_http(error)
        raise HTTPException(status_code=409, detail=str(error)) from error
    except IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An equivalent pending or active staff-grant change already exists.",
        ) from error


@router.post(
    "/administrative-grant-requests/revoke",
    response_model=AdministrativeGrantChangeRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_administrative_grant_revocation_request(
    payload: AdministrativeGrantRevocationRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(
        require_operations_permission(
            OperationsPermission.MANAGE_SCOPED_STAFF_GRANTS
        )
    ),
    session: AsyncSession = Depends(database_session),
) -> AdministrativeGrantChangeRequestResponse | JSONResponse:
    try:
        async with session.begin():
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation=(
                    "operations-administrative-grant-request:revoke:"
                    f"{payload.grant_id}"
                ),
                key=idempotency_key,
                payload=payload.model_dump(mode="json"),
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(
                    status_code=command.status_code,
                    content=command.payload,
                )
            request = await request_grant_revocation(
                session,
                grant_id=payload.grant_id,
                reason=payload.reason,
                requester_user_id=principal.user_id,
                authorized_market_ids=_authorized_grant_market_ids(principal),
            )
            result = grant_change_response(request)
            await finish_command(
                session,
                command,
                status_code=status.HTTP_201_CREATED,
                payload=result.model_dump(mode="json"),
            )
        return result
    except InvalidIdempotencyKey as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except (IdempotencyKeyReuse, GrantChangeError) as error:
        if isinstance(error, GrantChangeError):
            _raise_grant_change_http(error)
        raise HTTPException(status_code=409, detail=str(error)) from error
    except IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An equivalent pending staff-grant change already exists.",
        ) from error


async def _execute_grant_request_decision(
    *,
    decision: str,
    request_id: UUID,
    payload: AdministrativeGrantDecisionRequest,
    idempotency_key: str,
    principal: OperationsPrincipal,
    session: AsyncSession,
) -> AdministrativeGrantChangeRequestResponse | JSONResponse:
    try:
        async with session.begin():
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation=(
                    "operations-administrative-grant-request:"
                    f"{request_id}:{decision}"
                ),
                key=idempotency_key,
                payload=payload.model_dump(mode="json"),
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(
                    status_code=command.status_code,
                    content=command.payload,
                )
            arguments = {
                "session": session,
                "request_id": request_id,
                "expected_version": payload.expected_version,
                "reason": payload.reason,
                "authorized_market_ids": _authorized_grant_market_ids(principal),
            }
            if decision == "approve":
                request = await approve_grant_change(
                    **arguments,
                    approver_user_id=principal.user_id,
                )
            elif decision == "reject":
                request = await reject_grant_change(
                    **arguments,
                    approver_user_id=principal.user_id,
                )
            else:
                request = await cancel_grant_change(
                    **arguments,
                    requester_user_id=principal.user_id,
                )
            result = grant_change_response(request)
            await finish_command(
                session,
                command,
                status_code=status.HTTP_200_OK,
                payload=result.model_dump(mode="json"),
            )
        return result
    except InvalidIdempotencyKey as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except (IdempotencyKeyReuse, GrantChangeError) as error:
        if isinstance(error, GrantChangeError):
            _raise_grant_change_http(error)
        raise HTTPException(status_code=409, detail=str(error)) from error
    except IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The staff-grant request changed concurrently; refresh and retry.",
        ) from error


@router.post(
    "/administrative-grant-requests/{request_id}/approve",
    response_model=AdministrativeGrantChangeRequestResponse,
)
async def approve_administrative_grant_request(
    request_id: UUID,
    payload: AdministrativeGrantDecisionRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(
        require_operations_permission(
            OperationsPermission.MANAGE_SCOPED_STAFF_GRANTS
        )
    ),
    session: AsyncSession = Depends(database_session),
) -> AdministrativeGrantChangeRequestResponse | JSONResponse:
    return await _execute_grant_request_decision(
        decision="approve",
        request_id=request_id,
        payload=payload,
        idempotency_key=idempotency_key,
        principal=principal,
        session=session,
    )


@router.post(
    "/administrative-grant-requests/{request_id}/reject",
    response_model=AdministrativeGrantChangeRequestResponse,
)
async def reject_administrative_grant_request(
    request_id: UUID,
    payload: AdministrativeGrantDecisionRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(
        require_operations_permission(
            OperationsPermission.MANAGE_SCOPED_STAFF_GRANTS
        )
    ),
    session: AsyncSession = Depends(database_session),
) -> AdministrativeGrantChangeRequestResponse | JSONResponse:
    return await _execute_grant_request_decision(
        decision="reject",
        request_id=request_id,
        payload=payload,
        idempotency_key=idempotency_key,
        principal=principal,
        session=session,
    )


@router.post(
    "/administrative-grant-requests/{request_id}/cancel",
    response_model=AdministrativeGrantChangeRequestResponse,
)
async def cancel_administrative_grant_request(
    request_id: UUID,
    payload: AdministrativeGrantDecisionRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(
        require_operations_permission(
            OperationsPermission.MANAGE_SCOPED_STAFF_GRANTS
        )
    ),
    session: AsyncSession = Depends(database_session),
) -> AdministrativeGrantChangeRequestResponse | JSONResponse:
    return await _execute_grant_request_decision(
        decision="cancel",
        request_id=request_id,
        payload=payload,
        idempotency_key=idempotency_key,
        principal=principal,
        session=session,
    )


ACCOUNT_SECURITY_PERMISSION = OperationsPermission.MANAGE_ACCOUNT_SECURITY


async def _target_account_market_ids(
    session: AsyncSession,
    user_id: UUID,
) -> frozenset[UUID]:
    """Resolve every market where the account has participant or staff history."""
    market_ids: set[UUID] = set()

    async def add(statement) -> None:
        market_ids.update(await session.scalars(statement))

    await add(
        select(City.market_id)
        .join(DriverCityApplication, DriverCityApplication.city_id == City.id)
        .join(DriverProfile, DriverProfile.id == DriverCityApplication.driver_id)
        .where(DriverProfile.user_id == user_id)
    )
    await add(
        select(City.market_id)
        .join(DriverCityAuthorization, DriverCityAuthorization.city_id == City.id)
        .join(DriverProfile, DriverProfile.id == DriverCityAuthorization.driver_id)
        .where(DriverProfile.user_id == user_id)
    )
    await add(
        select(City.market_id)
        .join(Ride, Ride.city_id == City.id)
        .where(Ride.passenger_id == user_id)
    )
    await add(
        select(City.market_id)
        .join(Ride, Ride.city_id == City.id)
        .join(DriverProfile, DriverProfile.id == Ride.driver_id)
        .where(DriverProfile.user_id == user_id)
    )
    await add(
        select(City.market_id)
        .join(ScheduledBooking, ScheduledBooking.city_id == City.id)
        .where(ScheduledBooking.passenger_id == user_id)
    )
    await add(
        select(City.market_id)
        .join(SupportTicket, SupportTicket.city_id == City.id)
        .where(SupportTicket.user_id == user_id)
    )
    await add(
        select(City.market_id)
        .join(SafetyReport, SafetyReport.city_id == City.id)
        .where(
            or_(
                SafetyReport.reporter_user_id == user_id,
                SafetyReport.reported_user_id == user_id,
            )
        )
    )
    await add(
        select(AdministrativeGrant.market_id).where(
            AdministrativeGrant.user_id == user_id,
            AdministrativeGrant.market_id.is_not(None),
        )
    )
    await add(
        select(Operator.market_id)
        .join(
            AdministrativeGrant,
            AdministrativeGrant.operator_id == Operator.id,
        )
        .where(AdministrativeGrant.user_id == user_id)
    )
    await add(
        select(City.market_id)
        .join(AdministrativeGrant, AdministrativeGrant.city_id == City.id)
        .where(AdministrativeGrant.user_id == user_id)
    )
    return frozenset(market_ids)


async def _account_security_target(
    session: AsyncSession,
    principal: OperationsPrincipal,
    *,
    market_id: UUID,
    user_id: UUID,
) -> User:
    if not principal.allows(ACCOUNT_SECURITY_PERMISSION, market_id=market_id):
        raise HTTPException(status_code=404, detail="Market or account not found.")
    if await session.get(Market, market_id) is None:
        raise HTTPException(status_code=404, detail="Market or account not found.")
    user = await lock_user_for_status_change(session, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Market or account not found.")
    target_market_ids = await _target_account_market_ids(session, user.id)
    if market_id not in target_market_ids:
        raise HTTPException(status_code=404, detail="Market or account not found.")
    authorized_market_ids = principal.market_ids_for(ACCOUNT_SECURITY_PERMISSION)
    if not target_market_ids.issubset(authorized_market_ids):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The account has cross-market history. Escalate to staff who cover "
                "every associated market before applying an account-wide action."
            ),
        )
    return user


def _account_security_response(
    user: User,
    *,
    sessions_revoked: int,
    device_registrations_revoked: int,
    changed_at: datetime,
) -> AccountSecurityActionResponse:
    return AccountSecurityActionResponse(
        user_id=user.id,
        status=user.status.value,
        sessions_revoked=sessions_revoked,
        device_registrations_revoked=device_registrations_revoked,
        changed_at=changed_at,
    )


async def _execute_account_security_action(
    *,
    action: str,
    market_id: UUID,
    user_id: UUID,
    payload: OperationsAccountSecurityActionRequest,
    idempotency_key: str,
    principal: OperationsPrincipal,
    session: AsyncSession,
) -> AccountSecurityActionResponse | JSONResponse:
    if user_id == principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An operations user cannot apply an account-wide action to themselves.",
        )
    try:
        async with session.begin():
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation=f"operations-account-security:{action}:{market_id}:{user_id}",
                key=idempotency_key,
                payload=payload.model_dump(mode="json"),
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)

            user = await _account_security_target(
                session,
                principal,
                market_id=market_id,
                user_id=user_id,
            )
            changed_at = datetime.now(UTC)
            previous_status = user.status
            sessions_revoked = 0
            devices_revoked = 0
            if action == "sessions-revoke":
                sessions_revoked, devices_revoked = await revoke_user_access(
                    session,
                    user_id=user.id,
                    revoked_at=changed_at,
                )
                audit_action = "OPERATIONS_USER_SESSIONS_REVOKED"
            elif action == "suspend":
                if user.status == UserStatus.DEACTIVATED:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="A deactivated account cannot be suspended.",
                    )
                previous_status, sessions_revoked, devices_revoked = await suspend_locked_user_access(
                    session,
                    user=user,
                    changed_at=changed_at,
                )
                audit_action = "OPERATIONS_USER_SUSPENDED"
            elif action == "reactivate":
                if user.status == UserStatus.DEACTIVATED:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "A deactivated account cannot be reactivated through "
                            "suspension recovery."
                        ),
                    )
                if user.status == UserStatus.SUSPENDED:
                    user.status = UserStatus.ACTIVE
                    user.updated_at = changed_at
                audit_action = "OPERATIONS_USER_REACTIVATED"
            else:  # pragma: no cover - route declarations provide the closed set.
                raise RuntimeError("Unknown account security action")

            await audit(
                session,
                actor_user_id=principal.user_id,
                action=audit_action,
                resource_type="user",
                resource_id=user.id,
                market_id=market_id,
                changes={
                    "reason_code": payload.reason_code.value,
                    "case_reference": payload.case_reference,
                    "previous_status": previous_status.value,
                    "current_status": user.status.value,
                    "sessions_revoked": sessions_revoked,
                    "device_registrations_revoked": devices_revoked,
                },
            )
            result = _account_security_response(
                user,
                sessions_revoked=sessions_revoked,
                device_registrations_revoked=devices_revoked,
                changed_at=changed_at,
            )
            await finish_command(
                session,
                command,
                status_code=200,
                payload=result.model_dump(mode="json"),
            )
        return result
    except InvalidIdempotencyKey as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except IdempotencyKeyReuse as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post(
    "/markets/{market_id}/users/{user_id}/sessions/revoke",
    response_model=AccountSecurityActionResponse,
)
async def revoke_scoped_user_sessions(
    market_id: UUID,
    user_id: UUID,
    payload: OperationsAccountSecurityActionRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(
        require_operations_permission(ACCOUNT_SECURITY_PERMISSION)
    ),
    session: AsyncSession = Depends(database_session),
) -> AccountSecurityActionResponse | JSONResponse:
    return await _execute_account_security_action(
        action="sessions-revoke",
        market_id=market_id,
        user_id=user_id,
        payload=payload,
        idempotency_key=idempotency_key,
        principal=principal,
        session=session,
    )


@router.post(
    "/markets/{market_id}/users/{user_id}/suspend",
    response_model=AccountSecurityActionResponse,
)
async def suspend_scoped_user(
    market_id: UUID,
    user_id: UUID,
    payload: OperationsAccountSecurityActionRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(
        require_operations_permission(ACCOUNT_SECURITY_PERMISSION)
    ),
    session: AsyncSession = Depends(database_session),
) -> AccountSecurityActionResponse | JSONResponse:
    return await _execute_account_security_action(
        action="suspend",
        market_id=market_id,
        user_id=user_id,
        payload=payload,
        idempotency_key=idempotency_key,
        principal=principal,
        session=session,
    )


@router.post(
    "/markets/{market_id}/users/{user_id}/reactivate",
    response_model=AccountSecurityActionResponse,
)
async def reactivate_scoped_user(
    market_id: UUID,
    user_id: UUID,
    payload: OperationsAccountSecurityActionRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(
        require_operations_permission(ACCOUNT_SECURITY_PERMISSION)
    ),
    session: AsyncSession = Depends(database_session),
) -> AccountSecurityActionResponse | JSONResponse:
    return await _execute_account_security_action(
        action="reactivate",
        market_id=market_id,
        user_id=user_id,
        payload=payload,
        idempotency_key=idempotency_key,
        principal=principal,
        session=session,
    )


def _audit_visibility_filter(principal: OperationsPrincipal):
    clauses = []
    permission = OperationsPermission.VIEW_SCOPED_AUDIT
    for grant in principal.grants:
        if permission not in grant.permissions:
            continue
        if grant.city_id is not None:
            clauses.append(AuditLog.city_id == grant.city_id)
        elif grant.operator_id is not None:
            clauses.append(
                or_(
                    AuditLog.operator_id == grant.operator_id,
                    AuditLog.city_id.in_(grant.covered_city_ids),
                )
            )
        elif grant.market_id is not None:
            clauses.append(AuditLog.market_id == grant.market_id)
    return or_(*clauses) if clauses else AuditLog.id.in_([])


@router.get("/audit-logs", response_model=OperationsAuditLogListResponse)
async def list_operations_audit_logs(
    city_id: UUID | None = Query(default=None),
    operator_id: UUID | None = Query(default=None),
    action: str | None = Query(default=None, min_length=1, max_length=120),
    resource_type: str | None = Query(default=None, min_length=1, max_length=80),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: OperationsPrincipal = Depends(
        require_operations_permission(OperationsPermission.VIEW_SCOPED_AUDIT)
    ),
    session: AsyncSession = Depends(database_session),
) -> OperationsAuditLogListResponse:
    filters = [_audit_visibility_filter(principal)]
    if city_id is not None:
        filters.append(AuditLog.city_id == city_id)
    if operator_id is not None:
        filters.append(AuditLog.operator_id == operator_id)
    if action is not None:
        filters.append(AuditLog.action == action)
    if resource_type is not None:
        filters.append(AuditLog.resource_type == resource_type)
    entries = list(
        await session.scalars(
            select(AuditLog)
            .where(*filters)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    total = await session.scalar(select(func.count()).select_from(AuditLog).where(*filters))
    return OperationsAuditLogListResponse(
        items=[audit_response(entry) for entry in entries],
        page=page,
        limit=limit,
        total=total or 0,
    )
