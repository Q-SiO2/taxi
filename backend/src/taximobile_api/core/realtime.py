"""Best-effort connected-client refresh hints, never authoritative state."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from uuid import UUID

from fastapi import WebSocket

from taximobile_api.core.live_sessions import LiveSessionAuthorizer, LiveSocketSession
from taximobile_api.domains.auth.security import VerifiedAccessToken


class EventHub:
    """Keep per-user connections in one API process without persisting messages.

    Multi-instance delivery reaches each process through the PostgreSQL live-event
    transport; this final local socket hop intentionally makes no delivery guarantee.
    """

    def __init__(self, authorize: LiveSessionAuthorizer, **session_options) -> None:
        self._authorize = authorize
        self._session_options = session_options
        self._connections: dict[UUID, dict[WebSocket, LiveSocketSession]] = defaultdict(dict)
        self._lock = asyncio.Lock()
        self._connecting: set[WebSocket] = set()
        # Includes admission and closing owners, not just broadcast recipients.
        self._owned: set[LiveSocketSession] = set()
        self._closed = False

    async def connect(self, principal: VerifiedAccessToken, websocket: WebSocket) -> LiveSocketSession | None:
        connection = LiveSocketSession(
            principal, websocket, self._authorize, self._forget,
            released=self._release, **self._session_options,
        )
        async with self._lock:
            if websocket in self._connecting or any(websocket in sockets for sockets in self._connections.values()):
                raise RuntimeError("A socket has one subscription owner")
            self._connecting.add(websocket)
            self._owned.add(connection)
        try:
            if self._closed or not await connection.admit():
                await connection.aclose(1013)
                return None
            async with self._lock:
                admitted = not self._closed
                if admitted:
                    self._connections[principal.user_id][websocket] = connection
                    connection.start()
            if not admitted:
                await connection.aclose(1013)
                return None
            return connection
        except asyncio.CancelledError:
            await connection.aclose()
            raise
        finally:
            async with self._lock:
                self._connecting.discard(websocket)

    async def _forget(self, connection: LiveSocketSession) -> None:
        async with self._lock:
            sockets = self._connections.get(connection.principal.user_id)
            if sockets is not None and sockets.get(connection.socket) is connection:
                sockets.pop(connection.socket)
                if not sockets:
                    self._connections.pop(connection.principal.user_id, None)

    async def disconnect(self, user_id: UUID, websocket: WebSocket) -> None:
        async with self._lock:
            connection = self._connections.get(user_id, {}).get(websocket)
        if connection is not None:
            await connection.aclose()

    async def _release(self, connection: LiveSocketSession) -> None:
        async with self._lock:
            self._owned.discard(connection)

    async def aclose(self) -> None:
        async with self._lock:
            self._closed = True
            connections = tuple(self._owned)
        await asyncio.gather(*(connection.aclose() for connection in connections))

    async def publish_ride_refresh(self, user_id: UUID, ride_id: UUID, event_type: str) -> None:
        """Send only an event name and already-authorized resource identifier."""
        async with self._lock:
            connections = tuple(self._connections.get(user_id, {}).values())
        payload = {"type": event_type, "ride_id": str(ride_id)}
        # A stalled or revoked recipient cannot delay another socket's recheck.
        await asyncio.gather(*(connection.send_hint(payload) for connection in connections))
