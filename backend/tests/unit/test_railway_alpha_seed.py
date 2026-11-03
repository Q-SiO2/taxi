from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from taximobile_api.operations.alpha_seed_target import (
    ALPHA_CONFIRMATION, ALPHA_DATABASE, ALPHA_ENVIRONMENT_ID, ALPHA_PROJECT_ID,
    AlphaSeedRefused, RailwayAlphaTarget, require_pristine_alpha,
)
from taximobile_api.operations.railway_alpha_seed import enroll_alpha_mfa, main
from taximobile_api.operations.ux_demo_seed import DemoSeedRefused, seed_demo


URL = f"postgresql+asyncpg://taximobile_runtime:private@alpha-postgis.railway.internal:5432/{ALPHA_DATABASE}"


def target():
    return RailwayAlphaTarget(ALPHA_PROJECT_ID, ALPHA_ENVIRONMENT_ID, "aabbccdd", "Secret-Aa9!" * 4)


def test_explicit_isolated_target_and_credentials_are_accepted():
    target().validate(environment="staging", database_url=URL, confirmation=ALPHA_CONFIRMATION)
    assert target().password not in repr(target())


@pytest.mark.parametrize("change", [
    {"environment": "production"}, {"environment": "development"}, {"confirmation": "CONFIRM_LOCAL_UX_DEMO_DATA"},
    {"database_url": URL.replace("alpha-postgis.railway.internal", "localhost")},
    {"database_url": URL.replace(ALPHA_DATABASE, "postgres")},
    {"database_url": URL.replace("taximobile_runtime", "taximobile_owner")},
    {"database_url": URL.replace(":5432", ":5433")},
    {"database_url": URL + "?host=another-database"}, {"database_url": URL + "#fragment"},
])
def test_other_environments_and_database_targets_are_refused(change):
    values = dict(environment="staging", database_url=URL, confirmation=ALPHA_CONFIRMATION) | change
    with pytest.raises(AlphaSeedRefused):
        target().validate(**values)


@pytest.mark.parametrize("change", [
    {"project_id": "another-project"}, {"environment_id": "another-environment"},
    {"suffix": "invalid"}, {"password": "short"}, {"password": "x" * 129},
])
def test_unrelated_identity_or_invalid_credentials_are_refused(change):
    with pytest.raises(AlphaSeedRefused):
        replace(target(), **change).validate(environment="staging", database_url=URL,
                                           confirmation=ALPHA_CONFIRMATION)


@pytest.mark.asyncio
async def test_accounts_are_locked_before_check_and_existing_accounts_refuse():
    session = SimpleNamespace(execute=AsyncMock(), scalar=AsyncMock(return_value="existing"))
    with pytest.raises(AlphaSeedRefused, match="never overwrites"):
        await require_pristine_alpha(session)
    statements = [str(call.args[0]) for call in session.execute.await_args_list]
    assert "pg_advisory_xact_lock" in statements[0]
    assert statements[1] == "LOCK TABLE users IN SHARE ROW EXCLUSIVE MODE"
    session.scalar.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("profile,identity", [("union_live", "wrong"), ("ux_review", ALPHA_PROJECT_ID)])
async def test_hosted_callable_refuses_before_connecting(monkeypatch, profile, identity):
    def forbidden_engine(*args, **kwargs):
        pytest.fail("Guard must run before any connection.")
    monkeypatch.setattr("taximobile_api.operations.ux_demo_seed.create_async_engine", forbidden_engine)
    with pytest.raises((AlphaSeedRefused, DemoSeedRefused)):
        await seed_demo(SimpleNamespace(environment="staging", database_url=URL),
                        confirmation=ALPHA_CONFIRMATION, profile=profile,
                        railway_target=replace(target(), project_id=identity))


@pytest.mark.parametrize("failure", [False, True])
def test_cli_never_prints_credentials_even_on_database_error(monkeypatch, capsys, failure):
    password = target().password
    monkeypatch.setattr("sys.argv", ["seed", "--confirm", ALPHA_CONFIRMATION])
    for name, value in {"RAILWAY_PROJECT_ID": ALPHA_PROJECT_ID, "RAILWAY_ENVIRONMENT_ID": ALPHA_ENVIRONMENT_ID,
                        "TAXIMOBILE_ALPHA_SEED_SUFFIX": target().suffix,
                        "TAXIMOBILE_ALPHA_SEED_PASSWORD": password}.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr("taximobile_api.operations.railway_alpha_seed.Settings.from_environment",
                        lambda: SimpleNamespace(environment="staging", database_url=URL))
    async def fake_seed(settings, **arguments):
        assert arguments["railway_target"].password == password
        if failure:
            raise RuntimeError("SQL parameters " + password + URL)
        return {"password": password}
    monkeypatch.setattr("taximobile_api.operations.railway_alpha_seed.seed_demo", fake_seed)
    assert main() == (2 if failure else 0)
    output = capsys.readouterr()
    assert password not in output.out + output.err
    assert URL not in output.out + output.err
    import os
    assert "TAXIMOBILE_ALPHA_SEED_PASSWORD" not in os.environ


@pytest.mark.asyncio
@pytest.mark.parametrize("secret,codes", [("short", []), ("A" * 32, ["2" * 20] * 10),
                                       ("A" * 32, ["0" * 20] * 10)])
async def test_invalid_private_mfa_material_refuses_before_database_preflight(monkeypatch, secret, codes):
    async def forbidden(*args, **kwargs):
        pytest.fail("Invalid enrollment must not access the database.")
    monkeypatch.setattr("taximobile_api.cli.enroll_operations_mfa.preflight", forbidden)
    with pytest.raises(AlphaSeedRefused):
        await enroll_alpha_mfa(SimpleNamespace(), target(), secret, codes)
