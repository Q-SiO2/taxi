"""Minimal structured logging that deliberately excludes request bodies and secrets."""

import json
import logging
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from os import chmod
from pathlib import Path
from time import perf_counter
from uuid import UUID, uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

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

    def __init__(
        self,
        app: ASGIApp,
        *,
        metrics: MetricsRegistry,
        logger: logging.Logger,
        api_prefix: str,
        legacy_admin_api_enabled: bool,
    ) -> None:
        self.app = app
        self.metrics = metrics
        self.logger = logger
        self.legacy_admin_prefix = f"{api_prefix.rstrip('/')}/admin"
        self.legacy_admin_api_enabled = legacy_admin_api_enabled

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = correlation_id(Headers(scope=scope).get("X-Request-ID"))
        scope.setdefault("state", {})["request_id"] = request_id
        started_at = perf_counter()
        response_status: int | None = None
        raw_path = str(scope.get("path", ""))
        targets_legacy_admin = raw_path == self.legacy_admin_prefix or raw_path.startswith(
            f"{self.legacy_admin_prefix}/"
        )
        served_legacy_admin = False

        async def audited_send(message: Message) -> None:
            nonlocal response_status, served_legacy_admin
            if message["type"] == "http.response.start":
                response_status = int(message["status"])
                response_headers = MutableHeaders(scope=message)
                response_headers["X-Request-ID"] = request_id
                route_path = request_route_template(Request(scope))
                served_legacy_admin = (
                    targets_legacy_admin
                    and self.legacy_admin_api_enabled
                    and route_path != "_unmatched"
                )
                if served_legacy_admin:
                    response_headers["Deprecation"] = "true"
                    response_headers["Warning"] = (
                        '299 TaxiMobile "Legacy /admin API is local/test-only and '
                        'scheduled for removal"'
                    )
            await send(message)

        await self.app(scope, receive, audited_send)

        if response_status is None:
            return
        route_path = request_route_template(Request(scope))
        duration_seconds = perf_counter() - started_at
        if targets_legacy_admin:
            self.metrics.record_legacy_admin_request(
                "served" if served_legacy_admin else "blocked"
            )
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


class SecureRotatingFileHandler(RotatingFileHandler):
    """Keep the active JSON-lines file group-readable and otherwise private."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        chmod(self.baseFilename, 0o640)

    def doRollover(self) -> None:  # noqa: N802 - inherited logging API
        super().doRollover()
        chmod(self.baseFilename, 0o640)


def _rotating_json_handler(
    path: Path,
    *,
    max_bytes: int,
    backup_count: int,
) -> SecureRotatingFileHandler:
    """Build one bounded UTF-8 JSON-lines sink for an application-owned volume."""

    handler = SecureRotatingFileHandler(
        path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(JsonFormatter())
    setattr(handler, "_taximobile_file_sink", True)
    return handler


def configure_logging(
    level: str,
    *,
    log_file: Path | None = None,
    log_file_max_bytes: int = 10_485_760,
    log_file_backup_count: int = 5,
) -> logging.Logger:
    logger = logging.getLogger("taximobile_api")
    logger.setLevel(level)
    if not any(
        isinstance(handler, logging.StreamHandler)
        and not isinstance(handler, logging.FileHandler)
        for handler in logger.handlers
    ):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    requested_path = log_file.resolve() if log_file is not None else None
    for handler in list(logger.handlers):
        if not getattr(handler, "_taximobile_file_sink", False):
            continue
        active_path = Path(getattr(handler, "baseFilename", "")).resolve()
        if requested_path is None or active_path != requested_path:
            logger.removeHandler(handler)
            handler.close()
    if requested_path is not None and not any(
        getattr(handler, "_taximobile_file_sink", False)
        and Path(getattr(handler, "baseFilename", "")).resolve() == requested_path
        for handler in logger.handlers
    ):
        logger.addHandler(
            _rotating_json_handler(
                requested_path,
                max_bytes=log_file_max_bytes,
                backup_count=log_file_backup_count,
            )
        )
    logger.propagate = False
    return logger
