import importlib.util
from pathlib import Path

import pytest

path = Path(__file__).resolve().parents[3] / "infra/scripts/run_database_tls_ci.py"
spec = importlib.util.spec_from_file_location("database_tls_ci_guard", path)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def valid():
    return {"GITHUB_ACTIONS": "true", "TAXIMOBILE_ENV": "test",
            "TAXIMOBILE_DATABASE_URL": "postgresql+asyncpg://taximobile:ci-only@127.0.0.1:5432/taximobile_ci"}


def test_tls_ci_runner_only_accepts_the_disposable_loopback_target():
    assert runner.validate_target(valid(), "a" * 64).database == "taximobile_ci"


@pytest.mark.parametrize("key,value", [("GITHUB_ACTIONS", "false"), ("TAXIMOBILE_ENV", "staging"),
    ("TAXIMOBILE_DATABASE_URL", "postgresql+asyncpg://user:secret@production.example/taximobile_ci"),
    ("TAXIMOBILE_DATABASE_URL", "postgresql+asyncpg://user:secret@localhost:5432/taximobile_production"),
    ("TAXIMOBILE_DATABASE_URL", "postgresql+asyncpg://user:secret@localhost:5433/taximobile_ci")])
def test_tls_ci_runner_refuses_other_environments_or_targets(key, value):
    environment = valid() | {key: value}
    with pytest.raises(ValueError):
        runner.validate_target(environment, "a" * 64)


def test_tls_ci_runner_requires_an_exact_container_and_quotes_config_literals():
    with pytest.raises(ValueError):
        runner.validate_target(valid(), "service-name")
    assert runner.literal("test'fixture") == "'test''fixture'"
