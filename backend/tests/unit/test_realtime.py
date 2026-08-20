import asyncio
from uuid import uuid4

from taximobile_api.core.realtime import EventHub


class RecordingSocket:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    async def accept(self) -> None:
        return None

    async def send_json(self, payload: dict[str, str]) -> None:
        self.messages.append(payload)


def test_event_hub_sends_only_refresh_hints_to_the_addressed_user() -> None:
    first_user = uuid4()
    second_user = uuid4()
    ride_id = uuid4()
    first_socket = RecordingSocket()
    second_socket = RecordingSocket()
    hub = EventHub()

    asyncio.run(hub.connect(first_user, first_socket))
    asyncio.run(hub.connect(second_user, second_socket))
    asyncio.run(hub.publish_ride_refresh(first_user, ride_id, "DRIVER_ASSIGNED"))

    assert first_socket.messages == [{"type": "DRIVER_ASSIGNED", "ride_id": str(ride_id)}]
    assert second_socket.messages == []
