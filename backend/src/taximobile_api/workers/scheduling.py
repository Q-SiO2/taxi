"""Bounded processor for scheduled offer, commitment, and handoff deadlines."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taximobile_api.core.metrics import MetricsRegistry
from taximobile_api.core.config import Settings
from taximobile_api.domains.scheduled_bookings.service import advance_due_bookings
from taximobile_api.workers.runtime import run_polling_processor


class SchedulingProcessor:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        settings: Settings,
        *,
        batch_size: int = 100,
    ) -> None:
        self._sessions = sessions
        self._settings = settings
        self._batch_size = batch_size

    async def process_once(self) -> int:
        async with self._sessions() as session:
            async with session.begin():
                counts = await advance_due_bookings(
                    session,
                    limit=self._batch_size,
                    matching_settings=self._settings,
                )
        return sum(counts.values())


async def run_scheduling_processor(
    processor: SchedulingProcessor,
    poll_seconds: float,
    metrics: MetricsRegistry,
) -> None:
    await run_polling_processor(
        worker="scheduling",
        processor=processor,
        poll_seconds=poll_seconds,
        metrics=metrics,
    )
