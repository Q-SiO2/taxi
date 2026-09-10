"""Validate TaxiMobile's closed T4 device/browser laboratory catalog and evidence.

The default template is intentionally all ``NOT_STARTED``. An execution record
can establish evidence completeness only when every one of the 56 reviewed cases
has a retained PASS artifact. This validator never grants phase or deployment
acceptance; those decisions remain in the ordered promotion evidence index.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import tomllib
from typing import Any, Iterable


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = WORKSPACE_ROOT / "infra" / "testing" / "t4-lab-catalog.json"
DEFAULT_TEMPLATE = WORKSPACE_ROOT / "infra" / "testing" / "t4-lab-evidence.template.json"
PHASE_CATALOG = WORKSPACE_ROOT / "infra" / "testing" / "test-phase-catalog.json"
VERSIONS_FILE = WORKSPACE_ROOT / "TaxiMobile" / "gradle" / "libs.versions.toml"
IOS_PROJECT = WORKSPACE_ROOT / "TaxiMobile" / "iosApp" / "iosApp.xcodeproj" / "project.pbxproj"

REQUIRED_EVIDENCE_KINDS = (
    "SUPPORTED_MATRIX",
    "ANDROID_DEVICE_REPORT",
    "IOS_DEVICE_REPORT",
    "BROWSER_COMPATIBILITY_REPORT",
    "ACCESSIBILITY_AND_RTL_REPORT",
    "DEGRADED_NETWORK_AND_LIFECYCLE_REPORT",
    "CRASH_SYMBOLICATION_REPORT",
)
SURFACES = {
    "ANDROID_PASSENGER",
    "ANDROID_DRIVER",
    "IOS_PASSENGER",
    "IOS_DRIVER",
    "WEB_APPLICANT",
    "WEB_OPERATIONS",
    "CROSS_SURFACE",
}
ROLES = {"PASSENGER", "DRIVER", "APPLICANT", "OPERATIONS_STAFF"}
LOCALES = {"EN", "FR", "AR"}
TEST_TYPES = {
    "REVIEW",
    "PHYSICAL_DEVICE",
    "REAL_BROWSER",
    "ASSISTIVE_TECHNOLOGY",
    "FAULT_INJECTION",
}
SEVERITIES = {"S0", "S1", "S2"}
CASE_ID = re.compile(r"T4-[A-Z0-9]{3,8}-\d{3}")
CLOSED_ID = re.compile(r"[A-Z][A-Z0-9_]{2,95}")
REFERENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,399}")
SHA256 = re.compile(r"[0-9a-f]{64}")
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T[^\s]+Z")
CATALOG_ROOT_KEYS = {
    "schema_version",
    "catalog_revision",
    "phase",
    "safety",
    "source_matrix",
    "required_evidence_kinds",
    "cases",
}
CASE_KEYS = {
    "id",
    "evidence_kind",
    "surfaces",
    "roles",
    "locales",
    "test_type",
    "procedure",
    "required_observations",
    "blocking_severity",
    "requires_physical_device",
    "requires_real_browser",
}
EVIDENCE_ROOT_KEYS = {
    "schema_version",
    "catalog_revision",
    "catalog_sha256",
    "phase",
    "evidence_level",
    "status",
    "data_classification",
    "public_users_allowed",
    "live_money_allowed",
    "candidate_label",
    "case_results",
    "supported_evidence_kinds",
    "missing_evidence_kinds",
    "phase_evidence_complete",
    "phase_accepted",
    "deployment_accepted",
    "limitations",
}
RESULT_KEYS = {
    "id",
    "status",
    "evidence_reference",
    "evidence_sha256",
    "executed_at",
    "tester_reference",
    "defect_references",
}
FORBIDDEN_KEY_PARTS = {
    "serial",
    "password",
    "access_token",
    "refresh_token",
    "recovery_code",
    "precise_location",
    "credential",
    "document_content",
    "payment_instruction",
}


class T4LabEvidenceError(ValueError):
    """Raised when the T4 lab catalog or evidence weakens reviewed controls."""


def _load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise T4LabEvidenceError(f"Cannot read {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise T4LabEvidenceError(f"Invalid JSON in {path} at line {error.lineno}.") from error


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _closed_list(value: Any, *, allowed: set[str], label: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or item not in allowed for item in value)
        or len(value) != len(set(value))
    ):
        raise T4LabEvidenceError(f"{label} must be a non-empty unique reviewed list.")
    return value


def _scan_forbidden_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if any(part in normalized for part in FORBIDDEN_KEY_PARTS):
                raise T4LabEvidenceError(f"T4 evidence contains forbidden key {key!r}.")
            _scan_forbidden_keys(child)
    elif isinstance(value, list):
        for child in value:
            _scan_forbidden_keys(child)


def load_and_validate_catalog(path: Path = DEFAULT_CATALOG) -> dict[str, Any]:
    catalog = _load(path)
    if not isinstance(catalog, dict) or set(catalog) != CATALOG_ROOT_KEYS:
        raise T4LabEvidenceError("T4 catalog must use the exact reviewed root fields.")
    if catalog.get("schema_version") != 1 or catalog.get("phase") != "T4":
        raise T4LabEvidenceError("T4 catalog must be schema 1 for phase T4.")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(catalog.get("catalog_revision", ""))) is None:
        raise T4LabEvidenceError("T4 catalog revision must be a date.")
    if catalog.get("safety") != {
        "public_users_allowed": False,
        "live_money_allowed": False,
        "production_credentials_allowed": False,
        "real_personal_data_allowed": False,
        "intentional_failure_injection_allowed": True,
    }:
        raise T4LabEvidenceError("T4 safety flags cannot enable public, money, credential or personal activity.")
    source_matrix = catalog.get("source_matrix")
    if not isinstance(source_matrix, dict) or set(source_matrix) != {
        "android_min_sdk",
        "android_target_sdk",
        "ios_deployment_target",
        "browser_families",
        "locales",
        "rtl_locales",
    }:
        raise T4LabEvidenceError("T4 source matrix fields are invalid.")
    if tuple(catalog.get("required_evidence_kinds", ())) != REQUIRED_EVIDENCE_KINDS:
        raise T4LabEvidenceError("T4 required evidence kinds do not match the reviewed order.")

    phase_catalog = _load(PHASE_CATALOG)
    phase = next((item for item in phase_catalog.get("phases", []) if item.get("id") == "T4"), None)
    if phase is None or tuple(phase.get("required_evidence", ())) != REQUIRED_EVIDENCE_KINDS:
        raise T4LabEvidenceError("T4 lab catalog drifted from the promotion phase catalog.")

    versions = tomllib.loads(VERSIONS_FILE.read_text(encoding="utf-8"))["versions"]
    ios_targets = set(re.findall(r"IPHONEOS_DEPLOYMENT_TARGET = ([0-9.]+);", IOS_PROJECT.read_text(encoding="utf-8")))
    if (
        source_matrix["android_min_sdk"] != int(versions["android-minSdk"])
        or source_matrix["android_target_sdk"] != int(versions["android-targetSdk"])
        or ios_targets != {source_matrix["ios_deployment_target"]}
        or source_matrix["browser_families"] != ["CHROME", "FIREFOX", "SAFARI"]
        or source_matrix["locales"] != ["EN", "FR", "AR"]
        or source_matrix["rtl_locales"] != ["AR"]
    ):
        raise T4LabEvidenceError("T4 source matrix drifted from mobile targets or reviewed browser/locale coverage.")

    cases = catalog.get("cases")
    if not isinstance(cases, list) or len(cases) != 56:
        raise T4LabEvidenceError("T4 catalog must contain exactly 56 reviewed cases.")
    identifiers: list[str] = []
    kind_counts = {kind: 0 for kind in REQUIRED_EVIDENCE_KINDS}
    for index, case in enumerate(cases):
        if not isinstance(case, dict) or set(case) != CASE_KEYS:
            raise T4LabEvidenceError(f"T4 case {index} must use exact reviewed fields.")
        identifier = case.get("id")
        if not isinstance(identifier, str) or CASE_ID.fullmatch(identifier) is None:
            raise T4LabEvidenceError(f"T4 case {index} has an invalid ID.")
        kind = case.get("evidence_kind")
        if kind not in kind_counts:
            raise T4LabEvidenceError(f"T4 case {identifier} has an unsupported evidence kind.")
        _closed_list(case.get("surfaces"), allowed=SURFACES, label=f"{identifier} surfaces")
        _closed_list(case.get("roles"), allowed=ROLES, label=f"{identifier} roles")
        _closed_list(case.get("locales"), allowed=LOCALES, label=f"{identifier} locales")
        if case.get("test_type") not in TEST_TYPES or case.get("blocking_severity") not in SEVERITIES:
            raise T4LabEvidenceError(f"T4 case {identifier} has invalid type or severity.")
        if not isinstance(case.get("procedure"), str) or not 30 <= len(case["procedure"]) <= 400:
            raise T4LabEvidenceError(f"T4 case {identifier} needs a bounded procedure.")
        observations = case.get("required_observations")
        if (
            not isinstance(observations, list)
            or len(observations) < 3
            or any(not isinstance(item, str) or CLOSED_ID.fullmatch(item) is None for item in observations)
            or len(observations) != len(set(observations))
        ):
            raise T4LabEvidenceError(f"T4 case {identifier} has invalid required observations.")
        for flag in ("requires_physical_device", "requires_real_browser"):
            if not isinstance(case.get(flag), bool):
                raise T4LabEvidenceError(f"T4 case {identifier} {flag} must be Boolean.")
        if case["test_type"] == "PHYSICAL_DEVICE" and not case["requires_physical_device"]:
            raise T4LabEvidenceError(f"T4 case {identifier} cannot simulate a physical-device claim.")
        if case["test_type"] == "REAL_BROWSER" and not case["requires_real_browser"]:
            raise T4LabEvidenceError(f"T4 case {identifier} cannot simulate a real-browser claim.")
        identifiers.append(identifier)
        kind_counts[kind] += 1
    if len(identifiers) != len(set(identifiers)):
        raise T4LabEvidenceError("T4 case IDs must be unique.")
    if set(kind_counts.values()) != {8}:
        raise T4LabEvidenceError("Every T4 evidence kind must contain exactly eight cases.")
    return catalog


def validate_evidence(evidence: Any, catalog: dict[str, Any], catalog_path: Path) -> dict[str, Any]:
    if not isinstance(evidence, dict) or set(evidence) != EVIDENCE_ROOT_KEYS:
        raise T4LabEvidenceError("T4 evidence must use exact reviewed root fields.")
    _scan_forbidden_keys(evidence)
    if (
        evidence.get("schema_version") != 1
        or evidence.get("catalog_revision") != catalog["catalog_revision"]
        or evidence.get("catalog_sha256") != _sha256(catalog_path)
        or evidence.get("phase") != "T4"
        or evidence.get("evidence_level") != "T4_LAB_EXECUTION"
        or evidence.get("data_classification") != "STAFF_CONTROLLED"
        or evidence.get("public_users_allowed") is not False
        or evidence.get("live_money_allowed") is not False
        or evidence.get("phase_accepted") is not False
        or evidence.get("deployment_accepted") is not False
    ):
        raise T4LabEvidenceError("T4 evidence metadata or non-acceptance boundary is invalid.")
    status = evidence.get("status")
    case_results = evidence.get("case_results")
    if status == "NOT_STARTED":
        if (
            evidence.get("candidate_label") is not None
            or case_results != []
            or evidence.get("supported_evidence_kinds") != []
            or tuple(evidence.get("missing_evidence_kinds", ())) != REQUIRED_EVIDENCE_KINDS
            or evidence.get("phase_evidence_complete") is not False
        ):
            raise T4LabEvidenceError("T4 NOT_STARTED template cannot contain execution claims.")
        return {"status": status, "cases": 0, "passed": 0, "evidence_complete": False}
    if status != "EXECUTED":
        raise T4LabEvidenceError("T4 evidence status must be NOT_STARTED or EXECUTED.")
    if (
        not isinstance(evidence.get("candidate_label"), str)
        or REFERENCE.fullmatch(evidence["candidate_label"]) is None
        or not isinstance(case_results, list)
        or len(case_results) != len(catalog["cases"])
    ):
        raise T4LabEvidenceError("Executed T4 evidence needs one candidate and every catalog case.")
    expected_ids = [case["id"] for case in catalog["cases"]]
    kind_by_id = {case["id"]: case["evidence_kind"] for case in catalog["cases"]}
    actual_ids: list[str] = []
    passed = 0
    statuses_by_kind = {kind: [] for kind in REQUIRED_EVIDENCE_KINDS}
    for index, result in enumerate(case_results):
        if not isinstance(result, dict) or set(result) != RESULT_KEYS:
            raise T4LabEvidenceError(f"T4 result {index} must use exact reviewed fields.")
        identifier = result.get("id")
        actual_ids.append(identifier)
        if result.get("status") not in {"PASS", "FAIL", "BLOCKED"}:
            raise T4LabEvidenceError(f"T4 result {identifier} has invalid status.")
        for field in ("evidence_reference", "tester_reference"):
            if not isinstance(result.get(field), str) or REFERENCE.fullmatch(result[field]) is None:
                raise T4LabEvidenceError(f"T4 result {identifier} has invalid {field}.")
        if not isinstance(result.get("evidence_sha256"), str) or SHA256.fullmatch(result["evidence_sha256"]) is None:
            raise T4LabEvidenceError(f"T4 result {identifier} needs an evidence SHA-256.")
        if not isinstance(result.get("executed_at"), str) or TIMESTAMP.fullmatch(result["executed_at"]) is None:
            raise T4LabEvidenceError(f"T4 result {identifier} needs a UTC execution timestamp.")
        defects = result.get("defect_references")
        if not isinstance(defects, list) or any(
            not isinstance(item, str) or REFERENCE.fullmatch(item) is None for item in defects
        ):
            raise T4LabEvidenceError(f"T4 result {identifier} has invalid defect references.")
        if result["status"] != "PASS" and not defects:
            raise T4LabEvidenceError(f"T4 result {identifier} must link its blocking defect.")
        passed += result["status"] == "PASS"
        if identifier in kind_by_id:
            statuses_by_kind[kind_by_id[identifier]].append(result["status"])
    if actual_ids != expected_ids:
        raise T4LabEvidenceError("T4 results must match catalog IDs and order exactly.")
    expected_supported = [
        kind
        for kind in REQUIRED_EVIDENCE_KINDS
        if len(statuses_by_kind[kind]) == 8
        and all(status == "PASS" for status in statuses_by_kind[kind])
    ]
    expected_missing = [kind for kind in REQUIRED_EVIDENCE_KINDS if kind not in expected_supported]
    complete = not expected_missing
    if (
        evidence.get("supported_evidence_kinds") != expected_supported
        or evidence.get("missing_evidence_kinds") != expected_missing
        or evidence.get("phase_evidence_complete") is not complete
    ):
        raise T4LabEvidenceError("T4 aggregate evidence claims do not match case results.")
    return {"status": status, "cases": len(expected_ids), "passed": passed, "evidence_complete": complete}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_TEMPLATE)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    arguments = _parser().parse_args(list(argv) if argv is not None else None)
    try:
        catalog = load_and_validate_catalog(arguments.catalog)
        summary = validate_evidence(_load(arguments.evidence), catalog, arguments.catalog)
    except (OSError, KeyError, T4LabEvidenceError) as error:
        print(f"T4 laboratory evidence validation failed: {error}", file=sys.stderr)
        return 1
    print(
        f"T4 laboratory catalog passed: {len(catalog['cases'])} cases, "
        f"evidence status {summary['status']}, {summary['passed']} passed, "
        "zero phase/deployment acceptance claims."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
