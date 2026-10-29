import pytest
from unittest.mock import AsyncMock, MagicMock

from taximobile_api.operations.railway_entrypoint import (
    RailwayConfigurationError, command_for, configure_environment, migrate, migration_target, verify_runtime,
)


def staging():
    return {"RAILWAY_PROJECT_ID": "test-project", "RAILWAY_ENVIRONMENT_ID": "test-environment",
            "TAXIMOBILE_ENV": "staging", "RAILWAY_PUBLIC_DOMAIN": "alpha-api.up.railway.app"}


def test_api_has_exact_public_and_healthcheck_hosts_and_discards_migration_authority():
    environment = staging() | {"TAXIMOBILE_MIGRATION_DATABASE_URL": "private",
                               "TAXIMOBILE_RUNTIME_DATABASE_PASSWORD": "private",
                               "TAXIMOBILE_ALPHA_SEED_PASSWORD": "private",
                               "TAXIMOBILE_ALPHA_SEED_SUFFIX": "aabbccdd"}
    configure_environment(environment, "api")
    assert environment["TAXIMOBILE_ALLOWED_HOSTS"].split(",") == [
        "alpha-api.up.railway.app", "healthcheck.railway.app"]
    assert not any("MIGRATION" in key or "RUNTIME_DATABASE_PASSWORD" in key for key in environment)
    assert not any("ALPHA_SEED" in key for key in environment)
    assert environment["TAXIMOBILE_PROCESS_ROLE"] == "api"


@pytest.mark.parametrize("hostname", ["", "*", "https://api.example.test", "api.example.test:8000", "bad host"])
def test_api_rejects_unsafe_public_hostname(hostname):
    with pytest.raises(RailwayConfigurationError):
        configure_environment(staging() | {"RAILWAY_PUBLIC_DOMAIN": hostname}, "api")


@pytest.mark.parametrize("missing", ["RAILWAY_PROJECT_ID", "RAILWAY_ENVIRONMENT_ID"])
def test_missing_provider_identity_refuses_execution(missing):
    environment = staging()
    environment.pop(missing)
    with pytest.raises(RailwayConfigurationError):
        configure_environment(environment, "worker")


@pytest.mark.parametrize("environment", ["development", "production", "test"])
def test_alpha_adapter_cannot_be_used_to_migrate_another_environment(environment):
    with pytest.raises(RailwayConfigurationError):
        configure_environment(staging() | {"TAXIMOBILE_ENV": environment}, "migrate")


def test_worker_needs_no_public_hostname_and_uses_private_role():
    environment = staging()
    environment.pop("RAILWAY_PUBLIC_DOMAIN")
    configure_environment(environment, "worker")
    assert environment["TAXIMOBILE_PROCESS_ROLE"] == "worker"
    assert "TAXIMOBILE_ALLOWED_HOSTS" not in environment
    command = command_for("worker", environment | {"PORT": "13001"})
    assert command[1] == "taximobile_api.worker:app"
    assert command[command.index("--port") + 1] == "13001"


@pytest.mark.parametrize("port", ["80", "65536", "invalid", "8000; echo unsafe"])
def test_invalid_port_cannot_be_passed_to_server(port):
    with pytest.raises(RailwayConfigurationError):
        command_for("api", {"PORT": port})


def target():
    return staging() | {"TAXIMOBILE_RUNTIME_DATABASE_PASSWORD": "x" * 40,
        "TAXIMOBILE_DATABASE_URL":
        "postgresql+asyncpg://taximobile_runtime:" + "x" * 40 + "@alpha-postgis.railway.internal:5432/taximobile_alpha_testenvironm",
        "TAXIMOBILE_MIGRATION_DATABASE_URL":
        "postgresql+asyncpg://owner:secret@alpha-postgis.railway.internal:5432/taximobile_alpha_testenvironm"}


def test_migration_accepts_only_the_exact_isolated_database():
    assert migration_target(target())[0].endswith("taximobile_alpha_testenvironm")


@pytest.mark.parametrize("url", [
    "postgresql+asyncpg://owner:secret@alpha-postgis.railway.internal/taximobile",
    "postgresql+asyncpg://owner:secret@production.example.test/taximobile_alpha_testenvironm",
    "postgresql+asyncpg://owner:secret@127.0.0.1/taximobile_alpha_testenvironm",
])
def test_migration_refuses_wrong_database_or_host(url):
    with pytest.raises(RailwayConfigurationError):
        migration_target(target() | {"TAXIMOBILE_MIGRATION_DATABASE_URL": url})


def test_failed_migration_does_not_grant_runtime_access(monkeypatch):
    calls = []

    async def provision(url, password, *, grant, tls):
        assert tls.mode == "disable"
        calls.append(grant)

    class Failed:
        returncode = 1

    guard = MagicMock(fetchval=AsyncMock(return_value=True), close=AsyncMock())
    monkeypatch.setattr("taximobile_api.operations.railway_entrypoint.asyncpg.connect", AsyncMock(return_value=guard))

    monkeypatch.setattr("taximobile_api.operations.railway_entrypoint.provision_runtime", provision)
    monkeypatch.setattr("taximobile_api.operations.railway_entrypoint.subprocess.run", lambda *a, **kw: Failed())
    with pytest.raises(RailwayConfigurationError, match="migration failed"):
        migrate(target())
    assert calls == [False]
    guard.close.assert_awaited_once()


def test_busy_deployment_guard_refuses_before_role_changes(monkeypatch):
    guard = MagicMock(fetchval=AsyncMock(return_value=False), close=AsyncMock())
    provision = AsyncMock()
    monkeypatch.setattr("taximobile_api.operations.railway_entrypoint.asyncpg.connect", AsyncMock(return_value=guard))
    monkeypatch.setattr("taximobile_api.operations.railway_entrypoint.provision_runtime", provision)
    with pytest.raises(RailwayConfigurationError, match="Another alpha migrator"):
        migrate(target())
    provision.assert_not_awaited()
    guard.close.assert_awaited_once()


def test_verified_tls_reaches_the_deployment_guard(monkeypatch):
    import ssl
    guard = MagicMock(fetchval=AsyncMock(return_value=False), close=AsyncMock())
    connect = AsyncMock(return_value=guard)
    monkeypatch.setattr("taximobile_api.operations.railway_entrypoint.asyncpg.connect", connect)
    with pytest.raises(RailwayConfigurationError, match="Another alpha migrator"):
        migrate(target() | {"TAXIMOBILE_DATABASE_TLS_MODE": "verify-full"})
    context = connect.await_args.kwargs["ssl"]
    assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
    guard.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_required_tls_refuses_unencrypted_runtime_observation_before_refresh(monkeypatch):
    from taximobile_api.operations.railway_entrypoint import verify_runtime
    role = {"name": "taximobile_runtime", **{field: False for field in ("rolsuper", "rolcreatedb", "rolcreaterole", "rolreplication", "rolbypassrls")}}
    connection = MagicMock(fetchrow=AsyncMock(side_effect=[role, {"ssl": False, "version": None}]),
                           fetchval=AsyncMock(return_value=False), execute=AsyncMock(), close=AsyncMock())
    monkeypatch.setattr("taximobile_api.operations.railway_entrypoint.asyncpg.connect", AsyncMock(return_value=connection))
    with pytest.raises(RailwayConfigurationError, match="no encrypted session"):
        await verify_runtime({"TAXIMOBILE_DATABASE_URL": "postgresql+asyncpg://runtime:fixture@private/alpha", "TAXIMOBILE_DATABASE_TLS_MODE": "verify-full"})
    connection.execute.assert_not_awaited()
    connection.close.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("owned", [True, False])
async def test_runtime_grants_exclude_materialized_views_and_only_transfer_owner_once(monkeypatch, owned):
    from taximobile_api.operations.railway_entrypoint import provision_runtime
    table_command = 'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.new_table TO taximobile_runtime'
    connection = MagicMock(execute=AsyncMock(), fetch=AsyncMock(side_effect=[[{"command": table_command}], []]),
                           fetchval=AsyncMock(return_value=owned), close=AsyncMock())
    connection.transaction.return_value = AsyncMock()
    monkeypatch.setattr("taximobile_api.operations.railway_entrypoint.asyncpg.connect", AsyncMock(return_value=connection))
    await provision_runtime("postgresql://private/alpha", "unused", grant=True)
    assert "c.relkind IN ('r','p','v')" in connection.fetch.await_args_list[0].args[0]
    statements = [call.args[0] for call in connection.execute.await_args_list]
    assert table_command in statements
    assert not any("ON ALL TABLES" in statement for statement in statements)
    assert any("ALTER MATERIALIZED VIEW" in statement for statement in statements) is (not owned)
    connection.close.assert_awaited_once()


@pytest.mark.parametrize("failing_mode", [None, "cohort", "mfa"])
def test_explicit_bootstrap_sequences_jobs_and_stops_on_failure(monkeypatch, failing_mode):
    from types import SimpleNamespace
    from taximobile_api.operations.railway_entrypoint import bootstrap
    calls = []
    monkeypatch.setattr("taximobile_api.operations.railway_entrypoint.migrate", lambda env: calls.append("migrate"))
    def run(command, **arguments):
        mode = command[-1]
        assert "&&" not in command
        assert arguments["env"]["TAXIMOBILE_ALPHA_SEED_PASSWORD"] == "private"
        calls.append(mode)
        return SimpleNamespace(returncode=int(mode == failing_mode))
    monkeypatch.setattr("taximobile_api.operations.railway_entrypoint.subprocess.run", run)
    if failing_mode is None:
        bootstrap({"TAXIMOBILE_ALPHA_SEED_PASSWORD": "private"})
    else:
        with pytest.raises(RailwayConfigurationError, match=f"{failing_mode} bootstrap failed"):
            bootstrap({"TAXIMOBILE_ALPHA_SEED_PASSWORD": "private"})
    assert calls == (["migrate", "cohort"] if failing_mode == "cohort" else ["migrate", "cohort", "mfa"])


@pytest.mark.asyncio
@pytest.mark.parametrize("unsafe", ["rolsuper", "rolcreatedb", "rolcreaterole", "rolreplication", "rolbypassrls", "schema_create", "wrong_role"])
async def test_runtime_verification_rejects_privileged_login_and_closes_connection(monkeypatch, unsafe):
    class Connection:
        closed = False

        async def fetchrow(self, query):
            return {"name": "owner" if unsafe == "wrong_role" else "taximobile_runtime",
                    **{field: field == unsafe for field in ["rolsuper", "rolcreatedb", "rolcreaterole", "rolreplication", "rolbypassrls"]}}

        async def fetchval(self, query):
            assert "has_schema_privilege" in query
            return unsafe == "schema_create"

        async def close(self):
            self.closed = True

    connection = Connection()

    async def connect(url, *, ssl):
        assert ssl is False
        return connection

    monkeypatch.setattr("taximobile_api.operations.railway_entrypoint.asyncpg.connect", connect)
    with pytest.raises(RailwayConfigurationError, match="administrator authority"):
        await verify_runtime({"TAXIMOBILE_DATABASE_URL": "postgresql+asyncpg://runtime:secret@private/alpha"})
    assert connection.closed
