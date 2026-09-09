"""Privacy-bounded operational measurements for transactional delivery."""

import asyncio

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taximobile_api.core.metrics import OutboxMetrics, OutboxOwnerMetrics
from taximobile_api.core.notification_policy import (
    DEAD_LETTER_OWNERS,
    UnsupportedOutboxTopic,
    notification_policy_for_topic,
)
from taximobile_api.domains.outbox.models import OutboxEvent


class OutboxMetricsUnavailable(RuntimeError):
    """The aggregate snapshot could not be read from the database."""


@dataclass(slots=True)
class _OwnerTotals:
    pending_events: int = 0
    dead_letter_events: int = 0
    locked_events: int = 0
    oldest_pending_at: datetime | None = None


async def collect_outbox_metrics(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    observed_at: datetime | None = None,
    timeout_seconds: float = 5.0,
) -> OutboxMetrics:
    """Read one aggregate snapshot without loading payloads or identifiers."""

    now = observed_at or datetime.now(UTC)
    pending = and_(
        OutboxEvent.delivered_at.is_(None),
        OutboxEvent.dead_lettered_at.is_(None),
    )
    statement = select(
        OutboxEvent.topic,
        func.count(OutboxEvent.id).filter(pending),
        func.count(OutboxEvent.id).filter(OutboxEvent.dead_lettered_at.is_not(None)),
        func.count(OutboxEvent.id).filter(pending, OutboxEvent.locked_at.is_not(None)),
        func.min(OutboxEvent.created_at).filter(pending),
    ).group_by(OutboxEvent.topic)
    try:
        async with asyncio.timeout(timeout_seconds):
            async with session_factory() as session:
                rows = (await session.execute(statement)).all()
    except Exception as error:
        # Drivers do not consistently wrap connect/authentication failures in
        # SQLAlchemyError. Convert the entire database boundary to one safe,
        # expected operational condition without retaining or returning details.
        raise OutboxMetricsUnavailable("Aggregate outbox metrics are unavailable.") from error

    pending_count = sum(int(row[1]) for row in rows)
    dead_letter_count = sum(int(row[2]) for row in rows)
    locked_count = sum(int(row[3]) for row in rows)
    pending_times = [row[4] for row in rows if row[4] is not None]
    oldest_pending_at = min(pending_times) if pending_times else None
    oldest_age = (
        max(0.0, (now - oldest_pending_at).total_seconds())
        if oldest_pending_at is not None
        else 0.0
    )
    owner_values = {
        owner: _OwnerTotals()
        for owner in sorted(DEAD_LETTER_OWNERS | {"unclassified"})
    }
    for topic, topic_pending, topic_dead, topic_locked, topic_oldest in rows:
        try:
            owner = notification_policy_for_topic(topic).dead_letter_owner
        except UnsupportedOutboxTopic:
            owner = "unclassified"
        bucket = owner_values[owner]
        bucket.pending_events += int(topic_pending)
        bucket.dead_letter_events += int(topic_dead)
        bucket.locked_events += int(topic_locked)
        if topic_oldest is not None and (
            bucket.oldest_pending_at is None or topic_oldest < bucket.oldest_pending_at
        ):
            bucket.oldest_pending_at = topic_oldest
    owners = tuple(
        OutboxOwnerMetrics(
            owner=owner,
            pending_events=values.pending_events,
            dead_letter_events=values.dead_letter_events,
            locked_events=values.locked_events,
            oldest_pending_age_seconds=(
                max(0.0, (now - values.oldest_pending_at).total_seconds())
                if values.oldest_pending_at is not None
                else 0.0
            ),
        )
        for owner, values in owner_values.items()
    )
    return OutboxMetrics(
        available=True,
        pending_events=int(pending_count),
        dead_letter_events=int(dead_letter_count),
        locked_events=int(locked_count),
        oldest_pending_age_seconds=oldest_age,
        owners=owners,
    )
