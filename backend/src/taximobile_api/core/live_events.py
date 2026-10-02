"""Provider-neutral local and PostgreSQL fanout for minimized live refresh hints."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import logging
from math import isfinite
from typing import Protocol
from uuid import UUID

import asyncpg
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taximobile_api.core.notification_policy import LIVE_EVENT_TYPES
from taximobile_api.core.realtime import EventHub


LIVE_EVENT_CHANNEL = "taximobile_live_events_v1"
logger = logging.getLogger("taximobile_api")


@dataclass(frozen=True, slots=True)
class LiveEventHint:
    user_id: UUID
    ride_id: UUID
    event_type: str


class LiveEventPublisher(Protocol):
    async def publish_ride_refresh(self, user_id: UUID, ride_id: UUID, event_type: str) -> None: ...


class LocalLiveEventPublisher:
    def __init__(self, hub: EventHub) -> None:
        self._hub = hub

    async def publish_ride_refresh(self, user_id: UUID, ride_id: UUID, event_type: str) -> None:
        _validate_event_type(event_type)
        await self._hub.publish_ride_refresh(user_id, ride_id, event_type)


class PostgresLiveEventPublisher:
    """Commit a minimized PostgreSQL notification visible to every API replica."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def publish_ride_refresh(self, user_id: UUID, ride_id: UUID, event_type: str) -> None:
        payload = encode_hint(LiveEventHint(user_id=user_id, ride_id=ride_id, event_type=event_type))
        async with self._sessions() as session:
            async with session.begin():
                await session.execute(
                    text("SELECT pg_notify(:channel, :payload)"),
                    {"channel": LIVE_EVENT_CHANNEL, "payload": payload},
                )


class PostgresLiveEventListener:
    """Reconnect a dedicated LISTEN connection and dispatch hints to this process."""

    def __init__(
        self,
        database_url: str,
        hub: EventHub,
        *,
        reconnect_seconds: float = 1.0,
        heartbeat_seconds: float = 15.0,
        operation_timeout_seconds: float = 5.0,
        connect_timeout_seconds: float = 10.0,
    ) -> None:
        for value in (
            reconnect_seconds, heartbeat_seconds, operation_timeout_seconds,
            connect_timeout_seconds,
        ):
            if not isfinite(value) or value <= 0:
                raise ValueError("Live-event timing bounds must be positive and finite")
        url = make_url(database_url)
        if not url.drivername.startswith("postgresql"):
            raise ValueError("PostgreSQL live events require a PostgreSQL database URL")
        self._dsn = url.set(drivername="postgresql").render_as_string(hide_password=False)
        self._hub = hub
        self._reconnect_seconds = reconnect_seconds
        self._heartbeat_seconds = heartbeat_seconds
        self._operation_timeout_seconds = operation_timeout_seconds
        self._connect_timeout_seconds = connect_timeout_seconds
        self._ready = asyncio.Event()
        self._connection: asyncpg.Connection | None = None
        self._running = False
        self._dispatch_tasks: set[asyncio.Task] = set()

    @property
    def is_ready(self) -> bool:
        return self._ready.is_set() and self._connection is not None and not self._connection.is_closed()

    async def run(self) -> None:
        if self._running:
            raise RuntimeError("The live-event listener already has a process owner")
        self._running = True
        try:
            await self._run_connections()
        finally:
            self._running = False

    async def _run_connections(self) -> None:
        while True:
            connection: asyncpg.Connection | None = None
            disconnected = asyncio.Event()

            def on_termination(terminated_connection, lost=disconnected) -> None:
                # A callback queued by an old connection must not invalidate a
                # replacement connection. Bind the signal to this attempt.
                if self._connection is terminated_connection:
                    self._ready.clear()
                    lost.set()

            try:
                connection = await asyncpg.connect(
                    self._dsn,
                    timeout=self._connect_timeout_seconds,
                    command_timeout=self._operation_timeout_seconds,
                )
                self._connection = connection
                connection.add_termination_listener(on_termination)
                async with asyncio.timeout(self._operation_timeout_seconds):
                    await connection.add_listener(LIVE_EVENT_CHANNEL, self._on_notification)
                if disconnected.is_set() or connection.is_closed():
                    raise ConnectionError("Live-event connection closed during registration")
                self._ready.set()
                await self._watch_connection(connection, disconnected)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self._ready.clear()
                logger.error(
                    "live_event_listener_unavailable",
                    extra={"error_type": type(error).__name__},
                )
            finally:
                self._ready.clear()
                self._connection = None
                # Hints are best effort, not a queue of business commands. A
                # stalled socket must not prevent listener restart or shutdown.
                pending = tuple(self._dispatch_tasks)
                for task in pending:
                    task.cancel()
                if pending:
                    await asyncio.gather(*pending, return_exceptions=True)
                if connection is not None:
                    await self._close_connection(connection, on_termination)
            await asyncio.sleep(self._reconnect_seconds)

    async def _watch_connection(self, connection, disconnected: asyncio.Event) -> None:
        while True:
            try:
                await asyncio.wait_for(disconnected.wait(), timeout=self._heartbeat_seconds)
            except TimeoutError:
                # Termination callbacks cover observed closes. A bounded probe
                # also detects a half-open/blackholed transport that never
                # supplies a close callback. This adds no business authority.
                async with asyncio.timeout(self._operation_timeout_seconds):
                    await connection.execute("SELECT 1", timeout=self._operation_timeout_seconds)
                if connection.is_closed() or disconnected.is_set():
                    raise ConnectionError("Live-event connection closed during probe")
            else:
                raise ConnectionError("Live-event connection terminated")

    async def _close_connection(self, connection, on_termination) -> None:
        connection.remove_termination_listener(on_termination)
        try:
            async with asyncio.timeout(self._operation_timeout_seconds):
                await connection.remove_listener(LIVE_EVENT_CHANNEL, self._on_notification)
        except Exception as error:
            logger.warning(
                "live_event_listener_cleanup_failed", extra={"error_type": type(error).__name__},
            )
        finally:
            try:
                async with asyncio.timeout(self._operation_timeout_seconds):
                    await connection.close(timeout=self._operation_timeout_seconds)
            except Exception as error:
                logger.warning(
                    "live_event_listener_cleanup_failed", extra={"error_type": type(error).__name__},
                )
            finally:
                if not connection.is_closed():
                    connection.terminate()

    async def wait_until_ready(self, timeout_seconds: float) -> None:
        async with asyncio.timeout(timeout_seconds):
            while True:
                await self._ready.wait()
                if self.is_ready:
                    return
                self._ready.clear()

    async def dispatch_payload(self, payload: str) -> None:
        """Validate an untrusted notification payload before touching local sockets."""
        hint = decode_hint(payload)
        await self._hub.publish_ride_refresh(hint.user_id, hint.ride_id, hint.event_type)

    def _on_notification(self, _connection, _pid: int, _channel: str, payload: str) -> None:
        if _connection is not self._connection or not self.is_ready:
            return
        task = asyncio.create_task(self.dispatch_payload(payload))
        self._dispatch_tasks.add(task)
        task.add_done_callback(self._finish_dispatch)

    def _finish_dispatch(self, task: asyncio.Task) -> None:
        self._dispatch_tasks.discard(task)
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception as error:
            logger.error(
                "live_event_payload_rejected",
                extra={"error_type": type(error).__name__},
            )


def encode_hint(hint: LiveEventHint) -> str:
    _validate_event_type(hint.event_type)
    payload = json.dumps(
        {
            "version": 1,
            "user_id": str(hint.user_id),
            "ride_id": str(hint.ride_id),
            "type": hint.event_type,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    if len(payload.encode("utf-8")) > 1024:
        raise ValueError("Live event payload exceeds the bounded size")
    return payload


def decode_hint(payload: str) -> LiveEventHint:
    if len(payload.encode("utf-8")) > 1024:
        raise ValueError("Live event payload exceeds the bounded size")
    try:
        data = json.loads(payload)
        if not isinstance(data, dict) or set(data) != {"version", "user_id", "ride_id", "type"}:
            raise ValueError("Live event payload has unexpected fields")
        if data["version"] != 1 or not isinstance(data["type"], str):
            raise ValueError("Live event payload version or type is invalid")
        _validate_event_type(data["type"])
        return LiveEventHint(
            user_id=UUID(data["user_id"]),
            ride_id=UUID(data["ride_id"]),
            event_type=data["type"],
        )
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("Live event payload is invalid") from error


def _validate_event_type(event_type: str) -> None:
    if event_type not in LIVE_EVENT_TYPES:
        raise ValueError("Live event type is not allowed")
