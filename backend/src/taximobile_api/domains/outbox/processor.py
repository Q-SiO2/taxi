"""Lease-based transactional-outbox processing.

The worker deliberately handles only non-authoritative refresh hints. It stores
no recipient information in an event payload and retries infrastructure failures
without rolling back the business transaction that created the event.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taximobile_api.domains.outbox.models import OutboxEvent


@dataclass(frozen=True, slots=True)
class ClaimedOutboxEvent:
    id: UUID
    topic: str
    payload: dict


class OutboxDelivery(Protocol):
    async def deliver(self, event: ClaimedOutboxEvent) -> None: ...


def retry_delay_seconds(attempts: int) -> int:
    """Bound exponential retry; retry metadata must never include private errors."""
    return min(300, 2 ** max(0, min(attempts - 1, 9)))


def failure_outcome(attempts: int, max_attempts: int) -> str:
    """Return a fixed, non-sensitive operational outcome for a failed attempt."""
    return "DELIVERY_DEAD_LETTERED" if attempts >= max_attempts else "DELIVERY_RETRY"


class OutboxProcessor:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        delivery: OutboxDelivery,
        *,
        worker_id: str | None = None,
        batch_size: int = 20,
        lease_seconds: int = 60,
        max_attempts: int = 8,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self._sessions = session_factory
        self._delivery = delivery
        self._worker_id = worker_id or str(uuid4())
        self._batch_size = batch_size
        self._lease_seconds = lease_seconds
        self._max_attempts = max_attempts

    async def process_once(self) -> int:
        events = await self._claim_due_events()
        for event in events:
            try:
                await self._delivery.deliver(event)
            except Exception:
                await self._reschedule(event.id)
            else:
                await self._mark_delivered(event.id)
        return len(events)

    async def _claim_due_events(self) -> list[ClaimedOutboxEvent]:
        now = datetime.now(UTC)
        stale_lease = now - timedelta(seconds=self._lease_seconds)
        async with self._sessions() as session:
            async with session.begin():
                statement = (
                    select(OutboxEvent)
                    .where(
                        OutboxEvent.delivered_at.is_(None),
                        OutboxEvent.dead_lettered_at.is_(None),
                        OutboxEvent.available_at <= now,
                        or_(OutboxEvent.locked_at.is_(None), OutboxEvent.locked_at < stale_lease),
                    )
                    .order_by(OutboxEvent.available_at, OutboxEvent.created_at)
                    .limit(self._batch_size)
                    .with_for_update(skip_locked=True)
                )
                records = list(await session.scalars(statement))
                for record in records:
                    record.attempts += 1
                    record.locked_at = now
                    record.locked_by = self._worker_id
                    record.last_error = None
                return [ClaimedOutboxEvent(record.id, record.topic, dict(record.payload)) for record in records]

    async def _mark_delivered(self, event_id: UUID) -> None:
        async with self._sessions() as session:
            async with session.begin():
                event = await self._locked_event(session, event_id)
                if event is None:
                    return
                event.delivered_at = datetime.now(UTC)
                event.locked_at = None
                event.locked_by = None
                event.last_error = None

    async def _reschedule(self, event_id: UUID) -> None:
        async with self._sessions() as session:
            async with session.begin():
                event = await self._locked_event(session, event_id)
                if event is None:
                    return
                now = datetime.now(UTC)
                outcome = failure_outcome(event.attempts, self._max_attempts)
                if outcome == "DELIVERY_DEAD_LETTERED":
                    event.dead_lettered_at = now
                else:
                    event.available_at = now + timedelta(seconds=retry_delay_seconds(event.attempts))
                event.locked_at = None
                event.locked_by = None
                event.last_error = outcome

    async def _locked_event(self, session: AsyncSession, event_id: UUID) -> OutboxEvent | None:
        return await session.scalar(
            select(OutboxEvent)
            .where(
                OutboxEvent.id == event_id,
                OutboxEvent.delivered_at.is_(None),
                OutboxEvent.dead_lettered_at.is_(None),
                OutboxEvent.locked_by == self._worker_id,
            )
            .with_for_update()
        )
