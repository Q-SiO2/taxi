"""Shared bounded HTTP actor for synthetic passenger and driver workloads."""

import asyncio
import json
from time import perf_counter
from uuid import UUID

import httpx

from .config import PassengerWorkloadConfig
from .metrics import StepMetrics, WorkloadMetrics


class StepFailure(Exception):
    """Contains only a closed step and outcome, never a response or exception."""


class WorkloadClient:
    def __init__(self, client: httpx.AsyncClient, config: PassengerWorkloadConfig, metrics: WorkloadMetrics):
        self.client, self.config, self.metrics = client, config, metrics
        self.token: str | None = None

    async def request(self, step: str, method: str, path: str, expected: int, *, payload=None, key=None) -> dict:
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        if key is not None:
            headers["Idempotency-Key"] = key
        started = perf_counter()
        outcome = "interrupted"
        try:
            # httpx's per-I/O timeout alone does not bound slow trickle responses.
            async with asyncio.timeout(self.config.request_timeout_seconds):
                async with self.client.stream(method, path, headers=headers, json=payload) as response:
                    if response.status_code != expected:
                        outcome = f"http_{response.status_code}"
                        raise StepFailure()
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > 65536:
                            outcome = "oversized_response"
                            raise StepFailure()
                    try:
                        result = json.loads(body)
                    except (ValueError, UnicodeError, RecursionError):
                        outcome = "invalid_json"
                        raise StepFailure() from None
                    if not isinstance(result, dict):
                        outcome = "invalid_shape"
                        raise StepFailure()
                    outcome = "ok"
                    return result
        except (httpx.HTTPError, TimeoutError):
            outcome = "transport_error"
            raise StepFailure() from None
        finally:
            self.metrics.steps.setdefault(step, StepMetrics()).record(
                (perf_counter() - started) * 1000, outcome,
            )
            if outcome != "ok":
                self.metrics.failures[f"{step}:{outcome}"] += 1

    def check(self, condition: bool, step: str) -> None:
        if not condition:
            self.metrics.failures[f"{step}:invariant"] += 1
            raise StepFailure()

    def resource_id(self, body: dict, step: str) -> str:
        try:
            identifier = str(UUID(body.get("id", "")))
        except (ValueError, TypeError, AttributeError):
            self.check(False, step)
        return identifier
