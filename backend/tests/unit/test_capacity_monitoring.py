import asyncio
import json

import httpx
import pytest

from taximobile_api.operations.capacity_plan import main
from taximobile_api.operations.workload import capacity_plan as capacity_plan_module
from taximobile_api.operations.workload.capacity_plan import run_capacity_plan
from taximobile_api.operations.workload.capacity_profile import CapacityProfile
from taximobile_api.operations.workload.monitoring import (
    COUNTER_METRICS,
    PROMETHEUS_QUERIES,
    THRESHOLD_CHECKS,
    PrometheusPhaseSampler,
    _summary,
)

from test_capacity_plan import profile_document
from test_passenger_workload import SyntheticAPI


def thresholds():
    return dict(profile_document()["operational_thresholds"])


def values(**overrides):
    result = {
        "core_targets_up": 1,
        "http_request_rate_per_second": 1,
        "http_5xx_ratio": 0,
        "http_p95_latency_seconds": .1,
        "worker_seconds_since_success": 1,
        "worker_errors_total": 0,
        "outbox_pending_events": 0,
        "outbox_oldest_pending_age_seconds": 0,
        "outbox_dead_letter_events": 0,
        "unhandled_errors_total": 0,
        "log_dropped_lines_total": 0,
        "log_delivery_failures_total": 0,
        "database_metrics_up": 1,
        "database_connection_utilization_ratio": .1,
        "database_active_connections": 10,
        "database_waiting_locks": 0,
        "database_deadlocks_total": 0,
        "database_pool_metrics_up": 1,
        "database_pool_checked_out": 1,
        "database_pool_overflow": 0,
        "database_pool_checkout_wait_p95_seconds": .01,
        "database_pool_checkout_timeouts_total": 0,
    }
    result.update(overrides)
    return result


class PrometheusAPI:
    def __init__(self, metric_values=None, defect=None):
        self.metric_values = metric_values or values()
        self.defect = defect
        self.calls = []

    async def __call__(self, request):
        assert request.method == "GET" and request.url.path == "/api/v1/query"
        expression = request.url.params["query"]
        self.calls.append(expression)
        name = next(name for name, query in PROMETHEUS_QUERIES.items() if query == expression)
        if self.defect == "http":
            return httpx.Response(503, text="private-monitoring-response")
        if self.defect == "redirect":
            return httpx.Response(307, headers={"Location": "https://untrusted.example"})
        if self.defect == "oversized":
            return httpx.Response(200, content=b"x" * 65537)
        metric = {"instance": "private-host:8000"} if self.defect == "label" else {}
        result = [{"metric": metric, "value": [1, str(self.metric_values[name])]}]
        if self.defect == "multiple":
            result.append({"metric": {}, "value": [1, "0"]})
        if self.defect == "nonfinite":
            result[0]["value"][1] = "NaN"
        return httpx.Response(200, json={
            "status": "success",
            "data": {"resultType": "vector", "result": result},
        })


def sampler(api, **overrides):
    return PrometheusPhaseSampler(
        "http://127.0.0.1:9090",
        sample_interval_seconds=5,
        query_timeout_seconds=2,
        thresholds=thresholds(),
        confirm_monitoring_target=True,
        confirm_nonlocal_target=False,
        transport=httpx.MockTransport(api),
        **overrides,
    )


def sample_once(instance):
    async def scenario():
        stopped = asyncio.Event()
        stopped.set()
        return await instance.sample_until(stopped)

    return asyncio.run(scenario())


def test_fixed_aggregate_queries_produce_complete_private_evidence():
    api = PrometheusAPI()
    report = sample_once(sampler(api))
    assert report["status"] == "COMPLETE"
    assert report["sample_rounds"] == 1
    assert report["query_failures"] == {}
    assert report["threshold_failures"] == []
    assert set(report["metrics"]) == set(PROMETHEUS_QUERIES)
    assert sorted(api.calls) == sorted(PROMETHEUS_QUERIES.values())
    serialized = json.dumps(report)
    assert "127.0.0.1" not in serialized
    assert "private-host" not in serialized
    assert not any(expression in serialized for expression in PROMETHEUS_QUERIES.values())


def test_threshold_breach_fails_evidence_without_changing_observation():
    api = PrometheusAPI(values(http_p95_latency_seconds=1.5))
    report = sample_once(sampler(api))
    assert report["status"] == "INCOMPLETE"
    assert report["query_failures"] == {}
    assert report["threshold_failures"] == ["http_p95_latency_seconds_max"]
    assert report["metrics"]["http_p95_latency_seconds"]["max"] == 1.5


def test_pool_wait_breach_and_timeout_counter_are_part_of_capacity_evidence():
    api = PrometheusAPI(values(database_pool_checkout_wait_p95_seconds=0.2))

    report = sample_once(sampler(api))

    assert report["status"] == "INCOMPLETE"
    assert report["threshold_failures"] == [
        "database_pool_checkout_wait_p95_seconds_max"
    ]
    assert "database_pool_checkout_timeouts_total" in COUNTER_METRICS
    assert THRESHOLD_CHECKS["database_pool_checkout_timeouts_increase_max"] == (
        "database_pool_checkout_timeouts_total",
        "increase",
        "maximum",
    )


@pytest.mark.parametrize("defect,outcome", [
    ("http", "http_503"),
    ("redirect", "http_307"),
    ("oversized", "oversized_response"),
    ("label", "invalid_response"),
    ("multiple", "invalid_response"),
    ("nonfinite", "invalid_response"),
])
def test_invalid_or_labelled_prometheus_results_fail_closed(defect, outcome):
    report = sample_once(sampler(PrometheusAPI(defect=defect)))
    assert report["status"] == "INCOMPLETE"
    assert len(report["query_failures"]) == len(PROMETHEUS_QUERIES)
    assert all(key.endswith(f":{outcome}") for key in report["query_failures"])
    serialized = json.dumps(report)
    assert "private-monitoring-response" not in serialized
    assert "untrusted.example" not in serialized
    assert "private-host" not in serialized


def test_counter_summary_handles_restart_without_negative_increase():
    summary = _summary([2, 5, 1, 4], counter=True)
    assert summary["increase"] == 7
    assert summary["min"] == 1 and summary["max"] == 5


@pytest.mark.parametrize("kwargs", [
    {"origin": "http://secret:password@localhost:9090"},
    {"origin": "http://localhost:9090/api/v1"},
    {"origin": "http://remote.example:9090"},
    {"origin": "https://remote.example", "confirm_nonlocal_target": False},
    {"origin": "http://localhost:9090", "confirm_monitoring_target": False},
    {"origin": "http://localhost:9090", "sample_interval_seconds": 4},
    {"origin": "http://localhost:9090", "query_timeout_seconds": 5},
    {
        "origin": "http://localhost:9090",
        "thresholds": {**thresholds(), "worker_errors_increase_max": 1_000_000_001},
    },
])
def test_monitoring_target_and_timing_guards(kwargs):
    arguments = {
        "origin": "http://localhost:9090",
        "sample_interval_seconds": 5,
        "query_timeout_seconds": 2,
        "thresholds": thresholds(),
        "confirm_monitoring_target": True,
        "confirm_nonlocal_target": False,
    }
    arguments.update(kwargs)
    with pytest.raises(ValueError):
        PrometheusPhaseSampler(**arguments)


def test_complete_monitoring_is_attached_to_every_capacity_phase():
    profile = CapacityProfile.from_dict(profile_document())
    config = profile.phase_config(
        profile.phases[0],
        base_url="http://127.0.0.1:8000",
        confirm_synthetic_target=True,
        confirm_nonlocal_target=False,
    )
    workload_api = SyntheticAPI(config)
    monitoring_api = PrometheusAPI()
    monitor = sampler(monitoring_api)
    report = asyncio.run(run_capacity_plan(
        profile,
        base_url="http://127.0.0.1:8000",
        confirm_synthetic_target=True,
        confirm_nonlocal_target=False,
        transport=httpx.MockTransport(workload_api),
        monitoring_sampler=monitor,
    ))
    assert report["passed"] is True
    assert report["workload_passed"] is True
    assert report["monitoring_evidence_complete"] is True
    assert all(phase["monitoring"]["status"] == "COMPLETE" for phase in report["phases"])
    assert len(monitoring_api.calls) == len(PROMETHEUS_QUERIES) * 4


def test_workload_exception_stops_and_awaits_monitoring(monkeypatch):
    sampled = asyncio.Event()
    released = asyncio.Event()

    class Monitoring:
        async def sample_until(self, stopped):
            sampled.set()
            await stopped.wait()
            released.set()
            return {"status": "COMPLETE"}

    async def fail_workload(*_args, **_kwargs):
        await sampled.wait()
        raise RuntimeError("synthetic workload failure")

    monkeypatch.setattr(
        capacity_plan_module,
        "run_open_loop_passenger_workload",
        fail_workload,
    )
    profile = CapacityProfile.from_dict(profile_document())
    with pytest.raises(RuntimeError, match="synthetic workload failure"):
        asyncio.run(run_capacity_plan(
            profile,
            base_url="http://127.0.0.1:8000",
            confirm_synthetic_target=True,
            confirm_nonlocal_target=False,
            monitoring_sampler=Monitoring(),
        ))
    assert released.is_set()


def test_cli_requires_exactly_one_monitoring_mode_after_profile_validation(tmp_path, capsys):
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps(profile_document()), encoding="utf-8")
    base = [
        "--profile", str(profile_path),
        "--confirm-synthetic-target",
        "--confirm-approved-profile",
    ]
    assert main(base) == 2
    assert "Prometheus URL" in capsys.readouterr().err
    assert main(base + [
        "--prometheus-url", "http://127.0.0.1:9090",
        "--confirm-monitoring-target",
        "--confirm-harness-without-monitoring",
    ]) == 2
    assert "Prometheus URL" in capsys.readouterr().err
