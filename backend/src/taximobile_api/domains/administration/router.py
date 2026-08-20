"""Administrative mutations kept separate from the mobile-user domain routers."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.administration.models import AuditLog
from taximobile_api.domains.administration.schemas import (
    AccountSecurityActionRequest,
    AccountSecurityActionResponse,
    AuditLogListResponse,
    AuditLogResponse,
    DriverApprovalResponse,
    PricingRuleCreateRequest,
    PricingRuleResponse,
)
from taximobile_api.domains.administration.service import audit, revoke_user_access
from taximobile_api.domains.auth.dependencies import CurrentPrincipal, administrator
from taximobile_api.domains.auth.models import Role, User, UserRole, UserStatus
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.drivers.models import (
    AvailabilityStatus,
    DriverAccountStatus,
    DriverProfile,
    DriverVerification,
    Vehicle,
    VehicleStatus,
    VehicleVerificationStatus,
    VerificationStatus,
)
from taximobile_api.domains.drivers.schemas import DriverProfileResponse, VehicleResponse
from taximobile_api.domains.pricing.models import PricingModel, PricingRule, PricingRuleStatus


router = APIRouter(prefix="/admin", tags=["administration"])


def audit_log_response(entry: AuditLog) -> AuditLogResponse:
    return AuditLogResponse(
        id=entry.id,
        actor_user_id=entry.actor_user_id,
        action=entry.action,
        resource_type=entry.resource_type,
        resource_id=entry.resource_id,
        changes=entry.changes,
        created_at=entry.created_at,
    )


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    actor_user_id: UUID | None = Query(default=None),
    action: str | None = Query(default=None, min_length=1, max_length=120),
    resource_type: str | None = Query(default=None, min_length=1, max_length=80),
    resource_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    _: CurrentPrincipal = Depends(administrator),
    session: AsyncSession = Depends(database_session),
) -> AuditLogListResponse:
    filters = []
    if actor_user_id is not None:
        filters.append(AuditLog.actor_user_id == actor_user_id)
    if action is not None:
        filters.append(AuditLog.action == action)
    if resource_type is not None:
        filters.append(AuditLog.resource_type == resource_type)
    if resource_id is not None:
        filters.append(AuditLog.resource_id == resource_id)

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
    return AuditLogListResponse(
        items=[audit_log_response(entry) for entry in entries],
        page=page,
        limit=limit,
        total=total or 0,
    )


async def locked_user_or_404(session: AsyncSession, user_id: UUID) -> User:
    user = await session.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")
    return user


def account_security_response(
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


@router.post(
    "/users/{user_id}/sessions/revoke",
    response_model=AccountSecurityActionResponse,
)
async def revoke_user_sessions(
    user_id: UUID,
    payload: AccountSecurityActionRequest,
    principal: CurrentPrincipal = Depends(administrator),
    session: AsyncSession = Depends(database_session),
) -> AccountSecurityActionResponse:
    changed_at = datetime.now(UTC)
    async with session.begin():
        user = await locked_user_or_404(session, user_id)
        sessions_revoked, devices_revoked = await revoke_user_access(
            session,
            user_id=user.id,
            revoked_at=changed_at,
        )
        await audit(
            session,
            actor_user_id=principal.user_id,
            action="USER_SESSIONS_REVOKED",
            resource_type="user",
            resource_id=user.id,
            changes={
                "reason": payload.reason,
                "sessions_revoked": sessions_revoked,
                "device_registrations_revoked": devices_revoked,
            },
        )
    return account_security_response(
        user,
        sessions_revoked=sessions_revoked,
        device_registrations_revoked=devices_revoked,
        changed_at=changed_at,
    )


@router.post(
    "/users/{user_id}/suspend",
    response_model=AccountSecurityActionResponse,
)
async def suspend_user(
    user_id: UUID,
    payload: AccountSecurityActionRequest,
    principal: CurrentPrincipal = Depends(administrator),
    session: AsyncSession = Depends(database_session),
) -> AccountSecurityActionResponse:
    if user_id == principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An administrator cannot suspend their own account.",
        )
    changed_at = datetime.now(UTC)
    async with session.begin():
        user = await locked_user_or_404(session, user_id)
        if user.status == UserStatus.DEACTIVATED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A deactivated account cannot be suspended.",
            )
        previous_status = user.status
        user.status = UserStatus.SUSPENDED
        user.updated_at = changed_at
        sessions_revoked, devices_revoked = await revoke_user_access(
            session,
            user_id=user.id,
            revoked_at=changed_at,
        )
        await audit(
            session,
            actor_user_id=principal.user_id,
            action="USER_SUSPENDED",
            resource_type="user",
            resource_id=user.id,
            changes={
                "reason": payload.reason,
                "previous_status": previous_status.value,
                "current_status": user.status.value,
                "sessions_revoked": sessions_revoked,
                "device_registrations_revoked": devices_revoked,
            },
        )
    return account_security_response(
        user,
        sessions_revoked=sessions_revoked,
        device_registrations_revoked=devices_revoked,
        changed_at=changed_at,
    )


@router.post(
    "/users/{user_id}/reactivate",
    response_model=AccountSecurityActionResponse,
)
async def reactivate_user(
    user_id: UUID,
    payload: AccountSecurityActionRequest,
    principal: CurrentPrincipal = Depends(administrator),
    session: AsyncSession = Depends(database_session),
) -> AccountSecurityActionResponse:
    changed_at = datetime.now(UTC)
    async with session.begin():
        user = await locked_user_or_404(session, user_id)
        if user.status == UserStatus.DEACTIVATED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A deactivated account cannot be reactivated through suspension recovery.",
            )
        previous_status = user.status
        if previous_status == UserStatus.SUSPENDED:
            user.status = UserStatus.ACTIVE
            user.updated_at = changed_at
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="USER_REACTIVATED",
                resource_type="user",
                resource_id=user.id,
                changes={
                    "reason": payload.reason,
                    "previous_status": previous_status.value,
                    "current_status": user.status.value,
                },
            )
    return account_security_response(
        user,
        sessions_revoked=0,
        device_registrations_revoked=0,
        changed_at=changed_at,
    )


def pricing_rule_response(rule: PricingRule) -> PricingRuleResponse:
    return PricingRuleResponse(
        id=rule.id,
        name=rule.name,
        version=rule.version,
        model=rule.model.value,
        fixed_amount=rule.fixed_amount,
        currency=rule.currency,
        effective_from=rule.effective_from,
        effective_until=rule.effective_until,
        status=rule.status.value,
    )


def driver_profile_response(profile: DriverProfile) -> DriverProfileResponse:
    return DriverProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        display_name=profile.display_name,
        verification_status=profile.verification_status.value,
        account_status=profile.account_status.value,
        availability_status=profile.availability_status.value,
    )


def vehicle_response(vehicle: Vehicle) -> VehicleResponse:
    return VehicleResponse(
        id=vehicle.id,
        make=vehicle.make,
        model=vehicle.model,
        color=vehicle.color,
        status=vehicle.status.value,
        verification_status=vehicle.verification_status.value,
    )


@router.post("/drivers/{driver_id}/approve", response_model=DriverApprovalResponse)
async def approve_driver(
    driver_id: UUID,
    principal: CurrentPrincipal = Depends(administrator),
    session: AsyncSession = Depends(database_session),
) -> DriverApprovalResponse:
    approved_at = datetime.now(UTC)
    async with session.begin():
        profile = await session.scalar(select(DriverProfile).where(DriverProfile.id == driver_id).with_for_update())
        if profile is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver application not found.")
        if profile.account_status == DriverAccountStatus.DEACTIVATED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A deactivated driver cannot be approved.")
        if (
            profile.verification_status == VerificationStatus.APPROVED
            and profile.account_status == DriverAccountStatus.ACTIVE
        ):
            last_approval = await session.scalar(
                select(DriverVerification)
                .where(DriverVerification.driver_id == profile.id, DriverVerification.status == VerificationStatus.APPROVED)
                .order_by(DriverVerification.created_at.desc())
                .limit(1)
            )
            return DriverApprovalResponse(
                driver=driver_profile_response(profile),
                approved_at=last_approval.reviewed_at if last_approval and last_approval.reviewed_at else approved_at,
            )
        if profile.verification_status != VerificationStatus.SUBMITTED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Driver verification must be submitted before approval.")

        previous = {
            "verification_status": profile.verification_status.value,
            "account_status": profile.account_status.value,
        }
        profile.verification_status = VerificationStatus.APPROVED
        profile.account_status = DriverAccountStatus.ACTIVE
        profile.availability_status = AvailabilityStatus.OFFLINE
        profile.available_since = None
        session.add(
            DriverVerification(
                driver_id=profile.id,
                status=VerificationStatus.APPROVED,
                reviewed_at=approved_at,
                reviewed_by=principal.user_id,
            )
        )
        driver_role = await session.scalar(
            select(UserRole).where(UserRole.user_id == profile.user_id, UserRole.role == Role.DRIVER)
        )
        if driver_role is None:
            session.add(UserRole(user_id=profile.user_id, role=Role.DRIVER))
        await audit(
            session,
            actor_user_id=principal.user_id,
            action="DRIVER_APPROVED",
            resource_type="driver_profile",
            resource_id=profile.id,
            changes={"previous": previous, "current": {"verification_status": "APPROVED", "account_status": "ACTIVE"}},
        )
    return DriverApprovalResponse(driver=driver_profile_response(profile), approved_at=approved_at)


@router.post("/vehicles/{vehicle_id}/verify", response_model=VehicleResponse)
async def verify_vehicle(
    vehicle_id: UUID,
    principal: CurrentPrincipal = Depends(administrator),
    session: AsyncSession = Depends(database_session),
) -> VehicleResponse:
    """Make an administrator's vehicle-verification decision auditable.

    The driver can register a vehicle but cannot promote it to dispatch-eligible
    status. Repeating an already verified active vehicle is harmless.
    """
    async with session.begin():
        vehicle = await session.scalar(select(Vehicle).where(Vehicle.id == vehicle_id).with_for_update())
        if vehicle is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found.")
        if vehicle.status != VehicleStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An inactive vehicle cannot be verified.")
        if vehicle.verification_status != VehicleVerificationStatus.VERIFIED:
            previous_status = vehicle.verification_status.value
            vehicle.verification_status = VehicleVerificationStatus.VERIFIED
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="VEHICLE_VERIFIED",
                resource_type="vehicle",
                resource_id=vehicle.id,
                changes={"previous_verification_status": previous_status, "current_verification_status": "VERIFIED"},
            )
    return vehicle_response(vehicle)


@router.post("/pricing-rules", response_model=PricingRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_pricing_rule(
    payload: PricingRuleCreateRequest,
    principal: CurrentPrincipal = Depends(administrator),
    session: AsyncSession = Depends(database_session),
) -> PricingRuleResponse:
    rule = PricingRule(
        name=payload.name,
        version=payload.version,
        model=PricingModel.FIXED,
        fixed_amount=payload.fixed_amount,
        currency=payload.currency,
        effective_from=payload.effective_from,
        effective_until=payload.effective_until,
        status=PricingRuleStatus.INACTIVE,
    )
    try:
        async with session.begin():
            session.add(rule)
            await session.flush()
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="PRICING_RULE_CREATED",
                resource_type="pricing_rule",
                resource_id=rule.id,
                changes={"version": rule.version, "status": rule.status.value, "effective_from": rule.effective_from.isoformat()},
            )
    except IntegrityError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pricing rule version already exists.") from error
    return pricing_rule_response(rule)


@router.post("/pricing-rules/{pricing_rule_id}/activate", response_model=PricingRuleResponse)
async def activate_pricing_rule(
    pricing_rule_id: UUID,
    principal: CurrentPrincipal = Depends(administrator),
    session: AsyncSession = Depends(database_session),
) -> PricingRuleResponse:
    now = datetime.now(UTC)
    async with session.begin():
        rule = await session.scalar(select(PricingRule).where(PricingRule.id == pricing_rule_id).with_for_update())
        if rule is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pricing rule not found.")
        if rule.status == PricingRuleStatus.ACTIVE:
            return pricing_rule_response(rule)
        if rule.effective_from < now:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A pricing rule cannot be activated retrospectively.",
            )

        active_rules = list(
            await session.scalars(
                select(PricingRule)
                .where(
                    PricingRule.status == PricingRuleStatus.ACTIVE,
                    PricingRule.id != rule.id,
                    PricingRule.effective_from < (rule.effective_until or datetime.max.replace(tzinfo=UTC)),
                    or_(PricingRule.effective_until.is_(None), PricingRule.effective_until > rule.effective_from),
                )
                .with_for_update()
            )
        )
        future_conflict = next((active for active in active_rules if active.effective_from >= rule.effective_from), None)
        if future_conflict is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This tariff overlaps an already scheduled active tariff.",
            )
        for active in active_rules:
            active.effective_until = rule.effective_from
        rule.status = PricingRuleStatus.ACTIVE
        await audit(
            session,
            actor_user_id=principal.user_id,
            action="PRICING_RULE_ACTIVATED",
            resource_type="pricing_rule",
            resource_id=rule.id,
            changes={
                "version": rule.version,
                "effective_from": rule.effective_from.isoformat(),
                "superseded_rule_ids": [str(active.id) for active in active_rules],
            },
        )
    return pricing_rule_response(rule)
