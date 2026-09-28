"""Validate the provider-neutral GAP-003 managed PostGIS evidence record.

The committed template is deliberately ``NOT_STARTED``. A protected external
record can accept GAP-003 only after a real managed service proves private and
encrypted operation, least privilege, current-head migration, PITR, restore,
failover, capacity, and backup-retention behavior. The record contains bounded
references and aggregate measurements only. It never accepts T5 or deployment.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Iterable

from validate_docs import discover_migration_head


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE = WORKSPACE_ROOT / "infra" / "deploy" / "managed-postgis-evidence.template.json"
MIGRATIONS_ROOT = WORKSPACE_ROOT / "backend" / "migrations" / "versions"

ROOT_KEYS = {
    "schema_version",
    "evidence_revision",
    "gap",
    "phase",
    "status",
    "data_classification",
    "candidate_label",
    "source_commit",
    "environment_inventory_reference",
    "database",
    "least_privilege",
    "objectives",
    "capacity",
    "migration_rehearsal",
    "backup_policy",
    "restore_rehearsal",
    "failover_rehearsal",
    "retention_reconciliation",
    "approvals",
    "gap_003_accepted",
    "phase_accepted",
    "deployment_accepted",
    "limitations",
}
DATABASE_KEYS = {
    "service_reference",
    "network_policy_reference",
    "compatibility_report_reference",
    "postgres_major",
    "postgis_version",
    "private_access_only",
    "tls_in_transit",
    "encryption_at_rest",
    "automated_failover_enabled",
}
LEAST_PRIVILEGE_KEYS = {
    "role_review_reference",
    "application_role_non_superuser",
    "application_role_no_createdb",
    "application_role_no_createrole",
    "migration_role_separate",
    "backup_authority_separate",
    "monitoring_role_read_only",
}
OBJECTIVE_KEYS = {"approval_reference", "approved_rpo_seconds", "approved_rto_seconds"}
CAPACITY_KEYS = {
    "report_reference",
    "monitoring_reference",
    "alerting_reference",
    "server_connection_limit",
    "application_connection_budget",
    "headroom_percent",
}
MIGRATION_KEYS = {
    "source_copy_reference",
    "report_reference",
    "migration_head",
    "duration_seconds",
    "advisory_lock_verified",
    "timeouts_verified",
    "conflicting_data_count",
    "old_new_compatibility_reference",
    "forward_fix_reference",
}
BACKUP_KEYS = {
    "policy_reference",
    "access_review_reference",
    "provider_audit_reference",
    "encrypted",
    "automated_snapshots_enabled",
    "snapshot_frequency_hours",
    "continuous_pitr_enabled",
    "pitr_window_days",
    "backup_retention_days",
    "cross_failure_domain_copy",
}
RESTORE_KEYS = {
    "report_reference",
    "restored_at",
    "isolated_staging_target",
    "migration_head",
    "postgis_version_match",
    "table_counts_match",
    "schema_object_counts_match",
    "application_readiness_passed",
    "measured_data_loss_seconds",
    "measured_recovery_seconds",
    "restore_target_disposition_reference",
}
FAILOVER_KEYS = {
    "report_reference",
    "executed_at",
    "provider_failover_completed",
    "api_recovery_verified",
    "worker_recovery_verified",
    "alerts_acknowledged",
    "measured_data_loss_seconds",
    "measured_recovery_seconds",
}
RETENTION_KEYS = {
    "policy_reference",
    "legal_hold_review_reference",
    "expiry_test_reference",
    "held_records_survived_restore",
    "expired_personal_fields_absent_after_backup_expiry",
    "provider_backup_deletion_verified",
}
APPROVAL_KEYS = {"function", "decision", "evidence_reference", "decided_at"}

APPROVAL_FUNCTIONS = ("ENGINEERING", "SECURITY", "OPERATIONS", "PRIVACY_LEGAL")
REFERENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,399}")
SAFE_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._ -]{1,79}")
CLOSED_ID = re.compile(r"[A-Z][A-Z0-9_]{2,95}")
VERSION = re.compile(r"[0-9]+\.[0-9]+(?:\.[0-9]+)?")
COMMIT = re.compile(r"[0-9a-f]{40}")
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
FORBIDDEN_KEY_PARTS = {
    "password",
    "token",
    "api_key",
    "private_key",
    "connection_string",
    "credential",
    "database_url",
    "person_name",
    "email",
    "row_content",
}


class ManagedPostgisEvidenceError(ValueError):
    """Raised when GAP-003 evidence weakens the reviewed acceptance contract."""


def _load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ManagedPostgisEvidenceError(f"Cannot read {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise ManagedPostgisEvidenceError(
            f"Invalid JSON in {path} at line {error.lineno}."
        ) from error


def _exact_object(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ManagedPostgisEvidenceError(f"{label} must use exact reviewed fields.")
    return value


def _scan_forbidden_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if any(part in normalized for part in FORBIDDEN_KEY_PARTS):
                raise ManagedPostgisEvidenceError(
                    f"Managed PostGIS evidence contains forbidden key {key!r}."
                )
            _scan_forbidden_keys(child)
    elif isinstance(value, list):
        for child in value:
            _scan_forbidden_keys(child)


def _reference(value: Any, label: str, *, required: bool) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or REFERENCE.fullmatch(value) is None:
        raise ManagedPostgisEvidenceError(
            f"{label} must be a bounded opaque reference without credentials or query data."
        )
    return value


def _timestamp(value: Any, label: str, *, required: bool) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or TIMESTAMP.fullmatch(value) is None:
        raise ManagedPostgisEvidenceError(f"{label} must be a UTC second timestamp.")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as error:
        raise ManagedPostgisEvidenceError(f"{label} is not a real UTC timestamp.") from error
    return value


def _number(
    value: Any,
    label: str,
    *,
    required: bool,
    minimum: float = 0,
    maximum: float | None = None,
) -> float | None:
    if value is None and not required:
        return None
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < minimum
        or (maximum is not None and value > maximum)
    ):
        raise ManagedPostgisEvidenceError(f"{label} is outside its reviewed numeric bounds.")
    return float(value)


def _all_true(record: dict[str, Any], fields: set[str], label: str, *, accepted: bool) -> None:
    for field in fields:
        if not isinstance(record[field], bool):
            raise ManagedPostgisEvidenceError(f"{label}.{field} must be Boolean.")
        if accepted and record[field] is not True:
            raise ManagedPostgisEvidenceError(f"accepted evidence requires {label}.{field}=true.")


def _validate_database(value: Any, *, accepted: bool) -> None:
    record = _exact_object(value, DATABASE_KEYS, "database")
    for field in ("service_reference", "network_policy_reference", "compatibility_report_reference"):
        _reference(record[field], f"database.{field}", required=accepted)
    if record["postgres_major"] is not None or accepted:
        if isinstance(record["postgres_major"], bool) or record["postgres_major"] != 16:
            raise ManagedPostgisEvidenceError(
                "database.postgres_major must remain the tested PostgreSQL 16 line."
            )
    if record["postgis_version"] is not None or accepted:
        if not isinstance(record["postgis_version"], str) or VERSION.fullmatch(record["postgis_version"]) is None:
            raise ManagedPostgisEvidenceError("database.postgis_version is invalid.")
    _all_true(
        record,
        {
            "private_access_only",
            "tls_in_transit",
            "encryption_at_rest",
            "automated_failover_enabled",
        },
        "database",
        accepted=accepted,
    )


def _validate_least_privilege(value: Any, *, accepted: bool) -> None:
    record = _exact_object(value, LEAST_PRIVILEGE_KEYS, "least_privilege")
    _reference(record["role_review_reference"], "least_privilege.role_review_reference", required=accepted)
    _all_true(
        record,
        LEAST_PRIVILEGE_KEYS - {"role_review_reference"},
        "least_privilege",
        accepted=accepted,
    )


def _validate_objectives(value: Any, *, accepted: bool) -> tuple[float | None, float | None]:
    record = _exact_object(value, OBJECTIVE_KEYS, "objectives")
    _reference(record["approval_reference"], "objectives.approval_reference", required=accepted)
    rpo = _number(
        record["approved_rpo_seconds"],
        "objectives.approved_rpo_seconds",
        required=accepted,
        minimum=0,
    )
    rto = _number(
        record["approved_rto_seconds"],
        "objectives.approved_rto_seconds",
        required=accepted,
        minimum=1,
    )
    return rpo, rto


def _validate_capacity(value: Any, *, accepted: bool) -> None:
    record = _exact_object(value, CAPACITY_KEYS, "capacity")
    for field in ("report_reference", "monitoring_reference", "alerting_reference"):
        _reference(record[field], f"capacity.{field}", required=accepted)
    server = _number(
        record["server_connection_limit"],
        "capacity.server_connection_limit",
        required=accepted,
        minimum=1,
    )
    application = _number(
        record["application_connection_budget"],
        "capacity.application_connection_budget",
        required=accepted,
        minimum=1,
    )
    headroom = _number(
        record["headroom_percent"],
        "capacity.headroom_percent",
        required=accepted,
        minimum=10,
        maximum=90,
    )
    if accepted and server is not None and application is not None and application >= server:
        raise ManagedPostgisEvidenceError(
            "application connection budget must leave capacity outside application pools."
        )
    if accepted and server is not None and application is not None and headroom is not None:
        actual_headroom = ((server - application) / server) * 100
        if actual_headroom < headroom:
            raise ManagedPostgisEvidenceError(
                "declared connection headroom exceeds the reserved connection capacity."
            )


def _validate_migration(value: Any, *, accepted: bool, expected_head: str) -> None:
    record = _exact_object(value, MIGRATION_KEYS, "migration_rehearsal")
    for field in (
        "source_copy_reference",
        "report_reference",
        "old_new_compatibility_reference",
        "forward_fix_reference",
    ):
        _reference(record[field], f"migration_rehearsal.{field}", required=accepted)
    if record["migration_head"] is not None or accepted:
        if record["migration_head"] != expected_head:
            raise ManagedPostgisEvidenceError(
                f"migration rehearsal must reach current head {expected_head}."
            )
    _number(
        record["duration_seconds"],
        "migration_rehearsal.duration_seconds",
        required=accepted,
        minimum=0.001,
    )
    conflicts = _number(
        record["conflicting_data_count"],
        "migration_rehearsal.conflicting_data_count",
        required=accepted,
        minimum=0,
    )
    if accepted and conflicts != 0:
        raise ManagedPostgisEvidenceError("migration rehearsal cannot accept conflicting source data.")
    _all_true(
        record,
        {"advisory_lock_verified", "timeouts_verified"},
        "migration_rehearsal",
        accepted=accepted,
    )


def _validate_backup(value: Any, *, accepted: bool) -> None:
    record = _exact_object(value, BACKUP_KEYS, "backup_policy")
    for field in ("policy_reference", "access_review_reference", "provider_audit_reference"):
        _reference(record[field], f"backup_policy.{field}", required=accepted)
    _all_true(
        record,
        {
            "encrypted",
            "automated_snapshots_enabled",
            "continuous_pitr_enabled",
            "cross_failure_domain_copy",
        },
        "backup_policy",
        accepted=accepted,
    )
    _number(
        record["snapshot_frequency_hours"],
        "backup_policy.snapshot_frequency_hours",
        required=accepted,
        minimum=0.25,
        maximum=24,
    )
    pitr = _number(
        record["pitr_window_days"],
        "backup_policy.pitr_window_days",
        required=accepted,
        minimum=1,
        maximum=365,
    )
    retention = _number(
        record["backup_retention_days"],
        "backup_policy.backup_retention_days",
        required=accepted,
        minimum=1,
        maximum=3650,
    )
    if accepted and pitr is not None and retention is not None and retention < pitr:
        raise ManagedPostgisEvidenceError("backup retention cannot be shorter than the PITR window.")


def _validate_recovery_record(
    value: Any,
    *,
    label: str,
    keys: set[str],
    accepted: bool,
    rpo: float | None,
    rto: float | None,
) -> None:
    record = _exact_object(value, keys, label)
    _reference(record["report_reference"], f"{label}.report_reference", required=accepted)
    time_field = "restored_at" if label == "restore_rehearsal" else "executed_at"
    _timestamp(record[time_field], f"{label}.{time_field}", required=accepted)
    data_loss = _number(
        record["measured_data_loss_seconds"],
        f"{label}.measured_data_loss_seconds",
        required=accepted,
        minimum=0,
    )
    recovery = _number(
        record["measured_recovery_seconds"],
        f"{label}.measured_recovery_seconds",
        required=accepted,
        minimum=0.001,
    )
    if accepted and rpo is not None and data_loss is not None and data_loss > rpo:
        raise ManagedPostgisEvidenceError(f"{label} exceeds approved RPO.")
    if accepted and rto is not None and recovery is not None and recovery > rto:
        raise ManagedPostgisEvidenceError(f"{label} exceeds approved RTO.")


def _validate_restore(
    value: Any, *, accepted: bool, expected_head: str, rpo: float | None, rto: float | None
) -> None:
    _validate_recovery_record(
        value,
        label="restore_rehearsal",
        keys=RESTORE_KEYS,
        accepted=accepted,
        rpo=rpo,
        rto=rto,
    )
    record = value
    _reference(
        record["restore_target_disposition_reference"],
        "restore_rehearsal.restore_target_disposition_reference",
        required=accepted,
    )
    if record["migration_head"] is not None or accepted:
        if record["migration_head"] != expected_head:
            raise ManagedPostgisEvidenceError(
                f"restored database must reach current head {expected_head}."
            )
    _all_true(
        record,
        {
            "isolated_staging_target",
            "postgis_version_match",
            "table_counts_match",
            "schema_object_counts_match",
            "application_readiness_passed",
        },
        "restore_rehearsal",
        accepted=accepted,
    )


def _validate_failover(
    value: Any, *, accepted: bool, rpo: float | None, rto: float | None
) -> None:
    _validate_recovery_record(
        value,
        label="failover_rehearsal",
        keys=FAILOVER_KEYS,
        accepted=accepted,
        rpo=rpo,
        rto=rto,
    )
    _all_true(
        value,
        {
            "provider_failover_completed",
            "api_recovery_verified",
            "worker_recovery_verified",
            "alerts_acknowledged",
        },
        "failover_rehearsal",
        accepted=accepted,
    )


def _validate_retention(value: Any, *, accepted: bool) -> None:
    record = _exact_object(value, RETENTION_KEYS, "retention_reconciliation")
    for field in ("policy_reference", "legal_hold_review_reference", "expiry_test_reference"):
        _reference(record[field], f"retention_reconciliation.{field}", required=accepted)
    _all_true(
        record,
        RETENTION_KEYS
        - {"policy_reference", "legal_hold_review_reference", "expiry_test_reference"},
        "retention_reconciliation",
        accepted=accepted,
    )


def _validate_approvals(value: Any, *, accepted: bool) -> None:
    if not isinstance(value, list) or len(value) != len(APPROVAL_FUNCTIONS):
        raise ManagedPostgisEvidenceError("approvals must contain all four reviewed functions.")
    for expected, raw in zip(APPROVAL_FUNCTIONS, value):
        approval = _exact_object(raw, APPROVAL_KEYS, f"approval {expected}")
        if approval["function"] != expected:
            raise ManagedPostgisEvidenceError("approval order/function is invalid.")
        decision = approval["decision"]
        if decision not in {"PENDING", "APPROVED", "REJECTED"}:
            raise ManagedPostgisEvidenceError(f"approval {expected} decision is invalid.")
        decided = decision != "PENDING"
        _reference(
            approval["evidence_reference"],
            f"approval {expected} evidence",
            required=decided or accepted,
        )
        _timestamp(
            approval["decided_at"],
            f"approval {expected} decided_at",
            required=decided or accepted,
        )
        if accepted and decision != "APPROVED":
            raise ManagedPostgisEvidenceError(f"accepted evidence requires {expected} approval.")


def _validate_not_started(record: dict[str, Any]) -> None:
    if record["candidate_label"] is not None or record["source_commit"] is not None:
        raise ManagedPostgisEvidenceError("NOT_STARTED evidence cannot identify a candidate.")
    if record["environment_inventory_reference"] is not None:
        raise ManagedPostgisEvidenceError("NOT_STARTED evidence cannot identify an environment.")
    sections = (
        "database",
        "least_privilege",
        "objectives",
        "capacity",
        "migration_rehearsal",
        "backup_policy",
        "restore_rehearsal",
        "failover_rehearsal",
        "retention_reconciliation",
    )
    for section in sections:
        if any(
            value is not None and value is not False
            for value in record[section].values()
        ):
            raise ManagedPostgisEvidenceError(
                f"NOT_STARTED {section} cannot contain operational claims."
            )
    for approval in record["approvals"]:
        if (
            approval["decision"] != "PENDING"
            or approval["evidence_reference"] is not None
            or approval["decided_at"] is not None
        ):
            raise ManagedPostgisEvidenceError(
                "NOT_STARTED approvals must remain pending without evidence."
            )


def validate_evidence(
    evidence: Any, *, require_accepted: bool = False, expected_head: str | None = None
) -> dict[str, Any]:
    record = _exact_object(evidence, ROOT_KEYS, "managed PostGIS evidence")
    _scan_forbidden_keys(record)
    if (
        record["schema_version"] != 1
        or record["gap"] != "GAP-003"
        or record["phase"] != "T5"
        or record["data_classification"] != "CONTROL_REFERENCES_AND_AGGREGATES_ONLY"
    ):
        raise ManagedPostgisEvidenceError("managed PostGIS evidence identity is invalid.")
    try:
        date.fromisoformat(str(record["evidence_revision"]))
    except ValueError as error:
        raise ManagedPostgisEvidenceError("evidence_revision must be a real ISO date.") from error
    status = record["status"]
    if status not in {"NOT_STARTED", "IN_PROGRESS", "REJECTED", "ACCEPTED"}:
        raise ManagedPostgisEvidenceError("managed PostGIS evidence status is invalid.")
    accepted = status == "ACCEPTED"
    if record["gap_003_accepted"] is not accepted:
        raise ManagedPostgisEvidenceError(
            "gap_003_accepted must be true only for complete ACCEPTED evidence."
        )
    if record["phase_accepted"] is not False or record["deployment_accepted"] is not False:
        raise ManagedPostgisEvidenceError("GAP-003 evidence cannot accept T5 or deployment.")
    if require_accepted and not accepted:
        raise ManagedPostgisEvidenceError("externally accepted GAP-003 evidence is required.")
    if record["candidate_label"] is not None or accepted:
        if not isinstance(record["candidate_label"], str) or SAFE_LABEL.fullmatch(record["candidate_label"]) is None:
            raise ManagedPostgisEvidenceError("candidate_label is invalid.")
    if record["source_commit"] is not None or accepted:
        if not isinstance(record["source_commit"], str) or COMMIT.fullmatch(record["source_commit"]) is None:
            raise ManagedPostgisEvidenceError("source_commit must be a full lowercase Git commit.")
    _reference(
        record["environment_inventory_reference"],
        "environment_inventory_reference",
        required=accepted,
    )

    migration_head = expected_head or discover_migration_head(MIGRATIONS_ROOT)
    _validate_database(record["database"], accepted=accepted)
    _validate_least_privilege(record["least_privilege"], accepted=accepted)
    rpo, rto = _validate_objectives(record["objectives"], accepted=accepted)
    _validate_capacity(record["capacity"], accepted=accepted)
    _validate_migration(record["migration_rehearsal"], accepted=accepted, expected_head=migration_head)
    _validate_backup(record["backup_policy"], accepted=accepted)
    _validate_restore(
        record["restore_rehearsal"],
        accepted=accepted,
        expected_head=migration_head,
        rpo=rpo,
        rto=rto,
    )
    _validate_failover(record["failover_rehearsal"], accepted=accepted, rpo=rpo, rto=rto)
    _validate_retention(record["retention_reconciliation"], accepted=accepted)
    _validate_approvals(record["approvals"], accepted=accepted)

    limitations = record["limitations"]
    if (
        not isinstance(limitations, list)
        or "NO_PHASE_OR_DEPLOYMENT_ACCEPTANCE" not in limitations
        or any(not isinstance(item, str) or CLOSED_ID.fullmatch(item) is None for item in limitations)
        or len(limitations) != len(set(limitations))
    ):
        raise ManagedPostgisEvidenceError("limitations must retain the no-acceptance boundary.")
    if accepted and "NO_MANAGED_DATABASE_ACCEPTED" in limitations:
        raise ManagedPostgisEvidenceError("accepted evidence retains the unaccepted-database limit.")
    if status == "NOT_STARTED":
        if limitations != ["NO_MANAGED_DATABASE_ACCEPTED", "NO_PHASE_OR_DEPLOYMENT_ACCEPTANCE"]:
            raise ManagedPostgisEvidenceError("NOT_STARTED limitations are invalid.")
        _validate_not_started(record)
    return {
        "status": status,
        "migration_head": migration_head,
        "gap_003_accepted": accepted,
        "approvals": len(record["approvals"]),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--require-accepted", action="store_true")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    arguments = _parser().parse_args(list(argv) if argv is not None else None)
    try:
        summary = validate_evidence(
            _load(arguments.evidence), require_accepted=arguments.require_accepted
        )
    except (OSError, ValueError, ManagedPostgisEvidenceError) as error:
        print(f"Managed PostGIS evidence validation failed: {error}", file=sys.stderr)
        return 1
    print(
        "Managed PostGIS evidence passed: "
        f"status {summary['status']}, migration head {summary['migration_head']}, "
        f"{summary['approvals']} approval functions; zero phase/deployment acceptance claims."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
