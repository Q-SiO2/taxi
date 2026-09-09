"""Provider-neutral local and PostgreSQL fanout for minimized live refresh hints."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import logging
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
    ) -> None:
        if reconnect_seconds <= 0:
            raise ValueError("reconnect_seconds must be positive")
        url = make_url(database_url)
        if not url.drivername.startswith("postgresql"):
            raise ValueError("PostgreSQL live events require a PostgreSQL database URL")
        self._dsn = url.set(drivername="postgresql").render_as_string(hide_password=False)
        self._hub = hub
        self._reconnect_seconds = reconnect_seconds
        self._ready = asyncio.Event()
        self._dispatch_tasks: set[asyncio.Task] = set()

    async def run(self) -> None:
        while True:
            connection: asyncpg.Connection | None = None
            try:
                connection = await asyncpg.connect(self._dsn)
                await connection.add_listener(LIVE_EVENT_CHANNEL, self._on_notification)
                self._ready.set()
                await asyncio.Future()
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self._ready.clear()
                logger.error(
                    "live_event_listener_unavailable",
                    extra={"error_type": type(error).__name__},
                )
                await asyncio.sleep(self._reconnect_seconds)
            finally:
                if connection is not None:
                    try:
                        await connection.remove_listener(LIVE_EVENT_CHANNEL, self._on_notification)
                        await connection.close(timeout=5)
                    except Exception:
                        pass
                self._ready.clear()
                if self._dispatch_tasks:
                    await asyncio.gather(*tuple(self._dispatch_tasks), return_exceptions=True)

    async def wait_until_ready(self, timeout_seconds: float) -> None:
        await asyncio.wait_for(self._ready.wait(), timeout=timeout_seconds)

    async def dispatch_payload(self, payload: str) -> None:
        """Validate an untrusted notification payload before touching local sockets."""
        hint = decode_hint(payload)
        await self._hub.publish_ride_refresh(hint.user_id, hint.ride_id, hint.event_type)

    def _on_notification(self, _connection, _pid: int, _channel: str, payload: str) -> None:
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
