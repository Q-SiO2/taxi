"""ASGI socket admission/delivery/close protocol; SQL authority has T3 tests."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
import jwt
import pytest
from starlette.websockets import WebSocketDisconnect

from taximobile_api.core.config import Settings
from taximobile_api.domains.auth.security import JWT_ALGORITHM, JWT_AUDIENCE, JWT_ISSUER, TokenService
from taximobile_api.main import create_app


class AuthorityFactory:
    """A mutable T1 database seam, not a migrated-SQL correctness claim."""
    def __init__(self):
        self.active = True
        self.unavailable = False

    def __call__(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def scalar(self, _):
        if self.unavailable:
            raise RuntimeError("private database and credential detail")
        return uuid4() if self.active else None


def fixture_app():
    authority = AuthorityFactory()
    settings = replace(Settings.from_environment(), process_role="api", jwt_secret="a" * 32)
    app = create_app(settings=settings, session_factory=authority)
    app.state.event_hub._session_options.update(check_seconds=0.01, operation_seconds=0.1)
    return app, authority


def headers(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("kind", ["operations", "expired", "wrong-signature"])
def test_socket_rejects_wrong_token_authority_before_accept(kind):
    app, _ = fixture_app()
    service = TokenService("b" * 32 if kind == "wrong-signature" else "a" * 32)
    user_id, session_id = uuid4(), uuid4()
    token = (service.create_operations_access_token(user_id=user_id, session_id=session_id)
             if kind == "operations" else service.create_access_token(
                 user_id=user_id, session_id=session_id,
                 now=datetime.now(UTC) - timedelta(hours=1) if kind == "expired" else None,
             ))
    with TestClient(app) as client, pytest.raises(WebSocketDisconnect) as denied:
        with client.websocket_connect("/api/v1/events", headers=headers(token)):
            pytest.fail("Invalid authority was accepted")
    assert denied.value.code == 4401 and not app.state.event_hub._owned


@pytest.mark.parametrize("failure", ["revoked", "unavailable"])
def test_connected_socket_fails_closed_without_an_incoming_hint(failure):
    app, authority = fixture_app()
    token = TokenService("a" * 32).create_access_token(user_id=uuid4(), session_id=uuid4())
    with TestClient(app) as client:
        with client.websocket_connect("/api/v1/events", headers=headers(token)) as socket:
            owner = socket.portal.call(lambda: next(iter(app.state.event_hub._owned)))
            if failure == "revoked":
                authority.active = False
            else:
                authority.unavailable = True

            async def await_closed():
                await asyncio.wait_for(owner.closed.wait(), 2)

            socket.portal.call(await_closed)
            with pytest.raises(WebSocketDisconnect) as closed:
                socket.receive_json()
            assert closed.value.code == (4401 if failure == "revoked" else 1013)
            assert not app.state.event_hub._owned


def test_connected_socket_expiry_uses_verified_jwt_deadline_not_idle_poll_period():
    app, _ = fixture_app()
    app.state.event_hub._session_options["check_seconds"] = 60
    now = datetime.now(UTC)
    token = jwt.encode({"sub": str(uuid4()), "sid": str(uuid4()), "type": "access",
                        "iat": now, "exp": now + timedelta(seconds=2),
                        "iss": JWT_ISSUER, "aud": JWT_AUDIENCE}, "a" * 32, algorithm=JWT_ALGORITHM)
    with TestClient(app) as client:
        with client.websocket_connect("/api/v1/events", headers=headers(token)) as socket:
            async def await_closed():
                owner = next(iter(app.state.event_hub._owned))
                await asyncio.wait_for(owner.closed.wait(), 3)

            socket.portal.call(await_closed)
            with pytest.raises(WebSocketDisconnect) as closed:
                socket.receive_json()
            assert closed.value.code == 4401 and not app.state.event_hub._owned


def test_live_socket_delivers_minimized_hints_and_discards_inbound_commands():
    app, _ = fixture_app()
    user_id, ride_id = uuid4(), uuid4()
    token = TokenService("a" * 32).create_access_token(user_id=user_id, session_id=uuid4())
    with TestClient(app) as client:
        with client.websocket_connect("/api/v1/events", headers=headers(token)) as socket:
            owner = socket.portal.call(lambda: next(iter(app.state.event_hub._owned)))
            socket.send_text('{"type":"COMPLETE_RIDE"}')
            socket.send_bytes(b'{"type":"COMPLETE_RIDE"}')
            socket.portal.call(app.state.event_hub.publish_ride_refresh, user_id, ride_id, "RIDE_CANCELLED")
            assert socket.receive_json() == {"type": "RIDE_CANCELLED", "ride_id": str(ride_id)}

        async def await_closed():
            await asyncio.wait_for(owner.closed.wait(), 2)

        client.portal.call(await_closed)
        assert not app.state.event_hub._owned
