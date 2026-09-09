"""Scoped operations lifecycle for payment destinations and capabilities."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

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
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.markets.models import (
    AssignmentStatus,
    City,
    Operator,
    OperatorCityAssignment,
    OperatorStatus,
)
from taximobile_api.domains.payments.models import (
    PaymentCapabilityStatus,
    PaymentCapabilityVersion,
    PaymentRecipientAccount,
    PaymentRecipientStatus,
)
from taximobile_api.domains.payments.schemas import (
    PaymentCapabilityCommandRequest,
    PaymentCapabilityCreateRequest,
    PaymentCapabilityListResponse,
    PaymentCapabilityResponse,
    PaymentCapabilityUpdateRequest,
    PaymentRecipientCommandRequest,
    PaymentRecipientCreateRequest,
    PaymentRecipientListResponse,
    PaymentRecipientResponse,
    PaymentRecipientUpdateRequest,
)


router = APIRouter(prefix="/operations", tags=["operations-payments"])
MANAGE = OperationsPermission.MANAGE_PAYMENT_CAPABILITIES


class PaymentConfigurationConflict(ValueError):
    pass


def _expected(actual: int, expected: int) -> None:
    if actual != expected:
        raise PaymentConfigurationConflict(
            f"The resource changed; expected version {expected}, current version {actual}."
        )


def _same_grant(
    principal: OperationsPrincipal,
    *,
    city_id: UUID,
    operator_id: UUID,
) -> bool:
    return any(
        grant.allows(MANAGE, city_id=city_id)
        and grant.allows(MANAGE, operator_id=operator_id)
        for grant in principal.grants
    )


async def _scope(
    session: AsyncSession,
    principal: OperationsPrincipal,
    *,
    city_id: UUID,
    operator_id: UUID,
) -> tuple[City, Operator]:
    city = await session.scalar(
        select(City).where(City.id == city_id, City.id.in_(principal.city_ids_for(MANAGE)))
    )
    operator = await session.get(Operator, operator_id)
    if (
        city is None
        or operator is None
        or operator.market_id != city.market_id
        or not _same_grant(principal, city_id=city_id, operator_id=operator_id)
    ):
        raise HTTPException(status_code=404, detail="Payment configuration scope not found.")
    return city, operator


async def _active_assignment_exists(
    session: AsyncSession,
    *,
    city_id: UUID,
    operator_id: UUID,
    service_type,
) -> bool:
    now = datetime.now(UTC)
    assignment_id = await session.scalar(
        select(OperatorCityAssignment.id).where(
            OperatorCityAssignment.city_id == city_id,
            OperatorCityAssignment.operator_id == operator_id,
            OperatorCityAssignment.service_type == service_type,
            OperatorCityAssignment.status == AssignmentStatus.ACTIVE,
            OperatorCityAssignment.effective_from <= now,
            (
                OperatorCityAssignment.effective_until.is_(None)
                | (OperatorCityAssignment.effective_until > now)
            ),
        )
    )
    return assignment_id is not None


def recipient_response(account: PaymentRecipientAccount) -> PaymentRecipientResponse:
    return PaymentRecipientResponse(
        id=account.id,
        city_id=account.city_id,
        operator_id=account.operator_id,
        label=account.label,
        recipient_name=account.recipient_name,
        bank_account=account.bank_account,
        wallet_id=account.wallet_id,
        status=account.status,
        optimistic_version=account.optimistic_version,
        verified_at=account.verified_at,
        retired_at=account.retired_at,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


def capability_response(capability: PaymentCapabilityVersion) -> PaymentCapabilityResponse:
    return PaymentCapabilityResponse(
        id=capability.id,
        city_id=capability.city_id,
        operator_id=capability.operator_id,
        service_type=capability.service_type,
        version=capability.version,
        status=capability.status,
        cash_enabled=capability.cash_enabled,
        manual_transfer_enabled=capability.manual_transfer_enabled,
        recipient_account_id=capability.recipient_account_id,
        effective_from=capability.effective_from,
        effective_until=capability.effective_until,
        optimistic_version=capability.optimistic_version,
        submitted_at=capability.submitted_at,
        approved_at=capability.approved_at,
        activated_at=capability.activated_at,
        created_at=capability.created_at,
        updated_at=capability.updated_at,
    )


async def _recipient_or_404(
    session: AsyncSession,
    principal: OperationsPrincipal,
    account_id: UUID,
    *,
    lock: bool = False,
) -> PaymentRecipientAccount:
    statement = select(PaymentRecipientAccount).where(
        PaymentRecipientAccount.id == account_id,
        PaymentRecipientAccount.city_id.in_(principal.city_ids_for(MANAGE)),
        PaymentRecipientAccount.operator_id.in_(principal.operator_ids_for(MANAGE)),
    )
    if lock:
        statement = statement.with_for_update()
    account = await session.scalar(statement)
    if account is None or not _same_grant(
        principal, city_id=account.city_id, operator_id=account.operator_id
    ):
        raise HTTPException(status_code=404, detail="Payment recipient not found.")
    return account


async def _capability_or_404(
    session: AsyncSession,
    principal: OperationsPrincipal,
    capability_id: UUID,
    *,
    lock: bool = False,
) -> PaymentCapabilityVersion:
    statement = select(PaymentCapabilityVersion).where(
        PaymentCapabilityVersion.id == capability_id,
        PaymentCapabilityVersion.city_id.in_(principal.city_ids_for(MANAGE)),
        PaymentCapabilityVersion.operator_id.in_(principal.operator_ids_for(MANAGE)),
    )
    if lock:
        statement = statement.with_for_update()
    capability = await session.scalar(statement)
    if capability is None or not _same_grant(
        principal, city_id=capability.city_id, operator_id=capability.operator_id
    ):
        raise HTTPException(status_code=404, detail="Payment capability not found.")
    return capability


async def _recipient_for_capability(
    session: AsyncSession,
    capability: PaymentCapabilityVersion,
    *,
    require_verified: bool,
) -> PaymentRecipientAccount | None:
    if not capability.manual_transfer_enabled:
        if capability.recipient_account_id is not None:
            raise PaymentConfigurationConflict(
                "Cash-only capability cannot reference a transfer recipient."
            )
        return None
    if capability.recipient_account_id is None:
        raise PaymentConfigurationConflict(
            "Manual transfer requires a recipient account."
        )
    recipient = await session.get(PaymentRecipientAccount, capability.recipient_account_id)
    if (
        recipient is None
        or recipient.city_id != capability.city_id
        or recipient.operator_id != capability.operator_id
    ):
        raise PaymentConfigurationConflict(
            "The recipient account must belong to the same city and operator."
        )
    if require_verified and recipient.status != PaymentRecipientStatus.VERIFIED:
        raise PaymentConfigurationConflict(
            "Manual transfer activation requires a verified recipient account."
        )
    return recipient


@router.get(
    "/cities/{city_id}/payment-recipient-accounts",
    response_model=PaymentRecipientListResponse,
)
async def list_recipients(
    city_id: UUID,
    operator_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE)),
    session: AsyncSession = Depends(database_session),
) -> PaymentRecipientListResponse:
    if city_id not in principal.city_ids_for(MANAGE):
        raise HTTPException(status_code=404, detail="City not found.")
    filters = [PaymentRecipientAccount.city_id == city_id]
    if operator_id is not None:
        if not _same_grant(principal, city_id=city_id, operator_id=operator_id):
            raise HTTPException(status_code=404, detail="Payment configuration scope not found.")
        filters.append(PaymentRecipientAccount.operator_id == operator_id)
    else:
        filters.append(PaymentRecipientAccount.operator_id.in_(principal.operator_ids_for(MANAGE)))
    items = list(
        await session.scalars(
            select(PaymentRecipientAccount)
            .where(*filters)
            .order_by(PaymentRecipientAccount.created_at.desc(), PaymentRecipientAccount.id)
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    total = await session.scalar(
        select(func.count()).select_from(PaymentRecipientAccount).where(*filters)
    )
    return PaymentRecipientListResponse(
        items=[recipient_response(item) for item in items],
        page=page,
        limit=limit,
        total=total or 0,
    )


@router.post(
    "/cities/{city_id}/payment-recipient-accounts",
    response_model=PaymentRecipientResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_recipient(
    city_id: UUID,
    payload: PaymentRecipientCreateRequest,
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE)),
    session: AsyncSession = Depends(database_session),
) -> PaymentRecipientResponse:
    try:
        async with session.begin():
            city, _ = await _scope(
                session, principal, city_id=city_id, operator_id=payload.operator_id
            )
            account = PaymentRecipientAccount(
                city_id=city_id,
                operator_id=payload.operator_id,
                label=payload.label,
                recipient_name=payload.recipient_name,
                bank_account=payload.bank_account,
                wallet_id=payload.wallet_id,
                status=PaymentRecipientStatus.DRAFT,
                created_by_user_id=principal.user_id,
            )
            session.add(account)
            await session.flush()
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="PAYMENT_RECIPIENT_CREATED",
                resource_type="payment_recipient_account",
                resource_id=account.id,
                market_id=city.market_id,
                operator_id=account.operator_id,
                city_id=city.id,
                changes={"label": account.label, "status": account.status.value},
            )
            await session.flush()
            await session.refresh(account)
            return recipient_response(account)
    except PaymentConfigurationConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except IntegrityError as error:
        raise HTTPException(status_code=409, detail="That recipient label already exists in this scope.") from error


@router.patch(
    "/payment-recipient-accounts/{account_id}",
    response_model=PaymentRecipientResponse,
)
async def update_recipient(
    account_id: UUID,
    payload: PaymentRecipientUpdateRequest,
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE)),
    session: AsyncSession = Depends(database_session),
) -> PaymentRecipientResponse:
    try:
        async with session.begin():
            account = await _recipient_or_404(session, principal, account_id, lock=True)
            _expected(account.optimistic_version, payload.expected_version)
            if account.status != PaymentRecipientStatus.DRAFT:
                raise PaymentConfigurationConflict("Only a draft recipient can be edited.")
            if payload.operator_id is not None and payload.operator_id != account.operator_id:
                raise PaymentConfigurationConflict("A recipient cannot move to another operator.")
            account.label = payload.label
            account.recipient_name = payload.recipient_name
            account.bank_account = payload.bank_account
            account.wallet_id = payload.wallet_id
            account.optimistic_version += 1
            account.updated_at = datetime.now(UTC)
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="PAYMENT_RECIPIENT_UPDATED",
                resource_type="payment_recipient_account",
                resource_id=account.id,
                operator_id=account.operator_id,
                city_id=account.city_id,
                changes={"current_version": account.optimistic_version},
            )
            await session.flush()
            return recipient_response(account)
    except PaymentConfigurationConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


async def _recipient_command(
    *,
    session: AsyncSession,
    principal: OperationsPrincipal,
    account_id: UUID,
    payload: PaymentRecipientCommandRequest,
    target: PaymentRecipientStatus,
) -> PaymentRecipientAccount:
    account = await _recipient_or_404(session, principal, account_id, lock=True)
    _expected(account.optimistic_version, payload.expected_version)
    now = datetime.now(UTC)
    if target == PaymentRecipientStatus.VERIFIED:
        if account.status != PaymentRecipientStatus.DRAFT:
            raise PaymentConfigurationConflict("Only a draft recipient can be verified.")
        account.verified_by_user_id = principal.user_id
        account.verified_at = now
    elif target == PaymentRecipientStatus.RETIRED:
        if account.status != PaymentRecipientStatus.VERIFIED:
            raise PaymentConfigurationConflict("Only a verified recipient can be retired.")
        active_reference = await session.scalar(
            select(PaymentCapabilityVersion.id).where(
                PaymentCapabilityVersion.recipient_account_id == account.id,
                PaymentCapabilityVersion.status == PaymentCapabilityStatus.ACTIVE,
            ).limit(1)
        )
        if active_reference is not None:
            raise PaymentConfigurationConflict(
                "Retire or replace every active capability using this recipient first."
            )
        account.retired_by_user_id = principal.user_id
        account.retired_at = now
    account.status = target
    account.optimistic_version += 1
    account.updated_at = now
    await audit(
        session,
        actor_user_id=principal.user_id,
        action=f"PAYMENT_RECIPIENT_{target.value}",
        resource_type="payment_recipient_account",
        resource_id=account.id,
        operator_id=account.operator_id,
        city_id=account.city_id,
        changes={"status": target.value, "reason": payload.reason},
    )
    return account


@router.post("/payment-recipient-accounts/{account_id}/verify", response_model=PaymentRecipientResponse)
async def verify_recipient(
    account_id: UUID,
    payload: PaymentRecipientCommandRequest,
    _mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE)),
    session: AsyncSession = Depends(database_session),
) -> PaymentRecipientResponse:
    try:
        async with session.begin():
            account = await _recipient_command(
                session=session, principal=principal, account_id=account_id,
                payload=payload, target=PaymentRecipientStatus.VERIFIED,
            )
            await session.flush()
            return recipient_response(account)
    except PaymentConfigurationConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/payment-recipient-accounts/{account_id}/retire", response_model=PaymentRecipientResponse)
async def retire_recipient(
    account_id: UUID,
    payload: PaymentRecipientCommandRequest,
    _mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE)),
    session: AsyncSession = Depends(database_session),
) -> PaymentRecipientResponse:
    try:
        async with session.begin():
            account = await _recipient_command(
                session=session, principal=principal, account_id=account_id,
                payload=payload, target=PaymentRecipientStatus.RETIRED,
            )
            await session.flush()
            return recipient_response(account)
    except PaymentConfigurationConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get(
    "/cities/{city_id}/payment-capability-versions",
    response_model=PaymentCapabilityListResponse,
)
async def list_capabilities(
    city_id: UUID,
    operator_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE)),
    session: AsyncSession = Depends(database_session),
) -> PaymentCapabilityListResponse:
    if city_id not in principal.city_ids_for(MANAGE):
        raise HTTPException(status_code=404, detail="City not found.")
    filters = [PaymentCapabilityVersion.city_id == city_id]
    if operator_id is not None:
        if not _same_grant(principal, city_id=city_id, operator_id=operator_id):
            raise HTTPException(status_code=404, detail="Payment configuration scope not found.")
        filters.append(PaymentCapabilityVersion.operator_id == operator_id)
    else:
        filters.append(PaymentCapabilityVersion.operator_id.in_(principal.operator_ids_for(MANAGE)))
    items = list(
        await session.scalars(
            select(PaymentCapabilityVersion)
            .where(*filters)
            .order_by(PaymentCapabilityVersion.created_at.desc(), PaymentCapabilityVersion.id)
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    total = await session.scalar(
        select(func.count()).select_from(PaymentCapabilityVersion).where(*filters)
    )
    return PaymentCapabilityListResponse(
        items=[capability_response(item) for item in items], page=page, limit=limit, total=total or 0
    )


@router.post(
    "/cities/{city_id}/payment-capability-versions",
    response_model=PaymentCapabilityResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_capability(
    city_id: UUID,
    payload: PaymentCapabilityCreateRequest,
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE)),
    session: AsyncSession = Depends(database_session),
) -> PaymentCapabilityResponse:
    try:
        async with session.begin():
            city, _ = await _scope(
                session, principal, city_id=city_id, operator_id=payload.operator_id
            )
            capability = PaymentCapabilityVersion(
                city_id=city_id,
                operator_id=payload.operator_id,
                service_type=payload.service_type,
                version=payload.version,
                status=PaymentCapabilityStatus.DRAFT,
                cash_enabled=True,
                manual_transfer_enabled=payload.manual_transfer_enabled,
                recipient_account_id=payload.recipient_account_id,
                effective_from=payload.effective_from,
                effective_until=payload.effective_until,
                created_by_user_id=principal.user_id,
            )
            await _recipient_for_capability(session, capability, require_verified=False)
            session.add(capability)
            await session.flush()
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="PAYMENT_CAPABILITY_CREATED",
                resource_type="payment_capability_version",
                resource_id=capability.id,
                market_id=city.market_id,
                operator_id=capability.operator_id,
                city_id=city.id,
                changes={"version": capability.version, "status": capability.status.value},
            )
            await session.flush()
            await session.refresh(capability)
            return capability_response(capability)
    except PaymentConfigurationConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except IntegrityError as error:
        raise HTTPException(status_code=409, detail="That payment capability version already exists.") from error


@router.patch("/payment-capability-versions/{capability_id}", response_model=PaymentCapabilityResponse)
async def update_capability(
    capability_id: UUID,
    payload: PaymentCapabilityUpdateRequest,
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE)),
    session: AsyncSession = Depends(database_session),
) -> PaymentCapabilityResponse:
    try:
        async with session.begin():
            capability = await _capability_or_404(session, principal, capability_id, lock=True)
            _expected(capability.optimistic_version, payload.expected_version)
            if capability.status != PaymentCapabilityStatus.DRAFT:
                raise PaymentConfigurationConflict("Only a draft payment capability can be edited.")
            capability.manual_transfer_enabled = payload.manual_transfer_enabled
            capability.recipient_account_id = payload.recipient_account_id
            capability.effective_from = payload.effective_from
            capability.effective_until = payload.effective_until
            await _recipient_for_capability(session, capability, require_verified=False)
            capability.optimistic_version += 1
            capability.updated_at = datetime.now(UTC)
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="PAYMENT_CAPABILITY_UPDATED",
                resource_type="payment_capability_version",
                resource_id=capability.id,
                operator_id=capability.operator_id,
                city_id=capability.city_id,
                changes={"current_version": capability.optimistic_version},
            )
            await session.flush()
            return capability_response(capability)
    except PaymentConfigurationConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


async def _capability_command(
    *,
    session: AsyncSession,
    principal: OperationsPrincipal,
    capability_id: UUID,
    payload: PaymentCapabilityCommandRequest,
    target: PaymentCapabilityStatus,
) -> PaymentCapabilityVersion:
    capability = await _capability_or_404(session, principal, capability_id, lock=True)
    if capability.status == target:
        return capability
    _expected(capability.optimistic_version, payload.expected_version)
    transitions = {
        PaymentCapabilityStatus.DRAFT: PaymentCapabilityStatus.IN_REVIEW,
        PaymentCapabilityStatus.IN_REVIEW: PaymentCapabilityStatus.APPROVED,
        PaymentCapabilityStatus.APPROVED: PaymentCapabilityStatus.ACTIVE,
    }
    if transitions.get(capability.status) != target:
        raise PaymentConfigurationConflict(
            f"Payment capability cannot transition from {capability.status.value} to {target.value}."
        )
    now = datetime.now(UTC)
    if target == PaymentCapabilityStatus.ACTIVE:
        _, operator = await _scope(
            session, principal, city_id=capability.city_id, operator_id=capability.operator_id
        )
        if operator.status != OperatorStatus.ACTIVE or not await _active_assignment_exists(
            session,
            city_id=capability.city_id,
            operator_id=capability.operator_id,
            service_type=capability.service_type,
        ):
            raise PaymentConfigurationConflict(
                "Activation requires an active operator and current service assignment."
            )
        if capability.effective_from > now or (
            capability.effective_until is not None and capability.effective_until <= now
        ):
            raise PaymentConfigurationConflict(
                "The payment capability must be effective when activated."
            )
        await _recipient_for_capability(session, capability, require_verified=True)
        capability.activated_by_user_id = principal.user_id
        capability.activated_at = now
    elif target == PaymentCapabilityStatus.IN_REVIEW:
        await _recipient_for_capability(session, capability, require_verified=False)
        capability.submitted_by_user_id = principal.user_id
        capability.submitted_at = now
    elif target == PaymentCapabilityStatus.APPROVED:
        await _recipient_for_capability(session, capability, require_verified=True)
        capability.approved_by_user_id = principal.user_id
        capability.approved_at = now
    capability.status = target
    capability.optimistic_version += 1
    capability.updated_at = now
    await audit(
        session,
        actor_user_id=principal.user_id,
        action=f"PAYMENT_CAPABILITY_{target.value}",
        resource_type="payment_capability_version",
        resource_id=capability.id,
        operator_id=capability.operator_id,
        city_id=capability.city_id,
        changes={"status": target.value, "reason": payload.reason},
    )
    return capability


def _capability_endpoint(target: PaymentCapabilityStatus, *, recent_mfa: bool = False):
    dependencies = [Depends(require_recent_operations_mfa)] if recent_mfa else None

    async def endpoint(
        capability_id: UUID,
        payload: PaymentCapabilityCommandRequest,
        principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE)),
        session: AsyncSession = Depends(database_session),
    ) -> PaymentCapabilityResponse:
        try:
            async with session.begin():
                capability = await _capability_command(
                    session=session, principal=principal, capability_id=capability_id,
                    payload=payload, target=target,
                )
                await session.flush()
                return capability_response(capability)
        except PaymentConfigurationConflict as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    endpoint.__name__ = f"{target.value.lower()}_payment_capability"
    return endpoint, dependencies


for _path, _target, _recent in (
    ("submit", PaymentCapabilityStatus.IN_REVIEW, False),
    ("approve", PaymentCapabilityStatus.APPROVED, False),
    ("activate", PaymentCapabilityStatus.ACTIVE, True),
):
    _endpoint, _dependencies = _capability_endpoint(_target, recent_mfa=_recent)
    router.add_api_route(
        f"/payment-capability-versions/{{capability_id}}/{_path}",
        _endpoint,
        methods=["POST"],
        response_model=PaymentCapabilityResponse,
        dependencies=_dependencies,
    )
