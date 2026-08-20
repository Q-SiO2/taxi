"""Asynchronous GET-only API performance smoke test with explicit budgets."""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from dataclasses import dataclass
from ipaddress import ip_address
import json
from math import ceil
from os import getenv
from time import perf_counter
import sys
from urllib.parse import urlparse

import httpx


@dataclass(frozen=True, slots=True)
class PerformanceResult:
    requests: int
    successes: int
    failures: int
    duration_seconds: float
    latencies_ms: tuple[float, ...]
    outcomes: dict[str, int]

    @property
    def error_rate(self) -> float:
        return self.failures / self.requests

    @property
    def requests_per_second(self) -> float:
        return self.requests / self.duration_seconds if self.duration_seconds > 0 else 0.0

    def percentile_ms(self, percentile: float) -> float:
        if not self.latencies_ms:
            return 0.0
        rank = max(0, ceil(percentile * len(self.latencies_ms)) - 1)
        return sorted(self.latencies_ms)[rank]

    def as_dict(self) -> dict[str, object]:
        return {
            "requests": self.requests,
            "successes": self.successes,
            "failures": self.failures,
            "error_rate": round(self.error_rate, 6),
            "duration_seconds": round(self.duration_seconds, 3),
            "requests_per_second": round(self.requests_per_second, 2),
            "latency_ms": {
                "p50": round(self.percentile_ms(0.50), 2),
                "p95": round(self.percentile_ms(0.95), 2),
                "p99": round(self.percentile_ms(0.99), 2),
                "max": round(max(self.latencies_ms, default=0.0), 2),
            },
            "outcomes": dict(sorted(self.outcomes.items())),
        }


async def run_performance_smoke(
    *,
    base_url: str,
    path: str,
    requests: int,
    concurrency: int,
    warmup_requests: int,
    timeout_seconds: float,
    bearer_token: str | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> PerformanceResult:
    validate_target(base_url, path)
    if requests < 1 or concurrency < 1 or warmup_requests < 0 or timeout_seconds <= 0:
        raise ValueError("Requests, concurrency, and timeout must be positive; warmup cannot be negative.")
    worker_count = min(concurrency, requests)
    headers = {"Authorization": f"Bearer {bearer_token}"} if bearer_token else {}
    limits = httpx.Limits(
        max_connections=worker_count,
        max_keepalive_connections=worker_count,
    )
    timeout = httpx.Timeout(timeout_seconds)
    latencies: list[float] = []
    outcomes: Counter[str] = Counter()
    queue: asyncio.Queue[int] = asyncio.Queue()
    for index in range(requests):
        queue.put_nowait(index)

    async with httpx.AsyncClient(
        base_url=base_url.rstrip("/"),
        headers=headers,
        timeout=timeout,
        limits=limits,
        transport=transport,
        follow_redirects=False,
    ) as client:
        for _ in range(warmup_requests):
            try:
                await client.get(path)
            except httpx.HTTPError:
                # Warmup is deliberately excluded from measured outcomes.
                pass

        async def worker() -> None:
            while True:
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    return
                started_at = perf_counter()
                try:
                    response = await client.get(path)
                    outcomes[str(response.status_code)] += 1
                except httpx.HTTPError:
                    outcomes["transport_error"] += 1
                finally:
                    latencies.append((perf_counter() - started_at) * 1000)
                    queue.task_done()

        started_at = perf_counter()
        await asyncio.gather(*(worker() for _ in range(worker_count)))
        duration_seconds = perf_counter() - started_at

    successes = sum(count for outcome, count in outcomes.items() if outcome.startswith("2"))
    return PerformanceResult(
        requests=requests,
        successes=successes,
        failures=requests - successes,
        duration_seconds=duration_seconds,
        latencies_ms=tuple(latencies),
        outcomes=dict(outcomes),
    )


def validate_target(base_url: str, path: str) -> None:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Base URL must be an absolute HTTP or HTTPS URL.")
    if not path.startswith("/") or path.startswith("//") or urlparse(path).scheme:
        raise ValueError("Path must be a relative API path beginning with one slash.")


def is_local_target(base_url: str) -> bool:
    hostname = urlparse(base_url).hostname
    if hostname is None:
        return False
    if hostname.rstrip(".").lower() == "localhost":
        return True
    try:
        return ip_address(hostname).is_loopback
    except ValueError:
        return False


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="Run a bounded GET-only TaxiMobile API performance smoke test.")
    command.add_argument("--base-url", default="http://127.0.0.1:8000")
    command.add_argument("--path", default="/health")
    command.add_argument("--requests", type=int, default=200)
    command.add_argument("--concurrency", type=int, default=20)
    command.add_argument("--warmup-requests", type=int, default=10)
    command.add_argument("--timeout-seconds", type=float, default=5.0)
    command.add_argument("--p95-budget-ms", type=float, default=500.0)
    command.add_argument("--max-error-rate", type=float, default=0.0)
    command.add_argument(
        "--confirm-nonlocal-target",
        action="store_true",
        help="Confirm the target is an authorized non-production staging environment.",
    )
    return command


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if not is_local_target(arguments.base_url) and not arguments.confirm_nonlocal_target:
        print("Refusing a non-local target without --confirm-nonlocal-target.", file=sys.stderr)
        return 2
    if arguments.p95_budget_ms <= 0 or not 0 <= arguments.max_error_rate <= 1:
        print("Latency budget must be positive and max error rate must be between 0 and 1.", file=sys.stderr)
        return 2
    try:
        result = asyncio.run(
            run_performance_smoke(
                base_url=arguments.base_url,
                path=arguments.path,
                requests=arguments.requests,
                concurrency=arguments.concurrency,
                warmup_requests=arguments.warmup_requests,
                timeout_seconds=arguments.timeout_seconds,
                bearer_token=getenv("TAXIMOBILE_PERF_BEARER_TOKEN"),
            )
        )
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2

    print(json.dumps(result.as_dict(), sort_keys=True))
    if result.error_rate > arguments.max_error_rate:
        return 1
    if result.percentile_ms(0.95) > arguments.p95_budget_ms:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
