import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from taximobile_api.domains.outbox.metrics import (
    OutboxMetricsUnavailable,
    collect_outbox_metrics,
)


class _Result:
    def __init__(self, rows: list[tuple]) -> None:
        self._rows = rows

    def all(self) -> list[tuple]:
        return self._rows


class _Session:
    def __init__(self, rows: list[tuple] | None = None, failure: Exception | None = None) -> None:
        self._rows = rows or []
        self._failure = failure

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        return None

    async def execute(self, _statement):
        if self._failure is not None:
            raise self._failure
        return _Result(self._rows)


def test_outbox_metrics_are_aggregate_counts_and_bounded_age() -> None:
    observed_at = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    session = _Session(
        [
            ("ride.accepted", 4, 1, 1, observed_at - timedelta(seconds=12.5)),
            (
                "driver.city_authorization.changed",
                3,
                1,
                0,
                observed_at - timedelta(seconds=5),
            ),
        ]
    )

    result = asyncio.run(collect_outbox_metrics(lambda: session, observed_at=observed_at))

    assert result.available is True
    assert result.pending_events == 7
    assert result.dead_letter_events == 2
    assert result.locked_events == 1
    assert result.oldest_pending_age_seconds == 12.5
    by_owner = {owner.owner: owner for owner in result.owners}
    assert set(by_owner) == {
        "dispatch_operations",
        "scheduling_operations",
        "driver_compliance",
        "unclassified",
    }
    assert by_owner["dispatch_operations"].pending_events == 4
    assert by_owner["dispatch_operations"].dead_letter_events == 1
    assert by_owner["dispatch_operations"].locked_events == 1
    assert by_owner["dispatch_operations"].oldest_pending_age_seconds == 12.5
    assert by_owner["driver_compliance"].pending_events == 3
    assert by_owner["driver_compliance"].dead_letter_events == 1
    assert by_owner["driver_compliance"].oldest_pending_age_seconds == 5
    assert by_owner["scheduling_operations"].pending_events == 0


def test_outbox_metrics_use_zero_age_when_no_event_is_pending() -> None:
    session = _Session([("scheduled.offer.created", 0, 3, 0, None)])

    result = asyncio.run(collect_outbox_metrics(lambda: session))

    assert result.pending_events == 0
    assert result.dead_letter_events == 3
    assert result.oldest_pending_age_seconds == 0.0


def test_unknown_topics_are_counted_only_in_fixed_unclassified_bucket() -> None:
    observed_at = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    session = _Session(
        [
            (
                "future.arbitrary.user-controlled-looking-topic",
                2,
                1,
                0,
                observed_at - timedelta(seconds=4),
            ),
        ]
    )

    result = asyncio.run(collect_outbox_metrics(lambda: session, observed_at=observed_at))

    unclassified = next(owner for owner in result.owners if owner.owner == "unclassified")
    assert unclassified.pending_events == 2
    assert unclassified.dead_letter_events == 1
    assert unclassified.oldest_pending_age_seconds == 4


def test_outbox_metrics_hide_database_driver_failures() -> None:
    session = _Session(failure=RuntimeError("password=private connection detail"))

    with pytest.raises(OutboxMetricsUnavailable, match="Aggregate outbox metrics are unavailable") as caught:
        asyncio.run(collect_outbox_metrics(lambda: session))

    assert "private" not in str(caught.value)


def test_outbox_metrics_timeout_is_a_bounded_unavailable_result() -> None:
    class _SlowSession(_Session):
        async def execute(self, statement):
            await asyncio.sleep(.05)
            return await super().execute(statement)

    with pytest.raises(OutboxMetricsUnavailable):
        asyncio.run(collect_outbox_metrics(
            lambda: _SlowSession(),
            timeout_seconds=.001,
        ))
