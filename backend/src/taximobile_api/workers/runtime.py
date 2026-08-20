"""Shared, observable runtime for bounded background processor loops."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Protocol

from taximobile_api.core.metrics import MetricsRegistry


class PollingProcessor(Protocol):
    """Small contract shared by durable background processors."""

    async def process_once(self) -> int:
        """Process one bounded batch and return the number of handled items."""


async def run_polling_processor(
    *,
    worker: str,
    processor: PollingProcessor,
    poll_seconds: float,
    metrics: MetricsRegistry,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    logger: logging.Logger | None = None,
) -> None:
    """Run a processor forever while making retry failures operationally visible.

    Exception messages are deliberately not logged because dependency errors can
    contain URLs, credentials, registrations, or provider payload fragments.
    Cancellation is never converted into a retry so application shutdown remains
    prompt and deterministic.
    """

    active_logger = logger or logging.getLogger("taximobile_api")
    while True:
        try:
            processed = await processor.process_once()
            metrics.record_worker_success(worker, processed=processed)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            metrics.record_worker_failure(worker)
            active_logger.error(
                "worker_iteration_failed",
                extra={"worker": worker, "error_type": type(error).__name__},
            )
            await sleep(poll_seconds)
        else:
            await sleep(0 if processed else poll_seconds)
