"""ASGI request-body limits applied before multipart parsing or spooling."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from starlette.responses import JSONResponse
from starlette.types import Message, Receive, Scope, Send


class _BodyLimitExceeded(Exception):
    pass


class DriverDocumentBodyLimitMiddleware:
    """Bound applicant document multipart bodies independently of client headers."""

    def __init__(self, app: Callable[..., Awaitable[None]], *, max_file_bytes: int) -> None:
        self.app = app
        # Multipart boundaries and bounded form fields need a small fixed allowance.
        self._max_body_bytes = max_file_bytes + 256 * 1024

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self._is_document_upload(scope):
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        declared = headers.get(b"content-length")
        if declared is not None:
            try:
                declared_bytes = int(declared)
            except ValueError:
                await self._reject(scope, receive, send, 400, "Invalid Content-Length header.")
                return
            if declared_bytes < 0 or declared_bytes > self._max_body_bytes:
                await self._reject(scope, receive, send, 413, "Document upload body is too large.")
                return

        received = 0
        response_started = False

        async def bounded_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self._max_body_bytes:
                    raise _BodyLimitExceeded
            return message

        async def tracked_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, bounded_receive, tracked_send)
        except _BodyLimitExceeded:
            if response_started:
                raise
            await self._reject(scope, receive, send, 413, "Document upload body is too large.")

    @staticmethod
    def _is_document_upload(scope: Scope) -> bool:
        path = str(scope.get("path", ""))
        return (
            scope.get("type") == "http"
            and scope.get("method") == "POST"
            and "/drivers/me/city-applications/" in path
            and path.endswith("/documents")
        )

    @staticmethod
    async def _reject(
        scope: Scope,
        receive: Receive,
        send: Send,
        status_code: int,
        detail: str,
    ) -> None:
        response = JSONResponse(status_code=status_code, content={"detail": detail})
        await response(scope, receive, send)
