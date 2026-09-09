import asyncio

from taximobile_api.core.config import Settings
from taximobile_api.db.pool import InstrumentedAsyncAdaptedQueuePool
from taximobile_api.db.session import create_session_factory


def test_session_factory_uses_explicit_bounded_pool_configuration(monkeypatch):
    monkeypatch.setenv("TAXIMOBILE_DATABASE_POOL_SIZE", "7")
    monkeypatch.setenv("TAXIMOBILE_DATABASE_POOL_MAX_OVERFLOW", "3")
    monkeypatch.setenv("TAXIMOBILE_DATABASE_POOL_TIMEOUT_SECONDS", "2.5")

    sessions = create_session_factory(Settings.from_environment())
    pool = sessions.kw["bind"].pool
    try:
        assert pool.size() == 7
        assert pool.timeout() == 2.5
        assert pool.checkedout() == 0
        assert pool.overflow() == -7
        assert isinstance(pool, InstrumentedAsyncAdaptedQueuePool)
        assert pool.taximobile_wait_snapshot() == (0, 0.0, (0,) * 14, 0)
    finally:
        asyncio.run(sessions.kw["bind"].dispose())
