"""Validate the GAP-005 production operations identity/governance record.

The repository template is deliberately ``NOT_STARTED``. A protected external
copy may accept GAP-005 only after real operations accounts, MFA custody,
separation-of-duty assignments, JML/access-review controls, drills, audit
references, and owner approvals exist. The record stores opaque references, not
names, credentials, recovery codes, contact data, or copied documents. It never
accepts T5 or deployment.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GOVERNANCE = (
    WORKSPACE_ROOT / "infra" / "deploy" / "operations-identity-governance.template.json"
)

ROOT_KEYS = {
    "schema_version", "evidence_revision", "gap", "phase", "status",
    "data_classification", "candidate_label", "source_commit",
    "environment_inventory_reference", "database_evidence_reference",
    "submission", "governance", "duty_assignments", "mfa_enrollments",
    "control_drills", "audit_evidence", "approvals", "gap_005_accepted",
    "phase_accepted", "deployment_accepted", "limitations",
}
SUBMISSION_KEYS = {"submitted_by_account_reference", "submitted_at", "change_reference"}
GOVERNANCE_KEYS = {
    "authoritative_staff_roster_reference", "joiner_mover_leaver_policy_reference",
    "access_review_policy_reference", "recovery_policy_reference",
    "break_glass_policy_reference", "operations_origin_reference",
    "security_event_routing_reference", "access_review_interval_days",
    "leaver_revocation_sla_minutes", "minimum_active_platform_administrators",
    "shared_accounts_prohibited", "production_password_login_disabled",
    "last_access_review_at", "next_access_review_due_at",
}
ASSIGNMENT_KEYS = {
    "function", "account_reference", "role_template", "scope_reference",
    "roster_assignment_reference", "effective_from", "review_due_at",
}
MFA_KEYS = {
    "account_reference", "factor_method", "enrollment_audit_reference",
    "recovery_custody_reference", "enrolled_at", "verified_at",
    "reviewer_account_reference", "review_due_at",
}
DRILL_KEYS = {
    "drill", "status", "actor_account_reference", "reviewer_account_reference",
    "evidence_reference", "executed_at", "review_due_at",
}
AUDIT_KEYS = {
    "bootstrap_reference", "grant_request_reference", "grant_approval_reference",
    "mfa_enrollment_reference", "mfa_step_up_reference", "sensitive_action_reference",
    "access_review_reference", "leaver_revocation_reference",
}
APPROVAL_KEYS = {
    "function", "approver_role", "decision", "reviewer_account_reference",
    "evidence_reference", "decided_at", "review_due_at",
}

ASSIGNMENTS = (
    ("PLATFORM_ADMIN_MAKER", "PLATFORM_ADMIN"),
    ("PLATFORM_ADMIN_CHECKER", "PLATFORM_ADMIN"),
    ("PLATFORM_ADMIN_RECOVERY", "PLATFORM_ADMIN"),
    ("CITY_ROLLOUT_MAKER", "CITY_MANAGER"),
    ("CITY_ROLLOUT_CHECKER", "PLATFORM_ADMIN"),
    ("PRICING_POLICY_MAKER", "PRICING_MANAGER"),
    ("PRICING_POLICY_CHECKER", "PLATFORM_ADMIN"),
    ("PAYMENT_RECONCILIATION", "PAYMENT_RECONCILER"),
    ("DRIVER_DOCUMENT_REVIEW", "DRIVER_REVIEWER"),
    ("SENSITIVE_ACCESS_AUDIT", "PLATFORM_ADMIN"),
    ("SUPPORT_DUTY", "SUPPORT_AGENT"),
    ("SAFETY_DUTY", "SAFETY_RESPONDER"),
    ("ACCESS_REVIEW", "PLATFORM_ADMIN"),
    ("LEAVER_REVOCATION", "PLATFORM_ADMIN"),
    ("BREAK_GLASS_PRIMARY", "PLATFORM_ADMIN"),
    ("BREAK_GLASS_SECONDARY", "PLATFORM_ADMIN"),
)
DRILLS = (
    "MFA_ENROLLMENT", "RECOVERY_CODE_USE", "FACTOR_REPLACEMENT", "JOINER",
    "MOVER", "LEAVER_REVOCATION", "ACCESS_RECERTIFICATION", "BREAK_GLASS",
)
APPROVALS = (
    ("SECURITY", "SECURITY_OWNER"),
    ("OPERATIONS", "OPERATIONS_OWNER"),
    ("PRIVACY_LEGAL", "PRIVACY_LEGAL_OWNER"),
    ("PRODUCT_OWNER_AUTHORIZATION", "PRODUCT_OWNER"),
)
SEPARATION_GROUPS = (
    ("PLATFORM_ADMIN_MAKER", "PLATFORM_ADMIN_CHECKER", "PLATFORM_ADMIN_RECOVERY"),
    ("CITY_ROLLOUT_MAKER", "CITY_ROLLOUT_CHECKER"),
    ("PRICING_POLICY_MAKER", "PRICING_POLICY_CHECKER"),
    ("DRIVER_DOCUMENT_REVIEW", "SENSITIVE_ACCESS_AUDIT"),
    ("BREAK_GLASS_PRIMARY", "BREAK_GLASS_SECONDARY"),
)

REFERENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,399}")
LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._ -]{1,79}")
COMMIT = re.compile(r"[0-9a-f]{40}")
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
FORBIDDEN_KEY_PARTS = {
    "password", "token", "secret", "seed", "recovery_code", "private_key",
    "credential_value", "person_name", "email", "phone", "government_id",
    "document_content", "contact_detail",
}


class OperationsIdentityGovernanceError(ValueError):
    """Raised when GAP-005 evidence weakens the reviewed contract."""


def _load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise OperationsIdentityGovernanceError(f"Cannot read {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise OperationsIdentityGovernanceError(
            f"Invalid JSON in {path} at line {error.lineno}."
        ) from error


def _scan_forbidden_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized != "production_password_login_disabled" and any(
                part in normalized for part in FORBIDDEN_KEY_PARTS
            ):
                raise OperationsIdentityGovernanceError(
                    f"Operations governance evidence contains forbidden key {key!r}."
                )
            _scan_forbidden_keys(child)
    elif isinstance(value, list):
        for child in value:
            _scan_forbidden_keys(child)


def _exact_object(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise OperationsIdentityGovernanceError(f"{label} must use exact reviewed fields.")
    return value


def _reference(value: Any, label: str, *, required: bool) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or REFERENCE.fullmatch(value) is None:
        raise OperationsIdentityGovernanceError(
            f"{label} must be a bounded opaque reference without credentials or query data."
        )
    return value


def _timestamp(value: Any, label: str, *, required: bool) -> datetime | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or TIMESTAMP.fullmatch(value) is None:
        raise OperationsIdentityGovernanceError(f"{label} must be a UTC second timestamp.")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as error:
        raise OperationsIdentityGovernanceError(f"{label} is not a real UTC timestamp.") from error


def _positive_integer(value: Any, label: str, *, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise OperationsIdentityGovernanceError(
            f"{label} must be an integer between 1 and {maximum}."
        )
    return value


def _named_rows(
    value: Any,
    expected: tuple[tuple[str, str], ...],
    *,
    keys: set[str],
    name_key: str,
    role_key: str,
    label: str,
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) != len(expected):
        raise OperationsIdentityGovernanceError(f"{label} must contain every reviewed function once.")
    rows: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(value):
        row = _exact_object(raw, keys, f"{label}[{index}]")
        name = row[name_key]
        if not isinstance(name, str) or name in rows:
            raise OperationsIdentityGovernanceError(f"{label} contains a missing or duplicate function.")
        rows[name] = row
    expected_map = dict(expected)
    if set(rows) != set(expected_map):
        raise OperationsIdentityGovernanceError(f"{label} function allowlist changed.")
    for name, role in expected_map.items():
        if rows[name][role_key] != role:
            raise OperationsIdentityGovernanceError(f"{label} role for {name} changed.")
    return [rows[name] for name, _ in expected]


def _drill_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) != len(DRILLS):
        raise OperationsIdentityGovernanceError("control_drills must contain every required drill once.")
    rows: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(value):
        row = _exact_object(raw, DRILL_KEYS, f"control_drills[{index}]")
        name = row["drill"]
        if not isinstance(name, str) or name in rows:
            raise OperationsIdentityGovernanceError("control_drills contains a missing or duplicate drill.")
        rows[name] = row
    if set(rows) != set(DRILLS):
        raise OperationsIdentityGovernanceError("control_drills allowlist changed.")
    return [rows[name] for name in DRILLS]


def _validate_not_started(record: dict[str, Any]) -> None:
    for key in (
        "candidate_label", "source_commit", "environment_inventory_reference",
        "database_evidence_reference",
    ):
        if record[key] is not None:
            raise OperationsIdentityGovernanceError("NOT_STARTED evidence contains candidate claims.")
    if any(value is not None for value in record["submission"].values()):
        raise OperationsIdentityGovernanceError("NOT_STARTED evidence contains submission claims.")
    if any(value is not None for value in record["governance"].values()):
        raise OperationsIdentityGovernanceError("NOT_STARTED evidence contains governance claims.")
    if record["mfa_enrollments"]:
        raise OperationsIdentityGovernanceError("NOT_STARTED evidence contains MFA claims.")
    for row in record["duty_assignments"]:
        if any(row[key] is not None for key in ASSIGNMENT_KEYS - {"function", "role_template"}):
            raise OperationsIdentityGovernanceError("NOT_STARTED evidence contains duty claims.")
    for row in record["control_drills"]:
        if row["status"] != "PENDING" or any(
            row[key] is not None for key in DRILL_KEYS - {"drill", "status"}
        ):
            raise OperationsIdentityGovernanceError("NOT_STARTED evidence contains drill claims.")
    if any(value is not None for value in record["audit_evidence"].values()):
        raise OperationsIdentityGovernanceError("NOT_STARTED evidence contains audit claims.")
    for row in record["approvals"]:
        if row["decision"] != "PENDING" or any(
            row[key] is not None for key in APPROVAL_KEYS - {"function", "approver_role", "decision"}
        ):
            raise OperationsIdentityGovernanceError("NOT_STARTED evidence contains approval claims.")


def validate_governance(record: Any, *, require_accepted: bool = False) -> dict[str, Any]:
    record = _exact_object(record, ROOT_KEYS, "operations identity governance")
    _scan_forbidden_keys(record)
    if record["schema_version"] != 1:
        raise OperationsIdentityGovernanceError("schema_version must be 1.")
    try:
        datetime.strptime(record["evidence_revision"], "%Y-%m-%d")
    except (TypeError, ValueError) as error:
        raise OperationsIdentityGovernanceError("evidence_revision must be a real date.") from error
    if record["gap"] != "GAP-005" or record["phase"] != "T5":
        raise OperationsIdentityGovernanceError("The record must remain bound to GAP-005 and T5.")
    if record["data_classification"] != "ACCOUNT_REFERENCES_AND_CONTROL_EVIDENCE_ONLY":
        raise OperationsIdentityGovernanceError("data_classification weakened.")
    status = record["status"]
    if status not in {"NOT_STARTED", "ACCEPTED"}:
        raise OperationsIdentityGovernanceError("status must be NOT_STARTED or ACCEPTED.")
    accepted = status == "ACCEPTED"
    if record["gap_005_accepted"] is not accepted:
        raise OperationsIdentityGovernanceError("gap_005_accepted must match status.")
    if record["phase_accepted"] is not False or record["deployment_accepted"] is not False:
        raise OperationsIdentityGovernanceError("GAP-005 evidence cannot accept a phase or deployment.")
    if require_accepted and not accepted:
        raise OperationsIdentityGovernanceError("externally accepted GAP-005 evidence is required.")

    submission = _exact_object(record["submission"], SUBMISSION_KEYS, "submission")
    governance = _exact_object(record["governance"], GOVERNANCE_KEYS, "governance")
    assignments = _named_rows(
        record["duty_assignments"], ASSIGNMENTS, keys=ASSIGNMENT_KEYS,
        name_key="function", role_key="role_template", label="duty_assignments",
    )
    drills = _drill_rows(record["control_drills"])
    audit_evidence = _exact_object(record["audit_evidence"], AUDIT_KEYS, "audit_evidence")
    approvals = _named_rows(
        record["approvals"], APPROVALS, keys=APPROVAL_KEYS,
        name_key="function", role_key="approver_role", label="approvals",
    )

    if not accepted:
        _validate_not_started(record)
    else:
        if not isinstance(record["candidate_label"], str) or LABEL.fullmatch(record["candidate_label"]) is None:
            raise OperationsIdentityGovernanceError("candidate_label is invalid.")
        if not isinstance(record["source_commit"], str) or COMMIT.fullmatch(record["source_commit"]) is None:
            raise OperationsIdentityGovernanceError("source_commit must be a full lowercase Git commit.")
        for key in ("environment_inventory_reference", "database_evidence_reference"):
            _reference(record[key], key, required=True)
        submitter = _reference(
            submission["submitted_by_account_reference"],
            "submission.submitted_by_account_reference", required=True,
        )
        submitted_at = _timestamp(submission["submitted_at"], "submission.submitted_at", required=True)
        _reference(submission["change_reference"], "submission.change_reference", required=True)
        assert submitter is not None and submitted_at is not None

        for key in GOVERNANCE_KEYS - {
            "access_review_interval_days", "leaver_revocation_sla_minutes",
            "minimum_active_platform_administrators", "shared_accounts_prohibited",
            "production_password_login_disabled", "last_access_review_at",
            "next_access_review_due_at",
        }:
            _reference(governance[key], f"governance.{key}", required=True)
        interval = _positive_integer(
            governance["access_review_interval_days"],
            "governance.access_review_interval_days", maximum=90,
        )
        _positive_integer(
            governance["leaver_revocation_sla_minutes"],
            "governance.leaver_revocation_sla_minutes", maximum=1440,
        )
        if governance["minimum_active_platform_administrators"] != 3:
            raise OperationsIdentityGovernanceError(
                "governance.minimum_active_platform_administrators must be exactly 3."
            )
        if governance["shared_accounts_prohibited"] is not True:
            raise OperationsIdentityGovernanceError("Shared operations accounts must be prohibited.")
        if governance["production_password_login_disabled"] is not True:
            raise OperationsIdentityGovernanceError("Production password-only login must be disabled.")
        last_review = _timestamp(
            governance["last_access_review_at"], "governance.last_access_review_at", required=True
        )
        next_review = _timestamp(
            governance["next_access_review_due_at"],
            "governance.next_access_review_due_at", required=True,
        )
        assert last_review is not None and next_review is not None
        if last_review < submitted_at or next_review <= last_review:
            raise OperationsIdentityGovernanceError("Access review timing is stale or reversed.")
        if next_review > last_review + timedelta(days=interval):
            raise OperationsIdentityGovernanceError("Next access review exceeds the approved cadence.")

        by_function: dict[str, str] = {}
        for row in assignments:
            label = f"duty_assignments.{row['function']}"
            account = _reference(row["account_reference"], f"{label}.account_reference", required=True)
            _reference(row["scope_reference"], f"{label}.scope_reference", required=True)
            _reference(
                row["roster_assignment_reference"],
                f"{label}.roster_assignment_reference", required=True,
            )
            effective = _timestamp(row["effective_from"], f"{label}.effective_from", required=True)
            due = _timestamp(row["review_due_at"], f"{label}.review_due_at", required=True)
            assert account is not None and effective is not None and due is not None
            if effective > last_review or due < next_review:
                raise OperationsIdentityGovernanceError(
                    f"{label} must be effective at review and current through the next review."
                )
            by_function[row["function"]] = account
        for group in SEPARATION_GROUPS:
            accounts = [by_function[name] for name in group]
            if len(set(accounts)) != len(accounts):
                raise OperationsIdentityGovernanceError(
                    f"Separation of duty is violated for {', '.join(group)}."
                )

        enrollments = record["mfa_enrollments"]
        assigned_accounts = set(by_function.values())
        if not isinstance(enrollments, list) or len(enrollments) != len(assigned_accounts):
            raise OperationsIdentityGovernanceError(
                "mfa_enrollments must cover every assigned account exactly once."
            )
        enrollment_accounts: set[str] = set()
        for index, raw in enumerate(enrollments):
            row = _exact_object(raw, MFA_KEYS, f"mfa_enrollments[{index}]")
            account = _reference(row["account_reference"], f"mfa_enrollments[{index}].account_reference", required=True)
            if account not in assigned_accounts or account in enrollment_accounts:
                raise OperationsIdentityGovernanceError("MFA account coverage is missing, duplicate, or unassigned.")
            enrollment_accounts.add(account)
            if row["factor_method"] != "TOTP":
                raise OperationsIdentityGovernanceError("Every operations factor must use reviewed TOTP enrollment.")
            for key in ("enrollment_audit_reference", "recovery_custody_reference"):
                _reference(row[key], f"mfa_enrollments[{index}].{key}", required=True)
            reviewer = _reference(
                row["reviewer_account_reference"],
                f"mfa_enrollments[{index}].reviewer_account_reference", required=True,
            )
            if reviewer in {account, submitter}:
                raise OperationsIdentityGovernanceError("MFA enrollment requires an independent reviewer.")
            enrolled = _timestamp(row["enrolled_at"], f"mfa_enrollments[{index}].enrolled_at", required=True)
            verified = _timestamp(row["verified_at"], f"mfa_enrollments[{index}].verified_at", required=True)
            due = _timestamp(row["review_due_at"], f"mfa_enrollments[{index}].review_due_at", required=True)
            assert enrolled is not None and verified is not None and due is not None
            if verified < enrolled or due < next_review:
                raise OperationsIdentityGovernanceError("MFA enrollment verification is stale or reversed.")

        for row in drills:
            label = f"control_drills.{row['drill']}"
            if row["status"] != "PASSED":
                raise OperationsIdentityGovernanceError(f"{label} must be PASSED.")
            actor = _reference(row["actor_account_reference"], f"{label}.actor_account_reference", required=True)
            reviewer = _reference(row["reviewer_account_reference"], f"{label}.reviewer_account_reference", required=True)
            if actor == reviewer or reviewer == submitter:
                raise OperationsIdentityGovernanceError(f"{label} requires an independent reviewer.")
            _reference(row["evidence_reference"], f"{label}.evidence_reference", required=True)
            executed = _timestamp(row["executed_at"], f"{label}.executed_at", required=True)
            due = _timestamp(row["review_due_at"], f"{label}.review_due_at", required=True)
            assert executed is not None and due is not None
            if executed < submitted_at or due < next_review:
                raise OperationsIdentityGovernanceError(f"{label} is stale before the review horizon.")

        for key, value in audit_evidence.items():
            _reference(value, f"audit_evidence.{key}", required=True)
        for row in approvals:
            label = f"approvals.{row['function']}"
            if row["decision"] != "APPROVED":
                raise OperationsIdentityGovernanceError(f"{label} must be APPROVED.")
            reviewer = _reference(row["reviewer_account_reference"], f"{label}.reviewer_account_reference", required=True)
            if reviewer == submitter:
                raise OperationsIdentityGovernanceError(f"{label} reviewer must differ from submitter.")
            _reference(row["evidence_reference"], f"{label}.evidence_reference", required=True)
            decided = _timestamp(row["decided_at"], f"{label}.decided_at", required=True)
            due = _timestamp(row["review_due_at"], f"{label}.review_due_at", required=True)
            assert decided is not None and due is not None
            if decided < submitted_at or due < next_review:
                raise OperationsIdentityGovernanceError(f"{label} is stale before the review horizon.")

    limitations = record["limitations"]
    if (
        not isinstance(limitations, list)
        or "NO_PHASE_OR_DEPLOYMENT_ACCEPTANCE" not in limitations
        or len(limitations) != len(set(limitations))
        or any(not isinstance(item, str) or re.fullmatch(r"[A-Z][A-Z0-9_]{2,95}", item) is None for item in limitations)
    ):
        raise OperationsIdentityGovernanceError("limitations must retain the no-acceptance boundary.")
    if accepted and "NO_PRODUCTION_OPERATIONS_IDENTITY_ACCEPTED" in limitations:
        raise OperationsIdentityGovernanceError("Accepted evidence retains the unaccepted-identity limit.")
    if not accepted and limitations != [
        "NO_PRODUCTION_OPERATIONS_IDENTITY_ACCEPTED",
        "NO_PHASE_OR_DEPLOYMENT_ACCEPTANCE",
    ]:
        raise OperationsIdentityGovernanceError("NOT_STARTED limitations are invalid.")
    return {
        "status": status,
        "gap_005_accepted": accepted,
        "duty_assignments": len(assignments),
        "control_drills": len(drills),
        "approval_functions": len(approvals),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--governance", type=Path, default=DEFAULT_GOVERNANCE)
    parser.add_argument("--require-accepted", action="store_true")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    arguments = _parser().parse_args(list(argv) if argv is not None else None)
    try:
        summary = validate_governance(
            _load(arguments.governance), require_accepted=arguments.require_accepted
        )
    except (OSError, ValueError, OperationsIdentityGovernanceError) as error:
        print(f"Operations identity governance validation failed: {error}", file=sys.stderr)
        return 1
    print(
        "Operations identity governance passed: "
        f"status {summary['status']}, {summary['duty_assignments']} duties, "
        f"{summary['control_drills']} drills, {summary['approval_functions']} approvals; "
        "zero phase/deployment acceptance claims."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
