"""Validate the GAP-006 production maps, routing, and navigation record.

The committed template is deliberately ``NOT_STARTED``. A protected external
copy may accept GAP-006 only when a real launch scope is bound to versioned map
and Morocco routing artifacts, explicit license/cache/offline/refresh controls,
six field benchmark categories, four physical-device surfaces, outage and
rollback drills, and independent approvals. Accepted evidence must also bind to
the exact redacted JSON emitted by ``taximobile_api.operations.routing_acceptance``.

The record contains public artifact metadata and opaque control references. It
must not contain credentials, personal data, raw route traces, or provider
queries, and it never accepts T5 or deployment.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from math import isfinite
from pathlib import Path
import re
import sys
from typing import Any, Iterable


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE = (
    WORKSPACE_ROOT / "infra" / "deploy" / "maps-routing-navigation.template.json"
)

ROOT_KEYS = {
    "schema_version", "evidence_revision", "gap", "phase", "status",
    "data_classification", "candidate_label", "source_commit",
    "environment_inventory_reference", "database_evidence_reference",
    "pilot_city_approval_reference", "submission", "launch_scope",
    "map_delivery", "routing_artifact", "refresh_and_rollback",
    "benchmark_cases", "device_navigation", "operational_drills", "approvals",
    "gap_006_accepted", "phase_accepted", "deployment_accepted", "limitations",
}
SUBMISSION_KEYS = {"submitted_by_account_reference", "submitted_at", "change_reference"}
SCOPE_KEYS = {
    "market_code", "country_code", "city_id", "city_configuration_id",
    "service_area_reference", "quality_threshold_reference", "accepted_languages",
    "acceptance_valid_until",
}
MAP_KEYS = {
    "renderer", "style_artifact_reference", "style_version", "style_sha256",
    "tile_source_reference", "tile_source_version", "tile_catalog_sha256",
    "morocco_coverage_reference", "license_review_reference",
    "attribution_review_reference", "cache_policy_reference",
    "offline_policy_reference", "privacy_review_reference",
    "capacity_and_cost_reference", "visual_accessibility_review_reference",
}
ROUTING_KEYS = {
    "selected_provider", "engine_version", "engine_image_digest",
    "morocco_extract_source_reference", "morocco_extract_version",
    "morocco_extract_sha256", "graph_build_reference", "graph_artifact_digest",
    "routing_origin_reference", "routing_acceptance_report_reference",
    "routing_acceptance_report_sha256",
}
REFRESH_KEYS = {
    "graph_refresh_cadence_days", "map_refresh_cadence_days",
    "maximum_source_age_days", "refresh_runbook_reference",
    "license_change_review_reference", "traffic_policy_reference",
    "routing_outage_policy_reference",
    "traffic_data_enabled", "traffic_data_source_reference",
    "previous_graph_digest", "previous_style_sha256",
    "rollback_runbook_reference", "rollback_target_reference",
}
BENCHMARK_KEYS = {
    "category", "case_reference", "expected_route_reference", "result_reference",
    "status", "maximum_distance_error_percent", "measured_distance_error_percent",
    "maximum_duration_error_percent", "measured_duration_error_percent",
    "restricted_road_violations", "executed_at",
}
DEVICE_KEYS = {
    "surface", "status", "build_digest", "device_matrix_reference",
    "route_trace_reference", "narration_reference", "reroute_reference",
    "degraded_network_reference", "accessibility_reference", "languages", "tested_at",
}
DRILL_KEYS = {
    "drill", "status", "operator_account_reference", "evidence_reference",
    "executed_at", "recovery_minutes", "review_due_at",
}
APPROVAL_KEYS = {
    "function", "approver_role", "decision", "reviewer_account_reference",
    "evidence_reference", "decided_at", "review_due_at",
}
REPORT_KEYS = {
    "provider", "passed", "scenario_count", "required_languages", "checks",
    "failure_counts",
}
REPORT_CHECK_KEYS = {"scenario", "language", "passed", "failures"}

LANGUAGES = ("ar", "fr", "en")
REPORT_LANGUAGES = ("en", "fr", "ar")
BENCHMARK_CATEGORIES = (
    "URBAN", "PERI_URBAN", "RESTRICTED_ROAD", "ONE_WAY", "ROUNDABOUT", "FIXED_ROUTE",
)
DEVICE_SURFACES = (
    "PASSENGER_ANDROID_ROUTE_PREVIEW", "PASSENGER_IOS_ROUTE_PREVIEW",
    "DRIVER_ANDROID_TURN_BY_TURN", "DRIVER_IOS_TURN_BY_TURN",
)
DRILLS = (
    "ROUTING_PROVIDER_OUTAGE", "TILE_STYLE_OUTAGE", "GRAPH_ROLLBACK",
    "STYLE_ROLLBACK", "OFF_ROUTE_REROUTE", "NETWORK_LOSS_RECOVERY",
    "ATTRIBUTION_VISIBILITY",
)
APPROVALS = (
    ("MAP_LICENSE_PRIVACY", "PRIVACY_LEGAL_OWNER"),
    ("MAP_VISUAL_ACCESSIBILITY", "DESIGN_ACCESSIBILITY_OWNER"),
    ("ROUTING_QUALITY", "ROUTING_ENGINEERING_OWNER"),
    ("MOBILE_NAVIGATION", "MOBILE_RELEASE_OWNER"),
    ("OPERATIONS_ROLLBACK", "OPERATIONS_OWNER"),
    ("PRODUCT_OWNER_AUTHORIZATION", "PRODUCT_OWNER"),
)

REFERENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,399}")
LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._ -]{1,79}")
VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,79}")
COMMIT = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
UUID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
)
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
FORBIDDEN_KEY_PARTS = {
    "password", "token", "api_key", "secret", "credential", "private_key",
    "query", "raw_payload", "raw_trace", "route_geometry", "person_name",
    "email", "phone", "government_id", "participant_id", "device_identifier",
}


class MapsRoutingNavigationError(ValueError):
    """Raised when GAP-006 evidence weakens the reviewed acceptance contract."""


def _read_json(path: Path) -> tuple[Any, bytes]:
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise MapsRoutingNavigationError(f"Cannot read {path}: {error}") from error
    try:
        return json.loads(payload), payload
    except json.JSONDecodeError as error:
        raise MapsRoutingNavigationError(
            f"Invalid JSON in {path} at line {error.lineno}."
        ) from error


def _scan_forbidden_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if any(part in normalized for part in FORBIDDEN_KEY_PARTS):
                raise MapsRoutingNavigationError(
                    f"Maps/routing evidence contains forbidden key {key!r}."
                )
            _scan_forbidden_keys(child)
    elif isinstance(value, list):
        for child in value:
            _scan_forbidden_keys(child)


def _exact_object(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise MapsRoutingNavigationError(f"{label} must use exact reviewed fields.")
    return value


def _reference(value: Any, label: str, *, required: bool) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or REFERENCE.fullmatch(value) is None:
        raise MapsRoutingNavigationError(
            f"{label} must be a bounded opaque reference without credentials or query data."
        )
    return value


def _timestamp(value: Any, label: str, *, required: bool) -> datetime | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or TIMESTAMP.fullmatch(value) is None:
        raise MapsRoutingNavigationError(f"{label} must be a UTC second timestamp.")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as error:
        raise MapsRoutingNavigationError(f"{label} is not a real UTC timestamp.") from error


def _version(value: Any, label: str, *, required: bool) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or VERSION.fullmatch(value) is None:
        raise MapsRoutingNavigationError(f"{label} must be a bounded immutable version label.")
    return value


def _digest(value: Any, label: str, *, required: bool, prefixed: bool = False) -> str | None:
    if value is None and not required:
        return None
    pattern = DIGEST if prefixed else SHA256
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        expected = "sha256:<64 lowercase hex>" if prefixed else "64 lowercase hex"
        raise MapsRoutingNavigationError(f"{label} must be {expected}.")
    return value


def _bounded_number(value: Any, label: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise MapsRoutingNavigationError(f"{label} must be a finite number.")
    if value < 0 or (positive and value <= 0) or value > 100:
        raise MapsRoutingNavigationError(f"{label} must be within the reviewed 0-100 range.")
    return float(value)


def _named_rows(value: Any, names: tuple[str, ...], keys: set[str], name_key: str, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) != len(names):
        raise MapsRoutingNavigationError(f"{label} must contain every reviewed item once.")
    rows: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(value):
        row = _exact_object(raw, keys, f"{label}[{index}]")
        name = row[name_key]
        if not isinstance(name, str) or name in rows:
            raise MapsRoutingNavigationError(f"{label} contains a missing or duplicate item.")
        rows[name] = row
    if set(rows) != set(names):
        raise MapsRoutingNavigationError(f"{label} allowlist changed.")
    return [rows[name] for name in names]


def _approval_rows(value: Any) -> list[dict[str, Any]]:
    rows = _named_rows(value, tuple(name for name, _ in APPROVALS), APPROVAL_KEYS, "function", "approvals")
    roles = dict(APPROVALS)
    for row in rows:
        if row["approver_role"] != roles[row["function"]]:
            raise MapsRoutingNavigationError(
                f"approvals role for {row['function']} changed."
            )
    return rows


def _validate_not_started(record: dict[str, Any]) -> None:
    for key in (
        "candidate_label", "source_commit", "environment_inventory_reference",
        "database_evidence_reference", "pilot_city_approval_reference",
    ):
        if record[key] is not None:
            raise MapsRoutingNavigationError("NOT_STARTED evidence contains candidate claims.")
    if any(value is not None for value in record["submission"].values()):
        raise MapsRoutingNavigationError("NOT_STARTED evidence contains submission claims.")
    for key, value in record["launch_scope"].items():
        expected = [] if key == "accepted_languages" else None
        if value != expected:
            raise MapsRoutingNavigationError("NOT_STARTED evidence contains launch-scope claims.")
    for key, value in record["map_delivery"].items():
        expected = "MAPLIBRE" if key == "renderer" else None
        if value != expected:
            raise MapsRoutingNavigationError("NOT_STARTED evidence contains map-delivery claims.")
    if any(value is not None for value in record["routing_artifact"].values()):
        raise MapsRoutingNavigationError("NOT_STARTED evidence contains routing-artifact claims.")
    if any(value is not None for value in record["refresh_and_rollback"].values()):
        raise MapsRoutingNavigationError("NOT_STARTED evidence contains refresh/rollback claims.")
    for row in record["benchmark_cases"]:
        if row["status"] != "PENDING" or any(
            row[key] is not None for key in BENCHMARK_KEYS - {"category", "status"}
        ):
            raise MapsRoutingNavigationError("NOT_STARTED evidence contains benchmark claims.")
    for row in record["device_navigation"]:
        if row["status"] != "PENDING" or row["languages"] != [] or any(
            row[key] is not None for key in DEVICE_KEYS - {"surface", "status", "languages"}
        ):
            raise MapsRoutingNavigationError("NOT_STARTED evidence contains device claims.")
    for row in record["operational_drills"]:
        if row["status"] != "PENDING" or any(
            row[key] is not None for key in DRILL_KEYS - {"drill", "status"}
        ):
            raise MapsRoutingNavigationError("NOT_STARTED evidence contains drill claims.")
    for row in record["approvals"]:
        if row["decision"] != "PENDING" or any(
            row[key] is not None for key in APPROVAL_KEYS - {"function", "approver_role", "decision"}
        ):
            raise MapsRoutingNavigationError("NOT_STARTED evidence contains approval claims.")


def _validate_routing_report(report: Any, *, provider: str, expected_sha256: str, payload_sha256: str | None) -> None:
    if payload_sha256 is None or payload_sha256 != expected_sha256:
        raise MapsRoutingNavigationError("Routing acceptance report bytes do not match the recorded SHA-256.")
    report = _exact_object(report, REPORT_KEYS, "routing acceptance report")
    if report["provider"] != provider or report["passed"] is not True:
        raise MapsRoutingNavigationError("Routing acceptance report must pass for the selected provider.")
    if report["required_languages"] != list(REPORT_LANGUAGES):
        raise MapsRoutingNavigationError("Routing acceptance report must retain en/fr/ar coverage.")
    count = report["scenario_count"]
    if isinstance(count, bool) or not isinstance(count, int) or count < 3 or count > 100:
        raise MapsRoutingNavigationError("Routing acceptance report needs 3-100 fixed public scenarios.")
    if report["failure_counts"] != {}:
        raise MapsRoutingNavigationError("Routing acceptance report cannot retain failures.")
    checks = report["checks"]
    if not isinstance(checks, list) or len(checks) != count * len(REPORT_LANGUAGES):
        raise MapsRoutingNavigationError("Routing acceptance report check count is incomplete.")
    scenarios: dict[str, set[str]] = {}
    pairs: set[tuple[str, str]] = set()
    for index, raw in enumerate(checks):
        check = _exact_object(raw, REPORT_CHECK_KEYS, f"routing report checks[{index}]")
        scenario, language = check["scenario"], check["language"]
        if (
            not isinstance(scenario, str) or LABEL.fullmatch(scenario) is None
            or language not in REPORT_LANGUAGES or (scenario, language) in pairs
        ):
            raise MapsRoutingNavigationError("Routing acceptance report contains an invalid or duplicate check.")
        if check["passed"] is not True or check["failures"] != []:
            raise MapsRoutingNavigationError("Every routing acceptance check must pass without failures.")
        pairs.add((scenario, language))
        scenarios.setdefault(scenario, set()).add(language)
    if len(scenarios) != count or any(languages != set(REPORT_LANGUAGES) for languages in scenarios.values()):
        raise MapsRoutingNavigationError("Every routing scenario must cover en/fr/ar exactly once.")


def validate_evidence(
    record: Any,
    *,
    routing_report: Any | None = None,
    routing_report_sha256: str | None = None,
    require_accepted: bool = False,
) -> dict[str, Any]:
    record = _exact_object(record, ROOT_KEYS, "maps/routing/navigation evidence")
    _scan_forbidden_keys(record)
    if record["schema_version"] != 1:
        raise MapsRoutingNavigationError("schema_version must be 1.")
    try:
        datetime.strptime(record["evidence_revision"], "%Y-%m-%d")
    except (TypeError, ValueError) as error:
        raise MapsRoutingNavigationError("evidence_revision must be a real date.") from error
    if record["gap"] != "GAP-006" or record["phase"] != "T5":
        raise MapsRoutingNavigationError("The record must remain bound to GAP-006 and T5.")
    if record["data_classification"] != "PUBLIC_ARTIFACT_AND_CONTROL_REFERENCES_ONLY":
        raise MapsRoutingNavigationError("data_classification weakened.")
    if record["status"] not in {"NOT_STARTED", "ACCEPTED"}:
        raise MapsRoutingNavigationError("status must be NOT_STARTED or ACCEPTED.")
    accepted = record["status"] == "ACCEPTED"
    if record["gap_006_accepted"] is not accepted:
        raise MapsRoutingNavigationError("gap_006_accepted must match status.")
    if record["phase_accepted"] is not False or record["deployment_accepted"] is not False:
        raise MapsRoutingNavigationError("GAP-006 evidence cannot accept a phase or deployment.")
    if require_accepted and not accepted:
        raise MapsRoutingNavigationError("externally accepted GAP-006 evidence is required.")

    submission = _exact_object(record["submission"], SUBMISSION_KEYS, "submission")
    scope = _exact_object(record["launch_scope"], SCOPE_KEYS, "launch_scope")
    maps = _exact_object(record["map_delivery"], MAP_KEYS, "map_delivery")
    routing = _exact_object(record["routing_artifact"], ROUTING_KEYS, "routing_artifact")
    refresh = _exact_object(record["refresh_and_rollback"], REFRESH_KEYS, "refresh_and_rollback")
    benchmarks = _named_rows(record["benchmark_cases"], BENCHMARK_CATEGORIES, BENCHMARK_KEYS, "category", "benchmark_cases")
    devices = _named_rows(record["device_navigation"], DEVICE_SURFACES, DEVICE_KEYS, "surface", "device_navigation")
    drills = _named_rows(record["operational_drills"], DRILLS, DRILL_KEYS, "drill", "operational_drills")
    approvals = _approval_rows(record["approvals"])

    if not accepted:
        if routing_report is not None or routing_report_sha256 is not None:
            raise MapsRoutingNavigationError("NOT_STARTED evidence cannot bind a routing report.")
        if record["limitations"] != [
            "NO_PRODUCTION_MAP_ROUTING_NAVIGATION_ACCEPTED",
            "NO_PHASE_OR_DEPLOYMENT_ACCEPTANCE",
        ]:
            raise MapsRoutingNavigationError("NOT_STARTED limitations are invalid.")
        _validate_not_started(record)
        return {"status": "NOT_STARTED", "gap_006_accepted": False, "benchmark_cases": 6, "device_surfaces": 4}

    if not isinstance(record["candidate_label"], str) or LABEL.fullmatch(record["candidate_label"]) is None:
        raise MapsRoutingNavigationError("candidate_label is invalid.")
    if not isinstance(record["source_commit"], str) or COMMIT.fullmatch(record["source_commit"]) is None:
        raise MapsRoutingNavigationError("source_commit must be a full lowercase Git commit.")
    for key in ("environment_inventory_reference", "database_evidence_reference", "pilot_city_approval_reference"):
        _reference(record[key], key, required=True)

    submitter = _reference(submission["submitted_by_account_reference"], "submission.submitted_by_account_reference", required=True)
    submitted_at = _timestamp(submission["submitted_at"], "submission.submitted_at", required=True)
    _reference(submission["change_reference"], "submission.change_reference", required=True)
    assert submitter and submitted_at

    if scope["market_code"] != "MA" or scope["country_code"] != "MA":
        raise MapsRoutingNavigationError("GAP-006 launch scope must remain Morocco (MA).")
    for key in ("city_id", "city_configuration_id"):
        if not isinstance(scope[key], str) or UUID.fullmatch(scope[key]) is None:
            raise MapsRoutingNavigationError(f"launch_scope.{key} must be a lowercase UUID.")
    _reference(scope["service_area_reference"], "launch_scope.service_area_reference", required=True)
    _reference(scope["quality_threshold_reference"], "launch_scope.quality_threshold_reference", required=True)
    if scope["accepted_languages"] != list(LANGUAGES):
        raise MapsRoutingNavigationError("launch_scope.accepted_languages must be exactly ar/fr/en.")
    valid_until = _timestamp(scope["acceptance_valid_until"], "launch_scope.acceptance_valid_until", required=True)
    assert valid_until
    if valid_until <= submitted_at:
        raise MapsRoutingNavigationError("acceptance_valid_until must follow submission.")

    if maps["renderer"] != "MAPLIBRE":
        raise MapsRoutingNavigationError("MapLibre must remain the client renderer.")
    for key in MAP_KEYS - {"renderer", "style_version", "style_sha256", "tile_source_version", "tile_catalog_sha256"}:
        _reference(maps[key], f"map_delivery.{key}", required=True)
    _version(maps["style_version"], "map_delivery.style_version", required=True)
    _digest(maps["style_sha256"], "map_delivery.style_sha256", required=True)
    _version(maps["tile_source_version"], "map_delivery.tile_source_version", required=True)
    _digest(maps["tile_catalog_sha256"], "map_delivery.tile_catalog_sha256", required=True)

    provider = routing["selected_provider"]
    if provider not in {"valhalla", "graphhopper"}:
        raise MapsRoutingNavigationError("selected_provider must be valhalla or graphhopper.")
    _version(routing["engine_version"], "routing_artifact.engine_version", required=True)
    _digest(routing["engine_image_digest"], "routing_artifact.engine_image_digest", required=True, prefixed=True)
    for key in (
        "morocco_extract_source_reference", "graph_build_reference", "routing_origin_reference",
        "routing_acceptance_report_reference",
    ):
        _reference(routing[key], f"routing_artifact.{key}", required=True)
    _version(routing["morocco_extract_version"], "routing_artifact.morocco_extract_version", required=True)
    _digest(routing["morocco_extract_sha256"], "routing_artifact.morocco_extract_sha256", required=True)
    _digest(routing["graph_artifact_digest"], "routing_artifact.graph_artifact_digest", required=True, prefixed=True)
    report_digest = _digest(
        routing["routing_acceptance_report_sha256"],
        "routing_artifact.routing_acceptance_report_sha256",
        required=True,
    )
    assert report_digest
    if routing_report is None:
        raise MapsRoutingNavigationError("Accepted evidence requires the exact routing acceptance report file.")
    _validate_routing_report(
        routing_report,
        provider=provider,
        expected_sha256=report_digest,
        payload_sha256=routing_report_sha256,
    )

    for key, maximum in (
        ("graph_refresh_cadence_days", 180),
        ("map_refresh_cadence_days", 180),
        ("maximum_source_age_days", 365),
    ):
        value = refresh[key]
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
            raise MapsRoutingNavigationError(f"refresh_and_rollback.{key} must be 1-{maximum} days.")
    for key in (
        "refresh_runbook_reference", "license_change_review_reference", "traffic_policy_reference",
        "routing_outage_policy_reference",
        "rollback_runbook_reference", "rollback_target_reference",
    ):
        _reference(refresh[key], f"refresh_and_rollback.{key}", required=True)
    if not isinstance(refresh["traffic_data_enabled"], bool):
        raise MapsRoutingNavigationError("traffic_data_enabled must be an explicit boolean.")
    _reference(
        refresh["traffic_data_source_reference"],
        "refresh_and_rollback.traffic_data_source_reference",
        required=refresh["traffic_data_enabled"],
    )
    if not refresh["traffic_data_enabled"] and refresh["traffic_data_source_reference"] is not None:
        raise MapsRoutingNavigationError("Disabled traffic data cannot retain a source claim.")
    previous_graph = _digest(refresh["previous_graph_digest"], "refresh_and_rollback.previous_graph_digest", required=True, prefixed=True)
    previous_style = _digest(refresh["previous_style_sha256"], "refresh_and_rollback.previous_style_sha256", required=True)
    if previous_graph == routing["graph_artifact_digest"] or previous_style == maps["style_sha256"]:
        raise MapsRoutingNavigationError("Rollback artifacts must differ from the promoted artifacts.")

    benchmark_evidence: set[str] = set()
    for row in benchmarks:
        label = f"benchmark_cases.{row['category']}"
        if row["status"] != "PASSED":
            raise MapsRoutingNavigationError(f"{label} must be PASSED.")
        for key in ("case_reference", "expected_route_reference", "result_reference"):
            _reference(row[key], f"{label}.{key}", required=True)
        if row["result_reference"] in benchmark_evidence:
            raise MapsRoutingNavigationError("Every benchmark category requires distinct result evidence.")
        benchmark_evidence.add(row["result_reference"])
        max_distance = _bounded_number(row["maximum_distance_error_percent"], f"{label}.maximum_distance_error_percent", positive=True)
        measured_distance = _bounded_number(row["measured_distance_error_percent"], f"{label}.measured_distance_error_percent")
        max_duration = _bounded_number(row["maximum_duration_error_percent"], f"{label}.maximum_duration_error_percent", positive=True)
        measured_duration = _bounded_number(row["measured_duration_error_percent"], f"{label}.measured_duration_error_percent")
        if measured_distance > max_distance or measured_duration > max_duration:
            raise MapsRoutingNavigationError(f"{label} exceeds its approved benchmark tolerance.")
        if row["restricted_road_violations"] != 0:
            raise MapsRoutingNavigationError(f"{label} must have zero restricted-road violations.")
        executed = _timestamp(row["executed_at"], f"{label}.executed_at", required=True)
        assert executed
        if not submitted_at <= executed <= valid_until:
            raise MapsRoutingNavigationError(f"{label} execution is outside the acceptance window.")

    device_traces: set[str] = set()
    for row in devices:
        label = f"device_navigation.{row['surface']}"
        if row["status"] != "PASSED" or row["languages"] != list(LANGUAGES):
            raise MapsRoutingNavigationError(f"{label} must pass exact ar/fr/en coverage.")
        _digest(row["build_digest"], f"{label}.build_digest", required=True, prefixed=True)
        for key in (
            "device_matrix_reference", "route_trace_reference", "narration_reference",
            "reroute_reference", "degraded_network_reference", "accessibility_reference",
        ):
            _reference(row[key], f"{label}.{key}", required=True)
        if row["route_trace_reference"] in device_traces:
            raise MapsRoutingNavigationError("Every device surface requires a distinct route trace.")
        device_traces.add(row["route_trace_reference"])
        tested = _timestamp(row["tested_at"], f"{label}.tested_at", required=True)
        assert tested
        if not submitted_at <= tested <= valid_until:
            raise MapsRoutingNavigationError(f"{label} testing is outside the acceptance window.")

    drill_evidence: set[str] = set()
    for row in drills:
        label = f"operational_drills.{row['drill']}"
        if row["status"] != "PASSED":
            raise MapsRoutingNavigationError(f"{label} must be PASSED.")
        _reference(row["operator_account_reference"], f"{label}.operator_account_reference", required=True)
        _reference(row["evidence_reference"], f"{label}.evidence_reference", required=True)
        if row["evidence_reference"] in drill_evidence:
            raise MapsRoutingNavigationError("Every operational drill requires distinct evidence.")
        drill_evidence.add(row["evidence_reference"])
        executed = _timestamp(row["executed_at"], f"{label}.executed_at", required=True)
        due = _timestamp(row["review_due_at"], f"{label}.review_due_at", required=True)
        recovery = row["recovery_minutes"]
        if isinstance(recovery, bool) or not isinstance(recovery, int) or not 0 <= recovery <= 240:
            raise MapsRoutingNavigationError(f"{label}.recovery_minutes must be 0-240.")
        assert executed and due
        if not submitted_at <= executed <= valid_until or due < valid_until:
            raise MapsRoutingNavigationError(f"{label} timing does not cover the acceptance window.")

    reviewers: set[str] = set()
    for row in approvals:
        label = f"approvals.{row['function']}"
        if row["decision"] != "APPROVED":
            raise MapsRoutingNavigationError(f"{label} must be APPROVED.")
        reviewer = _reference(row["reviewer_account_reference"], f"{label}.reviewer_account_reference", required=True)
        _reference(row["evidence_reference"], f"{label}.evidence_reference", required=True)
        decided = _timestamp(row["decided_at"], f"{label}.decided_at", required=True)
        due = _timestamp(row["review_due_at"], f"{label}.review_due_at", required=True)
        assert reviewer and decided and due
        if reviewer == submitter:
            raise MapsRoutingNavigationError(f"{label} reviewer must differ from the submitter.")
        if not submitted_at <= decided <= valid_until or due < valid_until:
            raise MapsRoutingNavigationError(f"{label} timing does not cover the acceptance window.")
        reviewers.add(reviewer)
    if len(reviewers) < 3:
        raise MapsRoutingNavigationError("Accepted GAP-006 evidence requires at least three independent reviewers.")

    limitations = record["limitations"]
    if (
        not isinstance(limitations, list)
        or limitations != ["NO_PHASE_OR_DEPLOYMENT_ACCEPTANCE"]
    ):
        raise MapsRoutingNavigationError("Accepted evidence must retain only the phase/deployment boundary.")
    return {
        "status": "ACCEPTED",
        "gap_006_accepted": True,
        "provider": provider,
        "benchmark_cases": len(benchmarks),
        "device_surfaces": len(devices),
        "operational_drills": len(drills),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument(
        "--routing-report",
        type=Path,
        help="Exact redacted JSON emitted by the backend routing acceptance command.",
    )
    parser.add_argument("--require-accepted", action="store_true")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    arguments = _parser().parse_args(list(argv) if argv is not None else None)
    try:
        evidence, _ = _read_json(arguments.evidence)
        report = None
        report_sha256 = None
        if arguments.routing_report is not None:
            report, report_bytes = _read_json(arguments.routing_report)
            report_sha256 = hashlib.sha256(report_bytes).hexdigest()
        summary = validate_evidence(
            evidence,
            routing_report=report,
            routing_report_sha256=report_sha256,
            require_accepted=arguments.require_accepted,
        )
    except (OSError, ValueError, MapsRoutingNavigationError) as error:
        print(f"Maps/routing/navigation evidence validation failed: {error}", file=sys.stderr)
        return 1
    print(
        "Maps/routing/navigation evidence passed: "
        f"status {summary['status']}, {summary['benchmark_cases']} benchmark cases, "
        f"{summary['device_surfaces']} device surfaces; zero phase/deployment acceptance claims."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
