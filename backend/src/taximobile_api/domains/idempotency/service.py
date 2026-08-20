"""Transactional idempotency for commands whose response may be lost in transit."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.idempotency.models import IdempotencyRecord


class InvalidIdempotencyKey(ValueError):
    pass


class IdempotencyKeyReuse(ValueError):
    pass


class IdempotentReplay:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self.payload = payload


def request_fingerprint(payload: dict) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def validate_key(key: str | None) -> str:
    if key is None or not 16 <= len(key) <= 128:
        raise InvalidIdempotencyKey("Idempotency-Key must contain 16 to 128 characters.")
    return key


async def begin_command(
    session: AsyncSession,
    *,
    user_id,
    operation: str,
    key: str | None,
    payload: dict,
) -> IdempotencyRecord | IdempotentReplay:
    key = validate_key(key)
    fingerprint = request_fingerprint(payload)
    await session.execute(
        insert(IdempotencyRecord)
        .values(user_id=user_id, operation=operation, key=key, request_hash=fingerprint)
        .on_conflict_do_nothing(index_elements=["user_id", "operation", "key"])
    )
    record = await session.scalar(
        select(IdempotencyRecord)
        .where(
            IdempotencyRecord.user_id == user_id,
            IdempotencyRecord.operation == operation,
            IdempotencyRecord.key == key,
        )
        .with_for_update()
    )
    assert record is not None
    if record.request_hash != fingerprint:
        raise IdempotencyKeyReuse("Idempotency-Key cannot be reused for a different request.")
    if record.response_payload is not None and record.response_status is not None:
        return IdempotentReplay(record.response_status, record.response_payload)
    return record


async def finish_command(session: AsyncSession, record: IdempotencyRecord, *, status_code: int, payload: dict) -> None:
    record.response_status = status_code
    record.response_payload = payload
    record.completed_at = datetime.now(UTC)
    await session.flush()
