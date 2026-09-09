"""Deterministic tariff and operator-economics selection/calculation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.markets.constants import (
    LEGACY_CITY_ID,
    LEGACY_OPERATOR_ID,
    LEGACY_ZERO_OPERATOR_FEE_POLICY_ID,
)
from taximobile_api.domains.markets.models import ServiceType
from taximobile_api.domains.pricing.models import (
    BookingType,
    FareRecord,
    FinancialPolicyStatus,
    OperatorFeeCalculationMode,
    OperatorFeeFundingMode,
    OperatorFeePolicy,
    PricingModel,
    PricingRoundingRule,
    PricingRule,
    PricingRuleStatus,
    RideFinancialSnapshot,
    SchedulingPolicy,
    SchedulingSurchargeBeneficiary,
)


MONEY_QUANTUM = Decimal("0.01")


class NoActiveTariff(ValueError):
    pass


class InvalidFinancialPolicy(ValueError):
    pass


def money(value: Decimal | str) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def fixed_fare_amount(rule: PricingRule) -> Decimal:
    if rule.model != PricingModel.FIXED or rule.fixed_amount is None or rule.fixed_amount < 0:
        raise NoActiveTariff("No supported fixed tariff is active for this ride.")
    return money(rule.fixed_amount)


@dataclass(frozen=True, slots=True)
class FinancialQuote:
    pricing_rule_id: UUID
    pricing_rule_version: str
    operator_fee_policy_id: UUID
    operator_fee_policy_version: str
    scheduling_policy_id: UUID | None
    scheduling_policy_version: str | None
    booking_type: BookingType
    operator_fee_calculation_mode: OperatorFeeCalculationMode
    operator_fee_funding_mode: OperatorFeeFundingMode
    scheduling_surcharge_beneficiary: SchedulingSurchargeBeneficiary | None
    transport_fare_amount: Decimal
    scheduling_surcharge_amount: Decimal
    operator_fee_amount: Decimal
    passenger_total_amount: Decimal
    driver_gross_amount: Decimal
    driver_fee_deduction_amount: Decimal
    driver_net_amount: Decimal
    operator_allocation_amount: Decimal
    currency: str
    policy_snapshot: dict[str, str | None]

    def ride_snapshot(self, ride_id: UUID) -> RideFinancialSnapshot:
        return RideFinancialSnapshot(
            ride_id=ride_id,
            pricing_rule_id=self.pricing_rule_id,
            operator_fee_policy_id=self.operator_fee_policy_id,
            scheduling_policy_id=self.scheduling_policy_id,
            booking_type=self.booking_type,
            operator_fee_calculation_mode=self.operator_fee_calculation_mode,
            operator_fee_funding_mode=self.operator_fee_funding_mode,
            scheduling_surcharge_beneficiary=self.scheduling_surcharge_beneficiary,
            transport_fare_amount=self.transport_fare_amount,
            scheduling_surcharge_amount=self.scheduling_surcharge_amount,
            operator_fee_amount=self.operator_fee_amount,
            passenger_total_amount=self.passenger_total_amount,
            driver_gross_amount=self.driver_gross_amount,
            driver_fee_deduction_amount=self.driver_fee_deduction_amount,
            driver_net_amount=self.driver_net_amount,
            operator_allocation_amount=self.operator_allocation_amount,
            currency=self.currency,
            snapshot=self.policy_snapshot,
        )


def calculate_financial_quote(
    rule: PricingRule,
    fee_policy: OperatorFeePolicy,
    *,
    booking_type: BookingType,
    scheduling_policy: SchedulingPolicy | None = None,
) -> FinancialQuote:
    """Calculate every passenger/driver/operator component with exact arithmetic."""

    transport_fare = fixed_fare_amount(rule)
    if rule.currency != fee_policy.currency:
        raise InvalidFinancialPolicy("Tariff and operator-fee currencies do not match.")
    if fee_policy.eligible_base_code != "TRANSPORT_FARE":
        raise InvalidFinancialPolicy("The operator-fee calculation base is not supported.")
    if fee_policy.rounding_rule != PricingRoundingRule.HALF_UP_0_01:
        raise InvalidFinancialPolicy("The operator-fee rounding rule is not supported.")

    if fee_policy.calculation_mode == OperatorFeeCalculationMode.PERCENTAGE_OF_TRANSPORT_FARE:
        if (
            fee_policy.percentage_rate is None
            or fee_policy.percentage_rate < 0
            or fee_policy.percentage_rate >= 100
            or fee_policy.flat_amount is not None
        ):
            raise InvalidFinancialPolicy("The percentage operator-fee policy is invalid.")
        operator_fee = money(transport_fare * fee_policy.percentage_rate / Decimal("100"))
    elif fee_policy.calculation_mode == OperatorFeeCalculationMode.FLAT_PER_COMPLETED_BOOKING:
        if fee_policy.flat_amount is None or fee_policy.flat_amount < 0 or fee_policy.percentage_rate is not None:
            raise InvalidFinancialPolicy("The flat operator-fee policy is invalid.")
        operator_fee = money(fee_policy.flat_amount)
    else:  # pragma: no cover - database enum validation is the final arbiter.
        raise InvalidFinancialPolicy("The operator-fee calculation mode is not supported.")

    if booking_type == BookingType.IMMEDIATE:
        if scheduling_policy is not None:
            raise InvalidFinancialPolicy("An immediate ride cannot apply a scheduling surcharge.")
        scheduling_surcharge = Decimal("0.00")
        scheduling_beneficiary = None
    else:
        if scheduling_policy is None:
            raise InvalidFinancialPolicy("A scheduled booking requires an explicit scheduling policy.")
        if scheduling_policy.currency != rule.currency or scheduling_policy.surcharge_amount < 0:
            raise InvalidFinancialPolicy("The scheduling surcharge policy is invalid for this tariff.")
        scheduling_surcharge = money(scheduling_policy.surcharge_amount)
        scheduling_beneficiary = scheduling_policy.beneficiary

    driver_gross = transport_fare + (
        scheduling_surcharge
        if scheduling_beneficiary == SchedulingSurchargeBeneficiary.DRIVER
        else Decimal("0.00")
    )
    driver_fee_deduction = (
        operator_fee
        if fee_policy.funding_mode == OperatorFeeFundingMode.DRIVER_SETTLEMENT_DEDUCTION
        else Decimal("0.00")
    )
    driver_net = money(driver_gross - driver_fee_deduction)
    if driver_net < 0 or driver_net < money(fee_policy.minimum_driver_net):
        raise InvalidFinancialPolicy("The operator fee would violate the configured driver-net floor.")
    operator_allocation = operator_fee + (
        scheduling_surcharge
        if scheduling_beneficiary == SchedulingSurchargeBeneficiary.OPERATOR
        else Decimal("0.00")
    )
    passenger_total = transport_fare + scheduling_surcharge + (
        operator_fee
        if fee_policy.funding_mode == OperatorFeeFundingMode.PASSENGER_SURCHARGE
        else Decimal("0.00")
    )

    values = {
        "transport_fare": money(transport_fare),
        "scheduling_surcharge": money(scheduling_surcharge),
        "operator_fee": money(operator_fee),
        "passenger_total": money(passenger_total),
        "driver_gross": money(driver_gross),
        "driver_fee_deduction": money(driver_fee_deduction),
        "driver_net": money(driver_net),
        "operator_allocation": money(operator_allocation),
    }
    return FinancialQuote(
        pricing_rule_id=rule.id,
        pricing_rule_version=rule.version,
        operator_fee_policy_id=fee_policy.id,
        operator_fee_policy_version=fee_policy.version,
        scheduling_policy_id=scheduling_policy.id if scheduling_policy is not None else None,
        scheduling_policy_version=scheduling_policy.version if scheduling_policy is not None else None,
        booking_type=booking_type,
        operator_fee_calculation_mode=fee_policy.calculation_mode,
        operator_fee_funding_mode=fee_policy.funding_mode,
        scheduling_surcharge_beneficiary=scheduling_beneficiary,
        transport_fare_amount=values["transport_fare"],
        scheduling_surcharge_amount=values["scheduling_surcharge"],
        operator_fee_amount=values["operator_fee"],
        passenger_total_amount=values["passenger_total"],
        driver_gross_amount=values["driver_gross"],
        driver_fee_deduction_amount=values["driver_fee_deduction"],
        driver_net_amount=values["driver_net"],
        operator_allocation_amount=values["operator_allocation"],
        currency=rule.currency,
        policy_snapshot={
            "tariff_version": rule.version,
            "operator_fee_policy_version": fee_policy.version,
            "scheduling_policy_version": scheduling_policy.version if scheduling_policy is not None else None,
            "booking_type": booking_type.value,
            "operator_fee_calculation_mode": fee_policy.calculation_mode.value,
            "operator_fee_funding_mode": fee_policy.funding_mode.value,
            "operator_fee_eligible_base": fee_policy.eligible_base_code,
            "operator_fee_percentage_rate": (
                str(fee_policy.percentage_rate) if fee_policy.percentage_rate is not None else None
            ),
            "operator_fee_flat_amount": str(fee_policy.flat_amount) if fee_policy.flat_amount is not None else None,
            "operator_fee_rounding_rule": fee_policy.rounding_rule.value,
            "minimum_driver_net": str(money(fee_policy.minimum_driver_net)),
            "scheduling_surcharge_beneficiary": (
                scheduling_beneficiary.value if scheduling_beneficiary is not None else None
            ),
            **{key: str(value) for key, value in values.items()},
            "currency": rule.currency,
        },
    )


async def active_tariff(
    database_session: AsyncSession,
    at: datetime,
    city_id: UUID = LEGACY_CITY_ID,
    operator_id: UUID = LEGACY_OPERATOR_ID,
    service_type: ServiceType = ServiceType.ON_DEMAND,
    booking_type: BookingType = BookingType.IMMEDIATE,
) -> PricingRule:
    rule = await database_session.scalar(
        select(PricingRule)
        .where(
            PricingRule.status == PricingRuleStatus.ACTIVE,
            PricingRule.city_id == city_id,
            PricingRule.operator_id == operator_id,
            PricingRule.service_type == service_type,
            PricingRule.booking_type == booking_type,
            PricingRule.effective_from <= at,
            (PricingRule.effective_until.is_(None) | (PricingRule.effective_until > at)),
        )
        .order_by(PricingRule.effective_from.desc(), PricingRule.id)
        .limit(1)
    )
    if rule is None:
        raise NoActiveTariff("No active tariff is available.")
    return rule


def _effective(at: datetime, effective_from: datetime, effective_until: datetime | None) -> bool:
    return effective_from <= at and (effective_until is None or effective_until > at)


async def quote_immediate_ride(
    database_session: AsyncSession,
    *,
    city_id: UUID,
    operator_id: UUID,
    tariff_version_id: UUID | None,
    operator_fee_policy_version_id: UUID | None,
    at: datetime,
) -> FinancialQuote:
    if tariff_version_id is None:
        rule = await active_tariff(
            database_session,
            at,
            city_id=city_id,
            operator_id=operator_id,
        )
    else:
        rule = await database_session.get(PricingRule, tariff_version_id)
    if (
        rule is None
        or rule.city_id != city_id
        or rule.operator_id != operator_id
        or rule.service_type != ServiceType.ON_DEMAND
        or rule.booking_type != BookingType.IMMEDIATE
        or rule.status != PricingRuleStatus.ACTIVE
        or not _effective(at, rule.effective_from, rule.effective_until)
    ):
        raise NoActiveTariff("The active city bundle has no applicable on-demand tariff.")

    policy_id = operator_fee_policy_version_id
    if policy_id is None and city_id == LEGACY_CITY_ID and operator_id == LEGACY_OPERATOR_ID:
        policy_id = LEGACY_ZERO_OPERATOR_FEE_POLICY_ID
    policy = await database_session.get(OperatorFeePolicy, policy_id) if policy_id is not None else None
    if (
        policy is None
        or policy.city_id != city_id
        or policy.operator_id != operator_id
        or policy.service_type != ServiceType.ON_DEMAND
        or policy.status != FinancialPolicyStatus.ACTIVE
        or not _effective(at, policy.effective_from, policy.effective_until)
    ):
        raise InvalidFinancialPolicy("The active city bundle has no applicable operator-fee policy.")
    return calculate_financial_quote(rule, policy, booking_type=BookingType.IMMEDIATE)


async def quote_scheduled_ride(
    database_session: AsyncSession,
    *,
    city_id: UUID,
    operator_id: UUID,
    service_type: ServiceType,
    operator_fee_policy_version_id: UUID | None,
    scheduling_policy_version_id: UUID | None,
    at: datetime,
) -> tuple[FinancialQuote, SchedulingPolicy]:
    """Resolve and snapshot the complete policy bundle at passenger confirmation.

    On-demand scheduled transport uses an explicit SCHEDULED tariff. Fixed-route
    transport keeps the immutable direction fare and is quoted by the fixed-route
    resolver because the direction is part of its scope.
    """

    if service_type != ServiceType.ON_DEMAND:
        raise InvalidFinancialPolicy("Use the direction-scoped resolver for fixed-route scheduling.")
    rule = await active_tariff(
        database_session,
        at,
        city_id=city_id,
        operator_id=operator_id,
        service_type=service_type,
        booking_type=BookingType.SCHEDULED,
    )
    fee_policy = (
        await database_session.get(OperatorFeePolicy, operator_fee_policy_version_id)
        if operator_fee_policy_version_id is not None
        else None
    )
    scheduling_policy = (
        await database_session.get(SchedulingPolicy, scheduling_policy_version_id)
        if scheduling_policy_version_id is not None
        else None
    )
    if (
        fee_policy is None
        or fee_policy.city_id != city_id
        or fee_policy.operator_id != operator_id
        or fee_policy.service_type != service_type
        or fee_policy.status != FinancialPolicyStatus.ACTIVE
        or not _effective(at, fee_policy.effective_from, fee_policy.effective_until)
    ):
        raise InvalidFinancialPolicy("The active city bundle has no applicable operator-fee policy.")
    if (
        scheduling_policy is None
        or scheduling_policy.city_id != city_id
        or scheduling_policy.operator_id != operator_id
        or scheduling_policy.service_type != service_type
        or scheduling_policy.status != FinancialPolicyStatus.ACTIVE
        or not _effective(at, scheduling_policy.effective_from, scheduling_policy.effective_until)
    ):
        raise InvalidFinancialPolicy("Scheduled booking is not enabled by an active city policy.")
    return (
        calculate_financial_quote(
            rule,
            fee_policy,
            booking_type=BookingType.SCHEDULED,
            scheduling_policy=scheduling_policy,
        ),
        scheduling_policy,
    )


def finalized_fare_breakdown(record: FareRecord) -> tuple[str | None, list[dict[str, str]]]:
    """Return immutable passenger-charge components, with a legacy fallback.

    Driver-funded operator fees remain visible in the economics snapshot and
    driver settlement, but are not presented as a second passenger charge.
    """

    version = record.snapshot.get("tariff_version")
    if "transport_fare" not in record.snapshot:
        return (
            str(version) if version is not None else None,
            [{"code": "BASE_FARE", "label": "Base fare", "amount": str(money(record.base_amount))}],
        )
    components = [
        {
            "code": "TRANSPORT_FARE",
            "label": "Transport fare",
            "amount": str(record.snapshot["transport_fare"]),
        }
    ]
    if money(record.snapshot["scheduling_surcharge"]) != Decimal("0.00"):
        components.append(
            {
                "code": "SCHEDULING_SURCHARGE",
                "label": "Scheduling surcharge",
                "amount": str(record.snapshot["scheduling_surcharge"]),
            }
        )
    if (
        record.snapshot.get("operator_fee_funding_mode") == "PASSENGER_SURCHARGE"
        and money(record.snapshot["operator_fee"]) != Decimal("0.00")
    ):
        components.append(
            {
                "code": "OPERATOR_SERVICE_FEE",
                "label": "Operator service fee",
                "amount": str(record.snapshot["operator_fee"]),
            }
        )
    return str(version) if version is not None else None, components


async def finalize_fixed_fare(database_session: AsyncSession, ride_id, applicable_at: datetime) -> FareRecord:
    rule = await active_tariff(database_session, applicable_at)
    return await finalize_fixed_fare_for_rule(database_session, ride_id, rule)


async def finalize_fixed_fare_for_rule(
    database_session: AsyncSession,
    ride_id,
    rule: PricingRule,
    *,
    locked_amount: Decimal | None = None,
    locked_currency: str | None = None,
    financial_snapshot: RideFinancialSnapshot | None = None,
) -> FareRecord:
    """Finalize from the confirmation snapshot, never mutable current policy."""

    configured_amount = fixed_fare_amount(rule)
    if financial_snapshot is None:
        amount = money(locked_amount if locked_amount is not None else configured_amount)
        if amount < 0:
            raise NoActiveTariff("A locked fare cannot be negative.")
        currency = locked_currency or rule.currency
        snapshot = {
            "tariff_version": rule.version,
            "model": rule.model.value,
            "configured_base_fare": str(configured_amount),
            "base_fare": str(amount),
            "total": str(amount),
            "currency": currency,
        }
        base_amount = amount
        total_amount = amount
    else:
        if financial_snapshot.pricing_rule_id != rule.id:
            raise InvalidFinancialPolicy("The ride financial snapshot references another tariff.")
        currency = financial_snapshot.currency
        base_amount = financial_snapshot.transport_fare_amount
        total_amount = financial_snapshot.passenger_total_amount
        snapshot = {
            **financial_snapshot.snapshot,
            "model": rule.model.value,
            "configured_base_fare": str(configured_amount),
        }
    record = FareRecord(
        ride_id=ride_id,
        pricing_rule_id=rule.id,
        base_amount=base_amount,
        total_amount=total_amount,
        currency=currency,
        snapshot=snapshot,
        calculated_at=datetime.now(UTC),
        finalized_at=datetime.now(UTC),
    )
    database_session.add(record)
    await database_session.flush()
    return record
