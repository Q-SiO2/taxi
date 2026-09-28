"""Validate the provider-neutral GAP-002 production environment inventory.

The committed template is intentionally ``NOT_STARTED``. A deployment owner can
copy it into an access-controlled evidence store and fill it with bounded
references, never secret values or personal data. ``--require-accepted`` checks
that every GAP-002 control has external evidence and the required approval
functions, but it never grants T5 or deployment acceptance.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime
import ipaddress
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Iterable
from urllib.parse import urlsplit


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INVENTORY = (
    WORKSPACE_ROOT / "infra" / "deploy" / "production-environment-inventory.template.json"
)

ROOT_KEYS = {
    "schema_version",
    "inventory_revision",
    "gap",
    "phase",
    "status",
    "data_classification",
    "candidate_label",
    "source_commit",
    "target",
    "environments",
    "public_endpoints",
    "application_policy",
    "services",
    "network",
    "secrets",
    "recovery",
    "approvals",
    "gap_002_accepted",
    "phase_accepted",
    "deployment_accepted",
    "limitations",
}
TARGET_KEYS = {
    "provider_name",
    "region_code",
    "jurisdiction_code",
    "architecture_approval_reference",
    "data_region_approval_reference",
    "service_owner_role",
    "cost_owner_reference",
    "monthly_cost_limit",
    "currency",
}
ENVIRONMENT_KEYS = {
    "name",
    "account_reference",
    "network_reference",
    "secret_scope_reference",
    "database_reference",
    "isolated",
}
ENDPOINT_KEYS = {
    "name",
    "origin",
    "dns_evidence_reference",
    "tls_scan_evidence_reference",
}
APPLICATION_POLICY_KEYS = {
    "allowed_hosts",
    "cors_origins",
    "trusted_proxy_review_reference",
}
SERVICE_KEYS = {
    "name",
    "exposure",
    "delivery_model",
    "artifact_reference",
    "service_reference",
    "owner_role",
    "network_policy_reference",
}
NETWORK_KEYS = {
    "ingress_policy_reference",
    "egress_policy_reference",
    "iam_review_reference",
    "database_publicly_reachable",
    "worker_publicly_reachable",
    "monitoring_publicly_reachable",
    "scanner_publicly_reachable",
    "routing_publicly_reachable",
    "api_bypasses_tls_ingress",
}
SECRET_KEYS = {
    "manager_reference",
    "secret_inventory_reference",
    "rotation_evidence_reference",
    "rotation_completed_at",
    "production_secrets_in_repository",
    "application_credentials_embedded",
}
RECOVERY_KEYS = {
    "staging_deployment_reference",
    "production_change_reference",
    "migration_record_reference",
    "rollback_rehearsal_reference",
    "forward_fix_reference",
    "measured_rollback_seconds",
    "approved_rto_seconds",
}
APPROVAL_KEYS = {
    "function",
    "approver_role",
    "decision",
    "evidence_reference",
    "decided_at",
}

ENVIRONMENT_NAMES = ("development", "staging", "production")
ENDPOINTS = (
    ("API_ORIGIN", "https"),
    ("APPLICANT_WEB_ORIGIN", "https"),
    ("OPERATIONS_WEB_ORIGIN", "https"),
    ("LIVE_EVENTS_ORIGIN", "wss"),
)
SERVICE_EXPOSURES = (
    ("PUBLIC_TLS_INGRESS", "PUBLIC_HTTPS"),
    ("API", "PRIVATE"),
    ("WORKER", "PRIVATE"),
    ("MIGRATOR", "PRIVATE"),
    ("APPLICANT_WEB", "PUBLIC_HTTPS"),
    ("OPERATIONS_WEB", "PUBLIC_HTTPS"),
    ("DATABASE", "PRIVATE"),
    ("ARTIFACT_REGISTRY", "PRIVATE"),
    ("SECRET_MANAGER", "PRIVATE"),
    ("MONITORING", "PRIVATE"),
    ("SCANNER", "PRIVATE"),
    ("ROUTING", "PRIVATE"),
)
APPROVAL_FUNCTIONS = (
    ("ARCHITECTURE", "PLATFORM_ENGINEERING"),
    ("DATA_REGION", "PRIVACY_LEGAL"),
    ("SECURITY", "PLATFORM_SECURITY"),
    ("OPERATIONS", "PLATFORM_OPERATIONS"),
    ("COST", "FINANCE_OWNER"),
)
OWNER_ROLES = {role for _, role in APPROVAL_FUNCTIONS}
DELIVERY_MODELS = {"CONTAINER_IMAGE", "MANAGED_SERVICE", "STATIC_ARTIFACT"}
CONTAINER_SERVICES = {"API", "WORKER", "MIGRATOR", "SCANNER"}

REFERENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,399}")
SAFE_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._ -]{1,79}")
CLOSED_ID = re.compile(r"[A-Z][A-Z0-9_]{2,95}")
HOSTNAME = re.compile(
    r"(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?"
)
IMAGE_DIGEST = re.compile(
    r"[a-z0-9.-]+(?::[0-9]+)?/[a-z0-9._/-]+@sha256:[0-9a-f]{64}"
)
SHA1 = re.compile(r"[0-9a-f]{40}")
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
FORBIDDEN_KEY_PARTS = {
    "password",
    "token_value",
    "api_key",
    "private_key",
    "signing_key",
    "connection_string",
    "credential_value",
    "person_name",
    "email",
    "document_content",
}


class ProductionEnvironmentInventoryError(ValueError):
    """Raised when a GAP-002 inventory weakens the reviewed control schema."""


def _load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ProductionEnvironmentInventoryError(f"Cannot read {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise ProductionEnvironmentInventoryError(
            f"Invalid JSON in {path} at line {error.lineno}."
        ) from error


def _scan_forbidden_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if any(part in normalized for part in FORBIDDEN_KEY_PARTS):
                raise ProductionEnvironmentInventoryError(
                    f"Environment inventory contains forbidden key {key!r}."
                )
            _scan_forbidden_keys(child)
    elif isinstance(value, list):
        for child in value:
            _scan_forbidden_keys(child)


def _exact_object(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ProductionEnvironmentInventoryError(f"{label} must use exact reviewed fields.")
    return value


def _reference(value: Any, label: str, *, required: bool) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or REFERENCE.fullmatch(value) is None:
        raise ProductionEnvironmentInventoryError(
            f"{label} must be a bounded opaque reference without credentials or query data."
        )
    return value


def _timestamp(value: Any, label: str, *, required: bool) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or TIMESTAMP.fullmatch(value) is None:
        raise ProductionEnvironmentInventoryError(f"{label} must be a UTC second timestamp.")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as error:
        raise ProductionEnvironmentInventoryError(
            f"{label} must be a real UTC calendar timestamp."
        ) from error
    return value


def _positive_number(value: Any, label: str, *, required: bool) -> float | None:
    if value is None and not required:
        return None
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise ProductionEnvironmentInventoryError(f"{label} must be a positive number.")
    return float(value)


def _origin(value: Any, name: str, scheme: str, *, required: bool) -> tuple[str | None, str | None]:
    if value is None and not required:
        return None, None
    if not isinstance(value, str):
        raise ProductionEnvironmentInventoryError(f"{name} must be an exact {scheme} origin.")
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        port = parsed.port
    except ValueError as error:
        raise ProductionEnvironmentInventoryError(
            f"{name} must be a well-formed exact {scheme} origin."
        ) from error
    if (
        parsed.scheme != scheme
        or host is None
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or HOSTNAME.fullmatch(host) is None
        or value != f"{scheme}://{host}"
    ):
        raise ProductionEnvironmentInventoryError(
            f"{name} must be a lowercase domain-only {scheme} origin with no port or path."
        )
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ProductionEnvironmentInventoryError(f"{name} must use reviewed DNS, not an IP literal.")
    return value, host


def _validate_target(value: Any, *, accepted: bool) -> None:
    target = _exact_object(value, TARGET_KEYS, "target")
    for field in (
        "architecture_approval_reference",
        "data_region_approval_reference",
        "cost_owner_reference",
    ):
        _reference(target[field], f"target.{field}", required=accepted)
    if target["provider_name"] is not None or accepted:
        if (
            not isinstance(target["provider_name"], str)
            or SAFE_LABEL.fullmatch(target["provider_name"]) is None
        ):
            raise ProductionEnvironmentInventoryError("target.provider_name is invalid.")
    if target["region_code"] is not None or accepted:
        if (
            not isinstance(target["region_code"], str)
            or REFERENCE.fullmatch(target["region_code"]) is None
        ):
            raise ProductionEnvironmentInventoryError("target.region_code is invalid.")
    if target["jurisdiction_code"] is not None or accepted:
        if (
            not isinstance(target["jurisdiction_code"], str)
            or re.fullmatch(r"[A-Z]{2}", target["jurisdiction_code"]) is None
        ):
            raise ProductionEnvironmentInventoryError("target.jurisdiction_code must be an ISO alpha-2 code.")
    if target["service_owner_role"] is not None or accepted:
        if target["service_owner_role"] not in OWNER_ROLES:
            raise ProductionEnvironmentInventoryError("target.service_owner_role is not reviewed.")
    _positive_number(
        target["monthly_cost_limit"], "target.monthly_cost_limit", required=accepted
    )
    if target["currency"] is not None or accepted:
        if (
            not isinstance(target["currency"], str)
            or re.fullmatch(r"[A-Z]{3}", target["currency"]) is None
        ):
            raise ProductionEnvironmentInventoryError("target.currency must be an ISO-style currency code.")


def _validate_environments(value: Any, *, accepted: bool) -> None:
    if not isinstance(value, list) or len(value) != len(ENVIRONMENT_NAMES):
        raise ProductionEnvironmentInventoryError("environments must list development, staging and production.")
    collected = {field: [] for field in ENVIRONMENT_KEYS if field.endswith("_reference")}
    for expected_name, raw in zip(ENVIRONMENT_NAMES, value):
        environment = _exact_object(raw, ENVIRONMENT_KEYS, f"environment {expected_name}")
        if environment["name"] != expected_name or not isinstance(environment["isolated"], bool):
            raise ProductionEnvironmentInventoryError("environment order/name or isolation flag is invalid.")
        if accepted and environment["isolated"] is not True:
            raise ProductionEnvironmentInventoryError(f"{expected_name} must be explicitly isolated.")
        for field in collected:
            reference = _reference(
                environment[field], f"{expected_name}.{field}", required=accepted
            )
            if reference is not None:
                collected[field].append(reference)
    if accepted:
        for field, references in collected.items():
            if len(references) != len(set(references)):
                raise ProductionEnvironmentInventoryError(
                    f"environment {field} values must be distinct across development, staging and production."
                )


def _validate_endpoints(value: Any, *, accepted: bool) -> dict[str, tuple[str | None, str | None]]:
    if not isinstance(value, list) or len(value) != len(ENDPOINTS):
        raise ProductionEnvironmentInventoryError("public_endpoints must contain the four reviewed origins.")
    result: dict[str, tuple[str | None, str | None]] = {}
    for (expected_name, scheme), raw in zip(ENDPOINTS, value):
        endpoint = _exact_object(raw, ENDPOINT_KEYS, f"endpoint {expected_name}")
        if endpoint["name"] != expected_name:
            raise ProductionEnvironmentInventoryError("public endpoint order or name is invalid.")
        result[expected_name] = _origin(endpoint["origin"], expected_name, scheme, required=accepted)
        _reference(
            endpoint["dns_evidence_reference"],
            f"{expected_name}.dns_evidence_reference",
            required=accepted,
        )
        _reference(
            endpoint["tls_scan_evidence_reference"],
            f"{expected_name}.tls_scan_evidence_reference",
            required=accepted,
        )
    return result


def _validate_application_policy(
    value: Any,
    endpoints: dict[str, tuple[str | None, str | None]],
    *,
    accepted: bool,
) -> None:
    policy = _exact_object(value, APPLICATION_POLICY_KEYS, "application_policy")
    allowed_hosts = policy["allowed_hosts"]
    cors_origins = policy["cors_origins"]
    if (
        not isinstance(allowed_hosts, list)
        or any(
            not isinstance(item, str) or HOSTNAME.fullmatch(item) is None
            for item in allowed_hosts
        )
        or len(allowed_hosts) != len(set(allowed_hosts))
        or not isinstance(cors_origins, list)
        or len(cors_origins) != len(set(cors_origins))
    ):
        raise ProductionEnvironmentInventoryError(
            "application host/CORS policy must use unique exact values."
        )
    for origin in cors_origins:
        _origin(origin, "application_policy.cors_origins", "https", required=True)
    _reference(
        policy["trusted_proxy_review_reference"],
        "application_policy.trusted_proxy_review_reference",
        required=accepted,
    )
    if accepted:
        api_host = endpoints["API_ORIGIN"][1]
        expected_cors = {
            endpoints["APPLICANT_WEB_ORIGIN"][0],
            endpoints["OPERATIONS_WEB_ORIGIN"][0],
        }
        if api_host not in allowed_hosts or set(cors_origins) != expected_cors:
            raise ProductionEnvironmentInventoryError(
                "accepted allowed hosts/CORS must cover the exact API and both browser origins."
            )


def _validate_services(value: Any, *, accepted: bool) -> None:
    if not isinstance(value, list) or len(value) != len(SERVICE_EXPOSURES):
        raise ProductionEnvironmentInventoryError("services must contain the reviewed topology.")
    backend_artifacts: list[str] = []
    for (expected_name, expected_exposure), raw in zip(SERVICE_EXPOSURES, value):
        service = _exact_object(raw, SERVICE_KEYS, f"service {expected_name}")
        if service["name"] != expected_name or service["exposure"] != expected_exposure:
            raise ProductionEnvironmentInventoryError(
                f"service {expected_name} exposure must remain {expected_exposure}."
            )
        delivery_model = service["delivery_model"]
        if delivery_model is not None and delivery_model not in DELIVERY_MODELS:
            raise ProductionEnvironmentInventoryError(f"service {expected_name} delivery model is invalid.")
        artifact_value = service["artifact_reference"]
        if delivery_model == "CONTAINER_IMAGE":
            if (
                not isinstance(artifact_value, str)
                or IMAGE_DIGEST.fullmatch(artifact_value) is None
            ):
                raise ProductionEnvironmentInventoryError(
                    f"service {expected_name} container image must use an immutable sha256 digest."
                )
            artifact = artifact_value
        else:
            artifact = _reference(
                artifact_value, f"service {expected_name} artifact", required=accepted
            )
        _reference(
            service["service_reference"],
            f"service {expected_name} record",
            required=accepted,
        )
        _reference(
            service["network_policy_reference"],
            f"service {expected_name} network policy",
            required=accepted,
        )
        if service["owner_role"] is not None or accepted:
            if service["owner_role"] not in OWNER_ROLES:
                raise ProductionEnvironmentInventoryError(
                    f"service {expected_name} owner is invalid."
                )
        if accepted and delivery_model is None:
            raise ProductionEnvironmentInventoryError(f"service {expected_name} needs a delivery model.")
        if (
            accepted
            and expected_name in CONTAINER_SERVICES
            and delivery_model != "CONTAINER_IMAGE"
        ):
            raise ProductionEnvironmentInventoryError(
                f"service {expected_name} must identify its digest-pinned container image."
            )
        if expected_name in {"API", "WORKER", "MIGRATOR"} and artifact is not None:
            backend_artifacts.append(artifact)
    if accepted and len(set(backend_artifacts)) != 1:
        raise ProductionEnvironmentInventoryError(
            "API, worker and migrator must reference the same reviewed backend image digest."
        )


def _validate_network(value: Any, *, accepted: bool) -> None:
    network = _exact_object(value, NETWORK_KEYS, "network")
    for field in (
        "ingress_policy_reference",
        "egress_policy_reference",
        "iam_review_reference",
    ):
        _reference(network[field], f"network.{field}", required=accepted)
    for field in NETWORK_KEYS - {
        "ingress_policy_reference",
        "egress_policy_reference",
        "iam_review_reference",
    }:
        if not isinstance(network[field], bool):
            raise ProductionEnvironmentInventoryError(f"network.{field} must be Boolean.")
        if network[field] is not False:
            raise ProductionEnvironmentInventoryError(f"network.{field} cannot be enabled.")


def _validate_secrets(value: Any, *, accepted: bool) -> None:
    secrets = _exact_object(value, SECRET_KEYS, "secrets")
    for field in (
        "manager_reference",
        "secret_inventory_reference",
        "rotation_evidence_reference",
    ):
        _reference(secrets[field], f"secrets.{field}", required=accepted)
    _timestamp(
        secrets["rotation_completed_at"],
        "secrets.rotation_completed_at",
        required=accepted,
    )
    for field in ("production_secrets_in_repository", "application_credentials_embedded"):
        if secrets[field] is not False:
            raise ProductionEnvironmentInventoryError(f"secrets.{field} must remain false.")


def _validate_recovery(value: Any, *, accepted: bool) -> None:
    recovery = _exact_object(value, RECOVERY_KEYS, "recovery")
    for field in RECOVERY_KEYS - {"measured_rollback_seconds", "approved_rto_seconds"}:
        _reference(recovery[field], f"recovery.{field}", required=accepted)
    measured = _positive_number(
        recovery["measured_rollback_seconds"],
        "recovery.measured_rollback_seconds",
        required=accepted,
    )
    rto = _positive_number(
        recovery["approved_rto_seconds"], "recovery.approved_rto_seconds", required=accepted
    )
    if accepted and measured is not None and rto is not None and measured > rto:
        raise ProductionEnvironmentInventoryError("measured rollback time exceeds the approved RTO.")


def _validate_approvals(value: Any, *, accepted: bool) -> None:
    if not isinstance(value, list) or len(value) != len(APPROVAL_FUNCTIONS):
        raise ProductionEnvironmentInventoryError(
            "approvals must contain all five reviewed functions."
        )
    for (expected_function, expected_role), raw in zip(APPROVAL_FUNCTIONS, value):
        approval = _exact_object(raw, APPROVAL_KEYS, f"approval {expected_function}")
        if (
            approval["function"] != expected_function
            or approval["approver_role"] != expected_role
        ):
            raise ProductionEnvironmentInventoryError("approval function/order/role is invalid.")
        if approval["decision"] not in {"PENDING", "APPROVED", "REJECTED"}:
            raise ProductionEnvironmentInventoryError(
                f"approval {expected_function} decision is invalid."
            )
        decided = approval["decision"] != "PENDING"
        _reference(
            approval["evidence_reference"],
            f"approval {expected_function} evidence",
            required=decided or accepted,
        )
        _timestamp(
            approval["decided_at"],
            f"approval {expected_function} decided_at",
            required=decided or accepted,
        )
        if accepted and approval["decision"] != "APPROVED":
            raise ProductionEnvironmentInventoryError(
                f"accepted inventory requires {expected_function} approval."
            )


def _validate_not_started_has_no_claims(inventory: dict[str, Any]) -> None:
    if inventory["candidate_label"] is not None or inventory["source_commit"] is not None:
        raise ProductionEnvironmentInventoryError("NOT_STARTED inventory cannot identify a candidate.")
    if any(value is not None for value in inventory["target"].values()):
        raise ProductionEnvironmentInventoryError("NOT_STARTED target cannot contain provider claims.")
    for environment in inventory["environments"]:
        if environment["isolated"] or any(
            environment[field] is not None
            for field in ENVIRONMENT_KEYS - {"name", "isolated"}
        ):
            raise ProductionEnvironmentInventoryError(
                "NOT_STARTED environments cannot contain isolation claims."
            )
    for endpoint in inventory["public_endpoints"]:
        if any(endpoint[field] is not None for field in ENDPOINT_KEYS - {"name"}):
            raise ProductionEnvironmentInventoryError(
                "NOT_STARTED public endpoints cannot contain DNS or TLS claims."
            )
    policy = inventory["application_policy"]
    if policy != {
        "allowed_hosts": [],
        "cors_origins": [],
        "trusted_proxy_review_reference": None,
    }:
        raise ProductionEnvironmentInventoryError(
            "NOT_STARTED application policy cannot contain host or proxy claims."
        )
    for service in inventory["services"]:
        if any(service[field] is not None for field in SERVICE_KEYS - {"name", "exposure"}):
            raise ProductionEnvironmentInventoryError(
                "NOT_STARTED services cannot contain deployment claims."
            )
    network = inventory["network"]
    if any(network[field] is not None for field in (
        "ingress_policy_reference",
        "egress_policy_reference",
        "iam_review_reference",
    )):
        raise ProductionEnvironmentInventoryError(
            "NOT_STARTED network cannot contain review claims."
        )
    secrets = inventory["secrets"]
    if any(
        secrets[field] is not None
        for field in (
            "manager_reference",
            "secret_inventory_reference",
            "rotation_evidence_reference",
            "rotation_completed_at",
        )
    ):
        raise ProductionEnvironmentInventoryError(
            "NOT_STARTED secrets cannot contain manager or rotation claims."
        )
    if any(value is not None for value in inventory["recovery"].values()):
        raise ProductionEnvironmentInventoryError(
            "NOT_STARTED recovery cannot contain evidence claims."
        )
    for approval in inventory["approvals"]:
        if (
            approval["decision"] != "PENDING"
            or approval["evidence_reference"] is not None
            or approval["decided_at"] is not None
        ):
            raise ProductionEnvironmentInventoryError(
                "NOT_STARTED approvals must remain pending without evidence claims."
            )


def validate_inventory(inventory: Any, *, require_accepted: bool = False) -> dict[str, Any]:
    inventory = _exact_object(inventory, ROOT_KEYS, "environment inventory")
    _scan_forbidden_keys(inventory)
    if (
        inventory["schema_version"] != 1
        or inventory["gap"] != "GAP-002"
        or inventory["phase"] != "T5"
        or inventory["data_classification"] != "CONTROL_REFERENCES_ONLY"
    ):
        raise ProductionEnvironmentInventoryError("inventory identity metadata is invalid.")
    try:
        date.fromisoformat(str(inventory["inventory_revision"]))
    except ValueError as error:
        raise ProductionEnvironmentInventoryError(
            "inventory_revision must be a real ISO calendar date."
        ) from error
    status = inventory["status"]
    if status not in {"NOT_STARTED", "IN_PROGRESS", "REJECTED", "ACCEPTED"}:
        raise ProductionEnvironmentInventoryError("inventory status is invalid.")
    accepted = status == "ACCEPTED"
    if inventory["phase_accepted"] is not False or inventory["deployment_accepted"] is not False:
        raise ProductionEnvironmentInventoryError(
            "GAP-002 inventory cannot grant phase or deployment acceptance."
        )
    if inventory["gap_002_accepted"] is not accepted:
        raise ProductionEnvironmentInventoryError(
            "gap_002_accepted must be true only for a complete ACCEPTED inventory."
        )
    if require_accepted and not accepted:
        raise ProductionEnvironmentInventoryError("an externally accepted GAP-002 inventory is required.")

    if inventory["candidate_label"] is not None or accepted:
        if (
            not isinstance(inventory["candidate_label"], str)
            or SAFE_LABEL.fullmatch(inventory["candidate_label"]) is None
        ):
            raise ProductionEnvironmentInventoryError("candidate_label is invalid.")
    if inventory["source_commit"] is not None or accepted:
        if (
            not isinstance(inventory["source_commit"], str)
            or SHA1.fullmatch(inventory["source_commit"]) is None
        ):
            raise ProductionEnvironmentInventoryError("source_commit must be a full lowercase Git commit.")

    _validate_target(inventory["target"], accepted=accepted)
    _validate_environments(inventory["environments"], accepted=accepted)
    endpoints = _validate_endpoints(inventory["public_endpoints"], accepted=accepted)
    _validate_application_policy(inventory["application_policy"], endpoints, accepted=accepted)
    _validate_services(inventory["services"], accepted=accepted)
    _validate_network(inventory["network"], accepted=accepted)
    _validate_secrets(inventory["secrets"], accepted=accepted)
    _validate_recovery(inventory["recovery"], accepted=accepted)
    _validate_approvals(inventory["approvals"], accepted=accepted)

    limitations = inventory["limitations"]
    if (
        not isinstance(limitations, list)
        or "NO_PHASE_OR_DEPLOYMENT_ACCEPTANCE" not in limitations
        or any(
            not isinstance(item, str) or CLOSED_ID.fullmatch(item) is None
            for item in limitations
        )
        or len(limitations) != len(set(limitations))
    ):
        raise ProductionEnvironmentInventoryError(
            "limitations must retain the no-acceptance boundary."
        )
    if accepted and "NO_HOST_OR_PROVIDER_ACCEPTED" in limitations:
        raise ProductionEnvironmentInventoryError(
            "accepted inventory retains the unaccepted-host limitation."
        )
    if status == "NOT_STARTED":
        if (
            limitations
            != ["NO_HOST_OR_PROVIDER_ACCEPTED", "NO_PHASE_OR_DEPLOYMENT_ACCEPTANCE"]
        ):
            raise ProductionEnvironmentInventoryError("NOT_STARTED inventory cannot contain candidate claims.")
        _validate_not_started_has_no_claims(inventory)
    return {
        "status": status,
        "gap_002_accepted": accepted,
        "services": len(inventory["services"]),
        "environments": len(inventory["environments"]),
        "approvals": len(inventory["approvals"]),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--require-accepted", action="store_true")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    arguments = _parser().parse_args(list(argv) if argv is not None else None)
    try:
        summary = validate_inventory(
            _load(arguments.inventory), require_accepted=arguments.require_accepted
        )
    except ProductionEnvironmentInventoryError as error:
        print(
            f"Production environment inventory validation failed: {error}",
            file=sys.stderr,
        )
        return 1
    print(
        "Production environment inventory passed: "
        f"status {summary['status']}, {summary['environments']} isolated-environment slots, "
        f"{summary['services']} reviewed services, {summary['approvals']} approval functions; "
        "zero phase/deployment acceptance claims."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
