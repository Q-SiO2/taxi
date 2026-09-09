"""Control-plane invariants and data-plane city resolution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from geoalchemy2.elements import WKTElement
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.markets.constants import (
    PILOT_ENTRY_CITY_READINESS_GATES,
    PUBLIC_ACTIVATION_CITY_READINESS_GATES,
    REQUIRED_CITY_READINESS_GATES,
)
from taximobile_api.domains.driver_applications.models import (
    DriverRequirementVersion,
    RequirementVersionStatus,
)
from taximobile_api.domains.fixed_routes.models import (
    CityConfigurationRoute,
    FixedRoute,
    FixedRouteDirection,
    FixedRoutePublicationStatus,
    FixedRouteStatus,
    FixedRouteVersion,
)
from taximobile_api.domains.markets.models import (
    AssignmentStatus,
    City,
    CityConfigurationService,
    CityConfigurationVersion,
    CityLifecycleStatus,
    CityReadinessCheck,
    CityServiceAreaVersion,
    ConfigurationStatus,
    Market,
    MarketStatus,
    Operator,
    OperatorCityAssignment,
    OperatorStatus,
    ReadinessStatus,
    ServiceAreaStatus,
    ServiceType,
)
from taximobile_api.domains.pricing.models import (
    BookingType,
    FinancialPolicyStatus,
    OperatorFeePolicy,
    PricingRule,
    PricingRuleStatus,
    SchedulingPolicy,
)
from taximobile_api.domains.pricing.service import (
    InvalidFinancialPolicy,
    calculate_financial_quote,
)


class ControlPlaneConflict(ValueError):
    pass


class OptimisticVersionConflict(ControlPlaneConflict):
    pass


class CityServiceUnavailable(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ResolvedServiceContext:
    city_id: UUID
    operator_id: UUID
    operator_assignment_id: UUID
    tariff_version_id: UUID | None
    operator_fee_policy_version_id: UUID | None
    scheduling_policy_version_id: UUID | None


CITY_LIFECYCLE_TRANSITIONS: dict[CityLifecycleStatus, frozenset[CityLifecycleStatus]] = {
    CityLifecycleStatus.DRAFT: frozenset({CityLifecycleStatus.CONFIGURING}),
    CityLifecycleStatus.CONFIGURING: frozenset({CityLifecycleStatus.PILOT}),
    CityLifecycleStatus.PILOT: frozenset({CityLifecycleStatus.ACTIVE}),
    CityLifecycleStatus.ACTIVE: frozenset(
        {CityLifecycleStatus.PAUSED, CityLifecycleStatus.RETIRED}
    ),
    CityLifecycleStatus.PAUSED: frozenset(
        {CityLifecycleStatus.ACTIVE, CityLifecycleStatus.RETIRED}
    ),
}


async def resolve_on_demand_service_context(
    database_session: AsyncSession,
    *,
    pickup_latitude: float,
    pickup_longitude: float,
    city_hint: UUID | None,
    at: datetime | None = None,
) -> ResolvedServiceContext:
    """Resolve one authoritative city/operator from the active pickup boundary."""

    applicable_at = at or datetime.now(UTC)
    pickup = WKTElement(f"POINT({pickup_longitude} {pickup_latitude})", srid=4326)
    statement = (
        select(
            City.id,
            OperatorCityAssignment.operator_id,
            OperatorCityAssignment.id,
            CityConfigurationService.tariff_version_id,
            CityConfigurationService.operator_fee_policy_version_id,
            CityConfigurationService.scheduling_policy_version_id,
        )
        .join(
            CityConfigurationVersion,
            CityConfigurationVersion.id == City.active_configuration_version_id,
        )
        .join(
            CityServiceAreaVersion,
            CityServiceAreaVersion.id == CityConfigurationVersion.service_area_version_id,
        )
        .join(
            CityConfigurationService,
            CityConfigurationService.configuration_version_id == CityConfigurationVersion.id,
        )
        .join(
            OperatorCityAssignment,
            OperatorCityAssignment.id == CityConfigurationService.operator_city_assignment_id,
        )
        .where(
            City.lifecycle_status.in_({CityLifecycleStatus.PILOT, CityLifecycleStatus.ACTIVE}),
            CityConfigurationVersion.status == ConfigurationStatus.ACTIVE,
            CityConfigurationService.service_type == ServiceType.ON_DEMAND,
            CityConfigurationService.enabled.is_(True),
            CityServiceAreaVersion.status == ServiceAreaStatus.ACTIVE,
            CityServiceAreaVersion.effective_from <= applicable_at,
            or_(
                CityServiceAreaVersion.effective_until.is_(None),
                CityServiceAreaVersion.effective_until > applicable_at,
            ),
            OperatorCityAssignment.status == AssignmentStatus.ACTIVE,
            OperatorCityAssignment.service_type == ServiceType.ON_DEMAND,
            OperatorCityAssignment.effective_from <= applicable_at,
            or_(
                OperatorCityAssignment.effective_until.is_(None),
                OperatorCityAssignment.effective_until > applicable_at,
            ),
            func.ST_Covers(CityServiceAreaVersion.boundary, pickup),
        )
        .order_by(City.id)
        .limit(2)
    )
    if city_hint is not None:
        statement = statement.where(City.id == city_hint)
    rows = (await database_session.execute(statement)).all()
    if not rows:
        raise CityServiceUnavailable("The pickup is outside an available city service area.")
    if len(rows) != 1:
        # Overlapping active boundaries are an operational configuration error,
        # never a reason to choose an arbitrary tariff/operator.
        raise CityServiceUnavailable("The pickup does not resolve to one unambiguous city service.")
    (
        city_id,
        operator_id,
        assignment_id,
        tariff_version_id,
        operator_fee_policy_version_id,
        scheduling_policy_version_id,
    ) = rows[0]
    return ResolvedServiceContext(
        city_id=city_id,
        operator_id=operator_id,
        operator_assignment_id=assignment_id,
        tariff_version_id=tariff_version_id,
        operator_fee_policy_version_id=operator_fee_policy_version_id,
        scheduling_policy_version_id=scheduling_policy_version_id,
    )


async def ensure_assignment_does_not_overlap(
    database_session: AsyncSession,
    *,
    city_id: UUID,
    service_type: ServiceType,
    effective_from: datetime,
    effective_until: datetime | None,
    excluding_assignment_id: UUID | None = None,
) -> None:
    """Serialize one city/service authority range before the DB exclusion check."""

    scope = f"operator-assignment:{city_id}:{service_type.value}"
    await database_session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))"),
        {"scope": scope},
    )
    filters = [
        OperatorCityAssignment.city_id == city_id,
        OperatorCityAssignment.service_type == service_type,
        OperatorCityAssignment.status == AssignmentStatus.ACTIVE,
        or_(
            OperatorCityAssignment.effective_until.is_(None),
            OperatorCityAssignment.effective_until > effective_from,
        ),
    ]
    if effective_until is not None:
        filters.append(OperatorCityAssignment.effective_from < effective_until)
    if excluding_assignment_id is not None:
        filters.append(OperatorCityAssignment.id != excluding_assignment_id)
    conflict = await database_session.scalar(select(OperatorCityAssignment.id).where(*filters).limit(1))
    if conflict is not None:
        raise ControlPlaneConflict(
            "An active operator assignment already covers that city, service, and time range."
        )


async def validate_configuration_components(
    database_session: AsyncSession,
    configuration: CityConfigurationVersion,
    *,
    require_live_components: bool = False,
) -> None:
    now = datetime.now(UTC)
    city = await database_session.get(City, configuration.city_id)
    market = await database_session.get(Market, city.market_id) if city is not None else None
    if city is None or market is None:
        raise ControlPlaneConflict("The configuration city and market must exist.")
    if require_live_components and market.status != MarketStatus.ACTIVE:
        raise ControlPlaneConflict("An active configuration requires an active market.")
    area = await database_session.get(CityServiceAreaVersion, configuration.service_area_version_id)
    if (
        area is None
        or area.city_id != configuration.city_id
        or area.status not in {ServiceAreaStatus.APPROVED, ServiceAreaStatus.ACTIVE}
    ):
        raise ControlPlaneConflict(
            "The configuration must reference an approved service area from the same city."
        )
    if require_live_components and (
        area.effective_from > now
        or (area.effective_until is not None and area.effective_until <= now)
    ):
        raise ControlPlaneConflict("The service area must be effective when the configuration activates.")
    requirements = (
        await database_session.get(
            DriverRequirementVersion,
            configuration.driver_requirement_version_id,
        )
        if configuration.driver_requirement_version_id is not None
        else None
    )
    if requirements is not None and requirements.city_id != configuration.city_id:
        raise ControlPlaneConflict(
            "The driver requirement version must belong to the configuration city."
        )
    if require_live_components and not city.is_legacy_compatibility and requirements is None:
        raise ControlPlaneConflict(
            "A non-legacy city configuration requires an explicit driver requirement version."
        )
    if require_live_components and requirements is not None:
        if requirements.status != RequirementVersionStatus.ACTIVE:
            raise ControlPlaneConflict(
                "Driver requirements must be active when the configuration activates."
            )
        if requirements.effective_from > now or (
            requirements.effective_until is not None
            and requirements.effective_until <= now
        ):
            raise ControlPlaneConflict(
                "Driver requirements must be effective when the configuration activates."
            )
    services = list(
        await database_session.scalars(
            select(CityConfigurationService).where(
                CityConfigurationService.configuration_version_id == configuration.id,
                CityConfigurationService.enabled.is_(True),
            )
        )
    )
    if not services:
        raise ControlPlaneConflict("A configuration must enable at least one city service.")
    seen: set[ServiceType] = set()
    for service in services:
        if service.service_type in seen:
            raise ControlPlaneConflict("A configuration cannot duplicate a service type.")
        seen.add(service.service_type)
        assignment = await database_session.get(
            OperatorCityAssignment,
            service.operator_city_assignment_id,
        )
        if (
            assignment is None
            or assignment.city_id != configuration.city_id
            or assignment.service_type != service.service_type
            or assignment.status != AssignmentStatus.ACTIVE
        ):
            raise ControlPlaneConflict(
                "Every enabled service must reference an active same-city operator assignment."
            )
        operator = await database_session.get(Operator, assignment.operator_id)
        if operator is None or operator.market_id != city.market_id:
            raise ControlPlaneConflict("Every enabled service must reference a same-market operator.")
        if require_live_components and (
            operator.status != OperatorStatus.ACTIVE
            or assignment.effective_from > now
            or (assignment.effective_until is not None and assignment.effective_until <= now)
        ):
            raise ControlPlaneConflict(
                "Every enabled service requires an active operator assignment effective at activation."
            )
        # Local import avoids making the market model module depend on the
        # payment domain while still validating the coherent bundle boundary.
        from taximobile_api.domains.payments.models import (
            PaymentCapabilityStatus,
            PaymentCapabilityVersion,
            PaymentRecipientAccount,
            PaymentRecipientStatus,
        )

        capability = (
            await database_session.get(
                PaymentCapabilityVersion,
                service.payment_capability_version_id,
            )
            if service.payment_capability_version_id is not None
            else None
        )
        if capability is not None and (
            capability.city_id != configuration.city_id
            or capability.operator_id != assignment.operator_id
            or capability.service_type != service.service_type
        ):
            raise ControlPlaneConflict(
                "The payment capability must match the configuration city, operator, and service."
            )
        if require_live_components and not city.is_legacy_compatibility and capability is None:
            raise ControlPlaneConflict(
                "A non-legacy enabled service requires an explicit payment capability version."
            )
        if require_live_components and capability is not None:
            if (
                capability.status != PaymentCapabilityStatus.ACTIVE
                or capability.effective_from > now
                or (
                    capability.effective_until is not None
                    and capability.effective_until <= now
                )
            ):
                raise ControlPlaneConflict(
                    "The payment capability must be active and effective when the configuration activates."
                )
            if capability.manual_transfer_enabled:
                recipient = await database_session.get(
                    PaymentRecipientAccount,
                    capability.recipient_account_id,
                )
                if (
                    recipient is None
                    or recipient.status != PaymentRecipientStatus.VERIFIED
                    or recipient.city_id != capability.city_id
                    or recipient.operator_id != capability.operator_id
                ):
                    raise ControlPlaneConflict(
                        "Manual transfer requires a verified recipient in the same city/operator scope."
                    )
        if service.service_type == ServiceType.SCHEDULED:
            raise ControlPlaneConflict(
                f"{service.service_type.value} cannot enter a coherent bundle before its owning roadmap phase is implemented."
            )
        if service.service_type == ServiceType.ON_DEMAND:
            if service.tariff_version_id is None:
                raise ControlPlaneConflict("On-demand service requires an explicit city tariff.")
            tariff = await database_session.get(PricingRule, service.tariff_version_id)
            if (
                tariff is None
                or tariff.city_id != configuration.city_id
                or tariff.operator_id != assignment.operator_id
                or tariff.service_type != service.service_type
                or tariff.booking_type != BookingType.IMMEDIATE
            ):
                raise ControlPlaneConflict(
                    "The on-demand tariff must match the configuration city, operator, and service."
                )
            if require_live_components and (
                tariff.status != PricingRuleStatus.ACTIVE
                or tariff.effective_from > now
                or (tariff.effective_until is not None and tariff.effective_until <= now)
            ):
                raise ControlPlaneConflict(
                    "The on-demand tariff must be active and effective when the configuration activates."
                )
            if require_live_components and tariff.currency != market.default_currency:
                raise ControlPlaneConflict(
                    "The on-demand tariff currency must match the configuration market currency."
                )
            if service.operator_fee_policy_version_id is None:
                raise ControlPlaneConflict(
                    "On-demand service requires an explicit operator-fee policy, including zero fee."
                )
            fee_policy = await database_session.get(
                OperatorFeePolicy,
                service.operator_fee_policy_version_id,
            )
            if (
                fee_policy is None
                or fee_policy.city_id != configuration.city_id
                or fee_policy.operator_id != assignment.operator_id
                or fee_policy.service_type != service.service_type
            ):
                raise ControlPlaneConflict(
                    "The operator-fee policy must match the configuration city, operator, and service."
                )
            if require_live_components and (
                fee_policy.status != FinancialPolicyStatus.ACTIVE
                or fee_policy.effective_from > now
                or (fee_policy.effective_until is not None and fee_policy.effective_until <= now)
            ):
                raise ControlPlaneConflict(
                    "The operator-fee policy must be active and effective when the configuration activates."
                )
            if require_live_components and fee_policy.currency != market.default_currency:
                raise ControlPlaneConflict(
                    "The operator-fee policy currency must match the configuration market currency."
                )
            try:
                calculate_financial_quote(
                    tariff,
                    fee_policy,
                    booking_type=BookingType.IMMEDIATE,
                )
            except InvalidFinancialPolicy as error:
                raise ControlPlaneConflict(
                    f"The tariff and operator-fee policy do not form a valid quote: {error}"
                ) from error
            if service.scheduling_policy_version_id is not None:
                scheduling_policy = await database_session.get(
                    SchedulingPolicy,
                    service.scheduling_policy_version_id,
                )
                if (
                    scheduling_policy is None
                    or scheduling_policy.city_id != configuration.city_id
                    or scheduling_policy.operator_id != assignment.operator_id
                    or scheduling_policy.service_type != service.service_type
                ):
                    raise ControlPlaneConflict(
                        "The scheduling policy must match the configuration city, operator, and service."
                    )
                if require_live_components and (
                    scheduling_policy.status != FinancialPolicyStatus.ACTIVE
                    or scheduling_policy.effective_from > now
                    or (
                        scheduling_policy.effective_until is not None
                        and scheduling_policy.effective_until <= now
                    )
                    or scheduling_policy.currency != market.default_currency
                ):
                    raise ControlPlaneConflict(
                        "The scheduling policy must be active, effective, and currency-compatible at activation."
                    )
                try:
                    calculate_financial_quote(
                        tariff,
                        fee_policy,
                        booking_type=BookingType.SCHEDULED,
                        scheduling_policy=scheduling_policy,
                    )
                except InvalidFinancialPolicy as error:
                    raise ControlPlaneConflict(
                        "The tariff, fee, and scheduling policies do not form a valid "
                        f"scheduled quote: {error}"
                    ) from error
        elif service.service_type == ServiceType.FIXED_ROUTE:
            if service.tariff_version_id is not None:
                raise ControlPlaneConflict(
                    "Fixed-route service stores its flat tariff on each immutable direction."
                )
            fixed_route_scheduling_policy = (
                await database_session.get(
                    SchedulingPolicy, service.scheduling_policy_version_id
                )
                if service.scheduling_policy_version_id is not None
                else None
            )
            if fixed_route_scheduling_policy is not None and (
                fixed_route_scheduling_policy.city_id != configuration.city_id
                or fixed_route_scheduling_policy.operator_id != assignment.operator_id
                or fixed_route_scheduling_policy.service_type != ServiceType.FIXED_ROUTE
            ):
                raise ControlPlaneConflict(
                    "The fixed-route scheduling policy must match the configuration scope."
                )
            if require_live_components and fixed_route_scheduling_policy is not None and (
                fixed_route_scheduling_policy.status != FinancialPolicyStatus.ACTIVE
                or fixed_route_scheduling_policy.effective_from > now
                or (
                    fixed_route_scheduling_policy.effective_until is not None
                    and fixed_route_scheduling_policy.effective_until <= now
                )
                or fixed_route_scheduling_policy.currency != market.default_currency
            ):
                raise ControlPlaneConflict(
                    "The fixed-route scheduling policy must be active, effective, and currency-compatible."
                )
            if service.operator_fee_policy_version_id is None:
                raise ControlPlaneConflict(
                    "Fixed-route service requires an explicit operator-fee policy, including zero fee."
                )
            fee_policy = await database_session.get(
                OperatorFeePolicy,
                service.operator_fee_policy_version_id,
            )
            if (
                fee_policy is None
                or fee_policy.city_id != configuration.city_id
                or fee_policy.operator_id != assignment.operator_id
                or fee_policy.service_type != ServiceType.FIXED_ROUTE
            ):
                raise ControlPlaneConflict(
                    "The fixed-route operator-fee policy must match the configuration scope."
                )
            if require_live_components and (
                fee_policy.status != FinancialPolicyStatus.ACTIVE
                or fee_policy.effective_from > now
                or (
                    fee_policy.effective_until is not None
                    and fee_policy.effective_until <= now
                )
                or fee_policy.currency != market.default_currency
            ):
                raise ControlPlaneConflict(
                    "The fixed-route operator-fee policy must be active, effective, and currency-compatible."
                )
            configured_routes = list(
                await database_session.scalars(
                    select(CityConfigurationRoute).where(
                        CityConfigurationRoute.configuration_version_id
                        == configuration.id
                    )
                )
            )
            if not configured_routes:
                raise ControlPlaneConflict(
                    "Fixed-route service requires at least one reviewed route version."
                )
            for configured_route in configured_routes:
                if not configured_route.immediate_booking_enabled:
                    raise ControlPlaneConflict(
                        "A configured fixed route must retain immediate booking."
                    )
                if (
                    configured_route.scheduled_booking_enabled
                    and fixed_route_scheduling_policy is None
                ):
                    raise ControlPlaneConflict(
                        "Scheduled fixed-route booking requires an explicit scheduling policy."
                    )
                route_version = await database_session.get(
                    FixedRouteVersion,
                    configured_route.fixed_route_version_id,
                )
                route = (
                    await database_session.get(FixedRoute, route_version.fixed_route_id)
                    if route_version is not None
                    else None
                )
                if (
                    route_version is None
                    or route is None
                    or route.city_id != configuration.city_id
                    or route.operator_id != assignment.operator_id
                    or route.status != FixedRouteStatus.ACTIVE
                ):
                    raise ControlPlaneConflict(
                        "Every configured route must match the fixed-route service scope."
                    )
                if require_live_components and (
                    route_version.status != FixedRoutePublicationStatus.PUBLISHED
                    or route_version.effective_from > now
                    or (
                        route_version.effective_until is not None
                        and route_version.effective_until <= now
                    )
                ):
                    raise ControlPlaneConflict(
                        "Every configured route must be published and effective at activation."
                    )
                directions = list(
                    await database_session.scalars(
                        select(FixedRouteDirection).where(
                            FixedRouteDirection.route_version_id == route_version.id
                        )
                    )
                )
                if not directions:
                    raise ControlPlaneConflict(
                        "Every configured route version requires a direction."
                    )
                for direction in directions:
                    tariff = await database_session.get(
                        PricingRule,
                        direction.flat_fare_policy_version_id,
                    )
                    if (
                        tariff is None
                        or tariff.city_id != configuration.city_id
                        or tariff.operator_id != assignment.operator_id
                        or tariff.service_type != ServiceType.FIXED_ROUTE
                        or tariff.booking_type != BookingType.IMMEDIATE
                    ):
                        raise ControlPlaneConflict(
                            "Every route direction requires a same-scope immediate fixed tariff."
                        )
                    if require_live_components and (
                        tariff.status != PricingRuleStatus.ACTIVE
                        or tariff.effective_from > now
                        or (
                            tariff.effective_until is not None
                            and tariff.effective_until <= now
                        )
                        or tariff.currency != market.default_currency
                    ):
                        raise ControlPlaneConflict(
                            "Every route direction tariff must be active, effective, and currency-compatible."
                        )
                    try:
                        calculate_financial_quote(
                            tariff,
                            fee_policy,
                            booking_type=BookingType.IMMEDIATE,
                        )
                    except InvalidFinancialPolicy as error:
                        raise ControlPlaneConflict(
                            f"The fixed-route tariff and fee policy do not form a valid quote: {error}"
                        ) from error
                    if configured_route.scheduled_booking_enabled:
                        try:
                            calculate_financial_quote(
                                tariff,
                                fee_policy,
                                booking_type=BookingType.SCHEDULED,
                                scheduling_policy=fixed_route_scheduling_policy,
                            )
                        except InvalidFinancialPolicy as error:
                            raise ControlPlaneConflict(
                                "The fixed-route tariff, fee, and scheduling policy do not "
                                f"form a valid quote: {error}"
                            ) from error


async def missing_readiness_gates(
    database_session: AsyncSession,
    configuration_id: UUID,
    required_gates: frozenset[str] = REQUIRED_CITY_READINESS_GATES,
) -> list[str]:
    passed = set(
        await database_session.scalars(
            select(CityReadinessCheck.gate_code).where(
                CityReadinessCheck.configuration_version_id == configuration_id,
                CityReadinessCheck.status == ReadinessStatus.PASSED,
            )
        )
    )
    return sorted(required_gates - passed)


async def validate_city_lifecycle_transition(
    database_session: AsyncSession,
    city: City,
    target: CityLifecycleStatus,
) -> None:
    if target not in CITY_LIFECYCLE_TRANSITIONS.get(city.lifecycle_status, frozenset()):
        raise ControlPlaneConflict(
            f"City cannot transition from {city.lifecycle_status.value} to {target.value}."
        )
    if target not in {CityLifecycleStatus.PILOT, CityLifecycleStatus.ACTIVE}:
        return
    if city.active_configuration_version_id is None:
        raise ControlPlaneConflict("City requires an active coherent configuration.")
    configuration = await database_session.get(
        CityConfigurationVersion,
        city.active_configuration_version_id,
    )
    if configuration is None or configuration.status != ConfigurationStatus.ACTIVE:
        raise ControlPlaneConflict("City requires an active coherent configuration.")
    if (
        city.is_legacy_compatibility
        and city.lifecycle_status == CityLifecycleStatus.PAUSED
        and target == CityLifecycleStatus.ACTIVE
    ):
        # The migration preserves the proven pre-national pilot without
        # fabricating later policy/readiness evidence.  This exception applies
        # only to the immutable compatibility city and cannot activate a second
        # city or a new configuration bundle.
        return
    await validate_configuration_components(database_session, configuration)
    required_gates = (
        PILOT_ENTRY_CITY_READINESS_GATES
        if target == CityLifecycleStatus.PILOT
        else PUBLIC_ACTIVATION_CITY_READINESS_GATES
    )
    missing = await missing_readiness_gates(
        database_session,
        configuration.id,
        required_gates,
    )
    if missing:
        raise ControlPlaneConflict(
            f"City {target.value} readiness gates are incomplete: " + ", ".join(missing)
        )


def require_expected_version(actual: int, expected: int) -> None:
    if actual != expected:
        raise OptimisticVersionConflict(
            f"The resource changed; expected version {expected}, current version {actual}."
        )


async def same_market_operator_and_city(
    database_session: AsyncSession,
    operator_id: UUID,
    city_id: UUID,
) -> tuple[Operator, City]:
    operator = await database_session.get(Operator, operator_id)
    city = await database_session.get(City, city_id)
    if operator is None or city is None:
        raise ControlPlaneConflict("Operator or city does not exist.")
    if operator.market_id != city.market_id:
        raise ControlPlaneConflict("Operator and city must belong to the same market.")
    return operator, city
