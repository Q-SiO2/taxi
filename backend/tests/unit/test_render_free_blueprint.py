from pathlib import Path

import yaml


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
BLUEPRINT_PATH = WORKSPACE_ROOT / "infra" / "deploy" / "render.free-testing.yaml"


def test_free_blueprint_contains_only_free_resources() -> None:
    document = yaml.safe_load(BLUEPRINT_PATH.read_text(encoding="utf-8"))

    assert len(document["services"]) == 1
    assert document["services"][0]["type"] == "web"
    assert document["services"][0]["plan"] == "free"
    assert len(document["databases"]) == 1
    assert document["databases"][0]["plan"] == "free"
    assert document["databases"][0]["ipAllowList"] == []


def test_free_blueprint_runs_combined_staging_role_and_public_fair_use_routing() -> None:
    document = yaml.safe_load(BLUEPRINT_PATH.read_text(encoding="utf-8"))
    service = document["services"][0]
    environment = {item["key"]: item for item in service["envVars"]}

    assert service["dockerCommand"].endswith(" free-staging")
    assert "preDeployCommand" not in service
    assert service["healthCheckPath"] == "/ready"
    assert environment["TAXIMOBILE_ENV"]["value"] == "staging"
    assert environment["TAXIMOBILE_PROCESS_ROLE"]["value"] == "all"
    assert environment["TAXIMOBILE_LEGACY_ADMIN_API_ENABLED"]["value"] == "false"
    assert environment["TAXIMOBILE_OPERATIONS_PASSWORD_LOGIN_ENABLED"]["value"] == "true"
    assert environment["TAXIMOBILE_OPERATIONS_SECURE_COOKIE_ENABLED"]["value"] == "false"
    assert environment["TAXIMOBILE_ROUTING_BASE_URL"]["value"] == (
        "https://valhalla1.openstreetmap.de"
    )
    assert environment["TAXIMOBILE_ROUTING_RATE_LIMIT_PER_MINUTE"]["value"] == "10"
    assert environment["TAXIMOBILE_MANUAL_TRANSFER_ENABLED"]["value"] == "false"
    assert environment["TAXIMOBILE_CASE_ALERT_POLL_SECONDS"]["value"] == "60"
    assert environment["TAXIMOBILE_CASE_RETENTION_POLL_SECONDS"]["value"] == "3600"
    assert environment["TAXIMOBILE_CASE_RETENTION_BATCH_SIZE"]["value"] == "100"
    assert "TAXIMOBILE_CASE_PAGER_URL" not in environment
    assert "TAXIMOBILE_CASE_PAGER_TOKEN" not in environment
    assert "TAXIMOBILE_TRANSFER_RECIPIENT_NAME" not in environment


def test_free_blueprint_generates_secrets_without_embedding_values() -> None:
    document = yaml.safe_load(BLUEPRINT_PATH.read_text(encoding="utf-8"))
    environment = {item["key"]: item for item in document["services"][0]["envVars"]}

    assert environment["TAXIMOBILE_JWT_SECRET"]["generateValue"] is True
    assert environment["TAXIMOBILE_MONITORING_TOKEN"]["generateValue"] is True
    assert environment["TAXIMOBILE_FREE_TEST_ADMIN_EMAIL"]["sync"] is False
    assert environment["TAXIMOBILE_FREE_TEST_ADMIN_PASSWORD"]["sync"] is False
    assert environment["RENDER_DATABASE_URL"]["fromDatabase"]["property"] == "connectionString"
