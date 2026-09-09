"""Real PostgreSQL evidence for the privacy-bounded capacity snapshot."""

import asyncio
from os import getenv

import pytest
from sqlalchemy.exc import TimeoutError as SqlAlchemyTimeoutError

from taximobile_api.core.config import Settings
from taximobile_api.db.metrics import collect_database_metrics, collect_database_pool_metrics
from taximobile_api.db.session import create_session_factory


def test_database_capacity_snapshot_uses_the_current_isolated_database():
    if getenv("TAXIMOBILE_RUN_INTEGRATION") != "1":
        pytest.skip("Run through the guarded fresh-PostGIS integration harness.")
    sessions = create_session_factory(Settings.from_environment())

    async def scenario():
        try:
            return await collect_database_metrics(sessions)
        finally:
            await sessions.kw["bind"].dispose()

    result = asyncio.run(scenario())

    assert result.available is True
    assert result.connections >= 1
    assert result.active_connections >= 1
    assert result.active_connections <= result.connections
    assert result.connection_limit >= result.connections
    assert result.waiting_locks >= 0
    assert result.deadlocks_total >= 0


def test_database_pool_records_real_checkout_wait_and_timeout(monkeypatch):
    if getenv("TAXIMOBILE_RUN_INTEGRATION") != "1":
        pytest.skip("Run through the guarded fresh-PostGIS integration harness.")
    monkeypatch.setenv("TAXIMOBILE_DATABASE_POOL_SIZE", "1")
    monkeypatch.setenv("TAXIMOBILE_DATABASE_POOL_MAX_OVERFLOW", "0")
    monkeypatch.setenv("TAXIMOBILE_DATABASE_POOL_TIMEOUT_SECONDS", "0.5")
    sessions = create_session_factory(Settings.from_environment())
    engine = sessions.kw["bind"]

    async def scenario():
        try:
            async with engine.connect():
                with pytest.raises(SqlAlchemyTimeoutError):
                    async with engine.connect():
                        raise AssertionError("Pool exhaustion must not acquire a connection")
            return collect_database_pool_metrics(sessions)
        finally:
            await engine.dispose()

    result = asyncio.run(scenario())

    assert result.available is True
    assert result.size == 1
    assert result.checked_in == 1
    assert result.checked_out == 0
    assert result.overflow == 0
    assert result.checkout_wait_count == 2
    assert result.checkout_wait_sum_seconds >= 0.5
    assert result.checkout_wait_bucket_counts[-1] == 2
    assert result.checkout_timeouts_total == 1
