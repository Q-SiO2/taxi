import pytest

from taximobile_api.operations.render_entrypoint import (
    RenderConfigurationError,
    async_database_url,
    command_for,
    configure_render_environment,
    private_routing_url,
)


def test_render_adapter_builds_only_required_private_runtime_values() -> None:
    environment = {
        "RENDER": "true",
        "RENDER_DATABASE_URL": "postgresql://taxi:secret@database.internal:5432/taximobile",
        "RENDER_EXTERNAL_HOSTNAME": "taximobile-api.onrender.com",
        "RENDER_ROUTING_HOSTPORT": "taximobile-routing:8002",
        "TAXIMOBILE_ENV": "staging",
        "TAXIMOBILE_PROCESS_ROLE": "api",
    }

    configure_render_environment(environment)

    assert environment["TAXIMOBILE_DATABASE_URL"] == (
        "postgresql+asyncpg://taxi:secret@database.internal:5432/taximobile"
    )
    assert environment["TAXIMOBILE_ALLOWED_HOSTS"] == "taximobile-api.onrender.com"
    assert environment["TAXIMOBILE_ROUTING_BASE_URL"] == "http://taximobile-routing:8002"


def test_worker_receives_database_but_not_public_api_or_routing_configuration() -> None:
    environment = {
        "RENDER": "true",
        "RENDER_DATABASE_URL": "postgres://taxi:secret@database.internal/taximobile",
        "TAXIMOBILE_PROCESS_ROLE": "worker",
    }

    configure_render_environment(environment)

    assert environment["TAXIMOBILE_DATABASE_URL"].startswith("postgresql+asyncpg://")
    assert "TAXIMOBILE_ALLOWED_HOSTS" not in environment
    assert "TAXIMOBILE_ROUTING_BASE_URL" not in environment


@pytest.mark.parametrize(
    "value",
    ["", "mysql://database.internal/taximobile", "postgresql://", "not-a-url"],
)
def test_render_database_adapter_rejects_incomplete_or_wrong_urls(value: str) -> None:
    with pytest.raises(RenderConfigurationError):
        async_database_url(value)


@pytest.mark.parametrize(
    "value",
    ["https://routing.example", "user:password@routing:8002", "routing:bad", "routing:8002/path"],
)
def test_private_routing_adapter_rejects_non_hostport_values(value: str) -> None:
    with pytest.raises(RenderConfigurationError):
        private_routing_url(value)


def test_render_entrypoint_refuses_non_render_execution() -> None:
    with pytest.raises(RenderConfigurationError, match="only on Render"):
        configure_render_environment({})


def test_api_command_uses_render_port_and_fixed_single_process() -> None:
    command = command_for("api", {"PORT": "12000"})

    assert command[:2] == ["uvicorn", "taximobile_api.main:app"]
    assert command[command.index("--port") + 1] == "12000"
    assert command[command.index("--workers") + 1] == "1"


def test_api_command_rejects_unsafe_port() -> None:
    with pytest.raises(RenderConfigurationError):
        command_for("api", {"PORT": "80"})


def test_migration_configuration_does_not_require_public_or_routing_values() -> None:
    environment = {
        "RENDER": "true",
        "RENDER_DATABASE_URL": "postgresql://taxi:secret@database.internal/taximobile",
        "TAXIMOBILE_PROCESS_ROLE": "api",
    }

    configure_render_environment(environment, entrypoint_role="migrate")

    assert "TAXIMOBILE_ALLOWED_HOSTS" not in environment
    assert "TAXIMOBILE_ROUTING_BASE_URL" not in environment


def test_bootstrap_admin_command_preserves_hidden_password_prompt() -> None:
    command = command_for(
        "bootstrap-admin",
        {},
        administrator_email="operator@example.test",
    )

    assert command == [
        "taximobile-bootstrap-admin",
        "--email",
        "operator@example.test",
        "--confirm-initial-admin",
    ]
