import pytest
from types import SimpleNamespace
from uuid import uuid4
import json

from taximobile_api.operations.ux_demo_seed import (
    DEMO_CONFIRMATION,
    DemoSeedRefused,
    seed_demo,
    main,
    validate_demo_target,
)


def test_demo_seed_accepts_only_confirmed_loopback_development_database() -> None:
    validate_demo_target(
        environment="development",
        database_url="postgresql+asyncpg://taxi:local@127.0.0.1:5432/taximobile",
        confirmation=DEMO_CONFIRMATION,
    )


@pytest.mark.parametrize(
    ("environment", "database_url", "confirmation"),
    [
        ("production", "postgresql+asyncpg://taxi:secret@127.0.0.1/taximobile", DEMO_CONFIRMATION),
        ("development", "postgresql+asyncpg://taxi:secret@database.internal/taximobile", DEMO_CONFIRMATION),
        ("development", "postgresql+asyncpg://taxi:secret@127.0.0.1/postgres", DEMO_CONFIRMATION),
        ("development", "postgresql+asyncpg://taxi:secret@127.0.0.1/taximobile", "wrong"),
        ("test", "postgresql+asyncpg://taxi:secret@127.0.0.1/taximobile_ci", DEMO_CONFIRMATION),
        ("development", "https://127.0.0.1/taximobile", DEMO_CONFIRMATION),
        ("development", "postgresql+asyncpg://taxi:secret@127.0.0.1/template1", DEMO_CONFIRMATION),
    ],
)
def test_demo_seed_refuses_unsafe_or_unconfirmed_target(
    environment: str,
    database_url: str,
    confirmation: str,
) -> None:
    with pytest.raises(DemoSeedRefused):
        validate_demo_target(
            environment=environment,
            database_url=database_url,
            confirmation=confirmation,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("profile", ["ux_review", "union_live"])
async def test_callable_cannot_bypass_the_cli_local_guard(monkeypatch, profile) -> None:
    def forbidden_engine(*args, **kwargs):
        pytest.fail("Unsafe demo target must be rejected before connecting.")

    monkeypatch.setattr(
        "taximobile_api.operations.ux_demo_seed.create_async_engine", forbidden_engine,
    )
    with pytest.raises(DemoSeedRefused):
        await seed_demo(
            SimpleNamespace(environment="production", database_url="postgresql://localhost/demo"),
            confirmation=DEMO_CONFIRMATION,
            profile=profile,
        )


@pytest.mark.asyncio
async def test_unknown_profile_is_rejected_before_connecting(monkeypatch) -> None:
    def forbidden_engine(*args, **kwargs):
        pytest.fail("Unknown demo profile must be rejected before connecting.")

    monkeypatch.setattr(
        "taximobile_api.operations.ux_demo_seed.create_async_engine", forbidden_engine,
    )
    with pytest.raises(ValueError):
        await seed_demo(
            SimpleNamespace(environment="development", database_url="postgresql://localhost/demo"),
            confirmation=DEMO_CONFIRMATION,
            profile="unknown",
        )


def cli_environment(monkeypatch, output=None):
    arguments = ["seed", "--confirm", DEMO_CONFIRMATION, "--profile", "union_live"]
    if output is not None:
        arguments += ["--output", str(output)]
    monkeypatch.setattr("sys.argv", arguments)
    monkeypatch.setattr(
        "taximobile_api.operations.ux_demo_seed.Settings.from_environment",
        lambda: SimpleNamespace(
            environment="development", database_url="postgresql://localhost/demo",
        ),
    )


def test_union_cli_requires_private_output(monkeypatch, capsys):
    cli_environment(monkeypatch)
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    assert "requires --output" in capsys.readouterr().err


@pytest.mark.parametrize("occupied", [True, False])
def test_credentials_destination_refused_before_database_mutation(monkeypatch, tmp_path, occupied):
    output = tmp_path / "accounts.json" if occupied else tmp_path / "missing" / "accounts.json"
    if occupied:
        output.write_text("previous cohort", encoding="utf-8")
    cli_environment(monkeypatch, output)

    async def forbidden_seed(*args, **kwargs):
        pytest.fail("Invalid credentials destination must not mutate the database.")

    monkeypatch.setattr("taximobile_api.operations.ux_demo_seed.seed_demo", forbidden_seed)
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    if occupied:
        assert output.read_text(encoding="utf-8") == "previous cohort"


def test_union_credentials_go_to_exclusive_file_not_stdout(monkeypatch, tmp_path, capsys):
    output = tmp_path / "accounts.json"
    cli_environment(monkeypatch, output)
    sentinel = uuid4().hex

    async def fake_seed(settings, *, confirmation, profile):
        assert confirmation == DEMO_CONFIRMATION
        assert profile == "union_live"
        return {"password": sentinel, "accounts": {}}

    monkeypatch.setattr("taximobile_api.operations.ux_demo_seed.seed_demo", fake_seed)
    assert main() == 0
    assert json.loads(output.read_text(encoding="utf-8"))["password"] == sentinel
    captured = capsys.readouterr()
    assert sentinel not in captured.out + captured.err
    assert "credentials saved locally" in captured.out
