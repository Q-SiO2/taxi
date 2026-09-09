"""Lifecycle supervisor for TaxiMobile's authoritative background processors."""

from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taximobile_api.core.config import Settings
from taximobile_api.core.live_events import LiveEventPublisher
from taximobile_api.core.metrics import MetricsRegistry
from taximobile_api.domains.outbox.processor import OutboxProcessor
from taximobile_api.integrations.push import PushProvider
from taximobile_api.integrations.driver_documents import (
    ProtectedDriverDocumentStore,
    create_driver_document_store,
)
from taximobile_api.integrations.case_pager import DisabledCasePager, HttpCasePager
from taximobile_api.workers.credentials import (
    CredentialLifecycleProcessor,
    run_credential_lifecycle_processor,
)
from taximobile_api.workers.matching import MatchingProcessor, run_matching_processor
from taximobile_api.workers.outbox import WebSocketOutboxDelivery, run_outbox_processor
from taximobile_api.workers.scheduling import SchedulingProcessor, run_scheduling_processor
from taximobile_api.workers.analytics import AnalyticsProcessor, run_analytics_processor
from taximobile_api.workers.case_alerts import CaseAlertProcessor, run_case_alert_processor
from taximobile_api.workers.case_retention import (
    CaseRetentionProcessor,
    run_case_retention_processor,
)
from taximobile_api.workers.driver_document_retention import (
    DriverDocumentRetentionProcessor,
    run_driver_document_retention_processor,
)


class BackgroundWorkerRuntime:
    """Start and stop all bounded loops as one process-owned unit.

    Database row locks and leases remain the concurrency authority. This class
    only establishes process ownership and deterministic cancellation.
    """

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        settings: Settings,
        live_event_publisher: LiveEventPublisher,
        push_provider: PushProvider | None,
        driver_document_store: ProtectedDriverDocumentStore | None = None,
    ) -> None:
        self._sessions = sessions
        self._settings = settings
        self._live_event_publisher = live_event_publisher
        self._push_provider = push_provider
        self._driver_document_store = (
            driver_document_store
            or create_driver_document_store(
                root=settings.driver_document_storage_root,
                encryption_key=settings.driver_document_encryption_key,
                clamav_host=settings.driver_document_clamav_host,
                clamav_port=settings.driver_document_clamav_port,
                clamav_timeout_seconds=settings.driver_document_clamav_timeout_seconds,
                max_bytes=settings.driver_document_max_bytes,
            )
        )
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
        if self._settings.case_pager_configured:
            assert self._settings.case_pager_url is not None
            assert self._settings.case_pager_token is not None
            case_pager = HttpCasePager(
                url=self._settings.case_pager_url,
                bearer_token=self._settings.case_pager_token,
                timeout_seconds=self._settings.case_pager_timeout_seconds,
            )
        else:
            case_pager = DisabledCasePager()
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
            asyncio.create_task(
                run_scheduling_processor(
                    SchedulingProcessor(self._sessions, self._settings),
                    self._settings.scheduling_poll_seconds,
                    metrics,
                ),
                name="taximobile-scheduling",
            ),
            asyncio.create_task(
                run_analytics_processor(
                    AnalyticsProcessor(self._sessions),
                    self._settings.analytics_poll_seconds,
                    metrics,
                ),
                name="taximobile-analytics",
            ),
            asyncio.create_task(
                run_case_alert_processor(
                    CaseAlertProcessor(
                        self._sessions,
                        case_pager,
                        max_delivery_attempts=(
                            self._settings.case_alert_max_delivery_attempts
                        ),
                    ),
                    self._settings.case_alert_poll_seconds,
                    metrics,
                ),
                name="taximobile-case-alerts",
            ),
            asyncio.create_task(
                run_case_retention_processor(
                    CaseRetentionProcessor(
                        self._sessions,
                        batch_size=self._settings.case_retention_batch_size,
                    ),
                    self._settings.case_retention_poll_seconds,
                    metrics,
                ),
                name="taximobile-case-retention",
            ),
            asyncio.create_task(
                run_driver_document_retention_processor(
                    DriverDocumentRetentionProcessor(
                        self._sessions,
                        self._driver_document_store,
                        batch_size=self._settings.driver_document_retention_batch_size,
                    ),
                    self._settings.driver_document_retention_poll_seconds,
                    metrics,
                ),
                name="taximobile-driver-document-retention",
            ),
        )

    async def stop(self) -> None:
        tasks, self._tasks = self._tasks, ()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
