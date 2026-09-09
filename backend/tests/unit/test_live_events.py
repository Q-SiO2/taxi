import asyncio
import json
from uuid import uuid4

import pytest

from taximobile_api.core.live_events import (
    LiveEventHint,
    PostgresLiveEventListener,
    decode_hint,
    encode_hint,
)
from taximobile_api.core.realtime import EventHub


class RecordingSocket:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    async def accept(self) -> None:
        return None

    async def send_json(self, payload: dict[str, str]) -> None:
        self.messages.append(payload)


def test_live_event_payload_is_versioned_minimized_and_round_trips() -> None:
    hint = LiveEventHint(user_id=uuid4(), ride_id=uuid4(), event_type="DRIVER_ASSIGNED")

    payload = encode_hint(hint)

    assert decode_hint(payload) == hint
    assert set(json.loads(payload)) == {"version", "user_id", "ride_id", "type"}


def test_unmatched_refresh_is_an_explicit_allowlisted_minimal_hint() -> None:
    hint = LiveEventHint(user_id=uuid4(), ride_id=uuid4(), event_type="RIDE_UNMATCHED")

    assert decode_hint(encode_hint(hint)) == hint


def test_coordination_refresh_is_an_explicit_allowlisted_minimal_hint() -> None:
    hint = LiveEventHint(
        user_id=uuid4(),
        ride_id=uuid4(),
        event_type="RIDE_COORDINATION_MESSAGE",
    )

    payload = encode_hint(hint)

    assert decode_hint(payload) == hint
    assert set(json.loads(payload)) == {"version", "user_id", "ride_id", "type"}


@pytest.mark.parametrize(
    "payload",
    [
        "not-json",
        json.dumps({"version": 1, "user_id": str(uuid4()), "ride_id": str(uuid4()), "type": "PRIVATE"}),
        json.dumps(
            {
                "version": 1,
                "user_id": str(uuid4()),
                "ride_id": str(uuid4()),
                "type": "DRIVER_ASSIGNED",
                "passenger_email": "private@example.com",
            }
        ),
    ],
)
def test_live_event_payload_rejects_unknown_or_private_fields(payload: str) -> None:
    with pytest.raises(ValueError):
        decode_hint(payload)


def test_listener_dispatches_only_to_the_addressed_local_user() -> None:
    first_user = uuid4()
    second_user = uuid4()
    ride_id = uuid4()
    first_socket = RecordingSocket()
    second_socket = RecordingSocket()
    hub = EventHub()
    listener = PostgresLiveEventListener("postgresql+asyncpg://user:password@database/taxi", hub)

    async def scenario() -> None:
        await hub.connect(first_user, first_socket)
        await hub.connect(second_user, second_socket)
        await listener.dispatch_payload(
            encode_hint(LiveEventHint(first_user, ride_id, "RIDE_CANCELLED"))
        )

    asyncio.run(scenario())

    assert first_socket.messages == [{"type": "RIDE_CANCELLED", "ride_id": str(ride_id)}]
    assert second_socket.messages == []
