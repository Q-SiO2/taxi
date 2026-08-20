import asyncio

import httpx
import pytest

from taximobile_api.operations.performance_smoke import (
    PerformanceResult,
    is_local_target,
    run_performance_smoke,
    validate_target,
)


def test_performance_result_uses_nearest_rank_percentiles() -> None:
    result = PerformanceResult(
        requests=5,
        successes=4,
        failures=1,
        duration_seconds=1.0,
        latencies_ms=(1.0, 2.0, 3.0, 4.0, 100.0),
        outcomes={"200": 4, "500": 1},
    )

    assert result.percentile_ms(0.50) == 3.0
    assert result.percentile_ms(0.95) == 100.0
    assert result.error_rate == 0.2
    assert result.as_dict()["outcomes"] == {"200": 4, "500": 1}


def test_smoke_counts_http_and_transport_failures_without_leaking_token() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert request.headers["Authorization"] == "Bearer secret-test-token"
        if calls == 2:
            raise httpx.ConnectError("private transport detail", request=request)
        return httpx.Response(200 if calls < 4 else 503)

    result = asyncio.run(
        run_performance_smoke(
            base_url="http://localhost:8000",
            path="/health",
            requests=4,
            concurrency=1,
            warmup_requests=0,
            timeout_seconds=1,
            bearer_token="secret-test-token",
            transport=httpx.MockTransport(handler),
        )
    )

    assert result.successes == 2
    assert result.failures == 2
    assert result.outcomes == {"200": 2, "transport_error": 1, "503": 1}
    assert "secret-test-token" not in str(result.as_dict())
    assert "private transport detail" not in str(result.as_dict())


@pytest.mark.parametrize("base_url", ["http://localhost:8000", "http://127.0.0.1:8000", "http://[::1]:8000"])
def test_local_target_detection(base_url: str) -> None:
    assert is_local_target(base_url)


def test_absolute_path_cannot_override_the_authorized_target() -> None:
    with pytest.raises(ValueError, match="relative API path"):
        validate_target("http://localhost:8000", "//untrusted.example/private")
