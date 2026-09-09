"""Real Alembic subprocesses and PostgreSQL transaction/disconnect lock release."""

import asyncio
from os import environ
from pathlib import Path
import subprocess
import sys

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from taximobile_api.operations.migration_lock import (
    MIGRATION_BUSY_MESSAGE, MigrationAlreadyRunning, OFFLINE_MIGRATION_LOCK_SQL,
    acquire_migration_lock,
)
from test_mvp_lifecycle import require_integration_settings


pytestmark = pytest.mark.integration
BACKEND = Path(__file__).resolve().parents[2]
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


async def cli(*arguments, environment=None):
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "alembic", *arguments, cwd=BACKEND,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        creationflags=NO_WINDOW,
        env=None if environment is None else {**environ, **environment},
    )
    try:
        output, _ = await asyncio.wait_for(process.communicate(), 30)
        return process.returncode, output.decode("utf-8", errors="replace")
    finally:
        if process.returncode is None:
            process.kill()
            await process.communicate()


@pytest.mark.parametrize("arguments", [("upgrade", "head"), ("downgrade", "20260903_0047")])
def test_actual_alembic_command_refuses_competing_owner_before_schema_changes(arguments):
    async def prove():
        settings = require_integration_settings()
        engine = create_async_engine(settings.database_url)
        try:
            async with engine.begin() as owner:
                await owner.run_sync(acquire_migration_lock)
                version = await owner.scalar(text("SELECT version_num FROM alembic_version"))
                result, output = await cli(*arguments)
                assert result != 0 and MIGRATION_BUSY_MESSAGE in output
                assert settings.database_url not in output
                assert await owner.scalar(text("SELECT version_num FROM alembic_version")) == version
                assert await owner.scalar(text("SELECT count(*) FROM pg_indexes WHERE indexname='uq_rides_one_active_per_driver'")) == 1
            result, output = await cli("upgrade", "head")
            assert result == 0, output
        finally:
            await engine.dispose()
    asyncio.run(prove())


@pytest.mark.parametrize("finish", ["commit", "rollback", "disconnect"])
def test_lock_is_released_with_owning_transaction_or_connection(finish):
    async def prove():
        settings = require_integration_settings()
        engine = create_async_engine(settings.database_url)
        try:
            async with engine.connect() as owner:
                transaction = await owner.begin()
                await owner.run_sync(acquire_migration_lock)
                async with engine.begin() as contender:
                    with pytest.raises(MigrationAlreadyRunning):
                        await contender.run_sync(acquire_migration_lock)
                if finish == "commit":
                    await transaction.commit()
                elif finish == "rollback":
                    await transaction.rollback()
                else:
                    await owner.invalidate()
                    await transaction.rollback()
                deadline = asyncio.get_running_loop().time() + 5
                while True:
                    try:
                        async with engine.begin() as next_owner:
                            await next_owner.run_sync(acquire_migration_lock)
                        break
                    except MigrationAlreadyRunning:
                        assert asyncio.get_running_loop().time() < deadline, "Disconnected owner retained lock"
                        await asyncio.sleep(0.02)
        finally:
            await engine.dispose()
    asyncio.run(prove())


def test_offline_execution_guard_uses_same_lock_and_aborts_before_ddl():
    async def prove():
        settings = require_integration_settings()
        engine = create_async_engine(settings.database_url)
        try:
            async with engine.begin() as owner:
                await owner.run_sync(acquire_migration_lock)
                with pytest.raises(DBAPIError, match="Another TaxiMobile migration"):
                    async with engine.begin() as script:
                        await script.execute(text(OFFLINE_MIGRATION_LOCK_SQL))
                        pytest.fail("Offline guard allowed a competing migrator")
            async with engine.begin() as script:
                await script.execute(text(OFFLINE_MIGRATION_LOCK_SQL))
        finally:
            await engine.dispose()
    asyncio.run(prove())


def test_terminated_migrator_process_does_not_leave_a_stale_lock():
    async def prove():
        require_integration_settings()
        # The child holds the exact application lock in a real DB transaction.
        # Killing this synthetic child proves disconnect release, not merely
        # Python context-manager cleanup or a filesystem lock-file timeout.
        child_source = """
import asyncio, os
from sqlalchemy.ext.asyncio import create_async_engine
from taximobile_api.operations.migration_lock import acquire_migration_lock
async def main():
    engine = create_async_engine(os.environ['TAXIMOBILE_DATABASE_URL'])
    async with engine.begin() as connection:
        await connection.run_sync(acquire_migration_lock)
        print('MIGRATION_LOCK_HELD', flush=True)
        await asyncio.Event().wait()
asyncio.run(main())
"""
        child = await asyncio.create_subprocess_exec(sys.executable, "-c", child_source,
            cwd=BACKEND, env=dict(environ), stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE, creationflags=NO_WINDOW)
        try:
            signal = await asyncio.wait_for(child.stdout.readline(), 20)
            assert signal.strip() == b"MIGRATION_LOCK_HELD"
            result, output = await cli("upgrade", "head")
            assert result != 0 and MIGRATION_BUSY_MESSAGE in output
            child.kill()
            await asyncio.wait_for(child.communicate(), 10)
            deadline = asyncio.get_running_loop().time() + 10
            while True:
                result, output = await cli("upgrade", "head")
                if result == 0:
                    break
                assert MIGRATION_BUSY_MESSAGE in output
                assert asyncio.get_running_loop().time() < deadline, "Terminated process retained migration lock"
        finally:
            if child.returncode is None:
                child.kill()
                await child.communicate()
    asyncio.run(prove())
