"""Validate the GAP-004 real pilot-city launch approval record.

The committed template is deliberately ``NOT_STARTED``. A protected external
copy can accept GAP-004 only after a real Moroccan city, legal operator, active
configuration, public terms, bounded cohort, accountable functions, readiness
reviews, and owner authorization have been established. The record carries
public entity facts and opaque control references only. It never accepts T6 or
deployment and is not a substitute for the backend readiness commands.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_APPROVAL = (
    WORKSPACE_ROOT / "infra" / "deploy" / "pilot-city-launch-approval.template.json"
)

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
    "database_evidence_reference",
    "submission",
    "scope",
    "public_terms",
    "accountability",
    "pilot_limits",
    "readiness_decisions",
    "approvals",
    "gap_004_accepted",
    "phase_accepted",
    "deployment_accepted",
    "limitations",
}
SUBMISSION_KEYS = {
    "submitted_by_account_reference",
    "submitted_at",
    "change_reference",
}
SCOPE_KEYS = {
    "market_code",
    "country_code",
    "city_id",
    "city_code",
    "city_display_name",
    "city_timezone",
    "city_lifecycle_status",
    "operator_id",
    "operator_legal_name",
    "operator_type",
    "operator_authority_reference",
    "operator_authority_valid_until",
    "active_configuration_id",
    "configuration_version",
    "configuration_status",
    "service_types",
    "service_area_approval_reference",
    "operating_hours_reference",
    "tariff_and_fee_reference",
    "fixed_route_scope_reference",
    "scheduling_scope_reference",
    "payment_scope_reference",
    "payment_methods",
}
PUBLIC_TERMS_KEYS = {
    "passenger_terms_reference",
    "passenger_terms_version",
    "driver_terms_reference",
    "driver_terms_version",
    "privacy_notice_reference",
    "privacy_notice_version",
    "fare_disclosure_reference",
    "complaint_and_safety_publication_reference",
    "localization_review_reference",
    "effective_at",
    "languages",
}
ACCOUNTABILITY_KEYS = {
    "function",
    "owner_role",
    "assignment_reference",
    "duty_roster_reference",
    "effective_from",
    "review_due_at",
}
PILOT_LIMIT_KEYS = {
    "cohort_plan_reference",
    "pilot_start_at",
    "pilot_end_at",
    "maximum_passengers",
    "maximum_drivers",
    "maximum_concurrent_rides",
    "maximum_completed_rides",
    "go_no_go_thresholds_reference",
    "pause_runbook_reference",
    "rollback_reference",
    "participant_communications_reference",
}
READINESS_KEYS = {
    "gate_code",
    "decision",
    "configuration_id",
    "reviewer_account_reference",
    "evidence_reference",
    "decided_at",
    "review_due_at",
}
APPROVAL_KEYS = {
    "function",
    "approver_role",
    "decision",
    "reviewer_account_reference",
    "evidence_reference",
    "decided_at",
    "review_due_at",
}

ACCOUNTABILITY_FUNCTIONS = (
    ("CITY_OPERATIONS", "CITY_OPERATIONS_OWNER"),
    ("OPERATOR_AUTHORITY", "OPERATOR_GOVERNANCE_OWNER"),
    ("PRICING", "PRICING_OWNER"),
    ("SUPPORT_COMPLAINTS", "SUPPORT_OWNER"),
    ("SAFETY", "SAFETY_OWNER"),
    ("PRIVACY", "PRIVACY_OWNER"),
    ("PAYMENT_RECONCILIATION", "PAYMENT_OPERATIONS_OWNER"),
    ("PAUSE_AUTHORITY", "EMERGENCY_PAUSE_OWNER"),
    ("RELEASE_OWNER", "CITY_RELEASE_OWNER"),
)
READINESS_GATES = (
    "LEGAL_AND_OPERATOR_OWNERSHIP",
    "SERVICE_AREA_AND_TIMEZONE",
    "DRIVER_AND_VEHICLE_REQUIREMENTS",
    "TARIFF_AND_OPERATOR_FEE",
    "MATCHING_AND_CANCELLATION",
    "PAYMENT_AND_RECONCILIATION",
    "SUPPORT_SAFETY_AND_RETENTION",
    "LOCALIZATION_AR_FR_EN",
    "MAP_ROUTING_COVERAGE",
    "SECURITY_MONITORING_AND_ROLLBACK",
)
APPROVAL_FUNCTIONS = (
    ("LOCAL_LEGAL_REGULATORY", "LEGAL_COUNSEL_OR_REGULATOR"),
    ("OPERATOR_GOVERNANCE", "AUTHORIZED_OPERATOR_SIGNATORY"),
    ("COMMERCIAL_PRICING", "FINANCE_PRICING_OWNER"),
    ("SAFETY_SUPPORT", "SAFETY_OPERATIONS_OWNER"),
    ("PRIVACY_TERMS", "PRIVACY_LEGAL_OWNER"),
    ("PRODUCT_OWNER_PILOT_AUTHORIZATION", "PRODUCT_OWNER"),
)

REFERENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,399}")
SAFE_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._ -]{1,79}")
CITY_CODE = re.compile(r"[a-z0-9][a-z0-9-]{1,63}")
VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
COMMIT = re.compile(r"[0-9a-f]{40}")
UUID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
)
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
FORBIDDEN_KEY_PARTS = {
    "password",
    "token",
    "api_key",
    "private_key",
    "connection_string",
    "credential",
    "person_name",
    "email",
    "phone",
    "government_id",
    "document_content",
    "participant_id",
}


class PilotCityLaunchApprovalError(ValueError):
    """Raised when GAP-004 evidence weakens the reviewed acceptance contract."""


def _load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise PilotCityLaunchApprovalError(f"Cannot read {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise PilotCityLaunchApprovalError(
            f"Invalid JSON in {path} at line {error.lineno}."
        ) from error


def _scan_forbidden_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if any(part in normalized for part in FORBIDDEN_KEY_PARTS):
                raise PilotCityLaunchApprovalError(
                    f"Pilot approval contains forbidden key {key!r}."
                )
            _scan_forbidden_keys(child)
    elif isinstance(value, list):
        for child in value:
            _scan_forbidden_keys(child)


def _exact_object(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise PilotCityLaunchApprovalError(f"{label} must use exact reviewed fields.")
    return value


def _reference(value: Any, label: str, *, required: bool) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or REFERENCE.fullmatch(value) is None:
        raise PilotCityLaunchApprovalError(
            f"{label} must be a bounded opaque reference without credentials or query data."
        )
    return value


def _timestamp(value: Any, label: str, *, required: bool) -> datetime | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or TIMESTAMP.fullmatch(value) is None:
        raise PilotCityLaunchApprovalError(f"{label} must be a UTC second timestamp.")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as error:
        raise PilotCityLaunchApprovalError(f"{label} is not a real UTC timestamp.") from error


def _public_label(value: Any, label: str, *, maximum: int = 160) -> str:
    if (
        not isinstance(value, str)
        or value != value.strip()
        or not 2 <= len(value) <= maximum
        or not value.isprintable()
        or any(character in value for character in "\r\n<>?&=#")
    ):
        raise PilotCityLaunchApprovalError(f"{label} must be a bounded public label.")
    return value


def _positive_integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise PilotCityLaunchApprovalError(f"{label} must be a positive integer.")
    return value


def _exact_named_rows(
    value: Any,
    expected: tuple[tuple[str, str], ...],
    *,
    keys: set[str],
    name_key: str,
    role_key: str,
    label: str,
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) != len(expected):
        raise PilotCityLaunchApprovalError(f"{label} must contain every reviewed function once.")
    rows: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(value):
        row = _exact_object(raw, keys, f"{label}[{index}]")
        name = row[name_key]
        if not isinstance(name, str) or name in rows:
            raise PilotCityLaunchApprovalError(f"{label} contains a missing or duplicate function.")
        rows[name] = row
    expected_map = dict(expected)
    if set(rows) != set(expected_map):
        raise PilotCityLaunchApprovalError(f"{label} function allowlist changed.")
    for name, role in expected_map.items():
        if rows[name][role_key] != role:
            raise PilotCityLaunchApprovalError(f"{label} role for {name} changed.")
    return [rows[name] for name, _ in expected]


def _readiness_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) != len(READINESS_GATES):
        raise PilotCityLaunchApprovalError(
            "readiness_decisions must contain every pilot-entry gate once."
        )
    rows: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(value):
        row = _exact_object(raw, READINESS_KEYS, f"readiness_decisions[{index}]")
        gate = row["gate_code"]
        if not isinstance(gate, str) or gate in rows:
            raise PilotCityLaunchApprovalError(
                "readiness_decisions contains a missing or duplicate gate."
            )
        rows[gate] = row
    if set(rows) != set(READINESS_GATES):
        raise PilotCityLaunchApprovalError("readiness_decisions gate allowlist changed.")
    return [rows[gate] for gate in READINESS_GATES]


def _validate_not_started(record: dict[str, Any]) -> None:
    if any(
        record[key] is not None
        for key in (
            "candidate_label",
            "source_commit",
            "environment_inventory_reference",
            "database_evidence_reference",
        )
    ):
        raise PilotCityLaunchApprovalError("NOT_STARTED approval contains pilot claims.")
    if any(value is not None for value in record["submission"].values()):
        raise PilotCityLaunchApprovalError("NOT_STARTED approval contains submission claims.")
    for key, value in record["scope"].items():
        expected = [] if key in {"service_types", "payment_methods"} else None
        if value != expected:
            raise PilotCityLaunchApprovalError("NOT_STARTED approval contains scope claims.")
    for key, value in record["public_terms"].items():
        expected = [] if key == "languages" else None
        if value != expected:
            raise PilotCityLaunchApprovalError("NOT_STARTED approval contains terms claims.")
    for row in record["accountability"]:
        if any(
            row[key] is not None
            for key in (
                "assignment_reference",
                "duty_roster_reference",
                "effective_from",
                "review_due_at",
            )
        ):
            raise PilotCityLaunchApprovalError(
                "NOT_STARTED approval contains accountability claims."
            )
    if any(value is not None for value in record["pilot_limits"].values()):
        raise PilotCityLaunchApprovalError("NOT_STARTED approval contains pilot-limit claims.")
    for row in record["readiness_decisions"]:
        if row["decision"] != "PENDING" or any(
            row[key] is not None
            for key in (
                "configuration_id",
                "reviewer_account_reference",
                "evidence_reference",
                "decided_at",
                "review_due_at",
            )
        ):
            raise PilotCityLaunchApprovalError("NOT_STARTED approval contains readiness claims.")
    for row in record["approvals"]:
        if row["decision"] != "PENDING" or any(
            row[key] is not None
            for key in (
                "reviewer_account_reference",
                "evidence_reference",
                "decided_at",
                "review_due_at",
            )
        ):
            raise PilotCityLaunchApprovalError("NOT_STARTED approval contains approval claims.")


def _validate_pilot_limits(value: Any, *, accepted: bool) -> tuple[datetime | None, datetime | None]:
    limits = _exact_object(value, PILOT_LIMIT_KEYS, "pilot_limits")
    for key in (
        "cohort_plan_reference",
        "go_no_go_thresholds_reference",
        "pause_runbook_reference",
        "rollback_reference",
        "participant_communications_reference",
    ):
        _reference(limits[key], f"pilot_limits.{key}", required=accepted)
    start = _timestamp(limits["pilot_start_at"], "pilot_limits.pilot_start_at", required=accepted)
    end = _timestamp(limits["pilot_end_at"], "pilot_limits.pilot_end_at", required=accepted)
    if accepted:
        assert start is not None and end is not None
        if end <= start:
            raise PilotCityLaunchApprovalError("pilot_end_at must be after pilot_start_at.")
        passengers = _positive_integer(limits["maximum_passengers"], "maximum_passengers")
        drivers = _positive_integer(limits["maximum_drivers"], "maximum_drivers")
        concurrent = _positive_integer(
            limits["maximum_concurrent_rides"], "maximum_concurrent_rides"
        )
        completed = _positive_integer(
            limits["maximum_completed_rides"], "maximum_completed_rides"
        )
        if concurrent > min(passengers, drivers):
            raise PilotCityLaunchApprovalError(
                "maximum_concurrent_rides exceeds the bounded passenger or driver cohort."
            )
        if completed < concurrent:
            raise PilotCityLaunchApprovalError(
                "maximum_completed_rides cannot be below maximum_concurrent_rides."
            )
    else:
        for key in (
            "maximum_passengers",
            "maximum_drivers",
            "maximum_concurrent_rides",
            "maximum_completed_rides",
        ):
            if limits[key] is not None:
                raise PilotCityLaunchApprovalError(
                    "NOT_STARTED approval contains pilot-limit claims."
                )
    return start, end


def _validate_submission(value: Any, *, accepted: bool) -> tuple[str | None, datetime | None]:
    submission = _exact_object(value, SUBMISSION_KEYS, "submission")
    submitter = _reference(
        submission["submitted_by_account_reference"],
        "submission.submitted_by_account_reference",
        required=accepted,
    )
    submitted_at = _timestamp(
        submission["submitted_at"], "submission.submitted_at", required=accepted
    )
    _reference(submission["change_reference"], "submission.change_reference", required=accepted)
    return submitter, submitted_at


def _validate_scope(
    value: Any,
    *,
    accepted: bool,
    pilot_end: datetime | None,
) -> str | None:
    scope = _exact_object(value, SCOPE_KEYS, "scope")
    if not accepted:
        return None
    if scope["market_code"] != "MA" or scope["country_code"] != "MA":
        raise PilotCityLaunchApprovalError("The first national release must use market/country MA.")
    for key in ("city_id", "operator_id", "active_configuration_id"):
        if not isinstance(scope[key], str) or UUID.fullmatch(scope[key]) is None:
            raise PilotCityLaunchApprovalError(f"scope.{key} must be a canonical UUID.")
    if not isinstance(scope["city_code"], str) or CITY_CODE.fullmatch(scope["city_code"]) is None:
        raise PilotCityLaunchApprovalError("scope.city_code must be a bounded lowercase code.")
    _public_label(scope["city_display_name"], "scope.city_display_name")
    _public_label(scope["operator_legal_name"], "scope.operator_legal_name", maximum=200)
    if scope["city_timezone"] != "Africa/Casablanca":
        raise PilotCityLaunchApprovalError("scope.city_timezone must be Africa/Casablanca.")
    if scope["city_lifecycle_status"] != "CONFIGURING":
        raise PilotCityLaunchApprovalError(
            "scope.city_lifecycle_status must be CONFIGURING before PILOT authorization."
        )
    if scope["operator_type"] not in {"PLATFORM", "COOPERATIVE", "LOCAL_ENTITY"}:
        raise PilotCityLaunchApprovalError("scope.operator_type is invalid.")
    _reference(
        scope["operator_authority_reference"],
        "scope.operator_authority_reference",
        required=True,
    )
    authority_until = _timestamp(
        scope["operator_authority_valid_until"],
        "scope.operator_authority_valid_until",
        required=True,
    )
    assert authority_until is not None and pilot_end is not None
    if authority_until < pilot_end:
        raise PilotCityLaunchApprovalError("Operator authority expires before the pilot ends.")
    if not isinstance(scope["configuration_version"], str) or VERSION.fullmatch(
        scope["configuration_version"]
    ) is None:
        raise PilotCityLaunchApprovalError("scope.configuration_version is invalid.")
    if scope["configuration_status"] != "ACTIVE":
        raise PilotCityLaunchApprovalError("scope.configuration_status must be ACTIVE.")
    service_types = scope["service_types"]
    allowed_services = {"ON_DEMAND", "FIXED_ROUTE", "SCHEDULED"}
    if (
        not isinstance(service_types, list)
        or not service_types
        or len(service_types) != len(set(service_types))
        or any(item not in allowed_services for item in service_types)
    ):
        raise PilotCityLaunchApprovalError("scope.service_types must be a non-empty unique allowlist.")
    for key in (
        "service_area_approval_reference",
        "operating_hours_reference",
        "tariff_and_fee_reference",
        "payment_scope_reference",
    ):
        _reference(scope[key], f"scope.{key}", required=True)
    fixed_route_enabled = "FIXED_ROUTE" in service_types
    scheduled_enabled = "SCHEDULED" in service_types
    _reference(
        scope["fixed_route_scope_reference"],
        "scope.fixed_route_scope_reference",
        required=fixed_route_enabled,
    )
    _reference(
        scope["scheduling_scope_reference"],
        "scope.scheduling_scope_reference",
        required=scheduled_enabled,
    )
    if not fixed_route_enabled and scope["fixed_route_scope_reference"] is not None:
        raise PilotCityLaunchApprovalError("Fixed-route scope is present while FIXED_ROUTE is disabled.")
    if not scheduled_enabled and scope["scheduling_scope_reference"] is not None:
        raise PilotCityLaunchApprovalError("Scheduling scope is present while SCHEDULED is disabled.")
    payment_methods = scope["payment_methods"]
    if (
        not isinstance(payment_methods, list)
        or "CASH" not in payment_methods
        or len(payment_methods) != len(set(payment_methods))
        or any(item not in {"CASH", "MANUAL_TRANSFER"} for item in payment_methods)
    ):
        raise PilotCityLaunchApprovalError(
            "scope.payment_methods must be unique, allowlisted, and retain CASH."
        )
    return scope["active_configuration_id"]


def _validate_public_terms(
    value: Any,
    *,
    accepted: bool,
    pilot_start: datetime | None,
) -> None:
    terms = _exact_object(value, PUBLIC_TERMS_KEYS, "public_terms")
    if not accepted:
        return
    for key in (
        "passenger_terms_reference",
        "driver_terms_reference",
        "privacy_notice_reference",
        "fare_disclosure_reference",
        "complaint_and_safety_publication_reference",
        "localization_review_reference",
    ):
        _reference(terms[key], f"public_terms.{key}", required=True)
    for key in ("passenger_terms_version", "driver_terms_version", "privacy_notice_version"):
        if not isinstance(terms[key], str) or VERSION.fullmatch(terms[key]) is None:
            raise PilotCityLaunchApprovalError(f"public_terms.{key} is invalid.")
    effective = _timestamp(terms["effective_at"], "public_terms.effective_at", required=True)
    assert effective is not None and pilot_start is not None
    if effective > pilot_start:
        raise PilotCityLaunchApprovalError("Public terms become effective after the pilot starts.")
    languages = terms["languages"]
    if not isinstance(languages, list) or set(languages) != {"ar", "fr", "en"} or len(languages) != 3:
        raise PilotCityLaunchApprovalError("public_terms.languages must contain ar, fr and en once.")


def _validate_accountability(
    value: Any,
    *,
    accepted: bool,
    pilot_start: datetime | None,
    pilot_end: datetime | None,
) -> None:
    rows = _exact_named_rows(
        value,
        ACCOUNTABILITY_FUNCTIONS,
        keys=ACCOUNTABILITY_KEYS,
        name_key="function",
        role_key="owner_role",
        label="accountability",
    )
    if not accepted:
        return
    assert pilot_start is not None and pilot_end is not None
    for row in rows:
        label = f"accountability.{row['function']}"
        _reference(row["assignment_reference"], f"{label}.assignment_reference", required=True)
        _reference(row["duty_roster_reference"], f"{label}.duty_roster_reference", required=True)
        effective = _timestamp(row["effective_from"], f"{label}.effective_from", required=True)
        due = _timestamp(row["review_due_at"], f"{label}.review_due_at", required=True)
        assert effective is not None and due is not None
        if effective > pilot_start or due < pilot_end:
            raise PilotCityLaunchApprovalError(
                f"{label} must be effective before start and reviewed through pilot end."
            )


def _validate_readiness(
    value: Any,
    *,
    accepted: bool,
    configuration_id: str | None,
    submitter: str | None,
    submitted_at: datetime | None,
    pilot_start: datetime | None,
    pilot_end: datetime | None,
) -> None:
    rows = _readiness_rows(value)
    if not accepted:
        return
    assert configuration_id and submitter and submitted_at and pilot_start and pilot_end
    for row in rows:
        label = f"readiness_decisions.{row['gate_code']}"
        if row["decision"] != "PASSED":
            raise PilotCityLaunchApprovalError(f"{label} must be PASSED.")
        if row["configuration_id"] != configuration_id:
            raise PilotCityLaunchApprovalError(f"{label} is not bound to the active configuration.")
        reviewer = _reference(
            row["reviewer_account_reference"],
            f"{label}.reviewer_account_reference",
            required=True,
        )
        if reviewer == submitter:
            raise PilotCityLaunchApprovalError(
                f"{label} reviewer must differ from the configuration submitter."
            )
        _reference(row["evidence_reference"], f"{label}.evidence_reference", required=True)
        decided = _timestamp(row["decided_at"], f"{label}.decided_at", required=True)
        due = _timestamp(row["review_due_at"], f"{label}.review_due_at", required=True)
        assert decided is not None and due is not None
        if decided < submitted_at or decided > pilot_start:
            raise PilotCityLaunchApprovalError(
                f"{label} decision must follow submission and precede pilot start."
            )
        if due < pilot_end:
            raise PilotCityLaunchApprovalError(f"{label} review expires before pilot end.")


def _validate_approvals(
    value: Any,
    *,
    accepted: bool,
    submitter: str | None,
    submitted_at: datetime | None,
    pilot_start: datetime | None,
    pilot_end: datetime | None,
) -> None:
    rows = _exact_named_rows(
        value,
        APPROVAL_FUNCTIONS,
        keys=APPROVAL_KEYS,
        name_key="function",
        role_key="approver_role",
        label="approvals",
    )
    if not accepted:
        return
    assert submitter and submitted_at and pilot_start and pilot_end
    for row in rows:
        label = f"approvals.{row['function']}"
        if row["decision"] != "APPROVED":
            raise PilotCityLaunchApprovalError(f"{label} must be APPROVED.")
        reviewer = _reference(
            row["reviewer_account_reference"],
            f"{label}.reviewer_account_reference",
            required=True,
        )
        if reviewer == submitter:
            raise PilotCityLaunchApprovalError(f"{label} reviewer must differ from the submitter.")
        _reference(row["evidence_reference"], f"{label}.evidence_reference", required=True)
        decided = _timestamp(row["decided_at"], f"{label}.decided_at", required=True)
        due = _timestamp(row["review_due_at"], f"{label}.review_due_at", required=True)
        assert decided is not None and due is not None
        if decided < submitted_at or decided > pilot_start:
            raise PilotCityLaunchApprovalError(
                f"{label} decision must follow submission and precede pilot start."
            )
        if due < pilot_end:
            raise PilotCityLaunchApprovalError(f"{label} approval expires before pilot end.")


def validate_approval(record: Any, *, require_accepted: bool = False) -> dict[str, Any]:
    record = _exact_object(record, ROOT_KEYS, "pilot approval")
    _scan_forbidden_keys(record)
    if record["schema_version"] != 1:
        raise PilotCityLaunchApprovalError("schema_version must be 1.")
    try:
        datetime.strptime(record["evidence_revision"], "%Y-%m-%d")
    except (TypeError, ValueError) as error:
        raise PilotCityLaunchApprovalError("evidence_revision must be a real date.") from error
    if record["gap"] != "GAP-004" or record["phase"] != "T6":
        raise PilotCityLaunchApprovalError("The record must remain bound to GAP-004 and T6.")
    if record["data_classification"] != "PUBLIC_ENTITY_AND_CONTROL_REFERENCES_ONLY":
        raise PilotCityLaunchApprovalError("data_classification weakened.")
    status = record["status"]
    if status not in {"NOT_STARTED", "ACCEPTED"}:
        raise PilotCityLaunchApprovalError("status must be NOT_STARTED or ACCEPTED.")
    accepted = status == "ACCEPTED"
    if record["gap_004_accepted"] is not accepted:
        raise PilotCityLaunchApprovalError("gap_004_accepted must match status.")
    if record["phase_accepted"] is not False or record["deployment_accepted"] is not False:
        raise PilotCityLaunchApprovalError("GAP-004 evidence cannot accept a phase or deployment.")
    if require_accepted and not accepted:
        raise PilotCityLaunchApprovalError("externally accepted GAP-004 evidence is required.")
    if accepted:
        if not isinstance(record["candidate_label"], str) or SAFE_LABEL.fullmatch(
            record["candidate_label"]
        ) is None:
            raise PilotCityLaunchApprovalError("candidate_label is invalid.")
        if not isinstance(record["source_commit"], str) or COMMIT.fullmatch(
            record["source_commit"]
        ) is None:
            raise PilotCityLaunchApprovalError("source_commit must be a full lowercase Git commit.")
    _reference(
        record["environment_inventory_reference"],
        "environment_inventory_reference",
        required=accepted,
    )
    _reference(
        record["database_evidence_reference"],
        "database_evidence_reference",
        required=accepted,
    )

    submitter, submitted_at = _validate_submission(record["submission"], accepted=accepted)
    pilot_start, pilot_end = _validate_pilot_limits(record["pilot_limits"], accepted=accepted)
    configuration_id = _validate_scope(record["scope"], accepted=accepted, pilot_end=pilot_end)
    _validate_public_terms(record["public_terms"], accepted=accepted, pilot_start=pilot_start)
    _validate_accountability(
        record["accountability"],
        accepted=accepted,
        pilot_start=pilot_start,
        pilot_end=pilot_end,
    )
    _validate_readiness(
        record["readiness_decisions"],
        accepted=accepted,
        configuration_id=configuration_id,
        submitter=submitter,
        submitted_at=submitted_at,
        pilot_start=pilot_start,
        pilot_end=pilot_end,
    )
    _validate_approvals(
        record["approvals"],
        accepted=accepted,
        submitter=submitter,
        submitted_at=submitted_at,
        pilot_start=pilot_start,
        pilot_end=pilot_end,
    )

    limitations = record["limitations"]
    if (
        not isinstance(limitations, list)
        or "NO_PHASE_OR_DEPLOYMENT_ACCEPTANCE" not in limitations
        or len(limitations) != len(set(limitations))
        or any(not isinstance(item, str) or re.fullmatch(r"[A-Z][A-Z0-9_]{2,95}", item) is None for item in limitations)
    ):
        raise PilotCityLaunchApprovalError("limitations must retain the no-acceptance boundary.")
    if accepted and "NO_REAL_PILOT_SCOPE_ACCEPTED" in limitations:
        raise PilotCityLaunchApprovalError("Accepted evidence retains the unaccepted-pilot limit.")
    if status == "NOT_STARTED":
        if limitations != [
            "NO_REAL_PILOT_SCOPE_ACCEPTED",
            "NO_PHASE_OR_DEPLOYMENT_ACCEPTANCE",
        ]:
            raise PilotCityLaunchApprovalError("NOT_STARTED limitations are invalid.")
        _validate_not_started(record)
    return {
        "status": status,
        "gap_004_accepted": accepted,
        "readiness_gates": len(record["readiness_decisions"]),
        "approval_functions": len(record["approvals"]),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approval", type=Path, default=DEFAULT_APPROVAL)
    parser.add_argument("--require-accepted", action="store_true")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    arguments = _parser().parse_args(list(argv) if argv is not None else None)
    try:
        summary = validate_approval(
            _load(arguments.approval), require_accepted=arguments.require_accepted
        )
    except (OSError, ValueError, PilotCityLaunchApprovalError) as error:
        print(f"Pilot city launch approval validation failed: {error}", file=sys.stderr)
        return 1
    print(
        "Pilot city launch approval passed: "
        f"status {summary['status']}, {summary['readiness_gates']} readiness gates, "
        f"{summary['approval_functions']} approval functions; zero phase/deployment acceptance claims."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
