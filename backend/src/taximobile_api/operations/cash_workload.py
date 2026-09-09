"""Bounded passenger/driver cash simulation; no real transport or cash movement."""

import asyncio
import json
from os import environ
import sys
from time import perf_counter
from uuid import uuid4

import httpx

from .passenger_workload import parser
from .workload.cash_journey import CashPassengerClient
from .workload.client import StepFailure
from .workload.config import PassengerWorkloadConfig
from .workload.drivers import DriverClient, parse_driver_credentials
from .workload.metrics import WorkloadMetrics


async def run_cash_workload(config, credentials, *, confirm_synthetic_cash=False, transport=None):
    if confirm_synthetic_cash is not True or len(credentials) != config.users:
        raise ValueError("Confirm simulated cash and supply one distinct synthetic driver per passenger.")
    # Validate library callers too; do not rely exclusively on CLI admission.
    credentials = parse_driver_credentials(json.dumps([
        {"user_id": str(item.user_id), "access_token": item.access_token} for item in credentials
    ]), count=config.users)
    metrics = WorkloadMetrics(run_id=uuid4().hex)
    started = perf_counter()
    offline_unconfirmed = set()
    async with httpx.AsyncClient(
        base_url=config.base_url.rstrip("/"), timeout=config.request_timeout_seconds,
        limits=httpx.Limits(max_connections=config.users * 2, max_keepalive_connections=config.users * 2),
        follow_redirects=False, trust_env=False, transport=transport,
    ) as http:
        drivers = [DriverClient(http, config, metrics, item) for item in credentials]
        passengers = [CashPassengerClient(http, config, metrics) for _ in range(config.users)]

        async def journey(actor):
            try:
                await actor.cash_journey(drivers)
            except StepFailure:
                pass  # The actor records failure and unresolved financial state.

        async def execute():
            # All driver identity/scope checks are read-only and precede
            # passenger admission, GPS writes, online commands and ride writes.
            for driver in drivers:
                await driver.preflight()
            for index, passenger in enumerate(passengers):
                await passenger.provision(index)
            for wave in range(config.journeys_per_user):
                if metrics.failures:
                    break
                for driver in drivers:
                    offline_unconfirmed.add(driver.expected_user_id)
                    await driver.ready()
                async with asyncio.TaskGroup() as group:
                    for passenger in passengers:
                        group.create_task(journey(passenger))
                if wave + 1 < config.journeys_per_user and not metrics.failures:
                    await asyncio.sleep(config.interval_seconds)

        try:
            async with asyncio.timeout(config.duration_seconds):
                try:
                    await execute()
                except StepFailure:
                    pass
                # Setup failure still restores an AVAILABLE synthetic driver to
                # OFFLINE; active-ride states are never forced offline. Cleanup
                # shares the run deadline rather than silently extending it.
                for driver in drivers:
                    if driver.touched:
                        try:
                            await driver.confirm_offline()
                            offline_unconfirmed.discard(driver.expected_user_id)
                        except StepFailure:
                            pass
        except TimeoutError:
            metrics.deadline_exceeded = True
    result = metrics.report(elapsed=perf_counter() - started, planned=config.users * config.journeys_per_user,
                            p95_budget_ms=config.p95_budget_ms)
    result["scenario"] = "paired_cash_complete_v1"
    result["drivers_not_confirmed_offline"] = len(offline_unconfirmed)
    result["passed"] = result["passed"] and not offline_unconfirmed
    result["load_shape"] = {
        "model": "CLOSED_LOOP_SYNCHRONIZED_WAVES", "users": config.users,
        "drivers": len(drivers), "journeys_per_user": config.journeys_per_user,
        "interval_seconds": config.interval_seconds, "duration_limit_seconds": config.duration_seconds,
        "request_timeout_seconds": config.request_timeout_seconds, "admission_included_in_elapsed": True,
    }
    return result


def main(argv=None):
    command = parser(description=__doc__)
    command.add_argument("--confirm-synthetic-cash", action="store_true")
    args = vars(command.parse_args(argv))
    confirmed = args.pop("confirm_synthetic_cash")
    try:
        if confirmed is not True:
            raise ValueError("Confirm simulated cash before writing synthetic payment and earning records.")
        config = PassengerWorkloadConfig(**args)
        credentials = parse_driver_credentials(environ.pop("TAXIMOBILE_WORKLOAD_DRIVERS_JSON", ""), count=config.users)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    try:
        result = asyncio.run(run_cash_workload(config, credentials, confirm_synthetic_cash=True))
    except KeyboardInterrupt:
        print("Cash workload interrupted; reconcile synthetic rides, payments and driver availability.", file=sys.stderr)
        return 130
    except Exception:
        print("Cash workload failed unexpectedly; reconcile synthetic state before retrying.", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
