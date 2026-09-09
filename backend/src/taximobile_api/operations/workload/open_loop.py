"""Bounded constant-arrival passenger workload with saturation evidence."""

import asyncio
from time import perf_counter
from uuid import uuid4

import httpx

from .client import StepFailure
from .config import OpenLoopPassengerWorkloadConfig
from .metrics import WorkloadMetrics, latency_summary
from .passenger import PassengerClient


async def _wait_until_or_stopped(deadline: float, stopped: asyncio.Event) -> bool:
    delay = deadline - perf_counter()
    if delay <= 0:
        return stopped.is_set()
    try:
        await asyncio.wait_for(stopped.wait(), timeout=delay)
        return True
    except TimeoutError:
        return stopped.is_set()


async def run_open_loop_passenger_workload(
    config: OpenLoopPassengerWorkloadConfig,
    *,
    transport=None,
) -> dict:
    """Release arrivals independently of response time while bounding all work.

    The actor queue is both the concurrency limit and the backpressure boundary.
    A failed journey stops future release. Already released arrivals either finish
    or observe the stop flag before issuing a write; ambiguous commands remain in
    the aggregate report for manual reconciliation.
    """

    metrics = WorkloadMetrics(run_id=uuid4().hex)
    stopped = asyncio.Event()
    total_started = perf_counter()
    admission_seconds = 0.0
    measurement_started: float | None = None
    released_arrivals = 0
    arrival_lags: list[float] = []
    waiting = 0
    peak_waiting = 0
    in_flight = 0
    peak_in_flight = 0
    planned = config.users * config.journeys_per_user

    async with httpx.AsyncClient(
        base_url=config.base_url.rstrip("/"),
        timeout=config.request_timeout_seconds,
        limits=httpx.Limits(
            max_connections=config.users,
            max_keepalive_connections=config.users,
        ),
        follow_redirects=False,
        trust_env=False,
        transport=transport,
    ) as http:
        actors = [PassengerClient(http, config, metrics) for _ in range(config.users)]
        available: asyncio.Queue[PassengerClient] = asyncio.Queue(maxsize=config.users)
        for actor in actors:
            available.put_nowait(actor)

        async def execute_arrival(due_at: float) -> None:
            nonlocal waiting, peak_waiting, in_flight, peak_in_flight
            waiting += 1
            peak_waiting = max(peak_waiting, waiting)
            try:
                actor = await available.get()
            finally:
                waiting -= 1
            try:
                if stopped.is_set():
                    return
                lag_ms = max(0.0, (perf_counter() - due_at) * 1000)
                arrival_lags.append(lag_ms)
                in_flight += 1
                peak_in_flight = max(peak_in_flight, in_flight)
                try:
                    await actor.journey()
                except StepFailure:
                    stopped.set()
                finally:
                    in_flight -= 1
            finally:
                available.put_nowait(actor)

        try:
            async with asyncio.timeout(config.duration_seconds):
                admission_started = perf_counter()
                for index, actor in enumerate(actors):
                    await actor.provision(index)
                admission_seconds = perf_counter() - admission_started
                measurement_started = perf_counter()
                interval = 1.0 / config.arrival_rate_per_second
                async with asyncio.TaskGroup() as group:
                    for index in range(planned):
                        due_at = measurement_started + index * interval
                        if await _wait_until_or_stopped(due_at, stopped):
                            break
                        released_arrivals += 1
                        group.create_task(execute_arrival(due_at))
        except StepFailure:
            stopped.set()
        except TimeoutError:
            metrics.deadline_exceeded = True
            stopped.set()

    total_elapsed = perf_counter() - total_started
    measurement_elapsed = (
        max(0.0, perf_counter() - measurement_started)
        if measurement_started is not None
        else 0.0
    )
    report = metrics.report(
        elapsed=measurement_elapsed or total_elapsed,
        planned=planned,
        p95_budget_ms=config.p95_budget_ms,
    )
    lag_over_budget = sum(value > config.arrival_lag_budget_ms for value in arrival_lags)
    report["scenario"] = "passenger_request_cancel_open_loop_v1"
    report["passed"] = report["passed"] and released_arrivals == planned and lag_over_budget == 0
    report["total_elapsed_seconds"] = round(total_elapsed, 3)
    report["measurement_elapsed_seconds"] = round(measurement_elapsed, 3)
    report["admission_seconds"] = round(admission_seconds, 3)
    report["load_shape"] = {
        "model": "OPEN_LOOP_CONSTANT_ARRIVAL",
        "users": config.users,
        "max_in_flight": config.users,
        "journeys_per_user": config.journeys_per_user,
        "planned_arrivals": planned,
        "released_arrivals": released_arrivals,
        "arrival_rate_per_second": config.arrival_rate_per_second,
        "arrival_interval_seconds": round(1.0 / config.arrival_rate_per_second, 6),
        "arrival_lag_budget_ms": config.arrival_lag_budget_ms,
        "arrival_lag_over_budget": lag_over_budget,
        "arrival_lag_ms": latency_summary(arrival_lags),
        "peak_in_flight": peak_in_flight,
        "peak_waiting_for_actor": peak_waiting,
        "request_timeout_seconds": config.request_timeout_seconds,
        "duration_limit_seconds": config.duration_seconds,
        "admission_excluded_from_measurement": True,
    }
    return report
