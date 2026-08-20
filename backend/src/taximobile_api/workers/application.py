"""Lifecycle supervisor for TaxiMobile's authoritative background processors."""

from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taximobile_api.core.config import Settings
from taximobile_api.core.live_events import LiveEventPublisher
from taximobile_api.core.metrics import MetricsRegistry
from taximobile_api.domains.outbox.processor import OutboxProcessor
from taximobile_api.integrations.push import PushProvider
from taximobile_api.workers.credentials import (
    CredentialLifecycleProcessor,
    run_credential_lifecycle_processor,
)
from taximobile_api.workers.matching import MatchingProcessor, run_matching_processor
from taximobile_api.workers.outbox import WebSocketOutboxDelivery, run_outbox_processor


class BackgroundWorkerRuntime:
    """Start and stop the three bounded loops as one process-owned unit.

    Database row locks and leases remain the concurrency authority. This class
    only establishes process ownership and deterministic cancellation.
    """

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        settings: Settings,
        live_event_publisher: LiveEventPublisher,
        push_provider: PushProvider | None,
    ) -> None:
        self._sessions = sessions
        self._settings = settings
        self._live_event_publisher = live_event_publisher
        self._push_provider = push_provider
        self._tasks: tuple[asyncio.Task[None], ...] = ()

    @property
    def is_running(self) -> bool:
        return bool(self._tasks) and all(not task.done() for task in self._tasks)

    def start(self, metrics: MetricsRegistry) -> None:
        if self._tasks:
            raise RuntimeError("Background workers have already been started.")
        outbox = OutboxProcessor(
            self._sessions,
            WebSocketOutboxDelivery(
                self._sessions,
                self._live_event_publisher,
                self._push_provider,
            ),
            max_attempts=self._settings.outbox_max_attempts,
        )
        self._tasks = (
            asyncio.create_task(
                run_outbox_processor(outbox, self._settings.outbox_poll_seconds, metrics),
                name="taximobile-outbox",
            ),
            asyncio.create_task(
                run_matching_processor(
                    MatchingProcessor(self._sessions, self._settings),
                    self._settings.matching_poll_seconds,
                    metrics,
                ),
                name="taximobile-matching",
            ),
            asyncio.create_task(
                run_credential_lifecycle_processor(
                    CredentialLifecycleProcessor(self._sessions, self._settings),
                    self._settings.credential_poll_seconds,
                    metrics,
                ),
                name="taximobile-credentials",
            ),
        )

    async def stop(self) -> None:
        tasks, self._tasks = self._tasks, ()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
