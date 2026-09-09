"""Privacy-bounded PostgreSQL capacity measurements for protected scraping."""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taximobile_api.core.metrics import DatabaseMetrics, DatabasePoolMetrics


DATABASE_METRICS_SQL = text("""
SELECT
    (SELECT count(*) FROM pg_stat_activity WHERE datname = current_database())::bigint,
    (SELECT count(*) FROM pg_stat_activity
        WHERE datname = current_database() AND state = 'active')::bigint,
    (SELECT count(*) FROM pg_locks
        WHERE database = (SELECT oid FROM pg_database WHERE datname = current_database())
          AND NOT granted)::bigint,
    COALESCE((SELECT deadlocks FROM pg_stat_database
        WHERE datname = current_database()), 0)::bigint,
    current_setting('max_connections')::bigint
""")


class DatabaseMetricsUnavailable(RuntimeError):
    """The fixed aggregate PostgreSQL snapshot could not be read safely."""


class DatabasePoolMetricsUnavailable(RuntimeError):
    """The local SQLAlchemy pool snapshot could not be read safely."""


def collect_database_pool_metrics(
    session_factory: async_sessionmaker[AsyncSession],
) -> DatabasePoolMetrics:
    """Read fixed per-process pool counts without connection identities."""

    try:
        engine = session_factory.kw["bind"]
        pool = engine.pool
        wait_count, wait_sum, wait_buckets, timeouts = pool.taximobile_wait_snapshot()
        return DatabasePoolMetrics(
            available=True,
            size=int(pool.size()),
            checked_in=int(pool.checkedin()),
            checked_out=int(pool.checkedout()),
            overflow=max(0, int(pool.overflow())),
            checkout_wait_count=int(wait_count),
            checkout_wait_sum_seconds=float(wait_sum),
            checkout_wait_bucket_counts=tuple(int(value) for value in wait_buckets),
            checkout_timeouts_total=int(timeouts),
        )
    except Exception as error:
        raise DatabasePoolMetricsUnavailable(
            "Aggregate database pool metrics are unavailable."
        ) from error


async def collect_database_metrics(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    timeout_seconds: float = 5.0,
) -> DatabaseMetrics:
    """Read fixed current-database counters without query text or identities."""

    try:
        async with asyncio.timeout(timeout_seconds):
            async with session_factory() as session:
                row = (await session.execute(DATABASE_METRICS_SQL)).one()
        total, active, waiting_locks, deadlocks, maximum = (int(value) for value in row)
        if (
            minimum := min(total, active, waiting_locks, deadlocks, maximum)
        ) < 0 or maximum == 0 or active > total:
            raise ValueError(f"Invalid aggregate PostgreSQL snapshot: {minimum}")
        return DatabaseMetrics(
            available=True,
            connections=total,
            active_connections=active,
            connection_limit=maximum,
            waiting_locks=waiting_locks,
            deadlocks_total=deadlocks,
        )
    except Exception as error:
        # Driver, timeout and malformed-result details may include host or
        # credentials. Collapse all failures into one stable operational fact.
        raise DatabaseMetricsUnavailable(
            "Aggregate database metrics are unavailable."
        ) from error
