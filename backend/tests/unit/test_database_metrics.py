import asyncio

import pytest

from taximobile_api.db.metrics import (
    DATABASE_METRICS_SQL,
    DatabaseMetricsUnavailable,
    DatabasePoolMetricsUnavailable,
    collect_database_metrics,
    collect_database_pool_metrics,
)


class _Result:
    def __init__(self, row):
        self._row = row

    def one(self):
        return self._row


class _Session:
    def __init__(self, *, row=(8, 3, 1, 2, 100), failure=None):
        self.row = row
        self.failure = failure
        self.statement = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def execute(self, statement):
        self.statement = statement
        if self.failure is not None:
            raise self.failure
        return _Result(self.row)


def test_database_metrics_are_fixed_aggregate_current_database_facts():
    session = _Session()

    result = asyncio.run(collect_database_metrics(lambda: session))

    assert session.statement is DATABASE_METRICS_SQL
    assert result.available is True
    assert result.connections == 8
    assert result.active_connections == 3
    assert result.connection_limit == 100
    assert result.waiting_locks == 1
    assert result.deadlocks_total == 2
    statement = str(DATABASE_METRICS_SQL)
    assert "current_database()" in statement
    assert "query" not in statement.lower()
    assert "usename" not in statement.lower()


@pytest.mark.parametrize(
    "row",
    [
        (-1, 0, 0, 0, 100),
        (1, 2, 0, 0, 100),
        (1, 1, 0, 0, 0),
        ("private malformed value", 0, 0, 0, 100),
    ],
)
def test_database_metrics_fail_closed_on_inconsistent_or_malformed_results(row):
    with pytest.raises(
        DatabaseMetricsUnavailable,
        match="Aggregate database metrics are unavailable",
    ) as caught:
        asyncio.run(collect_database_metrics(lambda: _Session(row=row)))

    assert "private" not in str(caught.value)


def test_database_metrics_hide_driver_failures():
    with pytest.raises(DatabaseMetricsUnavailable) as caught:
        asyncio.run(collect_database_metrics(lambda: _Session(
            failure=RuntimeError("password=private host=database.internal")
        )))

    assert "password" not in str(caught.value)
    assert "database.internal" not in str(caught.value)


def test_database_metrics_timeout_is_a_bounded_unavailable_result():
    class _SlowSession(_Session):
        async def execute(self, statement):
            await asyncio.sleep(0.05)
            return await super().execute(statement)

    with pytest.raises(DatabaseMetricsUnavailable):
        asyncio.run(collect_database_metrics(
            lambda: _SlowSession(),
            timeout_seconds=0.001,
        ))


class _Pool:
    def size(self):
        return 5

    def checkedin(self):
        return 2

    def checkedout(self):
        return 4

    def overflow(self):
        return 1

    def taximobile_wait_snapshot(self):
        return (2, 0.25, (1,) * 14, 1)


def test_database_pool_metrics_are_fixed_per_process_counts():
    factory = type("Factory", (), {
        "kw": {"bind": type("Engine", (), {"pool": _Pool()})()}
    })()

    result = collect_database_pool_metrics(factory)

    assert result.available is True
    assert result.size == 5
    assert result.checked_in == 2
    assert result.checked_out == 4
    assert result.overflow == 1
    assert result.checkout_wait_count == 2
    assert result.checkout_wait_sum_seconds == 0.25
    assert result.checkout_wait_bucket_counts == (1,) * 14
    assert result.checkout_timeouts_total == 1


def test_database_pool_negative_internal_overflow_is_reported_as_zero():
    class _EmptyPool(_Pool):
        def checkedin(self):
            return 0

        def checkedout(self):
            return 0

        def overflow(self):
            return -5

    factory = type("Factory", (), {
        "kw": {"bind": type("Engine", (), {"pool": _EmptyPool()})()}
    })()

    assert collect_database_pool_metrics(factory).overflow == 0


def test_database_pool_metrics_fail_closed_without_a_supported_pool():
    with pytest.raises(
        DatabasePoolMetricsUnavailable,
        match="Aggregate database pool metrics are unavailable",
    ):
        collect_database_pool_metrics(object())
