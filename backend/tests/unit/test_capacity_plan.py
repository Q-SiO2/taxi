import asyncio
from copy import deepcopy
import json
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from taximobile_api.operations.capacity_plan import main
from taximobile_api.operations.workload.capacity_plan import run_capacity_plan
from taximobile_api.operations.workload.capacity_profile import CapacityProfile, load_capacity_profile

from test_passenger_workload import SyntheticAPI


def profile_document():
    return {
        "schema_version": 1,
        "profile_id": "casablanca-synthetic-harness-v1",
        "approval_status": "APPROVED",
        "approval_reference": "LOAD-LOCAL-001",
        "scenario": "passenger_request_cancel_open_loop_v1",
        "city_id": str(uuid4()),
        "pickup": [33.57, -7.59],
        "destination": [33.58, -7.61],
        "request_timeout_seconds": 5,
        "monitoring_sample_interval_seconds": 5,
        "monitoring_query_timeout_seconds": 2,
        "operational_thresholds": {
            "core_targets_up_min": 1,
            "http_5xx_ratio_max": .01,
            "http_p95_latency_seconds_max": 1,
            "worker_seconds_since_success_max": 300,
            "worker_errors_increase_max": 0,
            "outbox_pending_events_max": 100,
            "outbox_oldest_pending_age_seconds_max": 300,
            "outbox_dead_letter_events_max": 0,
            "unhandled_errors_increase_max": 0,
            "log_dropped_lines_increase_max": 0,
            "log_delivery_failures_increase_max": 0,
            "database_metrics_up_min": 1,
            "database_connection_utilization_ratio_max": .7,
            "database_active_connections_max": 70,
            "database_waiting_locks_max": 0,
            "database_deadlocks_increase_max": 0,
            "database_pool_metrics_up_min": 1,
            "database_pool_checked_out_max": 4,
            "database_pool_overflow_max": 0,
            "database_pool_checkout_wait_p95_seconds_max": 0.1,
            "database_pool_checkout_timeouts_increase_max": 0,
        },
        "cooldown_seconds": 0,
        "phases": [
            {
                "phase": phase,
                "users": 1,
                "journeys_per_user": 1,
                "arrival_rate_per_second": rate,
                "duration_seconds": 5,
                "p95_budget_ms": 60000,
                "arrival_lag_budget_ms": 60000,
            }
            for phase, rate in zip(
                ("WARMUP", "STEADY", "BURST", "RECOVERY"),
                (1, 2, 4, 1),
                strict=True,
            )
        ],
    }


def test_profile_executes_all_phases_and_emits_semantic_identity_only():
    profile = CapacityProfile.from_dict(profile_document())
    first_config = profile.phase_config(
        profile.phases[0],
        base_url="http://127.0.0.1:8000",
        confirm_synthetic_target=True,
        confirm_nonlocal_target=False,
    )
    api = SyntheticAPI(first_config)
    report = asyncio.run(run_capacity_plan(
        profile,
        base_url="http://127.0.0.1:8000",
        confirm_synthetic_target=True,
        confirm_nonlocal_target=False,
        transport=httpx.MockTransport(api),
    ))

    assert report["passed"] is True
    assert report["planned_phases"] == ["WARMUP", "STEADY", "BURST", "RECOVERY"]
    assert report["executed_phases"] == 4 and report["unexecuted_phases"] == []
    assert report["planned_arrivals"] == report["released_arrivals"] == 4
    assert report["completed_journeys"] == 4
    assert report["unresolved_ride_commands"] == 0
    assert report["monitoring_evidence_complete"] is False
    assert len(report["profile_sha256"]) == 64
    assert profile.semantic_digest() == CapacityProfile.from_dict(
        json.loads(json.dumps(profile_document() | {"city_id": str(profile.city_id)}))
    ).semantic_digest()
    serialized = json.dumps(report)
    assert "127.0.0.1" not in serialized
    assert str(profile.city_id) not in serialized
    assert "33.57" not in serialized and "-7.59" not in serialized


def test_failed_phase_prevents_later_phase_execution():
    profile = CapacityProfile.from_dict(profile_document())
    config = profile.phase_config(
        profile.phases[0],
        base_url="http://127.0.0.1:8000",
        confirm_synthetic_target=True,
        confirm_nonlocal_target=False,
    )
    api = SyntheticAPI(config)

    async def handler(request):
        if request.url.path.endswith("/estimate"):
            return httpx.Response(503)
        return await api(request)

    report = asyncio.run(run_capacity_plan(
        profile,
        base_url="http://127.0.0.1:8000",
        confirm_synthetic_target=True,
        confirm_nonlocal_target=False,
        transport=httpx.MockTransport(handler),
    ))
    assert report["passed"] is False
    assert report["executed_phases"] == 1
    assert report["unexecuted_phases"] == ["STEADY", "BURST", "RECOVERY"]
    assert report["released_arrivals"] == 1


@pytest.mark.parametrize("mutation", [
    lambda value: value.update(extra="rejected"),
    lambda value: value.update(schema_version=2),
    lambda value: value.update(approval_status="DRAFT"),
    lambda value: value.update(approval_reference="free text rejected"),
    lambda value: value.update(profile_id="UPPERCASE"),
    lambda value: value.update(scenario="another_scenario"),
    lambda value: value.update(city_id="invalid"),
    lambda value: value.update(pickup=[91, 0]),
    lambda value: value.update(cooldown_seconds=61),
    lambda value: value.update(monitoring_sample_interval_seconds=4),
    lambda value: value.update(monitoring_query_timeout_seconds=5),
    lambda value: value["operational_thresholds"].update(extra=1),
    lambda value: value["operational_thresholds"].update(core_targets_up_min=2),
    lambda value: value["phases"].reverse(),
    lambda value: value["phases"][0].update(extra="rejected"),
    lambda value: value["phases"][0].update(users=True),
    lambda value: value["phases"][0].update(arrival_rate_per_second=float("inf")),
])
def test_profile_rejects_unknown_unapproved_or_unbounded_input(mutation):
    document = profile_document()
    mutation(document)
    with pytest.raises(ValueError):
        CapacityProfile.from_dict(document)


def test_profile_rejects_aggregate_arrival_and_duration_excess():
    arrivals = profile_document()
    for phase in arrivals["phases"]:
        phase["users"] = 50
        phase["journeys_per_user"] = 6
    with pytest.raises(ValueError, match="1000 total arrivals"):
        CapacityProfile.from_dict(arrivals)

    duration = profile_document()
    for phase in duration["phases"]:
        phase["duration_seconds"] = 600
    duration["cooldown_seconds"] = 1
    with pytest.raises(ValueError, match="2400 total seconds"):
        CapacityProfile.from_dict(duration)


def test_profile_file_boundary_rejects_symlink_oversize_and_invalid_json(tmp_path: Path):
    valid = tmp_path / "profile.json"
    valid.write_text(json.dumps(profile_document()), encoding="utf-8")
    assert load_capacity_profile(valid).profile_id == "casablanca-synthetic-harness-v1"

    invalid = tmp_path / "invalid.json"
    invalid.write_text("not-json", encoding="utf-8")
    with pytest.raises(ValueError, match="valid bounded"):
        load_capacity_profile(invalid)

    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b"x" * 65537)
    with pytest.raises(ValueError, match="64 KiB"):
        load_capacity_profile(oversized)

    link = tmp_path / "link.json"
    try:
        link.symlink_to(valid)
    except OSError:
        return
    with pytest.raises(ValueError, match="non-symlink"):
        load_capacity_profile(link)


def test_repository_template_is_valid_but_deliberately_not_executable():
    template = (
        Path(__file__).resolve().parents[3]
        / "infra"
        / "load"
        / "capacity-profile.template.json"
    )
    document = json.loads(template.read_text(encoding="utf-8"))
    assert document["approval_status"] == "DRAFT"
    with pytest.raises(ValueError, match="APPROVED"):
        CapacityProfile.from_dict(document)
    document["approval_status"] = "APPROVED"
    profile = CapacityProfile.from_dict(document)
    assert [phase.phase for phase in profile.phases] == [
        "WARMUP", "STEADY", "BURST", "RECOVERY",
    ]


def test_cli_requires_profile_confirmation_before_reading_file(capsys):
    assert main(["--profile", "does-not-exist.json", "--confirm-synthetic-target"]) == 2
    assert "Confirm the reviewed capacity profile" in capsys.readouterr().err
