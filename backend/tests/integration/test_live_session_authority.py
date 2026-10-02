"""Fresh migrated SQL authority, separate from transport-only fanout fixtures.

No real users, providers or device delivery are exercised. Each test owns an
isolated migrated database and inert synthetic accounts; every authorization
read uses a fresh SQLAlchemy session rather than cached ORM state.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from test_mvp_lifecycle import require_integration_settings
from taximobile_api.core.realtime import EventHub
from taximobile_api.domains.auth.models import Session, User, UserStatus
from taximobile_api.domains.auth.security import VerifiedAccessToken
from taximobile_api.domains.auth.session_authority import mobile_session_is_active


pytestmark = pytest.mark.integration


class RecordingSocket:
    def __init__(self):
        self.messages = []
        self.close_codes = []

    async def accept(self):
        pass

    async def send_json(self, message):
        self.messages.append(message)

    async def close(self, *, code):
        self.close_codes.append(code)


async def seed(sessions):
    user_id, first_id, second_id = uuid4(), uuid4(), uuid4()
    now = datetime.now(UTC)
    async with sessions() as session, session.begin():
        session.add(User(id=user_id, email=f"socket-{uuid4().hex}@example.test",
                         password_hash="!inert-synthetic-account"))
        await session.flush()
        for session_id in (first_id, second_id):
            session.add(Session(id=session_id, user_id=user_id,
                                refresh_token_hash=uuid4().hex + uuid4().hex,
                                refresh_family_id=uuid4(), expires_at=now + timedelta(days=30)))
    return tuple(VerifiedAccessToken(user_id, session_id, now + timedelta(minutes=10))
                 for session_id in (first_id, second_id))


def test_live_session_revocation_and_suspension_recheck_migrated_authority():
    settings = require_integration_settings()

    async def scenario():
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)

        async def authorize(identity):
            async with sessions() as session:
                return await mobile_session_is_active(session, identity.user_id, identity.session_id)

        hub = EventHub(authorize, check_seconds=0.02)
        try:
            first, second = await seed(sessions)
            old_socket, current_socket = RecordingSocket(), RecordingSocket()
            await hub.connect(first, old_socket)
            current = await hub.connect(second, current_socket)
            assert current is not None
            # Ownership mismatch, absent session and session-expiry boundary use
            # the same SQL predicate shared with authenticated REST.
            async with sessions() as session:
                assert not await mobile_session_is_active(session, uuid4(), first.session_id)
                assert not await mobile_session_is_active(session, first.user_id, uuid4())
                assert not await mobile_session_is_active(
                    session, first.user_id, first.session_id,
                    now=datetime.now(UTC) + timedelta(days=31),
                )
            async with sessions() as session, session.begin():
                await session.execute(update(Session).where(Session.id == first.session_id)
                                      .values(revoked_at=datetime.now(UTC)))
            await hub.publish_ride_refresh(first.user_id, uuid4(), "RIDE_CANCELLED")
            assert old_socket.messages == [] and old_socket.close_codes == [4401]
            assert len(current_socket.messages) == 1 and current_socket.close_codes == []
            # A committed account suspension must also close an idle socket,
            # without requiring a new hint, reconnect or REST read.
            async with sessions() as session, session.begin():
                await session.execute(update(User).where(User.id == first.user_id)
                                      .values(status=UserStatus.SUSPENDED))
            await asyncio.wait_for(current.closed.wait(), 2)
            assert current_socket.close_codes == [4401]
            assert not hub._connections and not hub._owned
            assert not await authorize(second)
        finally:
            await hub.aclose()
            await engine.dispose()

    asyncio.run(scenario())


def test_idle_socket_closes_when_database_session_expires():
    settings = require_integration_settings()

    async def scenario():
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)

        async def authorize(identity):
            async with sessions() as session:
                return await mobile_session_is_active(session, identity.user_id, identity.session_id)

        hub = EventHub(authorize, check_seconds=0.02)
        try:
            identity, _ = await seed(sessions)
            socket = RecordingSocket()
            connection = await hub.connect(identity, socket)
            assert connection is not None
            async with sessions() as session, session.begin():
                await session.execute(update(Session).where(Session.id == identity.session_id)
                                      .values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
            await asyncio.wait_for(connection.closed.wait(), 2)
            assert socket.close_codes == [4401] and not socket.messages
            assert not hub._connections and not hub._owned
            assert not await authorize(identity)
        finally:
            await hub.aclose()
            await engine.dispose()

    asyncio.run(scenario())
