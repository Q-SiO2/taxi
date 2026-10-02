import asyncio
from contextlib import suppress
from datetime import UTC, datetime, timedelta
import json
import logging
from uuid import uuid4

import pytest

from taximobile_api.core.live_events import (
    LiveEventHint,
    PostgresLiveEventListener,
    LIVE_EVENT_CHANNEL,
    decode_hint,
    encode_hint,
)
from taximobile_api.core.realtime import EventHub
from taximobile_api.domains.auth.security import VerifiedAccessToken


async def permit_transport_fixture(_):
    """Transport tests isolate fanout, not real database session authority."""
    return True


def transport_identity(user_id):
    return VerifiedAccessToken(user_id, uuid4(), datetime.now(UTC) + timedelta(minutes=10))


class RecordingSocket:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    async def accept(self) -> None:
        return None

    async def send_json(self, payload: dict[str, str]) -> None:
        self.messages.append(payload)

    async def close(self, *, code) -> None:
        pass


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
    hub = EventHub(permit_transport_fixture)
    listener = PostgresLiveEventListener("postgresql+asyncpg://user:password@database/taxi", hub)

    async def scenario() -> None:
        try:
            await hub.connect(transport_identity(first_user), first_socket)
            await hub.connect(transport_identity(second_user), second_socket)
            await listener.dispatch_payload(
                encode_hint(LiveEventHint(first_user, ride_id, "RIDE_CANCELLED"))
            )
        finally:
            await hub.aclose()

    asyncio.run(scenario())

    assert first_socket.messages == [{"type": "RIDE_CANCELLED", "ride_id": str(ride_id)}]
    assert second_socket.messages == []


class ControlledConnection:
    """Driver-shaped connection with observable registration/termination races."""

    def __init__(self, *, registration_failure=False, stalled_registration=False, closed_on_registration=False,
                 probe_failure=False, stalled_probe=False, cleanup_failure=False) -> None:
        self.closed = False
        self.registration_failure = registration_failure
        self.stalled_registration = stalled_registration
        self.closed_on_registration = closed_on_registration
        self.probe_failure = probe_failure
        self.stalled_probe = stalled_probe
        self.cleanup_failure = cleanup_failure
        self.registered = asyncio.Event()
        self.probed = asyncio.Event()
        self.termination_callbacks = set()
        self.notification_callback = None
        self.saved_termination_callback = None
        self.close_count = 0
        self.terminate_count = 0

    def is_closed(self):
        return self.closed

    def add_termination_listener(self, callback):
        self.termination_callbacks.add(callback)
        self.saved_termination_callback = callback

    def remove_termination_listener(self, callback):
        self.termination_callbacks.discard(callback)

    async def add_listener(self, channel, callback):
        assert channel == LIVE_EVENT_CHANNEL
        self.notification_callback = callback
        if self.stalled_registration:
            await asyncio.Event().wait()
        if self.registration_failure:
            raise RuntimeError("private connection detail")
        if self.closed_on_registration:
            self.terminate()
        self.registered.set()

    async def remove_listener(self, channel, callback):
        assert channel == LIVE_EVENT_CHANNEL
        if self.cleanup_failure:
            raise RuntimeError("private cleanup detail")
        self.notification_callback = None

    async def execute(self, statement, *, timeout):
        assert statement == "SELECT 1" and timeout > 0
        self.probed.set()
        if self.stalled_probe:
            await asyncio.Event().wait()
        if self.probe_failure:
            raise RuntimeError("private probe detail")

    async def close(self, *, timeout):
        self.close_count += 1
        if self.cleanup_failure:
            await asyncio.Event().wait()
        self.closed = True

    def terminate(self):
        self.terminate_count += 1
        self.closed = True
        for callback in tuple(self.termination_callbacks):
            callback(self)


@pytest.fixture
def live_event_logs(caplog):
    # Application logging deliberately does not propagate to the root logger.
    # Observe its real records without changing production logging policy.
    logger = logging.getLogger("taximobile_api")
    logger.addHandler(caplog.handler)
    try:
        yield caplog
    finally:
        logger.removeHandler(caplog.handler)


def controlled_listener(monkeypatch, connections, *, hub=None):
    calls = []

    async def connect(_dsn, **options):
        assert options == {"timeout": 0.1, "command_timeout": 0.03}
        calls.append(len(calls))
        return connections[len(calls) - 1]

    monkeypatch.setattr("taximobile_api.core.live_events.asyncpg.connect", connect)
    return PostgresLiveEventListener(
        "postgresql+asyncpg://user:password@database/taxi", hub or EventHub(permit_transport_fixture),
        reconnect_seconds=0.01, heartbeat_seconds=0.02,
        operation_timeout_seconds=0.03, connect_timeout_seconds=0.1,
    ), calls


async def stop_listener(task):
    task.cancel()
    with suppress(asyncio.CancelledError):
        await asyncio.wait_for(task, timeout=1)


@pytest.mark.asyncio
async def test_established_disconnect_clears_readiness_and_restores_recipient_delivery(monkeypatch):
    first, second = ControlledConnection(), ControlledConnection()
    hub = EventHub(permit_transport_fixture)
    user_id, other_user_id, ride_id = uuid4(), uuid4(), uuid4()
    recipient, stranger = RecordingSocket(), RecordingSocket()
    await hub.connect(transport_identity(user_id), recipient)
    await hub.connect(transport_identity(other_user_id), stranger)
    listener, calls = controlled_listener(monkeypatch, [first, second], hub=hub)
    task = asyncio.create_task(listener.run())
    try:
        await listener.wait_until_ready(1)
        original_notification_callback = first.notification_callback
        first.terminate()
        assert not listener.is_ready
        await asyncio.wait_for(second.registered.wait(), timeout=1)
        await listener.wait_until_ready(1)
        first.saved_termination_callback(first)  # queued old callback
        assert listener.is_ready
        stale = encode_hint(LiveEventHint(user_id, ride_id, "RIDE_CANCELLED"))
        original_notification_callback(first, 1, LIVE_EVENT_CHANNEL, stale)
        assert not listener._dispatch_tasks
        second.notification_callback(second, 1, LIVE_EVENT_CHANNEL, stale)
        await asyncio.gather(*tuple(listener._dispatch_tasks))
        assert recipient.messages == [{"type": "RIDE_CANCELLED", "ride_id": str(ride_id)}]
        assert stranger.messages == []
        assert len(calls) == 2
    finally:
        await stop_listener(task)
        await hub.aclose()
    assert not listener.is_ready and second.closed
    assert not first.termination_callbacks and not second.termination_callbacks


@pytest.mark.parametrize("failure", ["registration_failure", "stalled_registration", "closed_on_registration",
                                     "probe_failure", "stalled_probe"])
@pytest.mark.asyncio
async def test_registration_or_half_open_failure_reconnects_without_private_errors(monkeypatch, live_event_logs, failure):
    first = ControlledConnection(**{failure: True})
    second = ControlledConnection()
    listener, calls = controlled_listener(monkeypatch, [first, second])
    task = asyncio.create_task(listener.run())
    try:
        await asyncio.wait_for(second.registered.wait(), timeout=1)
        await listener.wait_until_ready(1)
        assert len(calls) == 2 and first.closed
        assert "live_event_listener_unavailable" in live_event_logs.text
        assert "private" not in live_event_logs.text and "password" not in live_event_logs.text
    finally:
        await stop_listener(task)


@pytest.mark.asyncio
async def test_healthy_listener_probe_keeps_registration_and_readiness(monkeypatch):
    connection = ControlledConnection()
    listener, calls = controlled_listener(monkeypatch, [connection])
    task = asyncio.create_task(listener.run())
    try:
        await listener.wait_until_ready(1)
        await asyncio.wait_for(connection.probed.wait(), timeout=1)
        assert listener.is_ready and len(calls) == 1
        assert connection.notification_callback is not None
    finally:
        await stop_listener(task)
    assert connection.closed and not listener.is_ready


@pytest.mark.asyncio
async def test_listener_cancellation_bounds_failed_cleanup_and_releases_connection(monkeypatch, live_event_logs):
    connection = ControlledConnection(cleanup_failure=True)
    listener, _ = controlled_listener(monkeypatch, [connection])
    task = asyncio.create_task(listener.run())
    await listener.wait_until_ready(1)
    await stop_listener(task)
    assert not listener.is_ready and connection.closed
    assert connection.close_count == 1 and connection.terminate_count == 1
    assert not connection.termination_callbacks
    assert "live_event_listener_cleanup_failed" in live_event_logs.text
    assert "private" not in live_event_logs.text


@pytest.mark.asyncio
async def test_listener_shutdown_cancels_stalled_hint_dispatch(monkeypatch):
    sending = asyncio.Event()

    class StalledSocket(RecordingSocket):
        async def send_json(self, payload):
            sending.set()
            await asyncio.Event().wait()

    hub = EventHub(permit_transport_fixture)
    user_id = uuid4()
    await hub.connect(transport_identity(user_id), StalledSocket())
    connection = ControlledConnection()
    listener, _ = controlled_listener(monkeypatch, [connection], hub=hub)
    task = asyncio.create_task(listener.run())
    try:
        await listener.wait_until_ready(1)
        connection.notification_callback(connection, 1, LIVE_EVENT_CHANNEL,
            encode_hint(LiveEventHint(user_id, uuid4(), "RIDE_CANCELLED")))
        await asyncio.wait_for(sending.wait(), timeout=1)
        await stop_listener(task)
        assert not listener._dispatch_tasks and connection.closed
    finally:
        if not task.done():
            await stop_listener(task)
        await hub.aclose()


@pytest.mark.asyncio
async def test_listener_has_single_process_owner_and_failed_start_remains_unready(monkeypatch):
    attempts = asyncio.Event()

    async def unavailable(*_, **__):
        attempts.set()
        raise ConnectionError("private unavailable detail")

    monkeypatch.setattr("taximobile_api.core.live_events.asyncpg.connect", unavailable)
    listener = PostgresLiveEventListener("postgresql://user:password@database/taxi", EventHub(permit_transport_fixture))
    task = asyncio.create_task(listener.run())
    try:
        await asyncio.wait_for(attempts.wait(), timeout=1)
        assert not listener.is_ready
        with pytest.raises(RuntimeError, match="process owner"):
            await listener.run()
        with pytest.raises(TimeoutError):
            await listener.wait_until_ready(0.01)
    finally:
        await stop_listener(task)


@pytest.mark.parametrize("name", ["reconnect_seconds", "heartbeat_seconds",
                                  "operation_timeout_seconds", "connect_timeout_seconds"])
@pytest.mark.parametrize("value", [0, -1, float("inf"), float("nan")])
def test_listener_rejects_non_finite_or_non_positive_timing(name, value):
    with pytest.raises(ValueError, match="positive and finite"):
        PostgresLiveEventListener("postgresql://user:password@database/taxi", EventHub(permit_transport_fixture), **{name: value})
