"""Database-per-test isolation for migrated PostGIS integration tests."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from os import environ, getenv
import re
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine


_SAFE_TEST_DATABASE = re.compile(r"^taximobile_ci[A-Za-z0-9_]*$")


@pytest.fixture(autouse=True)
def isolated_integration_database() -> Iterator[None]:
    """Clone the migrated empty test database for every integration test."""

    if getenv("TAXIMOBILE_RUN_INTEGRATION") != "1":
        yield
        return

    original_url_text = getenv("TAXIMOBILE_DATABASE_URL", "")
    original_url = make_url(original_url_text)
    template_database = original_url.database or ""
    if (
        getenv("TAXIMOBILE_ENV") != "test"
        or not _SAFE_TEST_DATABASE.fullmatch(template_database)
    ):
        pytest.fail(
            "Integration cloning requires TAXIMOBILE_ENV=test and an isolated "
            "taximobile_ci database."
        )

    clone_database = f"taximobile_ci_test_{uuid4().hex}"
    clone_url = original_url.set(database=clone_database)
    maintenance_url = original_url.set(database="postgres")

    async def create_clone() -> None:
        engine = create_async_engine(maintenance_url, isolation_level="AUTOCOMMIT")
        try:
            async with engine.connect() as connection:
                await connection.execute(
                    text(
                        f'CREATE DATABASE "{clone_database}" '
                        f'WITH TEMPLATE "{template_database}"'
                    )
                )
        finally:
            await engine.dispose()

    async def drop_clone() -> None:
        engine = create_async_engine(maintenance_url, isolation_level="AUTOCOMMIT")
        try:
            async with engine.connect() as connection:
                # Refuse new sessions first. Test clients use the clone owner;
                # terminate only those client backends rather than attempting to
                # kill transient superuser auxiliaries such as autovacuum.
                await connection.execute(text(
                    f'ALTER DATABASE "{clone_database}" WITH ALLOW_CONNECTIONS false'
                ))
                await connection.execute(
                    text(
                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                        "WHERE datname = :database_name AND pid <> pg_backend_pid() "
                        "AND usename = current_user AND backend_type = 'client backend'"
                    ),
                    {"database_name": clone_database},
                )
                deadline = asyncio.get_running_loop().time() + 10
                while True:
                    try:
                        await connection.execute(text(f'DROP DATABASE IF EXISTS "{clone_database}"'))
                        break
                    except DBAPIError as error:
                        sqlstate = (
                            getattr(error.orig, "sqlstate", None)
                            or getattr(error.orig, "pgcode", None)
                        )
                        if sqlstate != "55006" or asyncio.get_running_loop().time() >= deadline:
                            raise
                        # A database-owner test role cannot and should not kill a
                        # superuser auxiliary. With connections disabled it must
                        # drain; retry the drop without broadening privileges.
                        await connection.rollback()
                        await asyncio.sleep(.05)
        finally:
            await engine.dispose()

    try:
        asyncio.run(create_clone())
    except Exception as error:
        pytest.fail(
            "The integration role could not clone the migrated test database. "
            "Run through the guarded test entry point so it receives temporary "
            f"CREATEDB authority. ({type(error).__name__})"
        )

    environ["TAXIMOBILE_DATABASE_URL"] = clone_url.render_as_string(hide_password=False)
    try:
        yield
    finally:
        environ["TAXIMOBILE_DATABASE_URL"] = original_url_text
        asyncio.run(drop_clone())
