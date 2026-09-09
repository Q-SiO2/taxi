import asyncio
import json
from uuid import uuid4

import httpx
import pytest

from taximobile_api.operations.passenger_workload import main
from taximobile_api.operations.workload.config import PassengerWorkloadConfig
from taximobile_api.operations.workload.metrics import StepMetrics, WorkloadMetrics, latency_summary
from taximobile_api.operations.workload.passenger import run_passenger_workload


def configuration(**overrides):
    return PassengerWorkloadConfig(**{
        "base_url": "http://127.0.0.1:8000", "city_id": uuid4(),
        "pickup": (33.57, -7.59), "destination": (33.58, -7.61),
        "confirm_synthetic_target": True, "users": 2, "journeys_per_user": 2,
        "interval_seconds": 0, **overrides,
    })


class SyntheticAPI:
    """Strict fake asserts commands, ownership, stable keys and role separation."""

    def __init__(self, config):
        self.config = config
        self.calls = []
        self.accounts = {}
        self.user_ids = {}
        self.commands = {}
        self.rides = {}

    async def __call__(self, request):
        await asyncio.sleep(0)  # Exercise concurrent actors, not only serial fakes.
        path = request.url.path
        payload = json.loads(request.content) if request.content else {}
        self.calls.append((request.method, path, dict(request.headers), payload))
        if path == "/api/v1/auth/register":
            assert payload["email"].endswith("@taximobile.invalid")
            assert "phone_number" not in payload
            self.accounts[payload["email"]] = payload["password"]
            self.user_ids[payload["email"]] = str(uuid4())
            return httpx.Response(201, json={"user": {"id": self.user_ids[payload["email"]]}})
        if path == "/api/v1/auth/login":
            assert self.accounts[payload["identifier"]] == payload["password"]
            return httpx.Response(200, json={"access_token": f"secret-{payload['identifier']}"})
        owner = request.headers.get("Authorization")
        assert owner and owner.startswith("Bearer secret-")
        if path == "/api/v1/me":
            return httpx.Response(200, json={"id": self.user_ids[owner.removeprefix("Bearer secret-")],
                                             "roles": ["PASSENGER"]})
        if path.endswith("/estimate"):
            assert payload == self.config.ride_payload()
            return httpx.Response(200, json={"estimate": {"city_id": str(self.config.city_id)},
                                             "payment_methods": ["CASH"]})
        key = request.headers.get("Idempotency-Key")
        if key and (owner, key) in self.commands:
            saved_payload, status, result = self.commands[owner, key]
            assert saved_payload == payload
            return httpx.Response(status, json=result)
        if path == "/api/v1/rides":
            assert payload == {**self.config.ride_payload(), "payment_method": "CASH"}
            assert key
            ride_id = str(uuid4())
            body = {"id": ride_id, "status": "MATCHING", "city_id": str(self.config.city_id),
                    "payment_method": "CASH", "driver": None}
            self.rides[ride_id] = (owner, body)
            self.commands[owner, key] = (payload, 201, dict(body))
            return httpx.Response(201, json=body)
        ride_id = path.split("/")[4]
        ride_owner, ride = self.rides[ride_id]
        assert ride_owner == owner
        if path.endswith("/cancel"):
            assert key
            ride["status"] = "CANCELLED"
            self.commands[owner, key] = (payload, 200, dict(ride))
        return httpx.Response(200, json=ride)


def run(config, handler):
    return asyncio.run(run_passenger_workload(config, transport=httpx.MockTransport(handler)))


def test_complete_concurrent_workload_is_aggregate_and_checks_exact_replays():
    config = configuration()
    api = SyntheticAPI(config)
    report = run(config, api)
    assert report["passed"]
    assert report["completed_journeys"] == 4
    assert report["unresolved_ride_commands"] == 0
    assert len(api.accounts) == 2 and len(api.rides) == 4
    assert all(ride["status"] == "CANCELLED" for _, ride in api.rides.values())
    assert sum(value["requests"] for value in report["steps"].values()) == 34
    serialized = json.dumps(report)
    for email, password in api.accounts.items():
        assert email not in serialized and password not in serialized
    for ride_id in api.rides:
        assert ride_id not in serialized
    assert "127.0.0.1" not in serialized and "secret-" not in serialized


@pytest.mark.parametrize("override", [
    {"confirm_synthetic_target": False}, {"confirm_synthetic_target": 1},
    {"base_url": "http://staging.example"}, {"base_url": "https://staging.example"},
    {"base_url": "http://secret:password@localhost"},
    {"base_url": "http://localhost/api/v1"}, {"base_url": "http://localhost/?token=secret"},
    {"base_url": "http://localhost/#secret"}, {"base_url": "http://localhost:99999"},
    {"base_url": "http://local host"}, {"base_url": "http://localhost\\@evil.example"},
    {"users": 0}, {"users": 51}, {"users": True}, {"journeys_per_user": 101},
    {"request_timeout_seconds": float("inf")}, {"duration_seconds": float("nan")},
    {"interval_seconds": -1}, {"p95_budget_ms": 0}, {"pickup": (float("nan"), 0)},
    {"destination": (0, 181)}, {"city_id": "not-a-uuid"},
])
def test_invalid_workload_is_rejected_before_network(override):
    with pytest.raises(ValueError):
        configuration(**override)


def test_nonlocal_requires_both_confirmation_and_tls():
    assert configuration(base_url="https://staging.example", confirm_nonlocal_target=True)
    with pytest.raises(ValueError):
        configuration(base_url="http://staging.example", confirm_nonlocal_target=True)


@pytest.mark.parametrize("failure", ["rate_limit", "redirect", "invalid_json", "array", "oversized", "wrong_role", "wrong_user"])
def test_failed_admission_never_starts_ride_writes_or_logs_responses(failure):
    config = configuration()
    api = SyntheticAPI(config)

    async def handler(request):
        if request.url.path == "/api/v1/me":
            return {
                "rate_limit": httpx.Response(429, text="private-response"),
                "redirect": httpx.Response(307, headers={"Location": "https://untrusted.example"}),
                "invalid_json": httpx.Response(200, text="private-response"),
                "array": httpx.Response(200, json=[]),
                "oversized": httpx.Response(200, content=b"x" * 65537),
                "wrong_role": httpx.Response(200, json={"roles": ["PASSENGER", "ADMIN"]}),
                "wrong_user": httpx.Response(200, json={"id": str(uuid4()), "roles": ["PASSENGER"]}),
            }[failure]
        return await api(request)

    report = run(config, handler)
    assert not report["passed"] and report["started_journeys"] == 0
    assert not api.rides
    assert "private-response" not in json.dumps(report)
    assert "untrusted" not in json.dumps(report)


def test_ambiguous_create_recovers_same_command_and_cancels_but_run_stays_failed():
    config = configuration(users=1, journeys_per_user=3)
    api = SyntheticAPI(config)
    lost = False

    async def handler(request):
        nonlocal lost
        response = await api(request)
        if request.url.path == "/api/v1/rides" and not lost:
            lost = True
            raise httpx.ReadTimeout("private-request-with-token", request=request)
        return response

    report = run(config, handler)
    assert not report["passed"]
    assert report["started_journeys"] == 1 and report["not_started_journeys"] == 2
    assert report["unresolved_ride_commands"] == 0
    assert len(api.rides) == 1
    assert report["failures"] == {"create:transport_error": 1}
    assert report["steps"]["recover_create"]["requests"] == 1
    assert "private-request" not in json.dumps(report)


@pytest.mark.parametrize("defect", ["changed_replay", "wrong_city", "assigned_driver", "cancel_failure", "terminal_lie"])
def test_invariant_failures_stop_and_report_unresolved_commands(defect):
    config = configuration(users=1, journeys_per_user=2)
    api = SyntheticAPI(config)
    reads = 0

    async def handler(request):
        nonlocal reads
        response = await api(request)
        body = response.json()
        if defect == "changed_replay" and request.url.path == "/api/v1/rides" and len(api.rides) == 1:
            if sum(path == "/api/v1/rides" for _, path, _, _ in api.calls) == 2:
                body["status"] = "CANCELLED"
        if request.method == "GET" and "/rides/" in request.url.path:
            reads += 1
            if defect == "wrong_city":
                body["city_id"] = str(uuid4())
            if defect == "assigned_driver" and reads == 1:
                body["driver"] = {"display_name": "never-print-personal-data"}
            if defect == "terminal_lie" and reads > 1:
                body["status"] = "MATCHING"
        if defect == "cancel_failure" and request.url.path.endswith("/cancel"):
            return httpx.Response(503)
        return httpx.Response(response.status_code, json=body)

    report = run(config, handler)
    assert not report["passed"] and report["started_journeys"] == 1
    assert report["unresolved_ride_commands"] == (1 if defect in {"cancel_failure", "terminal_lie"} else 0)
    assert "never-print" not in json.dumps(report)


def test_request_deadline_bounds_transport_and_global_deadline_reports_partial_run():
    async def scenario(global_deadline):
        config = configuration(users=1, journeys_per_user=1, duration_seconds=1,
                               request_timeout_seconds=2 if global_deadline else .1)
        api = SyntheticAPI(config)

        async def handler(request):
            if request.url.path == "/api/v1/rides":
                await asyncio.sleep(10)
            return await api(request)

        return await asyncio.wait_for(run_passenger_workload(
            config, transport=httpx.MockTransport(handler)), timeout=3)

    for global_deadline in (False, True):
        report = asyncio.run(scenario(global_deadline))
        assert not report["passed"] and report["unresolved_ride_commands"] == 1
        assert report["deadline_exceeded"] is global_deadline


def test_external_cancellation_is_not_converted_to_success():
    async def scenario():
        entered = asyncio.Event()

        async def handler(request):
            entered.set()
            await asyncio.Event().wait()

        task = asyncio.create_task(run_passenger_workload(
            configuration(), transport=httpx.MockTransport(handler)))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())


def test_nearest_rank_budget_is_per_step_not_hidden_by_other_fast_requests():
    assert latency_summary([1, 2, 3, 4, 100])["p95"] == 100
    metrics = WorkloadMetrics("synthetic")
    metrics.started = metrics.completed = 1
    metrics.steps["fast"] = StepMetrics(samples=[1] * 1000)
    metrics.steps["slow"] = StepMetrics(samples=[2000])
    report = metrics.report(elapsed=1, planned=1, p95_budget_ms=1000)
    assert not report["passed"] and report["steps_over_budget"] == ["slow"]
    metrics.steps["slow"].samples = [1000.00001]
    assert not metrics.report(elapsed=1, planned=1, p95_budget_ms=1000)["passed"]


def test_cli_missing_confirmation_has_fixed_diagnostic(capsys):
    assert main(["--city-id", str(uuid4()), "--pickup", "0", "0",
                 "--destination", "1", "1"]) == 2
    assert "Confirm an isolated synthetic-only target" in capsys.readouterr().err
