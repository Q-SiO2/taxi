import asyncio
from datetime import UTC, datetime, timedelta
import logging
from uuid import uuid4

import pytest
import pytest_asyncio

from taximobile_api.core.realtime import EventHub
from taximobile_api.core.live_sessions import LiveSocketSession
from taximobile_api.domains.auth.security import VerifiedAccessToken


class RecordingSocket:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []
        self.close_codes = []
        self.closed = asyncio.Event()
        self.accepted = False

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, payload: dict[str, str]) -> None:
        self.messages.append(payload)

    async def close(self, *, code) -> None:
        self.close_codes.append(code)
        self.closed.set()


def principal(user_id=None, session_id=None, *, seconds=600):
    return VerifiedAccessToken(user_id or uuid4(), session_id or uuid4(), datetime.now(UTC) + timedelta(seconds=seconds))


async def permit(_):
    return True


@pytest_asyncio.fixture
async def make_hub():
    hubs = []

    def make(authorize=permit, **options):
        hub = EventHub(authorize, **options)
        hubs.append(hub)
        return hub

    yield make
    for hub in hubs:
        await hub.aclose()


@pytest.mark.asyncio
async def test_event_hub_sends_only_refresh_hints_to_the_addressed_user(make_hub) -> None:
    first_user = uuid4()
    second_user = uuid4()
    ride_id = uuid4()
    first_socket = RecordingSocket()
    second_socket = RecordingSocket()
    hub = make_hub()

    await hub.connect(principal(first_user), first_socket)
    await hub.connect(principal(second_user), second_socket)
    await hub.publish_ride_refresh(first_user, ride_id, "DRIVER_ASSIGNED")

    assert first_socket.messages == [{"type": "DRIVER_ASSIGNED", "ride_id": str(ride_id)}]
    assert second_socket.messages == []


@pytest.mark.asyncio
async def test_revoking_one_session_does_not_revoke_another_for_same_account(make_hub):
    revoked = set()

    async def authorize(identity):
        return identity.session_id not in revoked

    hub = make_hub(authorize)
    identity, current = principal(), principal()
    current = principal(identity.user_id, current.session_id)
    old_socket, current_socket = RecordingSocket(), RecordingSocket()
    await hub.connect(identity, old_socket)
    await hub.connect(current, current_socket)
    revoked.add(identity.session_id)
    await hub.publish_ride_refresh(identity.user_id, uuid4(), "RIDE_CANCELLED")
    assert old_socket.messages == [] and old_socket.close_codes == [4401]
    assert len(current_socket.messages) == 1 and current_socket.close_codes == []
    assert len(hub._connections[identity.user_id]) == 1


@pytest.mark.asyncio
async def test_idle_monitor_closes_a_revoked_or_suspended_session(make_hub):
    active = True

    async def authorize(_):
        return active

    hub = make_hub(authorize, check_seconds=0.01)
    socket = RecordingSocket()
    connection = await hub.connect(principal(), socket)
    active = False
    await asyncio.wait_for(connection.closed.wait(), 1)
    assert socket.close_codes == [4401] and not hub._connections


@pytest.mark.asyncio
async def test_idle_socket_closes_at_verified_token_deadline_without_any_hint(make_hub):
    hub = make_hub(check_seconds=10)
    socket = RecordingSocket()
    connection = await hub.connect(principal(seconds=0.03), socket)
    await asyncio.wait_for(connection.closed.wait(), 1)
    assert socket.close_codes == [4401] and not socket.messages and not hub._connections


@pytest.mark.asyncio
async def test_expired_grant_is_not_accepted_even_when_database_authorizes(make_hub):
    hub = make_hub()
    socket = RecordingSocket()
    assert await hub.connect(principal(seconds=-1), socket) is None
    assert not socket.accepted and socket.close_codes == [4401] and not hub._connections


@pytest.mark.asyncio
async def test_expiry_during_authority_read_is_rechecked_before_sending(make_hub):
    identity = principal()
    clock = datetime.now(UTC)
    expire_on_read = False

    async def authorize(_):
        nonlocal clock
        if expire_on_read:
            clock = identity.expires_at
        return True

    hub = make_hub(authorize, now=lambda: clock)
    socket = RecordingSocket()
    await hub.connect(identity, socket)
    expire_on_read = True
    await hub.publish_ride_refresh(identity.user_id, uuid4(), "RIDE_CANCELLED")
    assert not socket.messages and socket.close_codes == [4401]


@pytest.mark.asyncio
@pytest.mark.parametrize("failed", [False, True])
async def test_authority_denial_or_failure_before_admission_is_fail_closed(make_hub, failed):
    async def authorize(_):
        if failed:
            raise RuntimeError("private bearer and database detail")
        return False

    hub = make_hub(authorize)
    socket = RecordingSocket()
    assert await hub.connect(principal(), socket) is None
    assert not socket.accepted and socket.close_codes == [1013 if failed else 4401]
    assert not hub._connections and not hub._connecting


@pytest.mark.asyncio
async def test_authority_blackhole_is_bounded_and_sanitized(make_hub, caplog):
    logger = logging.getLogger("taximobile_api")
    logger.addHandler(caplog.handler)

    async def stalled(_):
        await asyncio.Event().wait()

    try:
        hub = make_hub(stalled, operation_seconds=0.01)
        socket = RecordingSocket()
        assert await asyncio.wait_for(hub.connect(principal(), socket), 1) is None
        assert socket.close_codes == [1013] and not hub._connections
        assert "live_session_authority_unavailable" in caplog.text
        assert "bearer" not in caplog.text and "private" not in caplog.text
    finally:
        logger.removeHandler(caplog.handler)


@pytest.mark.asyncio
async def test_revocation_cancels_a_stalled_send_before_closing(make_hub):
    active = True
    sending, cancelled = asyncio.Event(), asyncio.Event()

    async def authorize(_):
        return active

    class StalledSocket(RecordingSocket):
        async def send_json(self, _):
            sending.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

    hub = make_hub(authorize, check_seconds=0.01)
    identity, socket = principal(), StalledSocket()
    connection = await hub.connect(identity, socket)
    publish = asyncio.create_task(hub.publish_ride_refresh(identity.user_id, uuid4(), "RIDE_CANCELLED"))
    await asyncio.wait_for(sending.wait(), 1)
    active = False
    await asyncio.wait_for(connection.closed.wait(), 1)
    await asyncio.wait_for(publish, 1)
    assert cancelled.is_set() and not socket.messages and socket.close_codes == [4401]
    assert not connection._sends and not hub._connections


@pytest.mark.asyncio
async def test_publisher_cancellation_is_not_absorbed_as_session_shutdown(make_hub):
    entered = asyncio.Event()

    class StalledSocket(RecordingSocket):
        async def send_json(self, _):
            entered.set()
            await asyncio.Event().wait()

    hub = make_hub()
    identity = principal()
    connection = await hub.connect(identity, StalledSocket())
    task = asyncio.create_task(hub.publish_ride_refresh(identity.user_id, uuid4(), "RIDE_CANCELLED"))
    await asyncio.wait_for(entered.wait(), 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not connection._sends


@pytest.mark.asyncio
async def test_concurrent_hints_are_serialized_per_socket_and_each_reauthorized(make_hub):
    calls = 0
    active = 0
    maximum = 0

    async def authorize(_):
        nonlocal calls
        calls += 1
        return True

    class SerializedSocket(RecordingSocket):
        async def send_json(self, message):
            nonlocal active, maximum
            active += 1
            maximum = max(maximum, active)
            await asyncio.sleep(0)
            await super().send_json(message)
            active -= 1

    hub = make_hub(authorize)
    identity, socket = principal(), SerializedSocket()
    await hub.connect(identity, socket)
    await asyncio.gather(*(hub.publish_ride_refresh(identity.user_id, uuid4(), "RIDE_CANCELLED") for _ in range(10)))
    assert maximum == 1 and len(socket.messages) == 10 and calls >= 11


@pytest.mark.asyncio
async def test_closed_and_replaced_sessions_cannot_deliver_old_callbacks(make_hub):
    hub = make_hub()
    identity = principal()
    old_socket, replacement = RecordingSocket(), RecordingSocket()
    old = await hub.connect(identity, old_socket)
    await hub.disconnect(identity.user_id, old_socket)
    await hub.connect(principal(identity.user_id), replacement)
    await old.send_hint({"type": "RIDE_CANCELLED", "ride_id": "obsolete"})
    await hub.publish_ride_refresh(identity.user_id, uuid4(), "RIDE_CANCELLED")
    assert not old_socket.messages and len(replacement.messages) == 1


@pytest.mark.asyncio
async def test_hub_shutdown_releases_monitors_and_refuses_new_admission(make_hub):
    hub = make_hub()
    socket = RecordingSocket()
    connection = await hub.connect(principal(), socket)
    await hub.aclose()
    assert connection.closed.is_set() and connection._monitor.done() and not hub._connections
    refused = RecordingSocket()
    assert await hub.connect(principal(), refused) is None
    assert not refused.accepted and refused.close_codes == [1013]


@pytest.mark.asyncio
async def test_socket_has_one_owner_and_constructor_failure_leaves_no_reservation(make_hub):
    hub = make_hub()
    socket = RecordingSocket()
    await hub.connect(principal(), socket)
    with pytest.raises(RuntimeError, match="one subscription owner"):
        await hub.connect(principal(), socket)
    invalid = make_hub(operation_seconds=0)
    with pytest.raises(ValueError):
        await invalid.connect(principal(), RecordingSocket())
    assert not invalid._connecting


@pytest.mark.asyncio
async def test_stalled_accept_and_close_are_bounded(make_hub):
    class StalledSocket(RecordingSocket):
        async def accept(self):
            await asyncio.Event().wait()

        async def close(self, *, code):
            await asyncio.Event().wait()

    hub = make_hub(operation_seconds=0.01)
    assert await asyncio.wait_for(hub.connect(principal(), StalledSocket()), 1) is None
    assert not hub._connecting and not hub._connections


@pytest.mark.asyncio
async def test_shutdown_cancels_admission_lookup_and_cannot_accept_afterward(make_hub):
    entered, cancelled = asyncio.Event(), asyncio.Event()

    async def authorize(_):
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    hub, socket = make_hub(authorize), RecordingSocket()
    opening = asyncio.create_task(hub.connect(principal(), socket))
    await asyncio.wait_for(entered.wait(), 1)
    await asyncio.wait_for(hub.aclose(), 1)
    assert await asyncio.wait_for(opening, 1) is None
    assert cancelled.is_set() and not socket.accepted
    assert not hub._owned and not hub._connecting


@pytest.mark.asyncio
async def test_shutdown_joins_a_close_already_removed_from_broadcast_registry(make_hub):
    closing, finish_close = asyncio.Event(), asyncio.Event()

    class ClosingSocket(RecordingSocket):
        async def close(self, *, code):
            closing.set()
            await finish_close.wait()
            await super().close(code=code)

    hub, socket = make_hub(), ClosingSocket()
    connection = await hub.connect(principal(), socket)
    first_close = asyncio.create_task(connection.aclose())
    await asyncio.wait_for(closing.wait(), 1)
    assert not hub._connections and connection in hub._owned
    shutdown = asyncio.create_task(hub.aclose())
    await asyncio.sleep(0)
    assert not shutdown.done() and not connection.closed.is_set()
    finish_close.set()
    await asyncio.wait_for(asyncio.gather(first_close, shutdown), 1)
    assert connection.closed.is_set() and not hub._owned


@pytest.mark.asyncio
async def test_cancelled_close_waiter_does_not_abandon_owned_cleanup(make_hub):
    closing, finish_close = asyncio.Event(), asyncio.Event()

    class ClosingSocket(RecordingSocket):
        async def close(self, *, code):
            closing.set()
            await finish_close.wait()
            await super().close(code=code)

    hub, socket = make_hub(), ClosingSocket()
    connection = await hub.connect(principal(), socket)
    waiter = asyncio.create_task(connection.aclose())
    await asyncio.wait_for(closing.wait(), 1)
    waiter.cancel()
    with pytest.raises(asyncio.CancelledError):
        await waiter
    assert connection in hub._owned and not connection._close_task.done()
    assert not connection.closed.is_set() and not hub._connections
    shutdown = asyncio.create_task(hub.aclose())
    await asyncio.sleep(0)
    assert not shutdown.done()
    finish_close.set()
    await asyncio.wait_for(shutdown, 1)
    assert connection._close_task.done() and connection.closed.is_set()
    assert socket.close_codes == [1000] and not hub._owned


@pytest.mark.asyncio
async def test_cancelled_admission_caller_releases_the_connection(make_hub):
    entered = asyncio.Event()

    async def authorize(_):
        entered.set()
        await asyncio.Event().wait()

    hub, socket = make_hub(authorize), RecordingSocket()
    opening = asyncio.create_task(hub.connect(principal(), socket))
    await asyncio.wait_for(entered.wait(), 1)
    opening.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(opening, 1)
    assert not socket.accepted and socket.close_codes == [1000]
    assert not hub._owned and not hub._connecting


@pytest.mark.asyncio
async def test_late_accept_completion_cannot_join_its_own_closer_or_start_a_monitor(make_hub):
    entered = asyncio.Event()

    class LateAcceptSocket(RecordingSocket):
        async def accept(self):
            entered.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                # An adapter finishing an already-started operation cannot
                # become an authorized recipient after shutdown began.
                await super().accept()

    hub, socket = make_hub(operation_seconds=2), LateAcceptSocket()
    opening = asyncio.create_task(hub.connect(principal(), socket))
    await asyncio.wait_for(entered.wait(), 1)
    await asyncio.wait_for(hub.aclose(), 1)
    assert await asyncio.wait_for(opening, 1) is None
    assert socket.close_codes == [1000] and not hub._owned and not hub._connections
    await hub.publish_ride_refresh(uuid4(), uuid4(), "RIDE_CANCELLED")
    assert not socket.messages


@pytest.mark.asyncio
async def test_noncooperative_first_send_cancellation_is_bounded_and_reported(make_hub, caplog):
    entered, first_cancel, reaped = asyncio.Event(), asyncio.Event(), asyncio.Event()
    finish_transport = asyncio.Event()
    logger = logging.getLogger("taximobile_api")
    logger.addHandler(caplog.handler)

    class DelayedCancellationSocket(RecordingSocket):
        async def send_json(self, _):
            entered.set()
            try:
                while not finish_transport.is_set():
                    try:
                        await finish_transport.wait()
                    except asyncio.CancelledError:
                        first_cancel.set()
            finally:
                reaped.set()

    try:
        hub = make_hub(operation_seconds=0.02)
        identity, socket = principal(), DelayedCancellationSocket()
        connection = await hub.connect(identity, socket)
        publishing = asyncio.create_task(hub.publish_ride_refresh(identity.user_id, uuid4(), "RIDE_CANCELLED"))
        await asyncio.wait_for(entered.wait(), 1)
        await asyncio.wait_for(connection.aclose(), 1)
        assert first_cancel.is_set() and not reaped.is_set()
        # The socket is removed and close remains bounded; Python cannot force
        # kill this deliberately broken adapter. Release it explicitly, then
        # prove the original publisher also reaps its retained send task.
        finish_transport.set()
        await asyncio.wait_for(publishing, 1)
        assert first_cancel.is_set() and reaped.is_set() and not socket.messages
        assert not hub._owned and socket.close_codes == [1000]
        assert "live_session_cleanup_incomplete" in caplog.text
        assert str(identity.user_id) not in caplog.text and str(identity.session_id) not in caplog.text
    finally:
        finish_transport.set()
        logger.removeHandler(caplog.handler)


@pytest.mark.asyncio
async def test_idle_authorizer_cancellation_cannot_leave_an_unmonitored_socket(make_hub):
    admitted = asyncio.Event()

    async def authorize(_):
        if admitted.is_set():
            raise asyncio.CancelledError()
        return True

    hub = make_hub(authorize, check_seconds=0.01)
    socket = RecordingSocket()
    connection = await hub.connect(principal(), socket)
    admitted.set()
    await asyncio.wait_for(connection.closed.wait(), 1)
    assert socket.close_codes == [1013] and not hub._owned


@pytest.mark.asyncio
async def test_send_timeout_removes_recipient_without_blocking_another_session(make_hub):
    class BlackholedSocket(RecordingSocket):
        async def send_json(self, _):
            await asyncio.Event().wait()

    hub = make_hub(operation_seconds=0.02)
    identity, stalled, healthy = principal(), BlackholedSocket(), RecordingSocket()
    await hub.connect(identity, stalled)
    await hub.connect(principal(identity.user_id), healthy)
    await asyncio.wait_for(hub.publish_ride_refresh(identity.user_id, uuid4(), "RIDE_CANCELLED"), 1)
    assert stalled.close_codes == [1013] and not stalled.messages
    assert len(healthy.messages) == 1 and len(hub._connections[identity.user_id]) == 1


@pytest.mark.parametrize("name", ["check_seconds", "operation_seconds"])
@pytest.mark.parametrize("value", [0, -1, float("inf"), float("nan")])
def test_live_session_rejects_non_positive_or_non_finite_timing(name, value):
    with pytest.raises(ValueError, match="positive and finite"):
        LiveSocketSession(principal(), RecordingSocket(), permit, permit, **{name: value})
