import ast
from pathlib import Path

import pytest

from taximobile_api.operations.migration_lock import (
    MIGRATION_BUSY_MESSAGE, MIGRATION_LOCK_NAMESPACE, MIGRATION_LOCK_RESOURCE,
    MigrationAlreadyRunning, OFFLINE_MIGRATION_LOCK_SQL, acquire_migration_lock,
)


class Connection:
    def __init__(self, acquired=True, in_transaction=True):
        self.acquired = acquired
        self.transaction = in_transaction
        self.calls = []

    def in_transaction(self):
        return self.transaction

    def scalar(self, statement, parameters):
        self.calls.append((str(statement), parameters))
        return self.acquired


def test_lock_is_parameterized_fail_fast_and_transaction_scoped():
    connection = Connection()
    acquire_migration_lock(connection)
    assert connection.calls == [("SELECT pg_try_advisory_xact_lock(:namespace, :resource)",
        {"namespace": MIGRATION_LOCK_NAMESPACE, "resource": MIGRATION_LOCK_RESOURCE})]


@pytest.mark.parametrize("result", [False, None])
def test_busy_or_unknown_result_refuses_migration(result):
    with pytest.raises(MigrationAlreadyRunning) as error:
        acquire_migration_lock(Connection(acquired=result))
    assert str(error.value) == MIGRATION_BUSY_MESSAGE


def test_lock_cannot_be_acquired_outside_migration_transaction():
    connection = Connection(in_transaction=False)
    with pytest.raises(RuntimeError, match="outer migration transaction"):
        acquire_migration_lock(connection)
    assert not connection.calls


def test_offline_sql_uses_same_namespace_and_diagnostic():
    assert f"pg_try_advisory_xact_lock({MIGRATION_LOCK_NAMESPACE}, {MIGRATION_LOCK_RESOURCE})" in OFFLINE_MIGRATION_LOCK_SQL
    assert MIGRATION_BUSY_MESSAGE in OFFLINE_MIGRATION_LOCK_SQL


def test_migration_chain_cannot_silently_release_the_transaction_lock():
    migrations = Path(__file__).resolve().parents[2] / "migrations"
    for path in migrations.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {"commit", "autocommit_block"}, (
                    f"{path.name}: transaction-breaking migrations require a new locking design"
                )
            if isinstance(node, ast.keyword):
                assert node.arg != "transaction_per_migration", (
                    "Per-migration transactions would release the chain-wide advisory lock"
                )
