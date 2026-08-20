import asyncio

import pytest

from taximobile_api.core.rate_limit import InMemoryRateLimiter, PostgresRateLimiter, rate_limit_key_hash


def allowed(limiter: InMemoryRateLimiter, key: str, *, limit: int, now: float) -> bool:
    return asyncio.run(limiter.allow(key, limit=limit, window_seconds=60, now=now))


def test_rate_limit_allows_only_the_configured_attempts_in_window() -> None:
    limiter = InMemoryRateLimiter()

    assert allowed(limiter, "login:user", limit=2, now=100)
    assert allowed(limiter, "login:user", limit=2, now=101)
    assert not allowed(limiter, "login:user", limit=2, now=102)
    assert allowed(limiter, "login:user", limit=2, now=161)


def test_rate_limit_keys_are_isolated() -> None:
    limiter = InMemoryRateLimiter()

    assert allowed(limiter, "login:first", limit=1, now=100)
    assert allowed(limiter, "login:second", limit=1, now=100)


def test_persistent_bucket_keys_do_not_contain_private_identifiers() -> None:
    key = "login:203.0.113.10:passenger@example.com"
    hashed = rate_limit_key_hash(key)

    assert len(hashed) == 64
    assert "passenger" not in hashed
    assert "203.0.113.10" not in hashed
    assert hashed == rate_limit_key_hash(key)


def test_shared_limiter_rejects_application_clock_overrides() -> None:
    limiter = PostgresRateLimiter(None)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="database time"):
        asyncio.run(limiter.allow("key", limit=1, window_seconds=60, now=100))
