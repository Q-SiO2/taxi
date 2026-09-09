"""Transactional maker-checker workflow for scoped operations grants.

The HTTP layer authenticates a caller and supplies the market IDs visible to
that caller.  This module still revalidates the caller's live PLATFORM_ADMIN
grant while holding the market row lock.  That closes the time-of-check to
time-of-use gap between dependency resolution and the grant mutation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.administration.models import (
    AdministrativeGrant,
    AdministrativeGrantChangeRequest,
    AdministrativeGrantRequestAction,
    AdministrativeGrantRequestStatus,
    AdministrativeRoleTemplate,
)
from taximobile_api.domains.administration.operations_schemas import (
    AdministrativeGrantCreateRequest,
)
from taximobile_api.domains.administration.service import audit
from taximobile_api.domains.auth.models import User, UserStatus
from taximobile_api.domains.markets.models import City, Market, Operator


MINIMUM_ACTIVE_PLATFORM_ADMINS = 2


class GrantChangeError(ValueError):
    """Base class for stable staff-grant workflow failures."""


class GrantChangeNotFound(GrantChangeError):
    """The requested resource is absent or outside the caller's scope."""


class GrantChangeForbidden(GrantChangeError):
    """The caller is known but cannot perform this state transition."""


class GrantChangeConflict(GrantChangeError):
    """Current durable state conflicts with the requested transition."""


class GrantChangeInvalid(GrantChangeError):
    """The request is structurally valid but violates a business invariant."""


async def resolve_scope_market_id(
    session: AsyncSession,
    *,
    market_id: UUID | None,
    operator_id: UUID | None,
    city_id: UUID | None,
) -> UUID:
    """Resolve the one validated scope to its parent market."""

    if market_id is not None:
        if await session.get(Market, market_id) is None:
            raise GrantChangeNotFound("Administrative scope not found.")
        return market_id
    if operator_id is not None:
        operator = await session.get(Operator, operator_id)
        if operator is None:
            raise GrantChangeNotFound("Administrative scope not found.")
        return operator.market_id
    if city_id is not None:
        city = await session.get(City, city_id)
        if city is None:
            raise GrantChangeNotFound("Administrative scope not found.")
        return city.market_id
    raise GrantChangeInvalid("Exactly one administrative scope is required.")


async def _lock_authorized_market(
    session: AsyncSession,
    *,
    market_id: UUID,
    actor_user_id: UUID,
    authorized_market_ids: frozenset[UUID],
    now: datetime,
) -> Market:
    """Serialize changes per market and revalidate the actor's authority."""

    if market_id not in authorized_market_ids:
        raise GrantChangeNotFound("Administrative grant request not found.")
    market = await session.scalar(
        select(Market).where(Market.id == market_id).with_for_update()
    )
    if market is None:
        raise GrantChangeNotFound("Administrative scope not found.")
    live_grant = await session.scalar(
        select(AdministrativeGrant.id)
        .join(User, User.id == AdministrativeGrant.user_id)
        .where(
            AdministrativeGrant.user_id == actor_user_id,
            AdministrativeGrant.role_template
            == AdministrativeRoleTemplate.PLATFORM_ADMIN,
            AdministrativeGrant.market_id == market_id,
            AdministrativeGrant.revoked_at.is_(None),
            User.status == UserStatus.ACTIVE,
            or_(
                AdministrativeGrant.expires_at.is_(None),
                AdministrativeGrant.expires_at > now,
            ),
        )
    )
    if live_grant is None:
        raise GrantChangeForbidden(
            "A live market-scoped platform administrator grant is required."
        )
    return market


def _same_scope(
    grant: AdministrativeGrant,
    request: AdministrativeGrantChangeRequest,
) -> bool:
    return (
        grant.user_id == request.target_user_id
        and grant.role_template == request.role_template
        and grant.market_id == request.market_id
        and grant.operator_id == request.operator_id
        and grant.city_id == request.city_id
    )


async def _existing_unrevoked_grant(
    session: AsyncSession,
    *,
    user_id: UUID,
    role_template: AdministrativeRoleTemplate,
    market_id: UUID | None,
    operator_id: UUID | None,
    city_id: UUID | None,
) -> AdministrativeGrant | None:
    return await session.scalar(
        select(AdministrativeGrant)
        .where(
            AdministrativeGrant.user_id == user_id,
            AdministrativeGrant.role_template == role_template,
            AdministrativeGrant.market_id.is_(market_id)
            if market_id is None
            else AdministrativeGrant.market_id == market_id,
            AdministrativeGrant.operator_id.is_(operator_id)
            if operator_id is None
            else AdministrativeGrant.operator_id == operator_id,
            AdministrativeGrant.city_id.is_(city_id)
            if city_id is None
            else AdministrativeGrant.city_id == city_id,
            AdministrativeGrant.revoked_at.is_(None),
        )
        .with_for_update()
    )


async def _active_platform_admin_count(
    session: AsyncSession,
    *,
    market_id: UUID,
    now: datetime,
    exclude_grant_id: UUID | None = None,
    authority_required_after: datetime | None = None,
) -> int:
    filters = [
        AdministrativeGrant.role_template
        == AdministrativeRoleTemplate.PLATFORM_ADMIN,
        AdministrativeGrant.market_id == market_id,
        AdministrativeGrant.revoked_at.is_(None),
        User.status == UserStatus.ACTIVE,
    ]
    if exclude_grant_id is not None:
        filters.append(AdministrativeGrant.id != exclude_grant_id)
    cutoff = authority_required_after or now
    filters.append(
        or_(
            AdministrativeGrant.expires_at.is_(None),
            AdministrativeGrant.expires_at > cutoff,
        )
    )
    count = await session.scalar(
        select(func.count(func.distinct(AdministrativeGrant.user_id)))
        .select_from(AdministrativeGrant)
        .join(User, User.id == AdministrativeGrant.user_id)
        .where(*filters)
    )
    return count or 0


async def ensure_platform_admin_continuity_before_revoke(
    session: AsyncSession,
    *,
    grant: AdministrativeGrant,
    market_id: UUID,
    now: datetime,
) -> None:
    """Refuse a revocation that would break the two-person control plane."""

    if grant.role_template != AdministrativeRoleTemplate.PLATFORM_ADMIN:
        return
    remaining = await _active_platform_admin_count(
        session,
        market_id=market_id,
        now=now,
        exclude_grant_id=grant.id,
    )
    if remaining < MINIMUM_ACTIVE_PLATFORM_ADMINS:
        raise GrantChangeConflict(
            "Revocation would leave fewer than two active platform administrators "
            "in the market. Establish an independently controlled replacement first."
        )


async def _ensure_expiring_admin_has_successors(
    session: AsyncSession,
    *,
    role_template: AdministrativeRoleTemplate,
    market_id: UUID,
    expires_at: datetime | None,
    now: datetime,
) -> None:
    if (
        role_template != AdministrativeRoleTemplate.PLATFORM_ADMIN
        or expires_at is None
    ):
        return
    durable_admins = await _active_platform_admin_count(
        session,
        market_id=market_id,
        now=now,
        authority_required_after=expires_at,
    )
    if durable_admins < MINIMUM_ACTIVE_PLATFORM_ADMINS:
        raise GrantChangeConflict(
            "An expiring platform administrator grant requires at least two other "
            "active administrators whose authority outlasts the requested expiry."
        )


async def request_grant_creation(
    session: AsyncSession,
    *,
    payload: AdministrativeGrantCreateRequest,
    requester_user_id: UUID,
    authorized_market_ids: frozenset[UUID],
    now: datetime | None = None,
) -> AdministrativeGrantChangeRequest:
    """Create a pending immutable snapshot; never mutate authority directly."""

    requested_at = now or datetime.now(UTC)
    if requester_user_id == payload.user_id:
        raise GrantChangeConflict(
            "An administrator cannot request a grant for their own account."
        )
    if payload.expires_at is not None and payload.expires_at <= requested_at:
        raise GrantChangeInvalid("expires_at must be in the future.")
    scope_market_id = await resolve_scope_market_id(
        session,
        market_id=payload.market_id,
        operator_id=payload.operator_id,
        city_id=payload.city_id,
    )
    await _lock_authorized_market(
        session,
        market_id=scope_market_id,
        actor_user_id=requester_user_id,
        authorized_market_ids=authorized_market_ids,
        now=requested_at,
    )
    target = await session.scalar(
        select(User).where(User.id == payload.user_id).with_for_update()
    )
    if target is None or target.status != UserStatus.ACTIVE:
        raise GrantChangeNotFound("Active target account not found.")
    existing = await _existing_unrevoked_grant(
        session,
        user_id=target.id,
        role_template=payload.role_template,
        market_id=payload.market_id,
        operator_id=payload.operator_id,
        city_id=payload.city_id,
    )
    if existing is not None:
        raise GrantChangeConflict(
            "The target already has an unrevoked grant for that role and scope."
        )
    request = AdministrativeGrantChangeRequest(
        action=AdministrativeGrantRequestAction.CREATE,
        status=AdministrativeGrantRequestStatus.PENDING,
        requester_user_id=requester_user_id,
        target_user_id=target.id,
        role_template=payload.role_template,
        market_id=payload.market_id,
        operator_id=payload.operator_id,
        city_id=payload.city_id,
        reason=payload.reason,
        requested_grant_expires_at=payload.expires_at,
        requested_at=requested_at,
    )
    session.add(request)
    await session.flush()
    await audit(
        session,
        actor_user_id=requester_user_id,
        action="ADMINISTRATIVE_GRANT_CREATION_REQUESTED",
        resource_type="administrative_grant_change_request",
        resource_id=request.id,
        market_id=scope_market_id,
        operator_id=request.operator_id,
        city_id=request.city_id,
        changes={
            "action": request.action.value,
            "target_user_id": str(request.target_user_id),
            "role_template": request.role_template.value,
            "requested_grant_expires_at": (
                request.requested_grant_expires_at.isoformat()
                if request.requested_grant_expires_at
                else None
            ),
        },
    )
    return request


async def request_grant_revocation(
    session: AsyncSession,
    *,
    grant_id: UUID,
    reason: str,
    requester_user_id: UUID,
    authorized_market_ids: frozenset[UUID],
    now: datetime | None = None,
) -> AdministrativeGrantChangeRequest:
    requested_at = now or datetime.now(UTC)
    grant = await session.get(AdministrativeGrant, grant_id)
    if grant is None:
        raise GrantChangeNotFound("Administrative grant not found.")
    scope_market_id = await resolve_scope_market_id(
        session,
        market_id=grant.market_id,
        operator_id=grant.operator_id,
        city_id=grant.city_id,
    )
    await _lock_authorized_market(
        session,
        market_id=scope_market_id,
        actor_user_id=requester_user_id,
        authorized_market_ids=authorized_market_ids,
        now=requested_at,
    )
    grant = await session.scalar(
        select(AdministrativeGrant)
        .where(AdministrativeGrant.id == grant_id)
        .with_for_update()
    )
    assert grant is not None
    if grant.revoked_at is not None:
        raise GrantChangeConflict("Administrative grant is already revoked.")
    if requester_user_id == grant.user_id:
        raise GrantChangeConflict(
            "An administrator cannot request revocation of their own grant."
        )
    request = AdministrativeGrantChangeRequest(
        action=AdministrativeGrantRequestAction.REVOKE,
        status=AdministrativeGrantRequestStatus.PENDING,
        requester_user_id=requester_user_id,
        target_user_id=grant.user_id,
        role_template=grant.role_template,
        market_id=grant.market_id,
        operator_id=grant.operator_id,
        city_id=grant.city_id,
        source_grant_id=grant.id,
        reason=reason,
        requested_at=requested_at,
    )
    session.add(request)
    await session.flush()
    await audit(
        session,
        actor_user_id=requester_user_id,
        action="ADMINISTRATIVE_GRANT_REVOCATION_REQUESTED",
        resource_type="administrative_grant_change_request",
        resource_id=request.id,
        market_id=scope_market_id,
        operator_id=request.operator_id,
        city_id=request.city_id,
        changes={
            "action": request.action.value,
            "source_grant_id": str(grant.id),
            "target_user_id": str(grant.user_id),
            "role_template": grant.role_template.value,
        },
    )
    return request


async def _lock_visible_request(
    session: AsyncSession,
    *,
    request_id: UUID,
    actor_user_id: UUID,
    authorized_market_ids: frozenset[UUID],
    now: datetime,
) -> tuple[AdministrativeGrantChangeRequest, UUID]:
    snapshot = await session.get(AdministrativeGrantChangeRequest, request_id)
    if snapshot is None:
        raise GrantChangeNotFound("Administrative grant request not found.")
    scope_market_id = await resolve_scope_market_id(
        session,
        market_id=snapshot.market_id,
        operator_id=snapshot.operator_id,
        city_id=snapshot.city_id,
    )
    await _lock_authorized_market(
        session,
        market_id=scope_market_id,
        actor_user_id=actor_user_id,
        authorized_market_ids=authorized_market_ids,
        now=now,
    )
    request = await session.scalar(
        select(AdministrativeGrantChangeRequest)
        .where(AdministrativeGrantChangeRequest.id == request_id)
        .with_for_update()
    )
    assert request is not None
    return request, scope_market_id


def _require_pending_version(
    request: AdministrativeGrantChangeRequest,
    expected_version: int,
) -> None:
    if request.status != AdministrativeGrantRequestStatus.PENDING:
        raise GrantChangeConflict(
            f"Administrative grant request is already {request.status.value.lower()}."
        )
    if request.optimistic_version != expected_version:
        raise GrantChangeConflict(
            "Administrative grant request changed; refresh before deciding."
        )


def _mark_approved(
    request: AdministrativeGrantChangeRequest,
    *,
    approver_user_id: UUID,
    reason: str,
    decided_at: datetime,
) -> None:
    request.status = AdministrativeGrantRequestStatus.APPROVED
    request.decided_by_user_id = approver_user_id
    request.decision_reason = reason
    request.decided_at = decided_at
    request.optimistic_version += 1


async def approve_grant_change(
    session: AsyncSession,
    *,
    request_id: UUID,
    expected_version: int,
    reason: str,
    approver_user_id: UUID,
    authorized_market_ids: frozenset[UUID],
    now: datetime | None = None,
) -> AdministrativeGrantChangeRequest:
    decided_at = now or datetime.now(UTC)
    request, scope_market_id = await _lock_visible_request(
        session,
        request_id=request_id,
        actor_user_id=approver_user_id,
        authorized_market_ids=authorized_market_ids,
        now=decided_at,
    )
    _require_pending_version(request, expected_version)
    if approver_user_id in {request.requester_user_id, request.target_user_id}:
        raise GrantChangeConflict(
            "Approval requires an administrator distinct from both requester and target."
        )
    if request.action == AdministrativeGrantRequestAction.CREATE:
        target = await session.scalar(
            select(User).where(User.id == request.target_user_id).with_for_update()
        )
        if target is None or target.status != UserStatus.ACTIVE:
            raise GrantChangeConflict(
                "The target account is no longer active; reject or cancel this request."
            )
        if (
            request.requested_grant_expires_at is not None
            and request.requested_grant_expires_at <= decided_at
        ):
            raise GrantChangeConflict(
                "The requested grant expiry has passed; reject and submit a new request."
            )
        existing = await _existing_unrevoked_grant(
            session,
            user_id=request.target_user_id,
            role_template=request.role_template,
            market_id=request.market_id,
            operator_id=request.operator_id,
            city_id=request.city_id,
        )
        if existing is not None:
            raise GrantChangeConflict(
                "The target now has an unrevoked grant for that role and scope."
            )
        await _ensure_expiring_admin_has_successors(
            session,
            role_template=request.role_template,
            market_id=scope_market_id,
            expires_at=request.requested_grant_expires_at,
            now=decided_at,
        )
        grant_id = uuid4()
        grant = AdministrativeGrant(
            id=grant_id,
            user_id=request.target_user_id,
            role_template=request.role_template,
            market_id=request.market_id,
            operator_id=request.operator_id,
            city_id=request.city_id,
            granted_by_user_id=approver_user_id,
            grant_reason=request.reason,
            granted_at=decided_at,
            expires_at=request.requested_grant_expires_at,
        )
        _mark_approved(
            request,
            approver_user_id=approver_user_id,
            reason=reason,
            decided_at=decided_at,
        )
        request.resulting_grant_id = grant_id
        session.add(grant)
        await session.flush()
        await audit(
            session,
            actor_user_id=approver_user_id,
            action="ADMINISTRATIVE_GRANT_CREATED",
            resource_type="administrative_grant",
            resource_id=grant.id,
            market_id=scope_market_id,
            operator_id=grant.operator_id,
            city_id=grant.city_id,
            changes={
                "request_id": str(request.id),
                "requester_user_id": str(request.requester_user_id),
                "target_user_id": str(grant.user_id),
                "role_template": grant.role_template.value,
                "expires_at": grant.expires_at.isoformat() if grant.expires_at else None,
            },
        )
    else:
        assert request.source_grant_id is not None
        grant = await session.scalar(
            select(AdministrativeGrant)
            .where(AdministrativeGrant.id == request.source_grant_id)
            .with_for_update()
        )
        if grant is None or not _same_scope(grant, request):
            raise GrantChangeConflict(
                "The source grant no longer matches the reviewed request snapshot."
            )
        if grant.revoked_at is not None:
            raise GrantChangeConflict("The source grant is already revoked.")
        await ensure_platform_admin_continuity_before_revoke(
            session,
            grant=grant,
            market_id=scope_market_id,
            now=decided_at,
        )
        _mark_approved(
            request,
            approver_user_id=approver_user_id,
            reason=reason,
            decided_at=decided_at,
        )
        grant.revoked_at = decided_at
        grant.revoked_by_user_id = approver_user_id
        grant.revocation_reason = request.reason
        await audit(
            session,
            actor_user_id=approver_user_id,
            action="ADMINISTRATIVE_GRANT_REVOKED",
            resource_type="administrative_grant",
            resource_id=grant.id,
            market_id=scope_market_id,
            operator_id=grant.operator_id,
            city_id=grant.city_id,
            changes={
                "request_id": str(request.id),
                "requester_user_id": str(request.requester_user_id),
                "target_user_id": str(grant.user_id),
                "role_template": grant.role_template.value,
                "reason": request.reason,
            },
        )

    await session.flush()
    await audit(
        session,
        actor_user_id=approver_user_id,
        action="ADMINISTRATIVE_GRANT_REQUEST_APPROVED",
        resource_type="administrative_grant_change_request",
        resource_id=request.id,
        market_id=scope_market_id,
        operator_id=request.operator_id,
        city_id=request.city_id,
        changes={
            "action": request.action.value,
            "requester_user_id": str(request.requester_user_id),
            "target_user_id": str(request.target_user_id),
            "resulting_grant_id": (
                str(request.resulting_grant_id) if request.resulting_grant_id else None
            ),
            "optimistic_version": request.optimistic_version,
        },
    )
    return request


async def reject_grant_change(
    session: AsyncSession,
    *,
    request_id: UUID,
    expected_version: int,
    reason: str,
    approver_user_id: UUID,
    authorized_market_ids: frozenset[UUID],
    now: datetime | None = None,
) -> AdministrativeGrantChangeRequest:
    decided_at = now or datetime.now(UTC)
    request, scope_market_id = await _lock_visible_request(
        session,
        request_id=request_id,
        actor_user_id=approver_user_id,
        authorized_market_ids=authorized_market_ids,
        now=decided_at,
    )
    _require_pending_version(request, expected_version)
    if approver_user_id in {request.requester_user_id, request.target_user_id}:
        raise GrantChangeConflict(
            "Rejection requires an administrator distinct from both requester and target."
        )
    request.status = AdministrativeGrantRequestStatus.REJECTED
    request.decided_by_user_id = approver_user_id
    request.decision_reason = reason
    request.decided_at = decided_at
    request.optimistic_version += 1
    await session.flush()
    await audit(
        session,
        actor_user_id=approver_user_id,
        action="ADMINISTRATIVE_GRANT_REQUEST_REJECTED",
        resource_type="administrative_grant_change_request",
        resource_id=request.id,
        market_id=scope_market_id,
        operator_id=request.operator_id,
        city_id=request.city_id,
        changes={
            "action": request.action.value,
            "requester_user_id": str(request.requester_user_id),
            "target_user_id": str(request.target_user_id),
            "optimistic_version": request.optimistic_version,
        },
    )
    return request


async def cancel_grant_change(
    session: AsyncSession,
    *,
    request_id: UUID,
    expected_version: int,
    reason: str,
    requester_user_id: UUID,
    authorized_market_ids: frozenset[UUID],
    now: datetime | None = None,
) -> AdministrativeGrantChangeRequest:
    decided_at = now or datetime.now(UTC)
    request, scope_market_id = await _lock_visible_request(
        session,
        request_id=request_id,
        actor_user_id=requester_user_id,
        authorized_market_ids=authorized_market_ids,
        now=decided_at,
    )
    _require_pending_version(request, expected_version)
    if request.requester_user_id != requester_user_id:
        raise GrantChangeForbidden("Only the original requester may cancel this request.")
    request.status = AdministrativeGrantRequestStatus.CANCELLED
    request.decided_by_user_id = requester_user_id
    request.decision_reason = reason
    request.decided_at = decided_at
    request.optimistic_version += 1
    await session.flush()
    await audit(
        session,
        actor_user_id=requester_user_id,
        action="ADMINISTRATIVE_GRANT_REQUEST_CANCELLED",
        resource_type="administrative_grant_change_request",
        resource_id=request.id,
        market_id=scope_market_id,
        operator_id=request.operator_id,
        city_id=request.city_id,
        changes={
            "action": request.action.value,
            "target_user_id": str(request.target_user_id),
            "optimistic_version": request.optimistic_version,
        },
    )
    return request
