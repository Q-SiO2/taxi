import asyncio
import json
from uuid import uuid4

import httpx
import pytest

from taximobile_api.operations.capacity_workload import main
from taximobile_api.operations.workload.config import OpenLoopPassengerWorkloadConfig
from taximobile_api.operations.workload.open_loop import run_open_loop_passenger_workload

from test_passenger_workload import SyntheticAPI


def configuration(**overrides):
    return OpenLoopPassengerWorkloadConfig(**{
        "base_url": "http://127.0.0.1:8000",
        "city_id": uuid4(),
        "pickup": (33.57, -7.59),
        "destination": (33.58, -7.61),
        "confirm_synthetic_target": True,
        "users": 2,
        "journeys_per_user": 2,
        "arrival_rate_per_second": 100,
        "arrival_lag_budget_ms": 60000,
        "duration_seconds": 5,
        "p95_budget_ms": 60000,
        **overrides,
    })


def run(config, handler):
    return asyncio.run(run_open_loop_passenger_workload(
        config,
        transport=httpx.MockTransport(handler),
    ))


def test_constant_arrival_workload_is_bounded_and_privacy_safe():
    config = configuration()
    api = SyntheticAPI(config)
    report = run(config, api)

    assert report["passed"]
    assert report["scenario"] == "passenger_request_cancel_open_loop_v1"
    assert report["completed_journeys"] == 4
    shape = report["load_shape"]
    assert shape["model"] == "OPEN_LOOP_CONSTANT_ARRIVAL"
    assert shape["planned_arrivals"] == shape["released_arrivals"] == 4
    assert 1 <= shape["peak_in_flight"] <= 2
    assert shape["peak_waiting_for_actor"] <= 2
    assert report["admission_seconds"] >= 0
    assert report["measurement_elapsed_seconds"] >= 0
    serialized = json.dumps(report)
    assert "127.0.0.1" not in serialized and "secret-" not in serialized
    for email, password in api.accounts.items():
        assert email not in serialized and password not in serialized
    for ride_id in api.rides:
        assert ride_id not in serialized


def test_slow_service_exposes_queue_lag_and_fails_budget():
    config = configuration(
        users=1,
        journeys_per_user=2,
        arrival_rate_per_second=100,
        arrival_lag_budget_ms=1,
    )
    api = SyntheticAPI(config)

    async def handler(request):
        if request.url.path.endswith("/estimate"):
            await asyncio.sleep(.05)
        return await api(request)

    report = run(config, handler)
    assert not report["passed"]
    assert report["completed_journeys"] == 2
    assert report["load_shape"]["arrival_lag_over_budget"] >= 1
    assert report["load_shape"]["peak_waiting_for_actor"] >= 1
    assert report["failures"] == {}


def test_first_failure_stops_future_arrival_release_without_hiding_failure():
    config = configuration(
        users=1,
        journeys_per_user=3,
        arrival_rate_per_second=2,
    )
    api = SyntheticAPI(config)

    async def handler(request):
        if request.url.path.endswith("/estimate"):
            return httpx.Response(503)
        return await api(request)

    report = run(config, handler)
    assert not report["passed"]
    assert report["load_shape"]["released_arrivals"] == 1
    assert report["started_journeys"] == 1
    assert report["not_started_journeys"] == 2
    assert report["failures"] == {"estimate:http_503": 1}
    assert report["unresolved_ride_commands"] == 0


def test_whole_run_deadline_preserves_ambiguous_command_evidence():
    config = configuration(
        users=1,
        journeys_per_user=1,
        arrival_rate_per_second=1,
        duration_seconds=1,
        request_timeout_seconds=2,
    )
    api = SyntheticAPI(config)

    async def handler(request):
        if request.url.path == "/api/v1/rides":
            await asyncio.sleep(10)
        return await api(request)

    report = asyncio.run(asyncio.wait_for(
        run_open_loop_passenger_workload(config, transport=httpx.MockTransport(handler)),
        timeout=3,
    ))
    assert not report["passed"]
    assert report["deadline_exceeded"] is True
    assert report["started_journeys"] == 1
    assert report["unresolved_ride_commands"] == 1


def test_external_cancellation_propagates_to_operator():
    async def scenario():
        entered = asyncio.Event()

        async def handler(request):
            entered.set()
            await asyncio.Event().wait()

        task = asyncio.create_task(run_open_loop_passenger_workload(
            configuration(),
            transport=httpx.MockTransport(handler),
        ))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())


@pytest.mark.parametrize("override", [
    {"arrival_rate_per_second": 0},
    {"arrival_rate_per_second": 101},
    {"arrival_rate_per_second": float("inf")},
    {"arrival_lag_budget_ms": 0},
    {"arrival_lag_budget_ms": float("nan")},
])
def test_invalid_open_loop_controls_are_rejected(override):
    with pytest.raises(ValueError):
        configuration(**override)


def test_open_loop_plan_is_strictly_bounded():
    with pytest.raises(ValueError, match="at most 1000"):
        configuration(users=50, journeys_per_user=21)


def test_cli_requires_synthetic_target_confirmation(capsys):
    assert main([
        "--city-id", str(uuid4()),
        "--pickup", "0", "0",
        "--destination", "1", "1",
    ]) == 2
    assert "Confirm an isolated synthetic-only target" in capsys.readouterr().err
