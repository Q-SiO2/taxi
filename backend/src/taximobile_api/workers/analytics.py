"""Coarse supply snapshot and source-derived operational fact refresh."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taximobile_api.core.metrics import MetricsRegistry
from taximobile_api.domains.analytics.service import refresh_operational_analytics
from taximobile_api.workers.runtime import run_polling_processor


class AnalyticsProcessor:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def process_once(self) -> int:
        async with self._sessions() as session:
            async with session.begin():
                return await refresh_operational_analytics(session)


async def run_analytics_processor(
    processor: AnalyticsProcessor,
    poll_seconds: float,
    metrics: MetricsRegistry,
) -> None:
    await run_polling_processor(
        worker="analytics",
        processor=processor,
        poll_seconds=poll_seconds,
        metrics=metrics,
    )
