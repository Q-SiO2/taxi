"""Validate security and readiness invariants in the production Compose template."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


MANIFEST_PATH = Path(__file__).resolve().parents[1] / "deploy" / "compose.production.yaml"
REQUIRED_SERVICES = {"migrate", "api", "worker", "clamav"}


def _mapping(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be a mapping.")
    return value


def _sequence(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{context} must be a list.")
    return value


def _require_hardened(service_name: str, service: dict[str, Any]) -> None:
    if service.get("user") != "2000:2000":
        raise ValueError(f"{service_name} must run as the fixed application UID/GID 2000.")
    if service.get("read_only") is not True:
        raise ValueError(f"{service_name} must use a read-only root filesystem.")
    if "ALL" not in _sequence(service.get("cap_drop"), f"{service_name}.cap_drop"):
        raise ValueError(f"{service_name} must drop all Linux capabilities.")
    if "no-new-privileges:true" not in _sequence(
        service.get("security_opt"), f"{service_name}.security_opt"
    ):
        raise ValueError(f"{service_name} must disable privilege escalation.")
    image = service.get("image")
    if not isinstance(image, str) or "TAXIMOBILE_API_IMAGE:?" not in image:
        raise ValueError(f"{service_name} must require the immutable deployment image input.")


def _require_readiness_healthcheck(
    service_name: str,
    service: dict[str, Any],
    *,
    port: int,
    requires_allowed_host: bool = False,
) -> None:
    healthcheck = _mapping(service.get("healthcheck"), f"{service_name}.healthcheck")
    command = _sequence(healthcheck.get("test"), f"{service_name}.healthcheck.test")
    if len(command) < 4 or command[0] != "CMD" or command[1:3] != ["python", "-c"]:
        raise ValueError(f"{service_name} healthcheck must use the image's Python runtime.")
    probe = command[3]
    expected_url = f"http://127.0.0.1:{port}/ready"
    if not isinstance(probe, str) or expected_url not in probe or "/health" in probe:
        raise ValueError(f"{service_name} healthcheck must probe {expected_url}.")
    if "timeout=" not in probe:
        raise ValueError(f"{service_name} readiness probe must use a bounded HTTP timeout.")
    if requires_allowed_host and not (
        "TAXIMOBILE_ALLOWED_HOSTS" in probe and "headers={'Host': host}" in probe
    ):
        raise ValueError(
            f"{service_name} readiness probe must send the first reviewed allowed Host value."
        )
    for setting in ("interval", "timeout", "start_period", "retries"):
        if setting not in healthcheck:
            raise ValueError(f"{service_name} healthcheck must define {setting}.")


def _require_loopback_port(service_name: str, service: dict[str, Any], container_port: int) -> None:
    ports = _sequence(service.get("ports"), f"{service_name}.ports")
    if len(ports) != 1 or not isinstance(ports[0], str):
        raise ValueError(f"{service_name} must publish exactly one loopback port.")
    if not ports[0].startswith("127.0.0.1:") or not ports[0].endswith(f":{container_port}"):
        raise ValueError(f"{service_name} port {container_port} must bind only to host loopback.")


def validate_document(document: Any) -> None:
    root = _mapping(document, "Compose document")
    services = _mapping(root.get("services"), "services")
    if set(services) != REQUIRED_SERVICES:
        raise ValueError(
            "Production services must be exactly migrate, api, worker, and clamav; "
            f"found {sorted(services)}."
        )

    migrate = _mapping(services["migrate"], "migrate")
    api = _mapping(services["api"], "api")
    worker = _mapping(services["worker"], "worker")
    clamav = _mapping(services["clamav"], "clamav")
    for name, service in (("migrate", migrate), ("api", api), ("worker", worker)):
        _require_hardened(name, service)

    migrate_environment = _mapping(migrate.get("environment"), "migrate.environment")
    if set(migrate_environment) != {
        "TAXIMOBILE_ENV", "TAXIMOBILE_DATABASE_URL",
        "TAXIMOBILE_MIGRATION_LOCK_TIMEOUT_SECONDS", "TAXIMOBILE_MIGRATION_STATEMENT_TIMEOUT_SECONDS",
    }:
        raise ValueError("Migration service may receive only environment, database and migration-limit configuration.")
    if migrate.get("command") != ["alembic", "upgrade", "head"] or migrate.get("restart") != "no":
        raise ValueError("Migration service must perform one forward migration and never restart.")

    api_environment = _mapping(api.get("environment"), "api.environment")
    worker_environment = _mapping(worker.get("environment"), "worker.environment")
    if api_environment.get("TAXIMOBILE_PROCESS_ROLE") != "api":
        raise ValueError("API service must use the closed api process role.")
    if worker_environment.get("TAXIMOBILE_PROCESS_ROLE") != "worker":
        raise ValueError("Worker service must use the closed worker process role.")
    for name, environment in (("api", api_environment), ("worker", worker_environment)):
        if environment.get("TAXIMOBILE_LOG_FILE") != "/var/log/taximobile/events.jsonl":
            raise ValueError(f"{name} must write the reviewed structured log file.")
        for limit_name in (
            "TAXIMOBILE_DATABASE_POOL_SIZE",
            "TAXIMOBILE_DATABASE_POOL_MAX_OVERFLOW",
            "TAXIMOBILE_DATABASE_POOL_TIMEOUT_SECONDS",
        ):
            if limit_name not in environment:
                raise ValueError(
                    f"{name} must receive bounded database-pool settings."
                )
        for limit_name in (
            "TAXIMOBILE_LOG_FILE_MAX_BYTES",
            "TAXIMOBILE_LOG_FILE_BACKUP_COUNT",
        ):
            if limit_name not in environment:
                raise ValueError(f"{name} must receive bounded file-log rotation.")
    for name, service in (("api", api), ("worker", worker)):
        deployment = service.get("deploy")
        if deployment is not None:
            replicas = _mapping(deployment, f"{name}.deploy").get("replicas")
            if replicas not in (None, 1):
                raise ValueError(
                    f"{name} cannot share one rotating role-log volume across replicas."
                )
    allowed_hosts = api_environment.get("TAXIMOBILE_ALLOWED_HOSTS")
    if not isinstance(allowed_hosts, str) or not allowed_hosts.startswith(
        "taximobile-api-metrics,${TAXIMOBILE_ALLOWED_HOSTS:?"
    ):
        raise ValueError(
            "API must allow the fixed internal metrics alias before required public hosts."
        )
    if "TAXIMOBILE_JWT_SECRET" not in api_environment:
        raise ValueError("API service requires the JWT signing secret.")
    if "TAXIMOBILE_JWT_SECRET" in worker_environment:
        raise ValueError("Worker service must not receive the API JWT signing secret.")
    client_compatibility_keys = {
        "TAXIMOBILE_CLIENT_COMPATIBILITY_ENFORCED",
        "TAXIMOBILE_CLIENT_POLICY_REVISION",
        *{
            f"TAXIMOBILE_CLIENT_{surface}_{kind}_VERSION"
            for surface in (
                "ANDROID_PASSENGER",
                "ANDROID_DRIVER",
                "IOS_PASSENGER",
                "IOS_DRIVER",
                "WEB_APPLICANT",
                "WEB_OPERATIONS",
            )
            for kind in ("MINIMUM", "RECOMMENDED")
        },
    }
    if not client_compatibility_keys.issubset(api_environment):
        raise ValueError("API service must receive the complete client compatibility policy.")
    if api_environment.get("TAXIMOBILE_CLIENT_COMPATIBILITY_ENFORCED") != "true":
        raise ValueError("Production API must force client compatibility enforcement on.")
    if client_compatibility_keys.intersection(worker_environment):
        raise ValueError("Worker service must not receive client compatibility policy.")
    if api_environment.get("TAXIMOBILE_LEGACY_ADMIN_API_ENABLED") != "false":
        raise ValueError("Production API must force the transitional legacy admin API off.")
    if "TAXIMOBILE_LEGACY_ADMIN_API_ENABLED" in worker_environment:
        raise ValueError("Worker service must not receive legacy admin API configuration.")
    if "TAXIMOBILE_OPERATIONS_MFA_ENCRYPTION_KEY" not in api_environment:
        raise ValueError("API service requires the independent operations MFA encryption key.")
    if "TAXIMOBILE_OPERATIONS_MFA_ENCRYPTION_KEY" in worker_environment:
        raise ValueError("Worker service must not receive the operations MFA encryption key.")
    if ":?" not in str(api_environment["TAXIMOBILE_OPERATIONS_MFA_ENCRYPTION_KEY"]):
        raise ValueError("Production must require the operations MFA encryption key.")
    if api_environment.get("TAXIMOBILE_OPERATIONS_SECURE_COOKIE_ENABLED") != "true":
        raise ValueError("Production API must enforce secure operations refresh cookies.")
    if "TAXIMOBILE_OPERATIONS_SECURE_COOKIE_ENABLED" in worker_environment:
        raise ValueError("Worker service must not receive operations cookie configuration.")
    if "TAXIMOBILE_FIREBASE_PROJECT_ID" not in worker_environment:
        raise ValueError("Worker service requires Firebase delivery configuration.")
    if "TAXIMOBILE_FIREBASE_PROJECT_ID" in api_environment:
        raise ValueError("API service must not receive Firebase delivery configuration.")
    for key in ("TAXIMOBILE_ROUTING_PROVIDER", "TAXIMOBILE_ROUTING_BASE_URL"):
        if key not in api_environment or key in worker_environment:
            raise ValueError(f"Routing configuration {key} must belong only to the API service.")
    geocoding_keys = {
        "TAXIMOBILE_GEOCODING_PROVIDER",
        "TAXIMOBILE_GEOCODING_BASE_URL",
        "TAXIMOBILE_GEOCODING_TIMEOUT_SECONDS",
        "TAXIMOBILE_GEOCODING_USER_AGENT",
        "TAXIMOBILE_PLACE_SEARCH_RATE_LIMIT_PER_MINUTE",
        "TAXIMOBILE_PLACE_REVERSE_RATE_LIMIT_PER_MINUTE",
    }
    if not geocoding_keys.issubset(api_environment):
        raise ValueError("API service must receive the complete fail-closed geocoding configuration surface.")
    if geocoding_keys.intersection(worker_environment):
        raise ValueError("Worker service must not receive geocoding request configuration.")
    manual_transfer_keys = {
        "TAXIMOBILE_MANUAL_TRANSFER_ENABLED",
        "TAXIMOBILE_TRANSFER_RECIPIENT_NAME",
        "TAXIMOBILE_TRANSFER_BANK_ACCOUNT",
        "TAXIMOBILE_TRANSFER_WALLET_ID",
    }
    if not manual_transfer_keys.issubset(api_environment):
        raise ValueError("API service must receive the complete fail-closed manual-transfer configuration surface.")
    if manual_transfer_keys.intersection(worker_environment):
        raise ValueError("Worker service must not receive manual-transfer recipient configuration.")
    case_pager_keys = {
        "TAXIMOBILE_CASE_ALERT_POLL_SECONDS",
        "TAXIMOBILE_CASE_ALERT_MAX_DELIVERY_ATTEMPTS",
        "TAXIMOBILE_CASE_PAGER_URL",
        "TAXIMOBILE_CASE_PAGER_TOKEN",
        "TAXIMOBILE_CASE_PAGER_TIMEOUT_SECONDS",
    }
    if not case_pager_keys.issubset(worker_environment):
        raise ValueError("Worker service must receive the complete fail-closed case-pager configuration surface.")
    if case_pager_keys.intersection(api_environment):
        raise ValueError("API service must not receive worker-only case-pager configuration.")
    if ":?" not in str(worker_environment["TAXIMOBILE_CASE_PAGER_URL"]):
        raise ValueError("Production must require a protected case-pager URL.")
    if ":?" not in str(worker_environment["TAXIMOBILE_CASE_PAGER_TOKEN"]):
        raise ValueError("Production must require a dedicated case-pager token.")
    retention_keys = {
        "TAXIMOBILE_CASE_RETENTION_POLL_SECONDS",
        "TAXIMOBILE_CASE_RETENTION_BATCH_SIZE",
    }
    if not retention_keys.issubset(worker_environment):
        raise ValueError("Worker service must receive the complete case-retention configuration surface.")
    if retention_keys.intersection(api_environment):
        raise ValueError("API service must not receive worker-only case-retention configuration.")

    shared_document_keys = {
        "TAXIMOBILE_DRIVER_DOCUMENT_STORAGE_ROOT",
        "TAXIMOBILE_DRIVER_DOCUMENT_ENCRYPTION_KEY",
        "TAXIMOBILE_DRIVER_DOCUMENT_CLAMAV_HOST",
        "TAXIMOBILE_DRIVER_DOCUMENT_CLAMAV_PORT",
        "TAXIMOBILE_DRIVER_DOCUMENT_CLAMAV_TIMEOUT_SECONDS",
        "TAXIMOBILE_DRIVER_DOCUMENT_MAX_BYTES",
    }
    for name, environment in (("API", api_environment), ("worker", worker_environment)):
        if not shared_document_keys.issubset(environment):
            raise ValueError(f"{name} must receive the complete protected driver-document boundary.")
        if environment["TAXIMOBILE_DRIVER_DOCUMENT_STORAGE_ROOT"] != "/var/lib/taximobile/driver-documents":
            raise ValueError(f"{name} must use the private driver-document volume path.")
        if environment["TAXIMOBILE_DRIVER_DOCUMENT_CLAMAV_HOST"] != "clamav":
            raise ValueError(f"{name} must scan through the private ClamAV service.")
        if ":?" not in str(environment["TAXIMOBILE_DRIVER_DOCUMENT_ENCRYPTION_KEY"]):
            raise ValueError(f"{name} must require the driver-document encryption key.")
    document_api_keys = {
        "TAXIMOBILE_DRIVER_DOCUMENT_UPLOAD_RATE_LIMIT_PER_HOUR",
        "TAXIMOBILE_DRIVER_DOCUMENT_ACCESS_RATE_LIMIT_PER_MINUTE",
    }
    document_worker_keys = {
        "TAXIMOBILE_DRIVER_DOCUMENT_RETENTION_DAYS",
        "TAXIMOBILE_DRIVER_DOCUMENT_RETENTION_POLL_SECONDS",
        "TAXIMOBILE_DRIVER_DOCUMENT_RETENTION_BATCH_SIZE",
    }
    if not document_api_keys.issubset(api_environment) or document_api_keys.intersection(worker_environment):
        raise ValueError("Driver-document request limits must belong only to the API service.")
    if not document_worker_keys.issubset(worker_environment) or document_worker_keys.intersection(api_environment):
        raise ValueError("Driver-document retention policy must belong only to the worker service.")
    expected_role_mounts = {
        "api": [
            "taximobile_driver_documents:/var/lib/taximobile/driver-documents",
            "taximobile_api_logs:/var/log/taximobile",
        ],
        "worker": [
            "taximobile_driver_documents:/var/lib/taximobile/driver-documents",
            "taximobile_worker_logs:/var/log/taximobile",
        ],
    }
    for name, service in (("api", api), ("worker", worker)):
        if service.get("volumes") != expected_role_mounts[name]:
            raise ValueError(
                f"{name} must mount only the shared document and private role-log volumes."
            )
        dependency = _mapping(service.get("depends_on"), f"{name}.depends_on")
        scanner_dependency = _mapping(dependency.get("clamav"), f"{name}.depends_on.clamav")
        if scanner_dependency.get("condition") != "service_healthy":
            raise ValueError(f"{name} must wait for a healthy private ClamAV service.")

    if clamav.get("read_only") is not True:
        raise ValueError("ClamAV must use a read-only root filesystem.")
    if "ALL" not in _sequence(clamav.get("cap_drop"), "clamav.cap_drop"):
        raise ValueError("ClamAV must drop all Linux capabilities.")
    if "no-new-privileges:true" not in _sequence(clamav.get("security_opt"), "clamav.security_opt"):
        raise ValueError("ClamAV must disable privilege escalation.")
    clamav_image = clamav.get("image")
    if not isinstance(clamav_image, str) or "TAXIMOBILE_CLAMAV_IMAGE:?" not in clamav_image:
        raise ValueError("ClamAV must require an immutable deployment image input.")
    if "ports" in clamav or clamav.get("expose") != ["3310"]:
        raise ValueError("ClamAV may expose port 3310 only to the private Compose network.")
    if clamav.get("volumes") != ["taximobile_clamav_database:/var/lib/clamav"]:
        raise ValueError("ClamAV may persist only its signature database volume.")
    scanner_health = _mapping(clamav.get("healthcheck"), "clamav.healthcheck")
    scanner_test = _sequence(scanner_health.get("test"), "clamav.healthcheck.test")
    if scanner_test[:1] != ["CMD-SHELL"] or not any("clamdscan --ping" in str(part) for part in scanner_test):
        raise ValueError("ClamAV health must prove that the scanner daemon accepts commands.")
    declared_volumes = _mapping(root.get("volumes"), "volumes")
    if set(declared_volumes) != {
        "taximobile_driver_documents",
        "taximobile_clamav_database",
        "taximobile_api_logs",
        "taximobile_worker_logs",
    }:
        raise ValueError(
            "Production must declare only protected document, scanner and role-log volumes."
        )

    _require_loopback_port("api", api, 8000)
    _require_loopback_port("worker", worker, 8001)
    _require_readiness_healthcheck("api", api, port=8000, requires_allowed_host=True)
    _require_readiness_healthcheck("worker", worker, port=8001)

    api_command = _sequence(api.get("command"), "api.command")
    worker_command = _sequence(worker.get("command"), "worker.command")
    if "taximobile_api.main:app" not in api_command or "--no-access-log" not in api_command:
        raise ValueError("API must launch the reviewed app without raw Uvicorn access logs.")
    if "taximobile_api.worker:app" not in worker_command or "--no-access-log" not in worker_command:
        raise ValueError("Worker must launch the private app without raw Uvicorn access logs.")


def validate_manifest(path: Path = MANIFEST_PATH) -> None:
    validate_document(yaml.safe_load(path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    validate_manifest()
    print("Validated TaxiMobile production Compose security and readiness contract.")
