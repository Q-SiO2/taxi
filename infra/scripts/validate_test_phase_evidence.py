"""Validate TaxiMobile's ordered T0-T10 promotion evidence.

The validator checks evidence metadata and promotion authority. It deliberately
does not execute tests, inspect external ticket systems, or turn a local result
into deployment acceptance. Evidence files are expected to be immutable and
hash-addressed by the system that retains them.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = WORKSPACE_ROOT / "infra" / "testing" / "test-phase-catalog.json"
DEFAULT_TEMPLATE = WORKSPACE_ROOT / "infra" / "testing" / "test-evidence-index.template.json"

PHASE_IDS = tuple(f"T{index}" for index in range(11))
STATUSES = {"NOT_STARTED", "IN_PROGRESS", "BLOCKED", "REJECTED", "INVALIDATED", "ACCEPTED"}
AUTHORITIES = {
    "ENGINEERING",
    "SECURITY",
    "OPERATIONS",
    "PRODUCT",
    "ACCESSIBILITY_DEVICE",
    "CITY_OPERATOR",
    "SAFETY_LEGAL",
    "GO_NO_GO_BOARD",
    "NATIONAL_OWNER",
}
DATA_CLASSIFICATIONS = {
    "SYNTHETIC",
    "STAFF_CONTROLLED",
    "REAL_USER_AGGREGATE",
    "CONTROLLED_REFERENCE",
}
FORBIDDEN_KEY_PARTS = {
    "access_token",
    "refresh_token",
    "password",
    "recovery_code",
    "provider_credential",
    "document_content",
    "precise_location",
    "payment_instruction",
    "private_key",
}
HEX_40 = re.compile(r"[0-9a-f]{40}")
HEX_64 = re.compile(r"[0-9a-f]{64}")
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
EVIDENCE_KIND = re.compile(r"[A-Z][A-Z0-9_]{2,95}")
GAP_ID = re.compile(r"GAP-\d{3}")
REFERENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,399}")


class PhaseEvidenceError(ValueError):
    """Raised when a catalog or evidence index cannot be safely interpreted."""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise PhaseEvidenceError(f"cannot read {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise PhaseEvidenceError(
            f"invalid JSON in {path} at line {error.lineno}, column {error.colno}"
        ) from error


def _mapping(value: Any, path: str, issues: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        issues.append(f"{path} must be an object")
        return {}
    return value


def _list(value: Any, path: str, issues: list[str]) -> list[Any]:
    if not isinstance(value, list):
        issues.append(f"{path} must be an array")
        return []
    return value


def _closed_string_list(
    value: Any,
    path: str,
    issues: list[str],
    *,
    allowed: set[str] | None = None,
    pattern: re.Pattern[str] | None = None,
    allow_empty: bool = False,
) -> list[str]:
    values = _list(value, path, issues)
    result: list[str] = []
    for index, item in enumerate(values):
        item_path = f"{path}[{index}]"
        if not isinstance(item, str):
            issues.append(f"{item_path} must be a string")
        elif allowed is not None and item not in allowed:
            issues.append(f"{item_path} has unsupported value {item!r}")
        elif pattern is not None and pattern.fullmatch(item) is None:
            issues.append(f"{item_path} has an invalid closed identifier")
        else:
            result.append(item)
    if not allow_empty and not result:
        issues.append(f"{path} must not be empty")
    if len(result) != len(set(result)):
        issues.append(f"{path} must not contain duplicates")
    return result


def _utc_timestamp(value: Any, path: str, issues: list[str]) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        issues.append(f"{path} must be an RFC3339 UTC timestamp ending in Z")
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        issues.append(f"{path} must be a valid RFC3339 UTC timestamp")
        return None
    if parsed.tzinfo != timezone.utc:
        issues.append(f"{path} must use UTC")
        return None
    return parsed


def _reference(value: Any, path: str, issues: list[str]) -> str | None:
    if (
        not isinstance(value, str)
        or REFERENCE.fullmatch(value) is None
        or ".." in value
        or "//" in value
    ):
        issues.append(
            f"{path} must be a bounded credential-free controlled reference without query or fragment"
        )
        return None
    return value


def _sha256(value: Any, path: str, issues: list[str]) -> None:
    if not isinstance(value, str) or HEX_64.fullmatch(value) is None:
        issues.append(f"{path} must be a lowercase SHA-256 digest")


def _scan_forbidden_keys(value: Any, path: str, issues: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                issues.append(f"{path} contains a non-string key")
                continue
            normalized = key.lower().replace("-", "_")
            if any(part in normalized for part in FORBIDDEN_KEY_PARTS):
                issues.append(f"{path}.{key} is forbidden in evidence metadata")
            _scan_forbidden_keys(child, f"{path}.{key}", issues)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_forbidden_keys(child, f"{path}[{index}]", issues)


def validate_catalog(catalog: Any) -> list[str]:
    issues: list[str] = []
    root = _mapping(catalog, "catalog", issues)
    if root.get("schema_version") != 1:
        issues.append("catalog.schema_version must be 1")
    revision = root.get("catalog_revision")
    if not isinstance(revision, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", revision) is None:
        issues.append("catalog.catalog_revision must be a YYYY-MM-DD date")

    phases = _list(root.get("phases"), "catalog.phases", issues)
    ids = [phase.get("id") if isinstance(phase, dict) else None for phase in phases]
    if tuple(ids) != PHASE_IDS:
        issues.append(f"catalog.phases must be ordered exactly as {PHASE_IDS!r}")

    for index, raw_phase in enumerate(phases):
        path = f"catalog.phases[{index}]"
        phase = _mapping(raw_phase, path, issues)
        phase_id = phase.get("id")
        expected_predecessor = None if index == 0 else PHASE_IDS[index - 1]
        if phase.get("predecessor") != expected_predecessor:
            issues.append(f"{path}.predecessor must be {expected_predecessor!r}")
        _closed_string_list(
            phase.get("environment_classes"),
            f"{path}.environment_classes",
            issues,
            pattern=IDENTIFIER,
        )
        _closed_string_list(
            phase.get("participant_modes"),
            f"{path}.participant_modes",
            issues,
            pattern=IDENTIFIER,
        )
        _closed_string_list(
            phase.get("required_authorities"),
            f"{path}.required_authorities",
            issues,
            allowed=AUTHORITIES,
        )
        _closed_string_list(
            phase.get("required_evidence"),
            f"{path}.required_evidence",
            issues,
            pattern=EVIDENCE_KIND,
        )
        _closed_string_list(
            phase.get("required_gap_closures"),
            f"{path}.required_gap_closures",
            issues,
            pattern=GAP_ID,
            allow_empty=True,
        )
        for flag in (
            "public_users_allowed",
            "live_money_allowed",
            "intentional_failure_injection_allowed",
        ):
            if not isinstance(phase.get(flag), bool):
                issues.append(f"{path}.{flag} must be boolean")

        if phase_id in {"T0", "T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8"} and phase.get(
            "public_users_allowed"
        ) is not False:
            issues.append(f"{path} cannot permit public users before T9")
        if phase_id in {"T0", "T1", "T2", "T3", "T4", "T5", "T6", "T7"} and phase.get(
            "live_money_allowed"
        ) is not False:
            issues.append(f"{path} cannot permit live money before T8")
        if phase_id in {"T7", "T8", "T9", "T10"} and phase.get(
            "intentional_failure_injection_allowed"
        ) is not False:
            issues.append(f"{path} cannot permit intentional failure injection in field/user phases")

    if phases:
        t8 = phases[8] if len(phases) > 8 and isinstance(phases[8], dict) else {}
        expected_gaps = [f"GAP-{index:03d}" for index in range(1, 20)]
        if t8.get("required_gap_closures") != expected_gaps:
            issues.append("catalog T8 must require exact GAP-001 through GAP-019 closure")
    return sorted(set(issues))


def _validate_candidate(candidate: Any, issues: list[str]) -> None:
    value = _mapping(candidate, "evidence.candidate", issues)
    commit = value.get("commit")
    if not isinstance(commit, str) or HEX_40.fullmatch(commit) is None or set(commit) == {"0"}:
        issues.append("evidence.candidate.commit must be a non-placeholder lowercase Git SHA")
    if value.get("clean") is not True:
        issues.append("evidence.candidate.clean must be true for phase promotion")
    migration_head = value.get("migration_head")
    if not isinstance(migration_head, str) or re.fullmatch(r"\d{8}_\d{4}", migration_head) is None:
        issues.append("evidence.candidate.migration_head must be an ordered revision")
    _reference(value.get("release_label"), "evidence.candidate.release_label", issues)
    for name in (
        "release_evidence_sha256",
        "artifact_manifest_sha256",
        "contract_inventory_sha256",
    ):
        _sha256(value.get(name), f"evidence.candidate.{name}", issues)


def _validate_evidence_items(
    raw_items: Any,
    path: str,
    issues: list[str],
    *,
    real_user_evidence_allowed: bool,
) -> set[str]:
    items = _list(raw_items, path, issues)
    kinds: list[str] = []
    for index, raw_item in enumerate(items):
        item_path = f"{path}[{index}]"
        item = _mapping(raw_item, item_path, issues)
        kind = item.get("kind")
        if not isinstance(kind, str) or EVIDENCE_KIND.fullmatch(kind) is None:
            issues.append(f"{item_path}.kind must be a closed uppercase identifier")
        else:
            kinds.append(kind)
        _reference(item.get("reference"), f"{item_path}.reference", issues)
        _sha256(item.get("sha256"), f"{item_path}.sha256", issues)
        collected_at = _utc_timestamp(item.get("collected_at"), f"{item_path}.collected_at", issues)
        retention_until = _utc_timestamp(
            item.get("retention_until"), f"{item_path}.retention_until", issues
        )
        if collected_at is not None and retention_until is not None and retention_until <= collected_at:
            issues.append(f"{item_path}.retention_until must be after collected_at")
        classification = item.get("data_classification")
        if classification not in DATA_CLASSIFICATIONS:
            issues.append(f"{item_path}.data_classification is unsupported")
        if classification == "REAL_USER_AGGREGATE" and not real_user_evidence_allowed:
            issues.append(f"{item_path} cannot contain real-user evidence before T8")
    if len(kinds) != len(set(kinds)):
        issues.append(f"{path} must not contain duplicate evidence kinds")
    return set(kinds)


def _validate_signoffs(
    raw_signoffs: Any,
    path: str,
    issues: list[str],
    required: set[str],
) -> None:
    signoffs = _list(raw_signoffs, path, issues)
    authorities: list[str] = []
    for index, raw_signoff in enumerate(signoffs):
        item_path = f"{path}[{index}]"
        signoff = _mapping(raw_signoff, item_path, issues)
        authority = signoff.get("authority")
        if authority not in AUTHORITIES:
            issues.append(f"{item_path}.authority is unsupported")
        elif isinstance(authority, str):
            authorities.append(authority)
        if signoff.get("decision") != "ACCEPTED":
            issues.append(f"{item_path}.decision must be ACCEPTED")
        _reference(signoff.get("approver_reference"), f"{item_path}.approver_reference", issues)
        _utc_timestamp(signoff.get("signed_at"), f"{item_path}.signed_at", issues)
    if len(authorities) != len(set(authorities)):
        issues.append(f"{path} must not contain duplicate authorities")
    if set(authorities) != required:
        issues.append(
            f"{path} authorities are {sorted(set(authorities))!r}, expected {sorted(required)!r}"
        )


def _validate_defects(raw_defects: Any, path: str, issues: list[str], *, accepted: bool) -> None:
    defects = _list(raw_defects, path, issues)
    identifiers: list[str] = []
    for index, raw_defect in enumerate(defects):
        item_path = f"{path}[{index}]"
        defect = _mapping(raw_defect, item_path, issues)
        identifier = defect.get("id")
        if not isinstance(identifier, str) or IDENTIFIER.fullmatch(identifier) is None:
            issues.append(f"{item_path}.id must be a controlled identifier")
        else:
            identifiers.append(identifier)
        severity = defect.get("severity")
        status = defect.get("status")
        if severity not in {"S0", "S1", "S2", "S3"}:
            issues.append(f"{item_path}.severity is unsupported")
        if status not in {"OPEN", "CLOSED", "RISK_ACCEPTED"}:
            issues.append(f"{item_path}.status is unsupported")
        if accepted and status == "OPEN":
            issues.append(f"{item_path} cannot remain OPEN in an accepted phase")
        if status == "RISK_ACCEPTED":
            if severity in {"S0", "S1"}:
                issues.append(f"{item_path} cannot risk-accept an S0/S1 defect")
            _reference(
                defect.get("disposition_reference"),
                f"{item_path}.disposition_reference",
                issues,
            )
            _reference(defect.get("owner_reference"), f"{item_path}.owner_reference", issues)
            _utc_timestamp(defect.get("expires_at"), f"{item_path}.expires_at", issues)
    if len(identifiers) != len(set(identifiers)):
        issues.append(f"{path} must not contain duplicate defect IDs")


def _validate_gap_closures(
    raw_closures: Any,
    path: str,
    issues: list[str],
    required: set[str],
) -> None:
    closures = _list(raw_closures, path, issues)
    identifiers: list[str] = []
    for index, raw_closure in enumerate(closures):
        item_path = f"{path}[{index}]"
        closure = _mapping(raw_closure, item_path, issues)
        gap_id = closure.get("gap_id")
        if not isinstance(gap_id, str) or GAP_ID.fullmatch(gap_id) is None:
            issues.append(f"{item_path}.gap_id must be GAP-NNN")
        else:
            identifiers.append(gap_id)
        _reference(closure.get("reference"), f"{item_path}.reference", issues)
        _sha256(closure.get("sha256"), f"{item_path}.sha256", issues)
        _reference(
            closure.get("authority_reference"),
            f"{item_path}.authority_reference",
            issues,
        )
        _utc_timestamp(closure.get("accepted_at"), f"{item_path}.accepted_at", issues)
    if len(identifiers) != len(set(identifiers)):
        issues.append(f"{path} must not contain duplicate gap IDs")
    if set(identifiers) != required:
        issues.append(
            f"{path} IDs are {sorted(set(identifiers))!r}, expected {sorted(required)!r}"
        )


def _validate_scope(
    raw_scope: Any,
    path: str,
    issues: list[str],
    *,
    phase_index: int,
    phase: dict[str, Any],
) -> None:
    scope = _mapping(raw_scope, path, issues)
    _sha256(scope.get("configuration_bundle_sha256"), f"{path}.configuration_bundle_sha256", issues)
    city_ids = _closed_string_list(
        scope.get("city_ids"),
        f"{path}.city_ids",
        issues,
        pattern=IDENTIFIER,
        allow_empty=phase_index < 4,
    )
    if phase_index in {7, 8, 9} and len(city_ids) != 1:
        issues.append(f"{path}.city_ids must identify exactly one city for T7-T9")
    if phase_index == 10 and len(city_ids) < 2:
        issues.append(f"{path}.city_ids must identify at least two cities for T10")

    environment_class = scope.get("environment_class")
    if environment_class not in phase.get("environment_classes", []):
        issues.append(f"{path}.environment_class is not allowed for this phase")
    participant_mode = scope.get("participant_mode")
    if participant_mode not in phase.get("participant_modes", []):
        issues.append(f"{path}.participant_mode is not allowed for this phase")

    for flag in ("public_users", "live_money", "intentional_failure_injection"):
        if not isinstance(scope.get(flag), bool):
            issues.append(f"{path}.{flag} must be boolean")
    if scope.get("public_users") and not phase.get("public_users_allowed"):
        issues.append(f"{path}.public_users exceeds the phase exposure boundary")
    if scope.get("live_money") and not phase.get("live_money_allowed"):
        issues.append(f"{path}.live_money exceeds the phase money boundary")
    if scope.get("intentional_failure_injection") and not phase.get(
        "intentional_failure_injection_allowed"
    ):
        issues.append(f"{path}.intentional_failure_injection is unsafe for this phase")
    if phase_index >= 9 and scope.get("public_users") is not True:
        issues.append(f"{path}.public_users must be true for accepted T9-T10")
    if phase_index >= 8 and scope.get("live_money") is not True:
        issues.append(f"{path}.live_money must be true for accepted T8-T10")
    if phase_index == 5 and scope.get("intentional_failure_injection") is not True:
        issues.append(f"{path}.intentional_failure_injection must be true for accepted T5")


def validate_evidence_index(catalog: Any, evidence: Any) -> list[str]:
    issues = validate_catalog(catalog)
    root = _mapping(evidence, "evidence", issues)
    _scan_forbidden_keys(root, "evidence", issues)
    if root.get("schema_version") != 1:
        issues.append("evidence.schema_version must be 1")
    catalog_root = catalog if isinstance(catalog, dict) else {}
    if root.get("catalog_revision") != catalog_root.get("catalog_revision"):
        issues.append("evidence.catalog_revision does not match the phase catalog")

    phases = catalog_root.get("phases") if isinstance(catalog_root.get("phases"), list) else []
    records = _list(root.get("phase_records"), "evidence.phase_records", issues)
    record_ids = [record.get("id") if isinstance(record, dict) else None for record in records]
    if tuple(record_ids) != PHASE_IDS:
        issues.append(f"evidence.phase_records must be ordered exactly as {PHASE_IDS!r}")

    statuses = [record.get("status") if isinstance(record, dict) else None for record in records]
    active = any(status != "NOT_STARTED" for status in statuses)
    if active:
        _validate_candidate(root.get("candidate"), issues)
    elif root.get("candidate") is not None:
        issues.append("evidence.candidate must be null while every phase is NOT_STARTED")

    for index, raw_record in enumerate(records):
        path = f"evidence.phase_records[{index}]"
        record = _mapping(raw_record, path, issues)
        status = record.get("status")
        if status not in STATUSES:
            issues.append(f"{path}.status is unsupported")
            continue
        if status == "NOT_STARTED":
            if set(record) != {"id", "status"}:
                issues.append(f"{path} NOT_STARTED records may contain only id and status")
            continue

        if index > 0 and statuses[index - 1] != "ACCEPTED":
            issues.append(f"{path} cannot start before {PHASE_IDS[index - 1]} is ACCEPTED")
        started_at = _utc_timestamp(record.get("started_at"), f"{path}.started_at", issues)
        evidence_kinds = _validate_evidence_items(
            record.get("evidence", []),
            f"{path}.evidence",
            issues,
            real_user_evidence_allowed=index >= 8,
        )
        _validate_defects(
            record.get("defects", []),
            f"{path}.defects",
            issues,
            accepted=status == "ACCEPTED",
        )

        if status == "ACCEPTED":
            phase = phases[index] if index < len(phases) and isinstance(phases[index], dict) else {}
            completed_at = _utc_timestamp(
                record.get("completed_at"), f"{path}.completed_at", issues
            )
            if started_at is not None and completed_at is not None and completed_at < started_at:
                issues.append(f"{path}.completed_at must not precede started_at")
            required_evidence = set(phase.get("required_evidence", []))
            if evidence_kinds != required_evidence:
                issues.append(
                    f"{path}.evidence kinds are {sorted(evidence_kinds)!r}, "
                    f"expected {sorted(required_evidence)!r}"
                )
            _validate_signoffs(
                record.get("signoffs"),
                f"{path}.signoffs",
                issues,
                set(phase.get("required_authorities", [])),
            )
            _validate_scope(record.get("scope"), f"{path}.scope", issues, phase_index=index, phase=phase)
            _validate_gap_closures(
                record.get("gap_closures", []),
                f"{path}.gap_closures",
                issues,
                set(phase.get("required_gap_closures", [])),
            )
        elif status in {"BLOCKED", "REJECTED", "INVALIDATED"}:
            _reference(
                record.get("decision_reference"),
                f"{path}.decision_reference",
                issues,
            )
        if status != "ACCEPTED" and ("signoffs" in record or "gap_closures" in record):
            issues.append(f"{path} cannot carry acceptance signoffs or gap closures before ACCEPTED")

    return sorted(set(issues))


def require_through(evidence: Any, phase_id: str) -> list[str]:
    if phase_id not in PHASE_IDS:
        return [f"unsupported required phase {phase_id!r}"]
    root = evidence if isinstance(evidence, dict) else {}
    records = root.get("phase_records") if isinstance(root.get("phase_records"), list) else []
    statuses = {
        item.get("id"): item.get("status")
        for item in records
        if isinstance(item, dict)
    }
    target = PHASE_IDS.index(phase_id)
    return [
        f"{candidate} is {statuses.get(candidate, 'MISSING')}, required ACCEPTED"
        for candidate in PHASE_IDS[: target + 1]
        if statuses.get(candidate) != "ACCEPTED"
    ]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument(
        "--require-through",
        choices=PHASE_IDS,
        help="also require this phase and every predecessor to be ACCEPTED",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    arguments = _parser().parse_args(list(argv) if argv is not None else None)
    try:
        catalog = load_json(arguments.catalog)
        evidence = load_json(arguments.evidence)
    except PhaseEvidenceError as error:
        print(f"Test-phase evidence validation failed: {error}", file=sys.stderr)
        return 1
    issues = validate_evidence_index(catalog, evidence)
    if arguments.require_through:
        issues.extend(require_through(evidence, arguments.require_through))
    if issues:
        print("Test-phase evidence validation failed:", file=sys.stderr)
        for issue in sorted(set(issues)):
            print(f"- {issue}", file=sys.stderr)
        return 1
    status_summary = ", ".join(
        f"{record['id']}={record['status']}" for record in evidence["phase_records"]
    )
    print(
        "Test-phase evidence validation passed. Metadata consistency only; external "
        f"evidence authenticity remains an approver responsibility. {status_summary}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
