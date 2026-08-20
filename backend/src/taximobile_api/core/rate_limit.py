"""Injectable local and shared fixed-window abuse-rate-limit adapters."""

from __future__ import annotations

from collections import defaultdict, deque
from hashlib import sha256
from time import monotonic
from typing import Protocol

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class RateLimitUnavailable(RuntimeError):
    """The authoritative shared quota could not be checked safely."""


class RateLimiter(Protocol):
    async def allow(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: float,
        now: float | None = None,
    ) -> bool: ...


def rate_limit_key_hash(key: str) -> str:
    """Persist an irreversible bucket key instead of an email, IP, or user ID."""
    return sha256(key.encode("utf-8")).hexdigest()


class InMemoryRateLimiter:
    """Deterministic single-process adapter for development and isolated tests."""

    def __init__(self) -> None:
        self._attempts: dict[str, deque[float]] = defaultdict(deque)

    async def allow(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: float,
        now: float | None = None,
    ) -> bool:
        _validate_limit(limit, window_seconds)
        current = monotonic() if now is None else now
        attempts = self._attempts[key]
        cutoff = current - window_seconds
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()
        if len(attempts) >= limit:
            return False
        attempts.append(current)
        return True


class PostgresRateLimiter:
    """Atomic shared quotas for staging/production API instances.

    PostgreSQL statement time is authoritative so differing application-host clocks
    cannot grant extra requests. The table stores only SHA-256 bucket identifiers.
    """

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        *,
        cleanup_interval: int = 1024,
    ) -> None:
        if cleanup_interval < 1:
            raise ValueError("cleanup_interval must be positive")
        self._sessions = sessions
        self._cleanup_interval = cleanup_interval
        self._calls = 0

    async def allow(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: float,
        now: float | None = None,
    ) -> bool:
        _validate_limit(limit, window_seconds)
        if now is not None:
            raise ValueError("PostgresRateLimiter uses authoritative database time")
        key_hash = rate_limit_key_hash(key)
        self._calls += 1
        should_cleanup = self._calls % self._cleanup_interval == 0
        try:
            async with self._sessions() as session:
                async with session.begin():
                    attempts = await session.scalar(
                        text(
                            """
                            INSERT INTO rate_limit_buckets
                                (key_hash, window_started_at, expires_at, attempts)
                            VALUES
                                (:key_hash, statement_timestamp(),
                                 statement_timestamp() + (:window_seconds * interval '1 second'), 1)
                            ON CONFLICT (key_hash) DO UPDATE SET
                                attempts = CASE
                                    WHEN rate_limit_buckets.expires_at <= statement_timestamp() THEN 1
                                    ELSE LEAST(rate_limit_buckets.attempts + 1, :maximum_attempts)
                                END,
                                window_started_at = CASE
                                    WHEN rate_limit_buckets.expires_at <= statement_timestamp()
                                        THEN statement_timestamp()
                                    ELSE rate_limit_buckets.window_started_at
                                END,
                                expires_at = CASE
                                    WHEN rate_limit_buckets.expires_at <= statement_timestamp()
                                        THEN statement_timestamp()
                                             + (:window_seconds * interval '1 second')
                                    ELSE rate_limit_buckets.expires_at
                                END
                            RETURNING attempts
                            """
                        ),
                        {
                            "key_hash": key_hash,
                            "window_seconds": window_seconds,
                            "maximum_attempts": limit + 1,
                        },
                    )
                    if should_cleanup:
                        await session.execute(
                            text(
                                """
                                DELETE FROM rate_limit_buckets
                                WHERE key_hash IN (
                                    SELECT key_hash
                                    FROM rate_limit_buckets
                                    WHERE expires_at < statement_timestamp() - interval '1 hour'
                                    ORDER BY expires_at
                                    LIMIT 1000
                                )
                                """
                            )
                        )
        except SQLAlchemyError as error:
            raise RateLimitUnavailable("Shared rate limiting is unavailable.") from error
        if attempts is None:
            raise RateLimitUnavailable("Shared rate limiting returned no decision.")
        return int(attempts) <= limit


def _validate_limit(limit: int, window_seconds: float) -> None:
    if limit < 1 or window_seconds <= 0:
        raise ValueError("Rate limit and window must be positive")
