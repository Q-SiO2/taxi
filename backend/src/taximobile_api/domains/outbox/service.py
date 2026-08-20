"""Outbox writes happen within the originating business transaction."""

from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.outbox.models import OutboxEvent


async def enqueue(database_session: AsyncSession, *, topic: str, payload: dict) -> OutboxEvent:
    event = OutboxEvent(topic=topic, payload=payload)
    database_session.add(event)
    await database_session.flush()
    return event
