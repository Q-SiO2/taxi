"""Minimal structured logging that deliberately excludes request bodies and secrets."""

import json
import logging
from time import perf_counter
from datetime import UTC, datetime
from starlette.datastructures import Headers, MutableHeaders
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from uuid import UUID, uuid4

from taximobile_api.core.metrics import MetricsRegistry


def correlation_id(candidate: str | None) -> str:
    """Accept only canonical UUID correlation IDs; otherwise mint a server ID."""

    if candidate is not None:
        try:
            parsed = UUID(candidate)
            if candidate == str(parsed):
                return candidate
        except (ValueError, AttributeError):
            pass
    return str(uuid4())


def request_route_template(request: Request) -> str:
    """Return a bounded framework route template, never the raw request path."""

    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path if isinstance(path, str) and path.startswith("/") else "_unmatched"


class RequestAuditMiddleware:
    """Record one bounded completion event without BaseHTTPMiddleware buffering.

    The middleware never reads a request or response body. The router populates
    ``scope['route']`` before response completion, allowing the final log and
    metric to use the reviewed route template rather than a caller-controlled
    raw path. WebSockets bypass this HTTP-only layer.
    """

    def __init__(self, app: ASGIApp, *, metrics: MetricsRegistry, logger: logging.Logger) -> None:
        self.app = app
        self.metrics = metrics
        self.logger = logger

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = correlation_id(Headers(scope=scope).get("X-Request-ID"))
        scope.setdefault("state", {})["request_id"] = request_id
        started_at = perf_counter()
        response_status: int | None = None

        async def audited_send(message: Message) -> None:
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = int(message["status"])
                MutableHeaders(scope=message)["X-Request-ID"] = request_id
            await send(message)

        await self.app(scope, receive, audited_send)

        if response_status is None:
            return
        route_path = request_route_template(Request(scope))
        duration_seconds = perf_counter() - started_at
        self.metrics.observe_request(
            method=str(scope.get("method", "OTHER")),
            route=route_path,
            status_code=response_status,
            duration_seconds=duration_seconds,
        )
        self.logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": scope.get("method", "OTHER"),
                "path": route_path,
                "status_code": response_status,
                "duration_ms": round(duration_seconds * 1000, 2),
            },
        )


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in (
            "request_id",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "worker",
            "error_type",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, separators=(",", ":"))


def configure_logging(level: str) -> logging.Logger:
    logger = logging.getLogger("taximobile_api")
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger
