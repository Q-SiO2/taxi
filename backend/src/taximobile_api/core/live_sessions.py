"""Bounded, session-owned final socket hop; no replay or business authority."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
import logging
import math

from fastapi import WebSocket

from taximobile_api.domains.auth.security import VerifiedAccessToken


LiveSessionAuthorizer = Callable[[VerifiedAccessToken], Awaitable[bool]]
logger = logging.getLogger("taximobile_api")


class LiveSocketSession:
    """Own one verified socket's monitor and cancellable in-flight sends.

    IDs/deadline stay inside the process. No credential or identity is emitted in
    logs, close reasons or payloads. Revalidation uses no positive-result cache.
    The monitor also checks idle connections; closing withdraws authority before
    awaiting cancellation or network IO. No database lock spans a network send.
    """

    def __init__(
        self, principal: VerifiedAccessToken, socket: WebSocket,
        authorize: LiveSessionAuthorizer,
        forget: Callable[[LiveSocketSession], Awaitable[None]],
        *, released: Callable[[LiveSocketSession], Awaitable[None]] | None = None,
        check_seconds: float = 15, operation_seconds: float = 5,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        for value in (check_seconds, operation_seconds):
            if not math.isfinite(value) or value <= 0:
                raise ValueError("Live-session timing must be positive and finite")
        if principal.expires_at.tzinfo is None:
            raise ValueError("A live-session deadline must be timezone-aware")
        self.principal = principal
        self.socket = socket
        self._authorize = authorize
        self._forget = forget
        self._released = released
        self._check_seconds = check_seconds
        self._operation_seconds = operation_seconds
        self._now = now
        self._send_lock = asyncio.Lock()
        self._closing = False
        self.closed = asyncio.Event()
        self._monitor: asyncio.Task[None] | None = None
        self._admission: asyncio.Task[bool] | None = None
        self._sends: set[asyncio.Task[None]] = set()
        self._close_task: asyncio.Task[None] | None = None

    def _remaining(self) -> float:
        return (self.principal.expires_at - self._now()).total_seconds()

    async def _denial(self) -> int | None:
        if self._closing or self._remaining() <= 0:
            return 4401
        try:
            async with asyncio.timeout(min(self._operation_seconds, self._remaining())):
                authorized = await self._authorize(self.principal)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("live_session_authority_unavailable", extra={"error_type": "LiveAuthorityUnavailable"})
            return 4401 if self._remaining() <= 0 else 1013
        return None if authorized and not self._closing and self._remaining() > 0 else 4401

    async def admit(self) -> bool:
        # Admission IO has an explicit child owner, so shutdown can cancel it
        # without cancelling the calling ASGI task or leaving an accept race.
        if self._closing:
            return False
        self._admission = asyncio.create_task(self._admit())
        try:
            return await self._admission
        except asyncio.CancelledError:
            if self._closing and not asyncio.current_task().cancelling():
                return False
            await self.aclose()
            raise
        finally:
            self._admission = None

    async def _admit(self) -> bool:
        denied = await self._denial()
        if denied is not None:
            await self.aclose(denied)
            return False
        try:
            async with asyncio.timeout(min(self._operation_seconds, self._remaining())):
                await self.socket.accept()
        except asyncio.CancelledError:
            raise
        except Exception:
            await self.aclose(4401 if self._remaining() <= 0 else 1013)
            return False
        if self._closing:
            # The closer already owns admission cancellation. Joining it here
            # would make that closer wait on the admission it is trying to reap.
            return False
        if self._remaining() <= 0:
            await self.aclose(4401)
            return False
        return True

    def start(self) -> None:
        if self._monitor is not None or self._closing:
            raise RuntimeError("A live socket has one monitor owner")
        self._monitor = asyncio.create_task(self._watch(), name="taximobile-live-session")

    async def _watch(self) -> None:
        try:
            while not self._closing:
                denied = await self._denial()
                if denied is not None:
                    await self.aclose(denied)
                    return
                await asyncio.sleep(min(self._check_seconds, max(0, self._remaining())))
        except asyncio.CancelledError:
            if not self._closing:
                await self.aclose(1013)
            raise
        except Exception:
            logger.warning("live_session_monitor_failed", extra={"error_type": "LiveMonitorFailure"})
            await self.aclose(1013)

    async def send_hint(self, payload: dict[str, str]) -> None:
        if self._closing:
            return
        task = asyncio.create_task(self._send(payload))
        self._sends.add(task)
        try:
            await task
        except asyncio.CancelledError:
            # Own closure withdraws the recipient, not the entire fanout job.
            # Cancellation of the publisher/parent still propagates.
            if not self._closing or asyncio.current_task().cancelling():
                raise
        finally:
            self._sends.discard(task)

    async def _send(self, payload: dict[str, str]) -> None:
        try:
            async with asyncio.timeout(min(self._operation_seconds, max(0, self._remaining()))):
                async with self._send_lock:
                    if self._closing:
                        return
                    denied = await self._denial()
                    if denied is not None:
                        await self.aclose(denied)
                        return
                    await self.socket.send_json(payload)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("live_session_send_failed", extra={"error_type": "LiveSendFailure"})
            await self.aclose(4401 if self._remaining() <= 0 else 1013)

    async def aclose(self, code: int = 1000) -> None:
        if self._close_task is None:
            # Withdraw authority synchronously. Cleanup has its own retained
            # task so cancellation of an ASGI caller cannot abandon removal,
            # monitor/send cancellation or release. Other closers join this task.
            self._closing = True
            initiator = asyncio.current_task()
            self._close_task = asyncio.create_task(
                self._finish_close(code, initiator), name="taximobile-live-close",
            )
        await asyncio.shield(self._close_task)

    async def _finish_close(self, code: int, initiator: asyncio.Task | None) -> None:
        try:
            await self._forget(self)
            tasks = tuple(
                task for task in (*self._sends, self._monitor, self._admission)
                if task is not None and task is not initiator
            )
            for task in tasks:
                task.cancel()
            if tasks:
                _, pending = await asyncio.wait(tasks, timeout=self._operation_seconds)
                for task in pending:
                    task.cancel()
                if pending:
                    # Cancellation-cooperative transports are reaped above.
                    # Python cannot force-kill a task that suppresses cancellation;
                    # keep close bounded and report this exceptional condition.
                    logger.warning("live_session_cleanup_incomplete", extra={"error_type": "LiveCleanupTimeout"})
            async with asyncio.timeout(self._operation_seconds):
                await self.socket.close(code=code)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("live_session_close_failed", extra={"error_type": "LiveCloseFailure"})
        finally:
            try:
                if self._released is not None:
                    await self._released(self)
            finally:
                self.closed.set()
