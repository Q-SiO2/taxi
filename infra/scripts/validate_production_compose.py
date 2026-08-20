"""Validate security and readiness invariants in the production Compose template."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


MANIFEST_PATH = Path(__file__).resolve().parents[1] / "deploy" / "compose.production.yaml"
REQUIRED_SERVICES = {"migrate", "api", "worker"}


def _mapping(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be a mapping.")
    return value


def _sequence(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{context} must be a list.")
    return value


def _require_hardened(service_name: str, service: dict[str, Any]) -> None:
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
            "Production services must be exactly migrate, api, and worker; "
            f"found {sorted(services)}."
        )

    migrate = _mapping(services["migrate"], "migrate")
    api = _mapping(services["api"], "api")
    worker = _mapping(services["worker"], "worker")
    for name, service in (("migrate", migrate), ("api", api), ("worker", worker)):
        _require_hardened(name, service)

    migrate_environment = _mapping(migrate.get("environment"), "migrate.environment")
    if set(migrate_environment) != {"TAXIMOBILE_ENV", "TAXIMOBILE_DATABASE_URL"}:
        raise ValueError("Migration service may receive only environment and database configuration.")
    if migrate.get("command") != ["alembic", "upgrade", "head"] or migrate.get("restart") != "no":
        raise ValueError("Migration service must perform one forward migration and never restart.")

    api_environment = _mapping(api.get("environment"), "api.environment")
    worker_environment = _mapping(worker.get("environment"), "worker.environment")
    if api_environment.get("TAXIMOBILE_PROCESS_ROLE") != "api":
        raise ValueError("API service must use the closed api process role.")
    if worker_environment.get("TAXIMOBILE_PROCESS_ROLE") != "worker":
        raise ValueError("Worker service must use the closed worker process role.")
    if "TAXIMOBILE_JWT_SECRET" not in api_environment:
        raise ValueError("API service requires the JWT signing secret.")
    if "TAXIMOBILE_JWT_SECRET" in worker_environment:
        raise ValueError("Worker service must not receive the API JWT signing secret.")
    if "TAXIMOBILE_FIREBASE_PROJECT_ID" not in worker_environment:
        raise ValueError("Worker service requires Firebase delivery configuration.")
    if "TAXIMOBILE_FIREBASE_PROJECT_ID" in api_environment:
        raise ValueError("API service must not receive Firebase delivery configuration.")
    for key in ("TAXIMOBILE_ROUTING_PROVIDER", "TAXIMOBILE_ROUTING_BASE_URL"):
        if key not in api_environment or key in worker_environment:
            raise ValueError(f"Routing configuration {key} must belong only to the API service.")

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
