"""Timeout rollback and recovery with real PostgreSQL and the Alembic CLI."""

import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from test_migration_serialization import cli
from test_mvp_lifecycle import require_integration_settings
from taximobile_api.operations.migration_lock import acquire_migration_lock
from taximobile_api.operations.migration_limits import (
    LOCK_TIMEOUT_ENV, STATEMENT_TIMEOUT_ENV, LOCK_TIMEOUT_MESSAGE, STATEMENT_TIMEOUT_MESSAGE,
    MigrationLimits, apply_migration_limits, migration_timeout_message,
)

pytestmark = pytest.mark.integration


def test_cli_ddl_lock_timeout_rolls_back_and_releases_migration_ownership():
    async def prove():
        settings = require_integration_settings()
        engine = create_async_engine(settings.database_url)
        try:
            result, output = await cli("downgrade", "20260903_0047")
            assert result == 0, output
            async with engine.begin() as blocker:
                # This ordinary writer lock conflicts with the index migration's
                # SHARE lock. Hold it until CLI completion; do not guess a sleep.
                await blocker.execute(text("LOCK TABLE rides IN ROW EXCLUSIVE MODE"))
                result, output = await cli("upgrade", "head", environment={
                    LOCK_TIMEOUT_ENV: "1", STATEMENT_TIMEOUT_ENV: "10",
                })
                assert result != 0 and LOCK_TIMEOUT_MESSAGE in output
                assert "Traceback" not in output and settings.database_url not in output
                assert await blocker.scalar(text("SELECT version_num FROM alembic_version")) == "20260903_0047"
                assert await blocker.scalar(text("SELECT count(*) FROM pg_indexes WHERE indexname='uq_rides_one_active_per_driver'")) == 0
                async with engine.begin() as next_owner:
                    await next_owner.run_sync(acquire_migration_lock)
            result, output = await cli("upgrade", "head")
            assert result == 0, output
        finally:
            await engine.dispose()
    asyncio.run(prove())


@pytest.mark.parametrize("offline", [False, True], ids=["online-config", "offline-sql"])
def test_statement_timeout_aborts_transaction_restores_settings_and_releases_lock(offline):
    async def prove():
        settings = require_integration_settings()
        engine = create_async_engine(settings.database_url)
        limits = MigrationLimits(1, 2)
        try:
            async with engine.connect() as connection:
                baseline = (await connection.execute(text(
                    "SELECT current_setting('lock_timeout'), current_setting('statement_timeout')"
                ))).one()
                await connection.rollback()
                with pytest.raises(DBAPIError) as failure:
                    async with connection.begin():
                        if offline:
                            for statement in limits.offline_sql():
                                await connection.execute(text(statement))
                        else:
                            await connection.run_sync(apply_migration_limits, limits)
                        await connection.run_sync(acquire_migration_lock)
                        await connection.execute(text("SELECT pg_sleep(3)"))
                assert migration_timeout_message(failure.value) == STATEMENT_TIMEOUT_MESSAGE
                restored = (await connection.execute(text(
                    "SELECT current_setting('lock_timeout'), current_setting('statement_timeout')"
                ))).one()
                assert restored == baseline
                await connection.rollback()
                async with engine.begin() as next_owner:
                    await next_owner.run_sync(acquire_migration_lock)
        finally:
            await engine.dispose()
    asyncio.run(prove())


def test_invalid_cli_limits_fail_before_database_access_without_echoing_value():
    async def prove():
        require_integration_settings()
        result, output = await cli("upgrade", "head", environment={
            LOCK_TIMEOUT_ENV: "private-pasted-value",
            "TAXIMOBILE_DATABASE_URL": "postgresql+asyncpg://invalid:invalid@127.0.0.1:1/invalid",
        })
        assert result != 0 and LOCK_TIMEOUT_ENV in output
        assert "private-pasted-value" not in output and "Traceback" not in output
        assert "Connection refused" not in output
    asyncio.run(prove())
