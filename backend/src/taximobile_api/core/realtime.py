"""Best-effort connected-client refresh hints, never authoritative state."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from uuid import UUID

from fastapi import WebSocket


class EventHub:
    """Keep per-user connections in one API process without persisting messages.

    Multi-instance delivery reaches each process through the PostgreSQL live-event
    transport; this final local socket hop intentionally makes no delivery guarantee.
    """

    def __init__(self) -> None:
        self._connections: dict[UUID, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, user_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[user_id].add(websocket)

    async def disconnect(self, user_id: UUID, websocket: WebSocket) -> None:
        async with self._lock:
            connections = self._connections.get(user_id)
            if connections is None:
                return
            connections.discard(websocket)
            if not connections:
                self._connections.pop(user_id, None)

    async def publish_ride_refresh(self, user_id: UUID, ride_id: UUID, event_type: str) -> None:
        """Send only an event name and already-authorized resource identifier."""
        async with self._lock:
            connections = tuple(self._connections.get(user_id, ()))
        failed: list[WebSocket] = []
        for websocket in connections:
            try:
                await websocket.send_json({"type": event_type, "ride_id": str(ride_id)})
            except Exception:
                failed.append(websocket)
        for websocket in failed:
            await self.disconnect(user_id, websocket)
