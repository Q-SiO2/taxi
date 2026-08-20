from pathlib import Path

import yaml


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
BLUEPRINT_PATH = WORKSPACE_ROOT / "infra" / "deploy" / "render.staging.yaml"


def _services(document: dict) -> dict[str, dict]:
    return {service["name"]: service for service in document["services"]}


def test_render_staging_blueprint_preserves_private_service_boundaries() -> None:
    document = yaml.safe_load(BLUEPRINT_PATH.read_text(encoding="utf-8"))
    services = _services(document)

    api = services["taximobile-staging-api"]
    worker = services["taximobile-staging-worker"]
    routing = services["taximobile-staging-routing"]

    assert api["type"] == "web"
    assert api["healthCheckPath"] == "/ready"
    assert api["preDeployCommand"].endswith(" migrate")
    assert worker["type"] == "worker"
    assert routing["type"] == "pserv"
    assert routing["image"]["url"].count("@sha256:") == 1
    assert routing["disk"]["mountPath"] == "/custom_files"
    assert all(service["region"] == "frankfurt" for service in services.values())


def test_render_staging_blueprint_uses_generated_and_linked_secrets() -> None:
    document = yaml.safe_load(BLUEPRINT_PATH.read_text(encoding="utf-8"))
    services = _services(document)
    api_environment = {item["key"]: item for item in services["taximobile-staging-api"]["envVars"]}
    worker_environment = {item["key"]: item for item in services["taximobile-staging-worker"]["envVars"]}

    assert api_environment["TAXIMOBILE_JWT_SECRET"]["generateValue"] is True
    assert api_environment["TAXIMOBILE_MONITORING_TOKEN"]["generateValue"] is True
    assert api_environment["RENDER_DATABASE_URL"]["fromDatabase"]["property"] == "connectionString"
    assert worker_environment["TAXIMOBILE_MONITORING_TOKEN"]["fromService"]["envVarKey"] == (
        "TAXIMOBILE_MONITORING_TOKEN"
    )
    assert "TAXIMOBILE_JWT_SECRET" not in worker_environment


def test_render_database_has_no_public_ingress() -> None:
    document = yaml.safe_load(BLUEPRINT_PATH.read_text(encoding="utf-8"))
    database = document["databases"][0]

    assert database["postgresMajorVersion"] == "16"
    assert database["ipAllowList"] == []
