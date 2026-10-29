"""Actual PostgreSQL serialization and refusal, on disposable CI clones only."""

import asyncio
from os import getenv

import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from taximobile_api.core.config import Settings
from taximobile_api.domains.auth.models import User
from taximobile_api.operations.alpha_seed_target import AlphaSeedRefused, require_pristine_alpha


pytestmark = pytest.mark.integration


def test_concurrent_bootstraps_create_one_cohort_and_retries_preserve_it():
    if getenv("TAXIMOBILE_RUN_INTEGRATION") != "1":
        pytest.skip("Requires the guarded disposable PostGIS runner.")
    settings = Settings.from_environment()
    assert settings.environment == "test"
    assert (make_url(settings.database_url).database or "").startswith("taximobile_ci_test_")

    async def exercise():
        engine = create_async_engine(settings.database_url, pool_size=10, max_overflow=0)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        start = asyncio.Event()
        async def bootstrap(index):
            await start.wait()
            try:
                async with sessions() as session, session.begin():
                    await require_pristine_alpha(session)
                    # Overlap the competing jobs while the winner still owns
                    # its transaction, simulating account password hashing.
                    await asyncio.sleep(.05)
                    session.add(User(email=f"synthetic-lock-{index}@example.test",
                                     password_hash="synthetic-test-hash"))
                return "created"
            except AlphaSeedRefused:
                return "refused"
        try:
            tasks = [asyncio.create_task(bootstrap(index)) for index in range(10)]
            start.set()
            outcomes = await asyncio.gather(*tasks)
            assert outcomes.count("created") == 1
            assert outcomes.count("refused") == 9
            async with sessions() as session:
                assert await session.scalar(select(func.count()).select_from(User)) == 1
                before = await session.scalar(select(User.email))
            assert await bootstrap(11) == "refused"
            async with sessions() as session:
                assert await session.scalar(select(User.email)) == before
        finally:
            await engine.dispose()
    asyncio.run(exercise())
