"""Async SQLAlchemy session construction."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from taximobile_api.core.config import Settings
from taximobile_api.db.pool import InstrumentedAsyncAdaptedQueuePool


def create_session_factory(settings: Settings) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_pool_max_overflow,
        pool_timeout=settings.database_pool_timeout_seconds,
        poolclass=InstrumentedAsyncAdaptedQueuePool,
    )
    return async_sessionmaker(engine, expire_on_commit=False)


async def session_scope(factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with factory() as session:
        yield session
