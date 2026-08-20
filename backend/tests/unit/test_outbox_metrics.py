import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from taximobile_api.domains.outbox.metrics import (
    OutboxMetricsUnavailable,
    collect_outbox_metrics,
)


class _Result:
    def __init__(self, row: tuple) -> None:
        self._row = row

    def one(self) -> tuple:
        return self._row


class _Session:
    def __init__(self, row: tuple | None = None, failure: Exception | None = None) -> None:
        self._row = row
        self._failure = failure

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        return None

    async def execute(self, _statement):
        if self._failure is not None:
            raise self._failure
        return _Result(self._row)


def test_outbox_metrics_are_aggregate_counts_and_bounded_age() -> None:
    observed_at = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    session = _Session((7, 2, 1, observed_at - timedelta(seconds=12.5)))

    result = asyncio.run(collect_outbox_metrics(lambda: session, observed_at=observed_at))

    assert result.available is True
    assert result.pending_events == 7
    assert result.dead_letter_events == 2
    assert result.locked_events == 1
    assert result.oldest_pending_age_seconds == 12.5


def test_outbox_metrics_use_zero_age_when_no_event_is_pending() -> None:
    session = _Session((0, 3, 0, None))

    result = asyncio.run(collect_outbox_metrics(lambda: session))

    assert result.pending_events == 0
    assert result.dead_letter_events == 3
    assert result.oldest_pending_age_seconds == 0.0


def test_outbox_metrics_hide_database_driver_failures() -> None:
    session = _Session(failure=RuntimeError("password=private connection detail"))

    with pytest.raises(OutboxMetricsUnavailable, match="Aggregate outbox metrics are unavailable") as caught:
        asyncio.run(collect_outbox_metrics(lambda: session))

    assert "private" not in str(caught.value)
