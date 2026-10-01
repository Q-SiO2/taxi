"""Real owned PostgreSQL connection termination and private hint recovery.

The standard integration fixture gives this test its own migrated database.
Only the listener's exact owned backend PID is terminated, never another
application, database or server process. This is not hosted failover evidence.
"""

import asyncio
from contextlib import suppress
from uuid import uuid4

import asyncpg
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from test_mvp_lifecycle import require_integration_settings
from taximobile_api.core.live_events import (
    LIVE_EVENT_CHANNEL, PostgresLiveEventListener, PostgresLiveEventPublisher,
)
from taximobile_api.core.realtime import EventHub


pytestmark = pytest.mark.integration


def test_live_event_listener_recovers_after_owned_backend_termination(monkeypatch):
    settings = require_integration_settings()

    async def scenario():
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        hub = EventHub()
        user_id, stranger_id, ride_id = uuid4(), uuid4(), uuid4()
        created = []
        replacement = asyncio.Event()
        real_connect = asyncpg.connect

        async def recording_connect(*args, **kwargs):
            connection = await real_connect(*args, **kwargs)
            # SQLAlchemy also uses asyncpg.connect. Only the listener supplies
            # this command bound; do not count pooled publisher connections.
            if "command_timeout" in kwargs:
                created.append(connection)
                if len(created) == 2:
                    replacement.set()
            return connection

        monkeypatch.setattr("taximobile_api.core.live_events.asyncpg.connect", recording_connect)

        class Socket:
            def __init__(self):
                self.messages = []
                self.received = asyncio.Event()

            async def accept(self):
                pass

            async def send_json(self, message):
                self.messages.append(message)
                self.received.set()

        recipient, stranger = Socket(), Socket()
        await hub.connect(user_id, recipient)
        await hub.connect(stranger_id, stranger)
        listener = PostgresLiveEventListener(settings.database_url, hub, reconnect_seconds=0.1)
        task = asyncio.create_task(listener.run())
        try:
            await listener.wait_until_ready(5)
            original = created[0]
            original_pid = original.get_server_pid()
            terminated = asyncio.Event()
            readiness_at_loss = []

            def observe_loss(_connection):
                readiness_at_loss.append(listener.is_ready)
                terminated.set()

            original.add_termination_listener(observe_loss)
            # Use a separate connection owned by the same non-superuser test
            # role. The parameter is the observed listener PID, not a pattern.
            control = await real_connect(listener._dsn)
            try:
                assert await control.fetchval("SELECT pg_terminate_backend($1)", original_pid)
            finally:
                await control.close(timeout=5)
            await asyncio.wait_for(terminated.wait(), timeout=5)
            assert original.is_closed() and readiness_at_loss == [False]
            await asyncio.wait_for(replacement.wait(), timeout=5)
            await listener.wait_until_ready(5)
            current = created[-1]
            assert current.get_server_pid() != original_pid
            # Query the actual replacement's registered channels; a second TCP
            # connection by itself is not proof of resumed LISTEN authority.
            channels = await current.fetch("SELECT pg_listening_channels() AS channel")
            assert [row["channel"] for row in channels] == [LIVE_EVENT_CHANNEL]
            await PostgresLiveEventPublisher(sessions).publish_ride_refresh(user_id, ride_id, "RIDE_CANCELLED")
            await asyncio.wait_for(recipient.received.wait(), timeout=5)
            assert recipient.messages == [{"type": "RIDE_CANCELLED", "ride_id": str(ride_id)}]
            assert stranger.messages == []
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await asyncio.wait_for(task, timeout=5)
            await engine.dispose()
        assert not listener.is_ready and not listener._dispatch_tasks
        assert all(connection.is_closed() for connection in created)

    asyncio.run(scenario())
