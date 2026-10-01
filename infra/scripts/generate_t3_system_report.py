"""Generate bounded T3 system evidence from full pytest and database metadata.

The generator requires a green, skip-free full backend JUnit report, named
concurrency/recovery/reconciliation regression cases, and a passing post-run
database metadata record. It intentionally leaves T3 incomplete until a current
backup/restore rehearsal is supplied as separate evidence.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable
import xml.etree.ElementTree as ET


MINIMUM_FULL_SUITE_TESTS = 900
REQUIRED_CASES = {
    "MIGRATION_AND_LOCKS": (
        "tests.integration.test_migration_serialization::test_actual_alembic_command_refuses_competing_owner_before_schema_changes",
        "tests.integration.test_migration_serialization::test_terminated_migrator_process_does_not_leave_a_stale_lock",
        "tests.integration.test_migration_timeouts::test_cli_ddl_lock_timeout_rolls_back_and_releases_migration_ownership",
    ),
    "CONCURRENT_AUTHORITY": (
        "tests.integration.test_assignment_invariants::test_competing_assignments_have_one_winner",
        "tests.integration.test_live_ride_concurrency::test_live_commands_observe_winning_transaction",
        "tests.integration.test_scheduled_acceptance_concurrency::test_concurrent_acceptance_reloads_authority_and_honors_buffered_windows",
        "tests.integration.test_security_incident_operations::test_concurrent_responsibility_assignments_have_one_authoritative_winner",
    ),
    "WORKER_KILL_AND_RECLAIM": (
        "tests.integration.test_city_authorization_notification_delivery::test_authorization_notice_survives_provider_failure_and_processor_restart",
        "tests.integration.test_city_authorization_notification_delivery::test_terminated_worker_process_releases_authorization_event_for_replacement",
        "tests.integration.test_live_ride_concurrency::test_expiry_worker_skips_locked_ride_then_expires_once",
    ),
    "LIVE_HINT_RECOVERY": (
        "tests.integration.test_live_event_recovery::test_live_event_listener_recovers_after_owned_backend_termination",
    ),
    "STATE_AND_MONEY_RECONCILIATION": (
        "tests.integration.test_cash_workload_http::test_cash_cli_durable_money_and_post_commit_failure",
        "tests.integration.test_capacity_workload_http::test_open_loop_capacity_cli_reconciles_every_released_arrival",
        "tests.integration.test_security_incident_operations::test_security_incident_scope_timeline_idempotency_and_lifecycle",
    ),
}
EXPECTED_METADATA_KEYS = {
    "schema_version",
    "generated_at",
    "evidence_level",
    "phase",
    "result",
    "data_classification",
    "phase_accepted",
    "deployment_accepted",
    "database_scope",
    "database_lifecycle",
    "migration_head",
    "postgres_version",
    "postgis_version",
    "preexisting_clone_databases_removed",
    "residual_clone_database_count",
    "authority",
    "limitations",
}
EXPECTED_BACKUP_KEYS = {
    "schema_version",
    "generated_at",
    "evidence_level",
    "phase",
    "result",
    "data_classification",
    "supported_evidence_kind",
    "phase_accepted",
    "deployment_accepted",
    "source_database_scope",
    "restore_target_scope",
    "restore_target_removed",
    "temporary_dump_removed",
    "backup_bytes",
    "backup_sha256",
    "reconciliation",
    "timings_seconds",
    "limitations",
}


class T3SystemEvidenceError(RuntimeError):
    """Raised when supplied artifacts cannot support the bounded T3 claims."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_junit(path: Path) -> tuple[dict[str, int], set[str], int]:
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as error:
        raise T3SystemEvidenceError(f"Cannot parse full backend JUnit: {error}") from error
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    if not suites:
        raise T3SystemEvidenceError("Full backend JUnit contains no test suite.")
    counts = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for suite in suites:
        for key in counts:
            try:
                counts[key] += int(suite.attrib.get(key, "0"))
            except ValueError as error:
                raise T3SystemEvidenceError(f"JUnit {key} count is not an integer.") from error
    cases: set[str] = set()
    case_elements = list(root.iter("testcase"))
    for case in case_elements:
        classname = case.attrib.get("classname", "")
        name = case.attrib.get("name", "").split("[", 1)[0]
        if classname and name:
            cases.add(f"{classname}::{name}")
    return counts, cases, len(case_elements)


def validate_database_metadata(metadata: Any) -> dict[str, Any]:
    if not isinstance(metadata, dict) or set(metadata) != EXPECTED_METADATA_KEYS:
        raise T3SystemEvidenceError("Database metadata does not use the reviewed schema.")
    if (
        metadata.get("schema_version") != 1
        or metadata.get("evidence_level") != "T3_DATABASE_POST_RUN_METADATA"
        or metadata.get("phase") != "T3"
        or metadata.get("result") != "PASS"
        or metadata.get("phase_accepted") is not False
        or metadata.get("deployment_accepted") is not False
        or metadata.get("database_scope") != "taximobile_ci"
        or metadata.get("database_lifecycle") not in {
            "RECREATED_BEFORE_MIGRATION",
            "EPHEMERAL_SERVICE_DATABASE",
        }
        or not isinstance(metadata.get("migration_head"), str)
        or not metadata["migration_head"]
        or not isinstance(metadata.get("postgres_version"), str)
        or not metadata["postgres_version"]
        or not isinstance(metadata.get("postgis_version"), str)
        or not metadata["postgis_version"]
        or not isinstance(metadata.get("preexisting_clone_databases_removed"), int)
        or metadata["preexisting_clone_databases_removed"] < 0
        or metadata.get("residual_clone_database_count") != 0
    ):
        raise T3SystemEvidenceError("Database metadata is not a passing bounded T3 record.")
    authority = metadata.get("authority")
    if not isinstance(authority, dict) or set(authority) != {
        "mode",
        "role_can_create_database",
        "role_is_superuser",
        "note",
    }:
        raise T3SystemEvidenceError("Database authority metadata is incomplete.")
    if not isinstance(authority["role_can_create_database"], bool) or not isinstance(
        authority["role_is_superuser"], bool
    ):
        raise T3SystemEvidenceError("Database authority flags are not Boolean values.")
    if authority["mode"] == "TEMPORARY_CREATEDB_REVOKED" and (
        authority["role_can_create_database"] or authority["role_is_superuser"]
    ):
        raise T3SystemEvidenceError("Local database authority was not revoked.")
    if authority["mode"] not in {
        "TEMPORARY_CREATEDB_REVOKED",
        "EPHEMERAL_CI_SERVICE_ROLE",
    }:
        raise T3SystemEvidenceError("Database authority mode is unsupported.")
    return metadata


def validate_backup_restore_evidence(
    evidence: Any, *, expected_head: str
) -> dict[str, Any]:
    if not isinstance(evidence, dict) or set(evidence) != EXPECTED_BACKUP_KEYS:
        raise T3SystemEvidenceError("Backup/restore evidence does not use the reviewed schema.")
    if (
        evidence.get("schema_version") != 1
        or evidence.get("evidence_level") != "T3_LOCAL_BACKUP_RESTORE_EXECUTION"
        or evidence.get("phase") != "T3"
        or evidence.get("result") != "PASS"
        or evidence.get("supported_evidence_kind") != "LOCAL_BACKUP_RESTORE_REPORT"
        or evidence.get("phase_accepted") is not False
        or evidence.get("deployment_accepted") is not False
        or evidence.get("source_database_scope") != "taximobile_ci"
        or evidence.get("restore_target_scope") != "EPHEMERAL_TAXIMOBILE_RESTORE_T3"
        or evidence.get("restore_target_removed") is not True
        or evidence.get("temporary_dump_removed") is not True
        or not isinstance(evidence.get("backup_bytes"), int)
        or evidence["backup_bytes"] <= 0
        or not isinstance(evidence.get("backup_sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", evidence["backup_sha256"]) is None
    ):
        raise T3SystemEvidenceError("Backup/restore evidence is not a passing bounded T3 record.")
    reconciliation = evidence.get("reconciliation")
    if (
        not isinstance(reconciliation, dict)
        or reconciliation.get("migration_head") != expected_head
        or not isinstance(reconciliation.get("postgis_version"), str)
        or not reconciliation["postgis_version"]
        or not isinstance(reconciliation.get("public_table_count"), int)
        or reconciliation["public_table_count"] <= 0
        or not isinstance(reconciliation.get("aggregate_row_count"), int)
        or reconciliation["aggregate_row_count"] < 0
        or reconciliation.get("table_counts_match") is not True
        or reconciliation.get("schema_object_counts_match") is not True
    ):
        raise T3SystemEvidenceError("Backup/restore reconciliation is incomplete or mismatched.")
    timings = evidence.get("timings_seconds")
    if (
        not isinstance(timings, dict)
        or set(timings) != {"backup", "restore", "verification", "total"}
        or any(not isinstance(value, (int, float)) or value < 0 for value in timings.values())
    ):
        raise T3SystemEvidenceError("Backup/restore timings are incomplete.")
    return evidence


def generate_report(
    junit_path: Path, metadata_path: Path, backup_restore_path: Path | None = None
) -> dict[str, Any]:
    counts, cases, case_element_count = parse_junit(junit_path)
    if (
        counts["tests"] < MINIMUM_FULL_SUITE_TESTS
        or counts["tests"] != case_element_count
        or counts["failures"]
        or counts["errors"]
        or counts["skipped"]
    ):
        raise T3SystemEvidenceError(
            "Full backend evidence requires at least 900 represented test cases and zero "
            "failures, errors, or skips."
        )
    if not any(item.startswith("tests.unit.") for item in cases) or not any(
        item.startswith("tests.integration.") for item in cases
    ):
        raise T3SystemEvidenceError("JUnit must contain both unit and integration tests.")

    coverage: dict[str, dict[str, Any]] = {}
    for category, required in REQUIRED_CASES.items():
        missing = sorted(set(required) - cases)
        if missing:
            raise T3SystemEvidenceError(
                f"Full backend JUnit is missing required {category} coverage: {missing[0]}"
            )
        coverage[category] = {
            "result": "PASS",
            "required_case_count": len(required),
            "required_cases": list(required),
        }

    try:
        metadata = validate_database_metadata(
            json.loads(metadata_path.read_text(encoding="utf-8"))
        )
    except OSError as error:
        raise T3SystemEvidenceError(f"Cannot read database metadata: {error}") from error
    except json.JSONDecodeError as error:
        raise T3SystemEvidenceError("Database metadata is invalid JSON.") from error

    supported_evidence_kinds = [
        "FULL_BACKEND_REPORT",
        "FRESH_DATABASE_MIGRATION_REPORT",
        "CONCURRENCY_AND_LOCK_REPORT",
        "WORKER_KILL_AND_RECLAIM_REPORT",
        "DATABASE_RECONCILIATION",
    ]
    missing_t3_evidence_kinds = ["LOCAL_BACKUP_RESTORE_REPORT"]
    backup_summary: dict[str, Any] | None = None
    backup_sha256: str | None = None
    if backup_restore_path is not None:
        try:
            backup = validate_backup_restore_evidence(
                json.loads(backup_restore_path.read_text(encoding="utf-8")),
                expected_head=metadata["migration_head"],
            )
        except OSError as error:
            raise T3SystemEvidenceError(f"Cannot read backup/restore evidence: {error}") from error
        except json.JSONDecodeError as error:
            raise T3SystemEvidenceError("Backup/restore evidence is invalid JSON.") from error
        supported_evidence_kinds.append("LOCAL_BACKUP_RESTORE_REPORT")
        missing_t3_evidence_kinds = []
        backup_sha256 = sha256_file(backup_restore_path)
        backup_summary = {
            "migration_head": backup["reconciliation"]["migration_head"],
            "postgis_version": backup["reconciliation"]["postgis_version"],
            "public_table_count": backup["reconciliation"]["public_table_count"],
            "aggregate_row_count": backup["reconciliation"]["aggregate_row_count"],
            "backup_bytes": backup["backup_bytes"],
            "restore_target_removed": backup["restore_target_removed"],
            "temporary_dump_removed": backup["temporary_dump_removed"],
            "timings_seconds": backup["timings_seconds"],
        }

    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_level": "T3_LOCAL_SYSTEM_EXECUTION",
        "phase": "T3",
        "result": "PASS",
        "data_classification": "SYNTHETIC",
        "phase_accepted": False,
        "phase_evidence_complete": not missing_t3_evidence_kinds,
        "deployment_accepted": False,
        "supported_evidence_kinds": supported_evidence_kinds,
        "missing_t3_evidence_kinds": missing_t3_evidence_kinds,
        "junit": counts,
        "junit_sha256": sha256_file(junit_path),
        "database_metadata_sha256": sha256_file(metadata_path),
        "database": {
            "scope": metadata["database_scope"],
            "lifecycle": metadata["database_lifecycle"],
            "migration_head": metadata["migration_head"],
            "postgres_version": metadata["postgres_version"],
            "postgis_version": metadata["postgis_version"],
            "preexisting_clone_databases_removed": metadata[
                "preexisting_clone_databases_removed"
            ],
            "residual_clone_database_count": metadata["residual_clone_database_count"],
            "authority_mode": metadata["authority"]["mode"],
        },
        "coverage": coverage,
        "limitations": [
            "NO_HOSTED_MULTI_REPLICA_CLAIM",
            "NO_PROVIDER_OR_DEVICE_CLAIM",
            "NO_REAL_USER_OR_LIVE_MONEY_ACTIVITY",
            "NO_PHASE_ACCEPTANCE_CLAIM",
            "NO_DEPLOYMENT_ACCEPTANCE_CLAIM",
        ],
    }
    if backup_summary is None:
        report["limitations"].insert(0, "NO_CURRENT_BACKUP_RESTORE_REHEARSAL_IN_THIS_REPORT")
    else:
        report["backup_restore_sha256"] = backup_sha256
        report["backup_restore"] = backup_summary
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--junit", required=True, type=Path)
    parser.add_argument("--database-metadata", required=True, type=Path)
    parser.add_argument("--backup-restore", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    arguments = _parser().parse_args(list(argv) if argv is not None else None)
    output = arguments.output.resolve()
    if output.exists():
        print("T3 system evidence failed: refusing to overwrite existing evidence.", file=sys.stderr)
        return 1
    try:
        report = generate_report(
            arguments.junit.resolve(),
            arguments.database_metadata.resolve(),
            arguments.backup_restore.resolve() if arguments.backup_restore else None,
        )
    except T3SystemEvidenceError as error:
        print(f"T3 system evidence failed: {error}", file=sys.stderr)
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"T3 system evidence PASS: {report['junit']['tests']} tests and "
        f"{len(report['supported_evidence_kinds'])} evidence kinds; "
        f"evidence_complete={str(report['phase_evidence_complete']).lower()}, "
        "phase/deployment acceptance remain false."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
