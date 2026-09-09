"""Scoped operations API for tariffs, operator fees, and scheduling surcharges."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.administration.operations_dependencies import (
    OperationsSessionIdentity,
    require_recent_operations_mfa,
    require_operations_permission,
)
from taximobile_api.domains.administration.permissions import (
    OperationsPermission,
    OperationsPrincipal,
)
from taximobile_api.domains.administration.service import audit
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.fixed_routes.models import (
    FixedRoute,
    FixedRouteDirection,
    FixedRoutePublicationStatus,
    FixedRouteStatus,
    FixedRouteVersion,
)
from taximobile_api.domains.markets.models import (
    AssignmentStatus,
    City,
    Market,
    Operator,
    OperatorCityAssignment,
    OperatorStatus,
    ServiceType,
)
from taximobile_api.domains.pricing.models import (
    BookingType,
    FinancialPolicyStatus,
    OperatorFeeCalculationMode,
    OperatorFeePolicy,
    PricingModel,
    PricingRule,
    PricingRuleStatus,
    SchedulingPolicy,
)
from taximobile_api.domains.pricing.schemas import (
    OperatorFeePolicyCreateRequest,
    OperatorFeePolicyListResponse,
    OperatorFeePolicyResponse,
    OperatorFeePolicyUpdateRequest,
    PricingPolicyCommandRequest,
    PricingRuleCreateRequest,
    PricingRuleListResponse,
    PricingRuleResponse,
    PricingRuleUpdateRequest,
    SchedulingPolicyCreateRequest,
    SchedulingPolicyListResponse,
    SchedulingPolicyResponse,
    SchedulingPolicyUpdateRequest,
)


router = APIRouter(prefix="/operations", tags=["operations-pricing"])

MANAGE_TARIFFS = OperationsPermission.MANAGE_CITY_TARIFFS
MANAGE_FEES = OperationsPermission.MANAGE_OPERATOR_FEE_POLICIES
MANAGE_SCHEDULING = OperationsPermission.MANAGE_SCHEDULING_POLICY


class PricingPolicyConflict(ValueError):
    """A stable, client-actionable operations conflict."""


def _require_expected_version(actual: int, expected: int) -> None:
    if actual != expected:
        raise PricingPolicyConflict(
            f"The resource changed; expected version {expected}, current version {actual}."
        )


def _http_conflict(error: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


def _scope_allowed(
    principal: OperationsPrincipal,
    permission: OperationsPermission,
    *,
    city_id: UUID,
    operator_id: UUID,
) -> bool:
    """Require city and operator authority to come from the same grant."""

    return any(
        grant.allows(permission, city_id=city_id)
        and grant.allows(permission, operator_id=operator_id)
        for grant in principal.grants
    )


async def _city_or_404(
    session: AsyncSession,
    principal: OperationsPrincipal,
    permission: OperationsPermission,
    city_id: UUID,
    *,
    lock: bool = False,
) -> City:
    statement = select(City).where(
        City.id == city_id,
        City.id.in_(principal.city_ids_for(permission)),
    )
    if lock:
        statement = statement.with_for_update()
    city = await session.scalar(statement)
    if city is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="City not found.")
    return city


async def _scope_context(
    session: AsyncSession,
    principal: OperationsPrincipal,
    permission: OperationsPermission,
    *,
    city_id: UUID,
    operator_id: UUID,
    service_type: ServiceType,
    require_current_assignment: bool,
) -> tuple[City, Market, Operator, OperatorCityAssignment]:
    city = await _city_or_404(session, principal, permission, city_id)
    if not _scope_allowed(
        principal,
        permission,
        city_id=city_id,
        operator_id=operator_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="City/operator scope not found.",
        )
    operator = await session.get(Operator, operator_id)
    market = await session.get(Market, city.market_id)
    if operator is None or market is None or operator.market_id != city.market_id:
        raise PricingPolicyConflict("The operator and city must belong to the same market.")

    filters = [
        OperatorCityAssignment.city_id == city_id,
        OperatorCityAssignment.operator_id == operator_id,
        OperatorCityAssignment.service_type == service_type,
        OperatorCityAssignment.status == AssignmentStatus.ACTIVE,
    ]
    now = datetime.now(UTC)
    if require_current_assignment:
        filters.extend(
            [
                OperatorCityAssignment.effective_from <= now,
                or_(
                    OperatorCityAssignment.effective_until.is_(None),
                    OperatorCityAssignment.effective_until > now,
                ),
            ]
        )
    assignment = await session.scalar(
        select(OperatorCityAssignment)
        .where(*filters)
        .order_by(OperatorCityAssignment.effective_from.desc())
        .limit(1)
    )
    if assignment is None:
        suffix = " and effective now" if require_current_assignment else ""
        raise PricingPolicyConflict(
            f"The operator needs an active {service_type.value} city assignment{suffix}."
        )
    if require_current_assignment and operator.status != OperatorStatus.ACTIVE:
        raise PricingPolicyConflict("The operator must be active before policy activation.")
    return city, market, operator, assignment


async def _advisory_scope_lock(session: AsyncSession, scope: str) -> None:
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))"),
        {"scope": scope},
    )


def _effective_now(effective_from: datetime, effective_until: datetime | None) -> bool:
    now = datetime.now(UTC)
    return effective_from <= now and (effective_until is None or effective_until > now)


def _validate_range(effective_from: datetime, effective_until: datetime | None) -> None:
    if effective_until is not None and effective_until <= effective_from:
        raise PricingPolicyConflict("effective_until must be after effective_from.")


def _validate_tariff(rule: PricingRule, market: Market) -> None:
    _validate_range(rule.effective_from, rule.effective_until)
    if rule.service_type not in {
        ServiceType.ON_DEMAND,
        ServiceType.FIXED_ROUTE,
    } or rule.booking_type != BookingType.IMMEDIATE:
        raise PricingPolicyConflict(
            "Phase 15 activates immediate on-demand or fixed-route tariffs only."
        )
    if rule.model != PricingModel.FIXED or rule.fixed_amount is None or rule.fixed_amount <= 0:
        raise PricingPolicyConflict("A Phase 14 tariff requires a positive fixed amount.")
    if rule.currency != market.default_currency:
        raise PricingPolicyConflict("The tariff currency must match the market currency.")
    if (
        rule.service_type == ServiceType.ON_DEMAND
        and rule.fixed_route_direction_id is not None
    ):
        raise PricingPolicyConflict(
            "An on-demand tariff cannot reference a fixed-route direction."
        )


async def _direction_for_tariff_scope(
    session: AsyncSession,
    *,
    direction_id: UUID,
    city_id: UUID,
    operator_id: UUID,
    lock: bool,
) -> tuple[FixedRouteDirection, FixedRouteVersion, FixedRoute]:
    statement = (
        select(FixedRouteDirection, FixedRouteVersion, FixedRoute)
        .join(
            FixedRouteVersion,
            FixedRouteVersion.id == FixedRouteDirection.route_version_id,
        )
        .join(FixedRoute, FixedRoute.id == FixedRouteVersion.fixed_route_id)
        .where(
            FixedRouteDirection.id == direction_id,
            FixedRoute.city_id == city_id,
            FixedRoute.operator_id == operator_id,
        )
    )
    if lock:
        statement = statement.with_for_update(of=FixedRouteDirection)
    row = (await session.execute(statement)).one_or_none()
    if row is None:
        raise PricingPolicyConflict(
            "The fixed-route direction does not belong to this city/operator scope."
        )
    return row


async def _validate_tariff_direction_link(
    session: AsyncSession,
    rule: PricingRule,
    *,
    require_link: bool,
) -> None:
    if rule.service_type != ServiceType.FIXED_ROUTE:
        if rule.fixed_route_direction_id is not None:
            raise PricingPolicyConflict(
                "Only a fixed-route tariff can reference a route direction."
            )
        return
    if rule.fixed_route_direction_id is None:
        if require_link:
            raise PricingPolicyConflict(
                "Bind this fixed-route tariff to one draft direction before activation."
            )
        return
    direction, version, route = await _direction_for_tariff_scope(
        session,
        direction_id=rule.fixed_route_direction_id,
        city_id=rule.city_id,
        operator_id=rule.operator_id,
        lock=require_link,
    )
    if route.status != FixedRouteStatus.ACTIVE or version.status not in {
        FixedRoutePublicationStatus.DRAFT,
        FixedRoutePublicationStatus.IN_REVIEW,
    }:
        raise PricingPolicyConflict(
            "A tariff can activate only for an active route's draft or in-review direction."
        )
    if direction.flat_fare_policy_version_id != rule.id:
        raise PricingPolicyConflict(
            "The route direction and tariff must reference each other exactly."
        )


def _validate_fee_policy(policy: OperatorFeePolicy, market: Market) -> None:
    _validate_range(policy.effective_from, policy.effective_until)
    if policy.service_type not in {
        ServiceType.ON_DEMAND,
        ServiceType.FIXED_ROUTE,
    }:
        raise PricingPolicyConflict(
            "Phase 15 fee policies support on-demand or fixed-route service only."
        )
    if policy.currency != market.default_currency:
        raise PricingPolicyConflict(
            "The operator-fee policy currency must match the market currency."
        )
    if policy.eligible_base_code != "TRANSPORT_FARE":
        raise PricingPolicyConflict("The operator-fee base must be TRANSPORT_FARE.")
    if policy.minimum_driver_net < Decimal("0.00"):
        raise PricingPolicyConflict("minimum_driver_net cannot be negative.")
    if policy.calculation_mode == OperatorFeeCalculationMode.PERCENTAGE_OF_TRANSPORT_FARE:
        if (
            policy.percentage_rate is None
            or policy.percentage_rate < 0
            or policy.percentage_rate >= 100
            or policy.flat_amount is not None
        ):
            raise PricingPolicyConflict(
                "A percentage operator-fee policy requires only a rate from 0 to below 100."
            )
    elif (
        policy.calculation_mode == OperatorFeeCalculationMode.FLAT_PER_COMPLETED_BOOKING
    ):
        if (
            policy.flat_amount is None
            or policy.flat_amount < 0
            or policy.percentage_rate is not None
        ):
            raise PricingPolicyConflict(
                "A flat operator-fee policy requires only a non-negative flat amount."
            )
    else:  # pragma: no cover - persisted enum validation is the final boundary.
        raise PricingPolicyConflict("Unsupported operator-fee calculation mode.")


def _validate_scheduling_policy(policy: SchedulingPolicy, market: Market) -> None:
    _validate_range(policy.effective_from, policy.effective_until)
    if policy.service_type not in {ServiceType.ON_DEMAND, ServiceType.FIXED_ROUTE}:
        raise PricingPolicyConflict("Scheduling supports on-demand or fixed-route service only.")
    if policy.currency != market.default_currency:
        raise PricingPolicyConflict(
            "The scheduling policy currency must match the market currency."
        )
    if policy.surcharge_amount < 0:
        raise PricingPolicyConflict("The scheduling surcharge cannot be negative.")
    if policy.collection_timing_code != "AT_RIDE_SETTLEMENT":
        raise PricingPolicyConflict("Unsupported scheduling collection timing.")
    if not (
        policy.offer_open_minutes_before > policy.commitment_deadline_minutes_before
        >= policy.handoff_minutes_before
    ):
        raise PricingPolicyConflict(
            "Offer, commitment, and handoff windows must be in descending order."
        )


def pricing_rule_response(rule: PricingRule) -> PricingRuleResponse:
    return PricingRuleResponse(
        id=rule.id,
        city_id=rule.city_id,
        operator_id=rule.operator_id,
        service_type=rule.service_type.value,
        booking_type=rule.booking_type.value,
        fixed_route_direction_id=rule.fixed_route_direction_id,
        name=rule.name,
        version=rule.version,
        model=rule.model.value,
        fixed_amount=rule.fixed_amount,
        currency=rule.currency,
        effective_from=rule.effective_from,
        effective_until=rule.effective_until,
        status=rule.status.value,
        optimistic_version=rule.optimistic_version,
        created_by_user_id=rule.created_by_user_id,
        submitted_by_user_id=rule.submitted_by_user_id,
        submitted_at=rule.submitted_at,
        activated_by_user_id=rule.activated_by_user_id,
        activated_at=rule.activated_at,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


def operator_fee_policy_response(policy: OperatorFeePolicy) -> OperatorFeePolicyResponse:
    return OperatorFeePolicyResponse(
        id=policy.id,
        city_id=policy.city_id,
        operator_id=policy.operator_id,
        service_type=policy.service_type.value,
        version=policy.version,
        status=policy.status.value,
        calculation_mode=policy.calculation_mode.value,
        funding_mode=policy.funding_mode.value,
        eligible_base_code=policy.eligible_base_code,
        percentage_rate=policy.percentage_rate,
        flat_amount=policy.flat_amount,
        currency=policy.currency,
        rounding_rule=policy.rounding_rule.value,
        minimum_driver_net=policy.minimum_driver_net,
        effective_from=policy.effective_from,
        effective_until=policy.effective_until,
        optimistic_version=policy.optimistic_version,
        created_by_user_id=policy.created_by_user_id,
        submitted_by_user_id=policy.submitted_by_user_id,
        submitted_at=policy.submitted_at,
        activated_by_user_id=policy.activated_by_user_id,
        activated_at=policy.activated_at,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


def scheduling_policy_response(policy: SchedulingPolicy) -> SchedulingPolicyResponse:
    return SchedulingPolicyResponse(
        id=policy.id,
        city_id=policy.city_id,
        operator_id=policy.operator_id,
        service_type=policy.service_type.value,
        version=policy.version,
        status=policy.status.value,
        surcharge_amount=policy.surcharge_amount,
        currency=policy.currency,
        beneficiary=policy.beneficiary.value,
        collection_timing_code=policy.collection_timing_code,
        minimum_lead_minutes=policy.minimum_lead_minutes,
        maximum_horizon_days=policy.maximum_horizon_days,
        offer_open_minutes_before=policy.offer_open_minutes_before,
        offer_response_seconds=policy.offer_response_seconds,
        commitment_deadline_minutes_before=policy.commitment_deadline_minutes_before,
        handoff_minutes_before=policy.handoff_minutes_before,
        protected_duration_minutes=policy.protected_duration_minutes,
        conflict_buffer_before_minutes=policy.conflict_buffer_before_minutes,
        conflict_buffer_after_minutes=policy.conflict_buffer_after_minutes,
        passenger_cancel_cutoff_minutes=policy.passenger_cancel_cutoff_minutes,
        driver_cancel_cutoff_minutes=policy.driver_cancel_cutoff_minutes,
        surcharge_refund_mode=policy.surcharge_refund_mode.value,
        fallback_matching_enabled=policy.fallback_matching_enabled,
        effective_from=policy.effective_from,
        effective_until=policy.effective_until,
        optimistic_version=policy.optimistic_version,
        created_by_user_id=policy.created_by_user_id,
        submitted_by_user_id=policy.submitted_by_user_id,
        submitted_at=policy.submitted_at,
        activated_by_user_id=policy.activated_by_user_id,
        activated_at=policy.activated_at,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


async def _pricing_rule_or_404(
    session: AsyncSession,
    principal: OperationsPrincipal,
    rule_id: UUID,
    *,
    lock: bool = False,
) -> tuple[PricingRule, City, Market]:
    statement = (
        select(PricingRule, City, Market)
        .join(City, City.id == PricingRule.city_id)
        .join(Market, Market.id == City.market_id)
        .where(
            PricingRule.id == rule_id,
            PricingRule.city_id.in_(principal.city_ids_for(MANAGE_TARIFFS)),
            PricingRule.operator_id.in_(principal.operator_ids_for(MANAGE_TARIFFS)),
        )
    )
    if lock:
        statement = statement.with_for_update(of=PricingRule)
    row = (await session.execute(statement)).one_or_none()
    if row is None or not _scope_allowed(
        principal,
        MANAGE_TARIFFS,
        city_id=row[0].city_id,
        operator_id=row[0].operator_id,
    ):
        raise HTTPException(status_code=404, detail="Pricing rule not found.")
    return row


async def _fee_policy_or_404(
    session: AsyncSession,
    principal: OperationsPrincipal,
    policy_id: UUID,
    *,
    lock: bool = False,
) -> tuple[OperatorFeePolicy, City, Market]:
    statement = (
        select(OperatorFeePolicy, City, Market)
        .join(City, City.id == OperatorFeePolicy.city_id)
        .join(Market, Market.id == City.market_id)
        .where(
            OperatorFeePolicy.id == policy_id,
            OperatorFeePolicy.city_id.in_(principal.city_ids_for(MANAGE_FEES)),
            OperatorFeePolicy.operator_id.in_(principal.operator_ids_for(MANAGE_FEES)),
        )
    )
    if lock:
        statement = statement.with_for_update(of=OperatorFeePolicy)
    row = (await session.execute(statement)).one_or_none()
    if row is None or not _scope_allowed(
        principal,
        MANAGE_FEES,
        city_id=row[0].city_id,
        operator_id=row[0].operator_id,
    ):
        raise HTTPException(status_code=404, detail="Operator-fee policy not found.")
    return row


async def _scheduling_policy_or_404(
    session: AsyncSession,
    principal: OperationsPrincipal,
    policy_id: UUID,
    *,
    lock: bool = False,
) -> tuple[SchedulingPolicy, City, Market]:
    statement = (
        select(SchedulingPolicy, City, Market)
        .join(City, City.id == SchedulingPolicy.city_id)
        .join(Market, Market.id == City.market_id)
        .where(
            SchedulingPolicy.id == policy_id,
            SchedulingPolicy.city_id.in_(principal.city_ids_for(MANAGE_SCHEDULING)),
            SchedulingPolicy.operator_id.in_(
                principal.operator_ids_for(MANAGE_SCHEDULING)
            ),
        )
    )
    if lock:
        statement = statement.with_for_update(of=SchedulingPolicy)
    row = (await session.execute(statement)).one_or_none()
    if row is None or not _scope_allowed(
        principal,
        MANAGE_SCHEDULING,
        city_id=row[0].city_id,
        operator_id=row[0].operator_id,
    ):
        raise HTTPException(status_code=404, detail="Scheduling policy not found.")
    return row


def _overlap_filters(model, resource):
    filters = [
        model.city_id == resource.city_id,
        model.operator_id == resource.operator_id,
        model.service_type == resource.service_type,
        model.id != resource.id,
        or_(model.effective_until.is_(None), model.effective_until > resource.effective_from),
    ]
    if resource.effective_until is not None:
        filters.append(model.effective_from < resource.effective_until)
    return filters


async def _replace_overlapping_tariffs(
    session: AsyncSession,
    rule: PricingRule,
    now: datetime,
) -> list[UUID]:
    previous = list(
        await session.scalars(
            select(PricingRule)
            .where(
                PricingRule.status == PricingRuleStatus.ACTIVE,
                PricingRule.booking_type == rule.booking_type,
                (
                    PricingRule.fixed_route_direction_id.is_(None)
                    if rule.fixed_route_direction_id is None
                    else PricingRule.fixed_route_direction_id
                    == rule.fixed_route_direction_id
                ),
                *_overlap_filters(PricingRule, rule),
            )
            .with_for_update()
        )
    )
    for item in previous:
        item.status = PricingRuleStatus.REPLACED
        item.updated_at = now
    if previous:
        await session.flush()
    return [item.id for item in previous]


async def _replace_overlapping_fees(
    session: AsyncSession,
    policy: OperatorFeePolicy,
    now: datetime,
) -> list[UUID]:
    previous = list(
        await session.scalars(
            select(OperatorFeePolicy)
            .where(
                OperatorFeePolicy.status == FinancialPolicyStatus.ACTIVE,
                *_overlap_filters(OperatorFeePolicy, policy),
            )
            .with_for_update()
        )
    )
    for item in previous:
        item.status = FinancialPolicyStatus.REPLACED
        item.updated_at = now
    if previous:
        await session.flush()
    return [item.id for item in previous]


async def _replace_overlapping_scheduling(
    session: AsyncSession,
    policy: SchedulingPolicy,
    now: datetime,
) -> list[UUID]:
    previous = list(
        await session.scalars(
            select(SchedulingPolicy)
            .where(
                SchedulingPolicy.status == FinancialPolicyStatus.ACTIVE,
                *_overlap_filters(SchedulingPolicy, policy),
            )
            .with_for_update()
        )
    )
    for item in previous:
        item.status = FinancialPolicyStatus.REPLACED
        item.updated_at = now
    if previous:
        await session.flush()
    return [item.id for item in previous]


@router.get("/cities/{city_id}/pricing-rules", response_model=PricingRuleListResponse)
async def list_pricing_rules(
    city_id: UUID,
    operator_id: UUID | None = Query(default=None),
    rule_status: PricingRuleStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE_TARIFFS)),
    session: AsyncSession = Depends(database_session),
) -> PricingRuleListResponse:
    await _city_or_404(session, principal, MANAGE_TARIFFS, city_id)
    filters = [
        PricingRule.city_id == city_id,
        PricingRule.operator_id.in_(principal.operator_ids_for(MANAGE_TARIFFS)),
    ]
    if operator_id is not None:
        if not _scope_allowed(
            principal,
            MANAGE_TARIFFS,
            city_id=city_id,
            operator_id=operator_id,
        ):
            raise HTTPException(status_code=404, detail="City/operator scope not found.")
        filters.append(PricingRule.operator_id == operator_id)
    if rule_status is not None:
        filters.append(PricingRule.status == rule_status)
    items = list(
        await session.scalars(
            select(PricingRule)
            .where(*filters)
            .order_by(PricingRule.created_at.desc(), PricingRule.id)
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    total = await session.scalar(
        select(func.count()).select_from(PricingRule).where(*filters)
    )
    return PricingRuleListResponse(
        items=[pricing_rule_response(item) for item in items],
        page=page,
        limit=limit,
        total=total or 0,
    )


@router.post(
    "/cities/{city_id}/pricing-rules",
    response_model=PricingRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_pricing_rule(
    city_id: UUID,
    payload: PricingRuleCreateRequest,
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE_TARIFFS)),
    session: AsyncSession = Depends(database_session),
) -> PricingRuleResponse:
    try:
        async with session.begin():
            city, market, _, _ = await _scope_context(
                session,
                principal,
                MANAGE_TARIFFS,
                city_id=city_id,
                operator_id=payload.operator_id,
                service_type=payload.service_type,
                require_current_assignment=False,
            )
            direction = None
            if payload.fixed_route_direction_id is not None:
                direction, direction_version, direction_route = (
                    await _direction_for_tariff_scope(
                        session,
                        direction_id=payload.fixed_route_direction_id,
                        city_id=city_id,
                        operator_id=payload.operator_id,
                        lock=True,
                    )
                )
                if payload.service_type != ServiceType.FIXED_ROUTE:
                    raise PricingPolicyConflict(
                        "Only a fixed-route tariff can reference a route direction."
                    )
                if (
                    direction_route.status != FixedRouteStatus.ACTIVE
                    or direction_version.status != FixedRoutePublicationStatus.DRAFT
                ):
                    raise PricingPolicyConflict(
                        "A tariff can be linked only while the route version is a draft."
                    )
                if direction.flat_fare_policy_version_id is not None:
                    raise PricingPolicyConflict(
                        "That fixed-route direction already has a tariff version."
                    )
            await _advisory_scope_lock(
                session,
                f"pricing-rule-version:{city_id}:{payload.operator_id}:"
                f"{payload.service_type.value}:{payload.booking_type.value}:"
                f"{payload.fixed_route_direction_id or 'unbound'}",
            )
            rule = PricingRule(
                city_id=city_id,
                operator_id=payload.operator_id,
                service_type=payload.service_type,
                booking_type=payload.booking_type,
                fixed_route_direction_id=payload.fixed_route_direction_id,
                name=payload.name,
                version=payload.version,
                model=payload.model,
                fixed_amount=payload.fixed_amount,
                currency=payload.currency,
                effective_from=payload.effective_from,
                effective_until=payload.effective_until,
                status=PricingRuleStatus.DRAFT,
                created_by_user_id=principal.user_id,
            )
            _validate_tariff(rule, market)
            session.add(rule)
            await session.flush()
            if direction is not None:
                direction.flat_fare_policy_version_id = rule.id
                await session.flush()
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="PRICING_RULE_CREATED",
                resource_type="pricing_rule",
                resource_id=rule.id,
                market_id=city.market_id,
                city_id=city.id,
                operator_id=rule.operator_id,
                changes={
                    "version": rule.version,
                    "status": rule.status.value,
                    "service_type": rule.service_type.value,
                    "booking_type": rule.booking_type.value,
                    "fixed_route_direction_id": (
                        str(rule.fixed_route_direction_id)
                        if rule.fixed_route_direction_id is not None
                        else None
                    ),
                    "fixed_amount": str(rule.fixed_amount),
                    "currency": rule.currency,
                },
            )
            await session.refresh(rule)
            response = pricing_rule_response(rule)
        return response
    except PricingPolicyConflict as error:
        raise _http_conflict(error) from error
    except IntegrityError as error:
        raise HTTPException(
            status_code=409,
            detail="That tariff version already exists in this scope.",
        ) from error


@router.get("/pricing-rules/{version_id}", response_model=PricingRuleResponse)
async def get_pricing_rule(
    version_id: UUID,
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE_TARIFFS)),
    session: AsyncSession = Depends(database_session),
) -> PricingRuleResponse:
    rule, _, _ = await _pricing_rule_or_404(session, principal, version_id)
    return pricing_rule_response(rule)


@router.patch("/pricing-rules/{version_id}", response_model=PricingRuleResponse)
async def update_pricing_rule(
    version_id: UUID,
    payload: PricingRuleUpdateRequest,
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE_TARIFFS)),
    session: AsyncSession = Depends(database_session),
) -> PricingRuleResponse:
    try:
        async with session.begin():
            rule, city, market = await _pricing_rule_or_404(
                session, principal, version_id, lock=True
            )
            if rule.status != PricingRuleStatus.DRAFT:
                raise PricingPolicyConflict("Only a draft tariff can be edited.")
            _require_expected_version(rule.optimistic_version, payload.expected_version)
            new_from = payload.effective_from or rule.effective_from
            new_until = (
                None
                if payload.clear_effective_until
                else payload.effective_until
                if payload.effective_until is not None
                else rule.effective_until
            )
            rule.name = payload.name if payload.name is not None else rule.name
            rule.fixed_amount = (
                payload.fixed_amount
                if payload.fixed_amount is not None
                else rule.fixed_amount
            )
            rule.currency = payload.currency or rule.currency
            rule.effective_from = new_from
            rule.effective_until = new_until
            _validate_tariff(rule, market)
            rule.optimistic_version += 1
            rule.updated_at = datetime.now(UTC)
            await session.flush()
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="PRICING_RULE_UPDATED",
                resource_type="pricing_rule",
                resource_id=rule.id,
                market_id=city.market_id,
                city_id=city.id,
                operator_id=rule.operator_id,
                changes={"optimistic_version": rule.optimistic_version},
            )
            response = pricing_rule_response(rule)
        return response
    except PricingPolicyConflict as error:
        raise _http_conflict(error) from error


async def _transition_pricing_rule(
    session: AsyncSession,
    principal: OperationsPrincipal,
    version_id: UUID,
    payload: PricingPolicyCommandRequest,
    target: PricingRuleStatus,
) -> PricingRule:
    rule, city, market = await _pricing_rule_or_404(
        session, principal, version_id, lock=True
    )
    if rule.status == target:
        return rule
    _require_expected_version(rule.optimistic_version, payload.expected_version)
    expected = {
        PricingRuleStatus.IN_REVIEW: PricingRuleStatus.DRAFT,
        PricingRuleStatus.ACTIVE: PricingRuleStatus.IN_REVIEW,
    }[target]
    if rule.status != expected:
        raise PricingPolicyConflict(
            f"Tariff cannot transition from {rule.status.value} to {target.value}."
        )
    await _scope_context(
        session,
        principal,
        MANAGE_TARIFFS,
        city_id=rule.city_id,
        operator_id=rule.operator_id,
        service_type=rule.service_type,
        require_current_assignment=target == PricingRuleStatus.ACTIVE,
    )
    _validate_tariff(rule, market)
    await _validate_tariff_direction_link(
        session,
        rule,
        require_link=target == PricingRuleStatus.ACTIVE,
    )
    now = datetime.now(UTC)
    replaced_ids: list[UUID] = []
    if target == PricingRuleStatus.ACTIVE:
        if not _effective_now(rule.effective_from, rule.effective_until):
            raise PricingPolicyConflict("Only a currently effective tariff can be activated.")
        await _advisory_scope_lock(
            session,
            f"pricing-rule-activation:{rule.city_id}:{rule.operator_id}:"
            f"{rule.service_type.value}:{rule.booking_type.value}:"
            f"{rule.fixed_route_direction_id or 'unbound'}",
        )
        replaced_ids = await _replace_overlapping_tariffs(session, rule, now)
        rule.activated_by_user_id = principal.user_id
        rule.activated_at = now
    else:
        rule.submitted_by_user_id = principal.user_id
        rule.submitted_at = now
    previous_status = rule.status
    rule.status = target
    rule.optimistic_version += 1
    rule.updated_at = now
    await session.flush()
    await audit(
        session,
        actor_user_id=principal.user_id,
        action=f"PRICING_RULE_{target.value}",
        resource_type="pricing_rule",
        resource_id=rule.id,
        market_id=city.market_id,
        city_id=city.id,
        operator_id=rule.operator_id,
        changes={
            "previous_status": previous_status.value,
            "current_status": target.value,
            "version": rule.version,
            "effective_from": rule.effective_from.isoformat(),
            "reason": payload.reason,
            "replaced_version_ids": [str(item) for item in replaced_ids],
            "optimistic_version": rule.optimistic_version,
        },
    )
    return rule


@router.post("/pricing-rules/{version_id}/submit", response_model=PricingRuleResponse)
async def submit_pricing_rule(
    version_id: UUID,
    payload: PricingPolicyCommandRequest,
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE_TARIFFS)),
    session: AsyncSession = Depends(database_session),
) -> PricingRuleResponse:
    try:
        async with session.begin():
            rule = await _transition_pricing_rule(
                session,
                principal,
                version_id,
                payload,
                PricingRuleStatus.IN_REVIEW,
            )
            response = pricing_rule_response(rule)
        return response
    except PricingPolicyConflict as error:
        raise _http_conflict(error) from error


@router.post("/pricing-rules/{version_id}/activate", response_model=PricingRuleResponse)
async def activate_pricing_rule(
    version_id: UUID,
    payload: PricingPolicyCommandRequest,
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE_TARIFFS)),
    session: AsyncSession = Depends(database_session),
) -> PricingRuleResponse:
    try:
        async with session.begin():
            rule = await _transition_pricing_rule(
                session,
                principal,
                version_id,
                payload,
                PricingRuleStatus.ACTIVE,
            )
            response = pricing_rule_response(rule)
        return response
    except PricingPolicyConflict as error:
        raise _http_conflict(error) from error
    except IntegrityError as error:
        raise HTTPException(
            status_code=409,
            detail="Another active tariff overlaps this city/operator/service scope.",
        ) from error


@router.get(
    "/cities/{city_id}/operator-fee-policies",
    response_model=OperatorFeePolicyListResponse,
)
async def list_operator_fee_policies(
    city_id: UUID,
    operator_id: UUID | None = Query(default=None),
    policy_status: FinancialPolicyStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE_FEES)),
    session: AsyncSession = Depends(database_session),
) -> OperatorFeePolicyListResponse:
    await _city_or_404(session, principal, MANAGE_FEES, city_id)
    filters = [
        OperatorFeePolicy.city_id == city_id,
        OperatorFeePolicy.operator_id.in_(principal.operator_ids_for(MANAGE_FEES)),
    ]
    if operator_id is not None:
        if not _scope_allowed(
            principal,
            MANAGE_FEES,
            city_id=city_id,
            operator_id=operator_id,
        ):
            raise HTTPException(status_code=404, detail="City/operator scope not found.")
        filters.append(OperatorFeePolicy.operator_id == operator_id)
    if policy_status is not None:
        filters.append(OperatorFeePolicy.status == policy_status)
    items = list(
        await session.scalars(
            select(OperatorFeePolicy)
            .where(*filters)
            .order_by(OperatorFeePolicy.created_at.desc(), OperatorFeePolicy.id)
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    total = await session.scalar(
        select(func.count()).select_from(OperatorFeePolicy).where(*filters)
    )
    return OperatorFeePolicyListResponse(
        items=[operator_fee_policy_response(item) for item in items],
        page=page,
        limit=limit,
        total=total or 0,
    )


@router.post(
    "/cities/{city_id}/operator-fee-policies",
    response_model=OperatorFeePolicyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_operator_fee_policy(
    city_id: UUID,
    payload: OperatorFeePolicyCreateRequest,
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE_FEES)),
    session: AsyncSession = Depends(database_session),
) -> OperatorFeePolicyResponse:
    try:
        async with session.begin():
            city, market, _, _ = await _scope_context(
                session,
                principal,
                MANAGE_FEES,
                city_id=city_id,
                operator_id=payload.operator_id,
                service_type=payload.service_type,
                require_current_assignment=False,
            )
            await _advisory_scope_lock(
                session,
                f"operator-fee-version:{city_id}:{payload.operator_id}:"
                f"{payload.service_type.value}",
            )
            policy = OperatorFeePolicy(
                city_id=city_id,
                operator_id=payload.operator_id,
                service_type=payload.service_type,
                version=payload.version,
                status=FinancialPolicyStatus.DRAFT,
                calculation_mode=payload.calculation_mode,
                funding_mode=payload.funding_mode,
                eligible_base_code=payload.eligible_base_code,
                percentage_rate=payload.percentage_rate,
                flat_amount=payload.flat_amount,
                currency=payload.currency,
                rounding_rule=payload.rounding_rule,
                minimum_driver_net=payload.minimum_driver_net,
                effective_from=payload.effective_from,
                effective_until=payload.effective_until,
                created_by_user_id=principal.user_id,
            )
            _validate_fee_policy(policy, market)
            session.add(policy)
            await session.flush()
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="OPERATOR_FEE_POLICY_CREATED",
                resource_type="operator_fee_policy",
                resource_id=policy.id,
                market_id=city.market_id,
                city_id=city.id,
                operator_id=policy.operator_id,
                changes={
                    "version": policy.version,
                    "status": policy.status.value,
                    "calculation_mode": policy.calculation_mode.value,
                    "funding_mode": policy.funding_mode.value,
                    "percentage_rate": (
                        str(policy.percentage_rate)
                        if policy.percentage_rate is not None
                        else None
                    ),
                    "flat_amount": (
                        str(policy.flat_amount) if policy.flat_amount is not None else None
                    ),
                    "currency": policy.currency,
                },
            )
            await session.refresh(policy)
            response = operator_fee_policy_response(policy)
        return response
    except PricingPolicyConflict as error:
        raise _http_conflict(error) from error
    except IntegrityError as error:
        raise HTTPException(
            status_code=409,
            detail="That operator-fee policy version already exists in this scope.",
        ) from error


@router.get(
    "/operator-fee-policies/{version_id}",
    response_model=OperatorFeePolicyResponse,
)
async def get_operator_fee_policy(
    version_id: UUID,
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE_FEES)),
    session: AsyncSession = Depends(database_session),
) -> OperatorFeePolicyResponse:
    policy, _, _ = await _fee_policy_or_404(session, principal, version_id)
    return operator_fee_policy_response(policy)


@router.patch(
    "/operator-fee-policies/{version_id}",
    response_model=OperatorFeePolicyResponse,
)
async def update_operator_fee_policy(
    version_id: UUID,
    payload: OperatorFeePolicyUpdateRequest,
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE_FEES)),
    session: AsyncSession = Depends(database_session),
) -> OperatorFeePolicyResponse:
    try:
        async with session.begin():
            policy, city, market = await _fee_policy_or_404(
                session, principal, version_id, lock=True
            )
            if policy.status != FinancialPolicyStatus.DRAFT:
                raise PricingPolicyConflict("Only a draft operator-fee policy can be edited.")
            _require_expected_version(policy.optimistic_version, payload.expected_version)
            fields = payload.model_fields_set
            if payload.calculation_mode is not None:
                policy.calculation_mode = payload.calculation_mode
                if (
                    payload.calculation_mode
                    == OperatorFeeCalculationMode.PERCENTAGE_OF_TRANSPORT_FARE
                ):
                    policy.flat_amount = None
                else:
                    policy.percentage_rate = None
            if payload.funding_mode is not None:
                policy.funding_mode = payload.funding_mode
            if "percentage_rate" in fields:
                policy.percentage_rate = payload.percentage_rate
            if "flat_amount" in fields:
                policy.flat_amount = payload.flat_amount
            if payload.currency is not None:
                policy.currency = payload.currency
            if payload.minimum_driver_net is not None:
                policy.minimum_driver_net = payload.minimum_driver_net
            policy.effective_from = payload.effective_from or policy.effective_from
            policy.effective_until = (
                None
                if payload.clear_effective_until
                else payload.effective_until
                if payload.effective_until is not None
                else policy.effective_until
            )
            _validate_fee_policy(policy, market)
            policy.optimistic_version += 1
            policy.updated_at = datetime.now(UTC)
            await session.flush()
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="OPERATOR_FEE_POLICY_UPDATED",
                resource_type="operator_fee_policy",
                resource_id=policy.id,
                market_id=city.market_id,
                city_id=city.id,
                operator_id=policy.operator_id,
                changes={"optimistic_version": policy.optimistic_version},
            )
            response = operator_fee_policy_response(policy)
        return response
    except PricingPolicyConflict as error:
        raise _http_conflict(error) from error


async def _transition_fee_policy(
    session: AsyncSession,
    principal: OperationsPrincipal,
    version_id: UUID,
    payload: PricingPolicyCommandRequest,
    target: FinancialPolicyStatus,
) -> OperatorFeePolicy:
    policy, city, market = await _fee_policy_or_404(
        session, principal, version_id, lock=True
    )
    if policy.status == target:
        return policy
    _require_expected_version(policy.optimistic_version, payload.expected_version)
    expected = {
        FinancialPolicyStatus.IN_REVIEW: FinancialPolicyStatus.DRAFT,
        FinancialPolicyStatus.ACTIVE: FinancialPolicyStatus.IN_REVIEW,
    }[target]
    if policy.status != expected:
        raise PricingPolicyConflict(
            f"Operator-fee policy cannot transition from {policy.status.value} "
            f"to {target.value}."
        )
    await _scope_context(
        session,
        principal,
        MANAGE_FEES,
        city_id=policy.city_id,
        operator_id=policy.operator_id,
        service_type=policy.service_type,
        require_current_assignment=target == FinancialPolicyStatus.ACTIVE,
    )
    _validate_fee_policy(policy, market)
    now = datetime.now(UTC)
    replaced_ids: list[UUID] = []
    if target == FinancialPolicyStatus.ACTIVE:
        if not _effective_now(policy.effective_from, policy.effective_until):
            raise PricingPolicyConflict(
                "Only a currently effective operator-fee policy can be activated."
            )
        await _advisory_scope_lock(
            session,
            f"operator-fee-activation:{policy.city_id}:{policy.operator_id}:"
            f"{policy.service_type.value}",
        )
        replaced_ids = await _replace_overlapping_fees(session, policy, now)
        policy.activated_by_user_id = principal.user_id
        policy.activated_at = now
    else:
        policy.submitted_by_user_id = principal.user_id
        policy.submitted_at = now
    previous_status = policy.status
    policy.status = target
    policy.optimistic_version += 1
    policy.updated_at = now
    await session.flush()
    await audit(
        session,
        actor_user_id=principal.user_id,
        action=f"OPERATOR_FEE_POLICY_{target.value}",
        resource_type="operator_fee_policy",
        resource_id=policy.id,
        market_id=city.market_id,
        city_id=city.id,
        operator_id=policy.operator_id,
        changes={
            "previous_status": previous_status.value,
            "current_status": target.value,
            "version": policy.version,
            "calculation_mode": policy.calculation_mode.value,
            "funding_mode": policy.funding_mode.value,
            "effective_from": policy.effective_from.isoformat(),
            "reason": payload.reason,
            "replaced_version_ids": [str(item) for item in replaced_ids],
            "optimistic_version": policy.optimistic_version,
        },
    )
    return policy


@router.post(
    "/operator-fee-policies/{version_id}/submit",
    response_model=OperatorFeePolicyResponse,
)
async def submit_operator_fee_policy(
    version_id: UUID,
    payload: PricingPolicyCommandRequest,
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE_FEES)),
    session: AsyncSession = Depends(database_session),
) -> OperatorFeePolicyResponse:
    try:
        async with session.begin():
            policy = await _transition_fee_policy(
                session,
                principal,
                version_id,
                payload,
                FinancialPolicyStatus.IN_REVIEW,
            )
            response = operator_fee_policy_response(policy)
        return response
    except PricingPolicyConflict as error:
        raise _http_conflict(error) from error


@router.post(
    "/operator-fee-policies/{version_id}/activate",
    response_model=OperatorFeePolicyResponse,
)
async def activate_operator_fee_policy(
    version_id: UUID,
    payload: PricingPolicyCommandRequest,
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE_FEES)),
    session: AsyncSession = Depends(database_session),
) -> OperatorFeePolicyResponse:
    try:
        async with session.begin():
            policy = await _transition_fee_policy(
                session,
                principal,
                version_id,
                payload,
                FinancialPolicyStatus.ACTIVE,
            )
            response = operator_fee_policy_response(policy)
        return response
    except PricingPolicyConflict as error:
        raise _http_conflict(error) from error
    except IntegrityError as error:
        raise HTTPException(
            status_code=409,
            detail="Another active operator-fee policy overlaps this scope.",
        ) from error


@router.get(
    "/cities/{city_id}/scheduling-policies",
    response_model=SchedulingPolicyListResponse,
)
async def list_scheduling_policies(
    city_id: UUID,
    operator_id: UUID | None = Query(default=None),
    policy_status: FinancialPolicyStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: OperationsPrincipal = Depends(
        require_operations_permission(MANAGE_SCHEDULING)
    ),
    session: AsyncSession = Depends(database_session),
) -> SchedulingPolicyListResponse:
    await _city_or_404(session, principal, MANAGE_SCHEDULING, city_id)
    filters = [
        SchedulingPolicy.city_id == city_id,
        SchedulingPolicy.operator_id.in_(
            principal.operator_ids_for(MANAGE_SCHEDULING)
        ),
    ]
    if operator_id is not None:
        if not _scope_allowed(
            principal,
            MANAGE_SCHEDULING,
            city_id=city_id,
            operator_id=operator_id,
        ):
            raise HTTPException(status_code=404, detail="City/operator scope not found.")
        filters.append(SchedulingPolicy.operator_id == operator_id)
    if policy_status is not None:
        filters.append(SchedulingPolicy.status == policy_status)
    items = list(
        await session.scalars(
            select(SchedulingPolicy)
            .where(*filters)
            .order_by(SchedulingPolicy.created_at.desc(), SchedulingPolicy.id)
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    total = await session.scalar(
        select(func.count()).select_from(SchedulingPolicy).where(*filters)
    )
    return SchedulingPolicyListResponse(
        items=[scheduling_policy_response(item) for item in items],
        page=page,
        limit=limit,
        total=total or 0,
    )


@router.post(
    "/cities/{city_id}/scheduling-policies",
    response_model=SchedulingPolicyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_scheduling_policy(
    city_id: UUID,
    payload: SchedulingPolicyCreateRequest,
    principal: OperationsPrincipal = Depends(
        require_operations_permission(MANAGE_SCHEDULING)
    ),
    session: AsyncSession = Depends(database_session),
) -> SchedulingPolicyResponse:
    try:
        async with session.begin():
            city, market, _, _ = await _scope_context(
                session,
                principal,
                MANAGE_SCHEDULING,
                city_id=city_id,
                operator_id=payload.operator_id,
                service_type=payload.service_type,
                require_current_assignment=False,
            )
            await _advisory_scope_lock(
                session,
                f"scheduling-policy-version:{city_id}:{payload.operator_id}:"
                f"{payload.service_type.value}",
            )
            policy = SchedulingPolicy(
                city_id=city_id,
                operator_id=payload.operator_id,
                service_type=payload.service_type,
                version=payload.version,
                status=FinancialPolicyStatus.DRAFT,
                surcharge_amount=payload.surcharge_amount,
                currency=payload.currency,
                beneficiary=payload.beneficiary,
                collection_timing_code=payload.collection_timing_code,
                minimum_lead_minutes=payload.minimum_lead_minutes,
                maximum_horizon_days=payload.maximum_horizon_days,
                offer_open_minutes_before=payload.offer_open_minutes_before,
                offer_response_seconds=payload.offer_response_seconds,
                commitment_deadline_minutes_before=payload.commitment_deadline_minutes_before,
                handoff_minutes_before=payload.handoff_minutes_before,
                protected_duration_minutes=payload.protected_duration_minutes,
                conflict_buffer_before_minutes=payload.conflict_buffer_before_minutes,
                conflict_buffer_after_minutes=payload.conflict_buffer_after_minutes,
                passenger_cancel_cutoff_minutes=payload.passenger_cancel_cutoff_minutes,
                driver_cancel_cutoff_minutes=payload.driver_cancel_cutoff_minutes,
                surcharge_refund_mode=payload.surcharge_refund_mode,
                fallback_matching_enabled=payload.fallback_matching_enabled,
                effective_from=payload.effective_from,
                effective_until=payload.effective_until,
                created_by_user_id=principal.user_id,
            )
            _validate_scheduling_policy(policy, market)
            session.add(policy)
            await session.flush()
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="SCHEDULING_POLICY_CREATED",
                resource_type="scheduling_policy",
                resource_id=policy.id,
                market_id=city.market_id,
                city_id=city.id,
                operator_id=policy.operator_id,
                changes={
                    "version": policy.version,
                    "status": policy.status.value,
                    "surcharge_amount": str(policy.surcharge_amount),
                    "currency": policy.currency,
                    "beneficiary": policy.beneficiary.value,
                    "collection_timing_code": policy.collection_timing_code,
                },
            )
            await session.refresh(policy)
            response = scheduling_policy_response(policy)
        return response
    except PricingPolicyConflict as error:
        raise _http_conflict(error) from error
    except IntegrityError as error:
        raise HTTPException(
            status_code=409,
            detail="That scheduling policy version already exists in this scope.",
        ) from error


@router.get(
    "/scheduling-policies/{version_id}",
    response_model=SchedulingPolicyResponse,
)
async def get_scheduling_policy(
    version_id: UUID,
    principal: OperationsPrincipal = Depends(
        require_operations_permission(MANAGE_SCHEDULING)
    ),
    session: AsyncSession = Depends(database_session),
) -> SchedulingPolicyResponse:
    policy, _, _ = await _scheduling_policy_or_404(session, principal, version_id)
    return scheduling_policy_response(policy)


@router.patch(
    "/scheduling-policies/{version_id}",
    response_model=SchedulingPolicyResponse,
)
async def update_scheduling_policy(
    version_id: UUID,
    payload: SchedulingPolicyUpdateRequest,
    principal: OperationsPrincipal = Depends(
        require_operations_permission(MANAGE_SCHEDULING)
    ),
    session: AsyncSession = Depends(database_session),
) -> SchedulingPolicyResponse:
    try:
        async with session.begin():
            policy, city, market = await _scheduling_policy_or_404(
                session, principal, version_id, lock=True
            )
            if policy.status != FinancialPolicyStatus.DRAFT:
                raise PricingPolicyConflict("Only a draft scheduling policy can be edited.")
            _require_expected_version(policy.optimistic_version, payload.expected_version)
            if payload.surcharge_amount is not None:
                policy.surcharge_amount = payload.surcharge_amount
            if payload.currency is not None:
                policy.currency = payload.currency
            if payload.beneficiary is not None:
                policy.beneficiary = payload.beneficiary
            for field in (
                "minimum_lead_minutes",
                "maximum_horizon_days",
                "offer_open_minutes_before",
                "offer_response_seconds",
                "commitment_deadline_minutes_before",
                "handoff_minutes_before",
                "protected_duration_minutes",
                "conflict_buffer_before_minutes",
                "conflict_buffer_after_minutes",
                "passenger_cancel_cutoff_minutes",
                "driver_cancel_cutoff_minutes",
                "surcharge_refund_mode",
                "fallback_matching_enabled",
            ):
                value = getattr(payload, field)
                if value is not None:
                    setattr(policy, field, value)
            policy.effective_from = payload.effective_from or policy.effective_from
            policy.effective_until = (
                None
                if payload.clear_effective_until
                else payload.effective_until
                if payload.effective_until is not None
                else policy.effective_until
            )
            _validate_scheduling_policy(policy, market)
            policy.optimistic_version += 1
            policy.updated_at = datetime.now(UTC)
            await session.flush()
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="SCHEDULING_POLICY_UPDATED",
                resource_type="scheduling_policy",
                resource_id=policy.id,
                market_id=city.market_id,
                city_id=city.id,
                operator_id=policy.operator_id,
                changes={"optimistic_version": policy.optimistic_version},
            )
            response = scheduling_policy_response(policy)
        return response
    except PricingPolicyConflict as error:
        raise _http_conflict(error) from error


async def _transition_scheduling_policy(
    session: AsyncSession,
    principal: OperationsPrincipal,
    version_id: UUID,
    payload: PricingPolicyCommandRequest,
    target: FinancialPolicyStatus,
) -> SchedulingPolicy:
    policy, city, market = await _scheduling_policy_or_404(
        session, principal, version_id, lock=True
    )
    if policy.status == target:
        return policy
    _require_expected_version(policy.optimistic_version, payload.expected_version)
    expected = {
        FinancialPolicyStatus.IN_REVIEW: FinancialPolicyStatus.DRAFT,
        FinancialPolicyStatus.ACTIVE: FinancialPolicyStatus.IN_REVIEW,
    }[target]
    if policy.status != expected:
        raise PricingPolicyConflict(
            f"Scheduling policy cannot transition from {policy.status.value} "
            f"to {target.value}."
        )
    await _scope_context(
        session,
        principal,
        MANAGE_SCHEDULING,
        city_id=policy.city_id,
        operator_id=policy.operator_id,
        service_type=policy.service_type,
        require_current_assignment=target == FinancialPolicyStatus.ACTIVE,
    )
    _validate_scheduling_policy(policy, market)
    now = datetime.now(UTC)
    replaced_ids: list[UUID] = []
    if target == FinancialPolicyStatus.ACTIVE:
        if not _effective_now(policy.effective_from, policy.effective_until):
            raise PricingPolicyConflict(
                "Only a currently effective scheduling policy can be activated."
            )
        await _advisory_scope_lock(
            session,
            f"scheduling-policy-activation:{policy.city_id}:{policy.operator_id}:"
            f"{policy.service_type.value}",
        )
        replaced_ids = await _replace_overlapping_scheduling(session, policy, now)
        policy.activated_by_user_id = principal.user_id
        policy.activated_at = now
    else:
        policy.submitted_by_user_id = principal.user_id
        policy.submitted_at = now
    previous_status = policy.status
    policy.status = target
    policy.optimistic_version += 1
    policy.updated_at = now
    await session.flush()
    await audit(
        session,
        actor_user_id=principal.user_id,
        action=f"SCHEDULING_POLICY_{target.value}",
        resource_type="scheduling_policy",
        resource_id=policy.id,
        market_id=city.market_id,
        city_id=city.id,
        operator_id=policy.operator_id,
        changes={
            "previous_status": previous_status.value,
            "current_status": target.value,
            "version": policy.version,
            "beneficiary": policy.beneficiary.value,
            "effective_from": policy.effective_from.isoformat(),
            "reason": payload.reason,
            "replaced_version_ids": [str(item) for item in replaced_ids],
            "optimistic_version": policy.optimistic_version,
        },
    )
    return policy


@router.post(
    "/scheduling-policies/{version_id}/submit",
    response_model=SchedulingPolicyResponse,
)
async def submit_scheduling_policy(
    version_id: UUID,
    payload: PricingPolicyCommandRequest,
    principal: OperationsPrincipal = Depends(
        require_operations_permission(MANAGE_SCHEDULING)
    ),
    session: AsyncSession = Depends(database_session),
) -> SchedulingPolicyResponse:
    try:
        async with session.begin():
            policy = await _transition_scheduling_policy(
                session,
                principal,
                version_id,
                payload,
                FinancialPolicyStatus.IN_REVIEW,
            )
            response = scheduling_policy_response(policy)
        return response
    except PricingPolicyConflict as error:
        raise _http_conflict(error) from error


@router.post(
    "/scheduling-policies/{version_id}/activate",
    response_model=SchedulingPolicyResponse,
)
async def activate_scheduling_policy(
    version_id: UUID,
    payload: PricingPolicyCommandRequest,
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(
        require_operations_permission(MANAGE_SCHEDULING)
    ),
    session: AsyncSession = Depends(database_session),
) -> SchedulingPolicyResponse:
    try:
        async with session.begin():
            policy = await _transition_scheduling_policy(
                session,
                principal,
                version_id,
                payload,
                FinancialPolicyStatus.ACTIVE,
            )
            response = scheduling_policy_response(policy)
        return response
    except PricingPolicyConflict as error:
        raise _http_conflict(error) from error
    except IntegrityError as error:
        raise HTTPException(
            status_code=409,
            detail="Another active scheduling policy overlaps this scope.",
        ) from error
