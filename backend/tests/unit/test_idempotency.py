import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from taximobile_api.domains.idempotency.models import IdempotencyRecord
from taximobile_api.domains.idempotency.service import (
    IdempotencyKeyReuse,
    IdempotentReplay,
    InvalidIdempotencyKey,
    begin_command,
    request_fingerprint,
    validate_key,
)


def test_request_fingerprint_is_stable_across_dictionary_order() -> None:
    assert request_fingerprint({"ride_id": "ride", "reason": "cancel"}) == request_fingerprint(
        {"reason": "cancel", "ride_id": "ride"}
    )


@pytest.mark.parametrize("key", [None, "short", "x" * 129])
def test_idempotency_key_length_is_bounded(key: str | None) -> None:
    with pytest.raises(InvalidIdempotencyKey):
        validate_key(key)


def test_completed_matching_command_replays_the_original_response() -> None:
    payload = {"ride_id": "ride", "reason": "cancel"}
    record = IdempotencyRecord(
        user_id=uuid4(),
        operation="ride.cancel",
        key="a" * 16,
        request_hash=request_fingerprint(payload),
        response_status=200,
        response_payload={"id": "ride", "status": "CANCELLED"},
    )
    session = AsyncMock()
    session.scalar.return_value = record

    result = asyncio.run(
        begin_command(
            session,
            user_id=record.user_id,
            operation=record.operation,
            key=record.key,
            payload=payload,
        )
    )

    assert isinstance(result, IdempotentReplay)
    assert result.payload == record.response_payload


def test_reusing_a_key_for_a_different_command_payload_is_rejected() -> None:
    record = IdempotencyRecord(
        user_id=uuid4(),
        operation="ride.cancel",
        key="a" * 16,
        request_hash=request_fingerprint({"ride_id": "ride", "reason": "first"}),
    )
    session = AsyncMock()
    session.scalar.return_value = record

    with pytest.raises(IdempotencyKeyReuse):
        asyncio.run(
            begin_command(
                session,
                user_id=record.user_id,
                operation=record.operation,
                key=record.key,
                payload={"ride_id": "ride", "reason": "second"},
            )
        )
