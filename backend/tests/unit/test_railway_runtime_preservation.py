"""An ordinary schema deployment verifies an established login without reset."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import asyncpg
import pytest
from sqlalchemy.engine import make_url

from taximobile_api.db.transport import DatabaseTLS
from taximobile_api.operations import railway_entrypoint as deployment


PASSWORD = "synthetic-runtime-fixture-" + "x" * 32
OWNER_URL = "postgresql+asyncpg://owner:synthetic-owner@alpha-postgis.railway.internal:5432/taximobile_alpha_preservefixt"


def owner():
    connection = MagicMock(fetchval=AsyncMock(side_effect=[True, "ALTER ROLE synthetic-fixture"]),
                           execute=AsyncMock(), close=AsyncMock())
    connection.transaction.return_value = AsyncMock()
    return connection


def runtime(*, privileged=False, encrypted=True):
    role = {"name": "taximobile_runtime", **{name: False for name in (
        "rolsuper", "rolcreatedb", "rolcreaterole", "rolreplication", "rolbypassrls")}}
    role["rolsuper"] = privileged
    connection = MagicMock(fetchrow=AsyncMock(side_effect=[role, {"ssl": encrypted, "version": "TLSv1.3"}]),
                           fetchval=AsyncMock(return_value=False), execute=AsyncMock(), close=AsyncMock())
    connection.transaction.return_value = AsyncMock()
    return connection


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["disable", "verify-full"])
async def test_existing_login_is_verified_read_only_and_never_altered(monkeypatch, mode):
    privileged, existing = owner(), runtime()
    connect = AsyncMock(side_effect=[privileged, existing])
    monkeypatch.setattr(deployment.asyncpg, "connect", connect)
    await deployment.provision_runtime(OWNER_URL, PASSWORD, grant=False, tls=DatabaseTLS(mode))
    privileged.execute.assert_not_awaited()
    assert connect.await_count == 2
    call = connect.await_args_list[1]
    parsed = make_url(call.args[0])
    assert parsed.username == "taximobile_runtime" and parsed.password == PASSWORD
    assert parsed.host == "alpha-postgis.railway.internal" and parsed.database == "taximobile_alpha_preservefixt"
    assert call.kwargs["timeout"] == 10
    assert call.kwargs["server_settings"]["default_transaction_read_only"] == "on"
    if mode == "verify-full":
        assert call.kwargs["ssl"].check_hostname
    else:
        assert call.kwargs["ssl"] is False
    existing.execute.assert_not_awaited()  # No role DCL, refresh, seed or recovery.
    existing.transaction.assert_called_once_with(readonly=True)
    privileged.close.assert_awaited_once()
    existing.close.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [asyncpg.InvalidPasswordError("private-fixture-detail"),
                                    OSError("private-fixture-detail"), TimeoutError("private-fixture-detail")])
async def test_unverified_existing_login_fails_without_a_password_reset(monkeypatch, error):
    privileged = owner()
    connect = AsyncMock(side_effect=[privileged, error])
    monkeypatch.setattr(deployment.asyncpg, "connect", connect)
    with pytest.raises(deployment.RailwayConfigurationError, match="Existing runtime login") as rejected:
        await deployment.provision_runtime(OWNER_URL, PASSWORD, grant=False, tls=DatabaseTLS())
    assert "private-fixture-detail" not in str(rejected.value) and PASSWORD not in str(rejected.value)
    privileged.execute.assert_not_awaited()
    privileged.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_existing_privileged_role_is_rejected_instead_of_repaired_silently(monkeypatch):
    privileged, existing = owner(), runtime(privileged=True)
    monkeypatch.setattr(deployment.asyncpg, "connect", AsyncMock(side_effect=[privileged, existing]))
    with pytest.raises(deployment.RailwayConfigurationError, match="administrator authority"):
        await deployment.provision_runtime(OWNER_URL, PASSWORD, grant=False, tls=DatabaseTLS())
    privileged.execute.assert_not_awaited()
    existing.execute.assert_not_awaited()
    existing.close.assert_awaited_once()
    privileged.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_established_login_mismatch_stops_before_any_schema_migration(monkeypatch):
    guard = MagicMock(fetchval=AsyncMock(return_value=True), close=AsyncMock())
    privileged = owner()
    connect = AsyncMock(side_effect=[guard, privileged, asyncpg.InvalidPasswordError("private-fixture-detail")])
    command = MagicMock(return_value=SimpleNamespace(returncode=0))
    monkeypatch.setattr(deployment.asyncpg, "connect", connect)
    monkeypatch.setattr(deployment.subprocess, "run", command)
    environment = {"RAILWAY_PROJECT_ID": "synthetic-project", "RAILWAY_ENVIRONMENT_ID": "preservefixture",
                   "TAXIMOBILE_MIGRATION_DATABASE_URL": OWNER_URL,
                   "TAXIMOBILE_DATABASE_URL": make_url(OWNER_URL).set(username="taximobile_runtime", password=PASSWORD).render_as_string(hide_password=False),
                   "TAXIMOBILE_RUNTIME_DATABASE_PASSWORD": PASSWORD}
    with pytest.raises(deployment.RailwayConfigurationError, match="Existing runtime login"):
        await deployment.migrate_locked(environment)
    command.assert_not_called()
    privileged.execute.assert_not_awaited()
    guard.close.assert_awaited_once()


@pytest.mark.parametrize("change", [
    {"host": "other.example.test"}, {"database": "other_database"}, {"username": "owner"},
    {"password": "synthetic-other-password"}, {"port": 6543},
])
def test_runtime_target_mismatch_fails_before_any_owner_connection(monkeypatch, change):
    expected = make_url(OWNER_URL).set(username="taximobile_runtime", password=PASSWORD)
    environment = {"RAILWAY_ENVIRONMENT_ID": "preservefixture", "TAXIMOBILE_MIGRATION_DATABASE_URL": OWNER_URL,
                   "TAXIMOBILE_DATABASE_URL": expected.set(**change).render_as_string(hide_password=False),
                   "TAXIMOBILE_RUNTIME_DATABASE_PASSWORD": PASSWORD}
    connect = AsyncMock()
    monkeypatch.setattr(deployment.asyncpg, "connect", connect)
    with pytest.raises(deployment.RailwayConfigurationError, match="Runtime configuration") as rejected:
        deployment.migrate(environment)
    assert PASSWORD not in str(rejected.value)
    connect.assert_not_awaited()


def test_runtime_transport_override_is_rejected_before_owner_connection(monkeypatch):
    from taximobile_api.db.transport import DatabaseTLSConfigurationError
    runtime_url = make_url(OWNER_URL).set(username="taximobile_runtime", password=PASSWORD)
    environment = {"RAILWAY_ENVIRONMENT_ID": "preservefixture", "TAXIMOBILE_MIGRATION_DATABASE_URL": OWNER_URL,
                   "TAXIMOBILE_DATABASE_URL": runtime_url.update_query_dict({"sslmode": "disable"}).render_as_string(hide_password=False),
                   "TAXIMOBILE_RUNTIME_DATABASE_PASSWORD": PASSWORD}
    connect = AsyncMock()
    monkeypatch.setattr(deployment.asyncpg, "connect", connect)
    with pytest.raises(DatabaseTLSConfigurationError, match="overrides are forbidden"):
        deployment.migrate(environment)
    connect.assert_not_awaited()


@pytest.mark.asyncio
async def test_existing_login_handles_escaped_password_without_logging_or_reencoding_it(monkeypatch):
    privileged, existing = owner(), runtime()
    connect = AsyncMock(side_effect=[privileged, existing])
    monkeypatch.setattr(deployment.asyncpg, "connect", connect)
    password = PASSWORD + "@/:#%'"
    await deployment.provision_runtime(OWNER_URL, password, grant=False, tls=DatabaseTLS())
    assert make_url(connect.await_args_list[1].args[0]).password == password
    privileged.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_first_role_creation_is_create_only_and_never_uses_alter(monkeypatch):
    privileged = owner()
    privileged.fetchval.side_effect = [False, "CREATE ROLE synthetic-fixture-only"]
    connect = AsyncMock(return_value=privileged)
    monkeypatch.setattr(deployment.asyncpg, "connect", connect)
    await deployment.provision_runtime(OWNER_URL, PASSWORD, grant=False, tls=DatabaseTLS())
    format_call = privileged.fetchval.await_args_list[1]
    assert format_call.args[1].startswith("CREATE ROLE taximobile_runtime LOGIN PASSWORD %L")
    assert format_call.args[2] == PASSWORD
    assert connect.await_count == 1
    privileged.execute.assert_awaited_once_with("CREATE ROLE synthetic-fixture-only")
