"""Validated per-statement migration limits; never disable timeouts with zero."""

from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError


LOCK_TIMEOUT_ENV = "TAXIMOBILE_MIGRATION_LOCK_TIMEOUT_SECONDS"
STATEMENT_TIMEOUT_ENV = "TAXIMOBILE_MIGRATION_STATEMENT_TIMEOUT_SECONDS"
LOCK_TIMEOUT_MESSAGE = (
    "Migration database lock wait exceeded its limit. No migration was committed. "
    "Review blocking transactions and the maintenance window before retrying."
)
STATEMENT_TIMEOUT_MESSAGE = (
    "Migration statement was cancelled or exceeded its time limit. No migration was committed. "
    "Review database load and the migration plan before retrying."
)


@dataclass(frozen=True)
class MigrationLimits:
    lock_seconds: int = 5
    statement_seconds: int = 300

    def __post_init__(self):
        for name, value, maximum in (
            (LOCK_TIMEOUT_ENV, self.lock_seconds, 120),
            (STATEMENT_TIMEOUT_ENV, self.statement_seconds, 7200),
        ):
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError(f"{name} must be an integer from 1 to {maximum}.")
        if self.statement_seconds <= self.lock_seconds:
            raise ValueError(f"{STATEMENT_TIMEOUT_ENV} must exceed {LOCK_TIMEOUT_ENV}.")

    @classmethod
    def from_environment(cls, environment: Mapping[str, str]):
        values = []
        for name, default in ((LOCK_TIMEOUT_ENV, 5), (STATEMENT_TIMEOUT_ENV, 300)):
            value = environment.get(name)
            if value is None:
                values.append(default)
            elif not value.isascii() or not value.isdecimal() or len(value) > 5:
                # Never echo a pasted secret or arbitrary value into deployment logs.
                raise ValueError(f"{name} must contain bounded whole seconds.")
            else:
                values.append(int(value))
        return cls(*values)

    def offline_sql(self) -> tuple[str, str]:
        return (
            f"SET LOCAL lock_timeout = '{self.lock_seconds * 1000}ms'",
            f"SET LOCAL statement_timeout = '{self.statement_seconds * 1000}ms'",
        )


def apply_migration_limits(connection: Connection, limits: MigrationLimits) -> None:
    if not connection.in_transaction():
        raise RuntimeError("Migration limits require the outer migration transaction.")
    connection.execute(text(
        "SELECT set_config('lock_timeout', :lock_limit, true), "
        "set_config('statement_timeout', :statement_limit, true)"
    ), {"lock_limit": f"{limits.lock_seconds * 1000}ms", "statement_limit": f"{limits.statement_seconds * 1000}ms"})


def migration_timeout_message(error: DBAPIError) -> str | None:
    state = getattr(error.orig, "sqlstate", None) or getattr(error.orig, "pgcode", None)
    if state == "55P03":
        return LOCK_TIMEOUT_MESSAGE
    if state == "57014":
        return STATEMENT_TIMEOUT_MESSAGE
    return None
