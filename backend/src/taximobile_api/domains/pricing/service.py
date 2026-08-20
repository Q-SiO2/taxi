from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.pricing.models import FareRecord, PricingModel, PricingRule, PricingRuleStatus


class NoActiveTariff(ValueError):
    pass


def fixed_fare_amount(rule: PricingRule) -> Decimal:
    if rule.model != PricingModel.FIXED or rule.fixed_amount is None or rule.fixed_amount < 0:
        raise NoActiveTariff("No supported fixed tariff is active for this ride.")
    return rule.fixed_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def finalized_fare_breakdown(record: FareRecord) -> tuple[str | None, list[dict[str, str]]]:
    """Return only the components actually present in an immutable fare record."""
    version = record.snapshot.get("tariff_version")
    return (
        str(version) if version is not None else None,
        [{"code": "BASE_FARE", "label": "Base fare", "amount": str(record.base_amount)}],
    )


async def active_tariff(database_session: AsyncSession, at: datetime) -> PricingRule:
    rule = await database_session.scalar(
        select(PricingRule)
        .where(
            PricingRule.status == PricingRuleStatus.ACTIVE,
            PricingRule.effective_from <= at,
            (PricingRule.effective_until.is_(None) | (PricingRule.effective_until > at)),
        )
        .order_by(PricingRule.effective_from.desc())
        .limit(1)
    )
    if rule is None:
        raise NoActiveTariff("No active tariff is available.")
    return rule


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
) -> FareRecord:
    """Finalize from the tariff selected at confirmation, not from mutable current policy."""
    configured_amount = fixed_fare_amount(rule)
    amount = (locked_amount if locked_amount is not None else configured_amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if amount < 0:
        raise NoActiveTariff("A locked fare cannot be negative.")
    currency = locked_currency or rule.currency
    record = FareRecord(
        ride_id=ride_id,
        pricing_rule_id=rule.id,
        base_amount=amount,
        total_amount=amount,
        currency=currency,
        snapshot={"tariff_version": rule.version, "model": rule.model.value, "configured_base_fare": str(configured_amount), "base_fare": str(amount), "total": str(amount), "currency": currency},
        calculated_at=datetime.now(UTC),
        finalized_at=datetime.now(UTC),
    )
    database_session.add(record)
    await database_session.flush()
    return record
