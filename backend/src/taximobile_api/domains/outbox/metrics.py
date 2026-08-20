"""Privacy-bounded operational measurements for transactional delivery."""

from datetime import UTC, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taximobile_api.core.metrics import OutboxMetrics
from taximobile_api.domains.outbox.models import OutboxEvent


class OutboxMetricsUnavailable(RuntimeError):
    """The aggregate snapshot could not be read from the database."""


async def collect_outbox_metrics(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    observed_at: datetime | None = None,
) -> OutboxMetrics:
    """Read one aggregate snapshot without loading payloads or identifiers."""

    now = observed_at or datetime.now(UTC)
    pending = and_(
        OutboxEvent.delivered_at.is_(None),
        OutboxEvent.dead_lettered_at.is_(None),
    )
    statement = select(
        func.count(OutboxEvent.id).filter(pending),
        func.count(OutboxEvent.id).filter(OutboxEvent.dead_lettered_at.is_not(None)),
        func.count(OutboxEvent.id).filter(pending, OutboxEvent.locked_at.is_not(None)),
        func.min(OutboxEvent.created_at).filter(pending),
    )
    try:
        async with session_factory() as session:
            pending_count, dead_letter_count, locked_count, oldest_pending_at = (
                await session.execute(statement)
            ).one()
    except Exception as error:
        # Drivers do not consistently wrap connect/authentication failures in
        # SQLAlchemyError. Convert the entire database boundary to one safe,
        # expected operational condition without retaining or returning details.
        raise OutboxMetricsUnavailable("Aggregate outbox metrics are unavailable.") from error

    oldest_age = (
        max(0.0, (now - oldest_pending_at).total_seconds())
        if oldest_pending_at is not None
        else 0.0
    )
    return OutboxMetrics(
        available=True,
        pending_events=int(pending_count),
        dead_letter_events=int(dead_letter_count),
        locked_events=int(locked_count),
        oldest_pending_age_seconds=oldest_age,
    )
