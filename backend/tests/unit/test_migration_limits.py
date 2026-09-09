from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import DBAPIError

from taximobile_api.operations.migration_limits import (
    LOCK_TIMEOUT_ENV, STATEMENT_TIMEOUT_ENV, LOCK_TIMEOUT_MESSAGE, STATEMENT_TIMEOUT_MESSAGE,
    MigrationLimits, apply_migration_limits, migration_timeout_message,
)


def test_defaults_and_explicit_limits_are_bounded_seconds():
    assert MigrationLimits.from_environment({}) == MigrationLimits(5, 300)
    assert MigrationLimits.from_environment({LOCK_TIMEOUT_ENV: "120", STATEMENT_TIMEOUT_ENV: "7200"}) == MigrationLimits(120, 7200)


@pytest.mark.parametrize("value", ["", "0", "-1", "+2", "1.5", " 5", "１２", "121", "999999", "private-pasted-value"])
def test_invalid_lock_configuration_never_echoes_input(value):
    with pytest.raises(ValueError) as error:
        MigrationLimits.from_environment({LOCK_TIMEOUT_ENV: value})
    assert LOCK_TIMEOUT_ENV in str(error.value)
    assert "private-pasted-value" not in str(error.value)


@pytest.mark.parametrize("value", [0, 5, 7201, True, 2.5])
def test_statement_limit_cannot_disable_or_preempt_lock_limit(value):
    with pytest.raises(ValueError):
        MigrationLimits(statement_seconds=value)


def test_online_limits_are_transaction_local_and_parameterized():
    connection = MagicMock()
    connection.in_transaction.return_value = True
    apply_migration_limits(connection, MigrationLimits(2, 20))
    statement, parameters = connection.execute.call_args.args
    assert "set_config('lock_timeout', :lock_limit, true)" in str(statement)
    assert "set_config('statement_timeout', :statement_limit, true)" in str(statement)
    assert parameters == {"lock_limit": "2000ms", "statement_limit": "20000ms"}
    connection.in_transaction.return_value = False
    with pytest.raises(RuntimeError, match="outer migration transaction"):
        apply_migration_limits(connection, MigrationLimits())


def test_offline_statements_have_same_limits():
    assert MigrationLimits(2, 20).offline_sql() == (
        "SET LOCAL lock_timeout = '2000ms'", "SET LOCAL statement_timeout = '20000ms'",
    )


@pytest.mark.parametrize("state,expected", [("55P03", LOCK_TIMEOUT_MESSAGE), ("57014", STATEMENT_TIMEOUT_MESSAGE), ("23505", None)])
def test_only_known_cancellation_states_receive_fixed_diagnostics(state, expected):
    error = DBAPIError("private statement", {"private": "value"}, SimpleNamespace(sqlstate=state))
    assert migration_timeout_message(error) == expected
