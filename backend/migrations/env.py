import asyncio
from os import environ, getenv

from alembic import context
from alembic.util import CommandError
from sqlalchemy import pool
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_engine_from_config

from taximobile_api.db.base import Base
from taximobile_api.operations.migration_lock import (
    MigrationAlreadyRunning, OFFLINE_MIGRATION_LOCK_SQL, acquire_migration_lock,
)
from taximobile_api.operations.migration_limits import (
    MigrationLimits, apply_migration_limits, migration_timeout_message,
)

config = context.config
# Deployment configuration is authoritative. The checked-in URL is only the
# isolated local-development default; Compose, CI, staging, and production must
# migrate the exact database supplied to the API process.
database_url = getenv("TAXIMOBILE_DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
target_metadata = Base.metadata
try:
    migration_limits = MigrationLimits.from_environment(environ)
except ValueError as error:
    raise CommandError(str(error)) from None


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        for statement in migration_limits.offline_sql():
            context.execute(statement)
        context.execute(OFFLINE_MIGRATION_LOCK_SQL)
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        try:
            apply_migration_limits(connection, migration_limits)
            acquire_migration_lock(connection)
            context.run_migrations()
        except MigrationAlreadyRunning as error:
            # Alembic prints a fixed actionable message, not a connection URL
            # or database exception containing deployment internals.
            raise CommandError(str(error)) from None
        except DBAPIError as error:
            message = migration_timeout_message(error)
            if message is not None:
                raise CommandError(message) from None
            raise


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    try:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
