"""FastAPI application factory and operational endpoints."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from secrets import compare_digest
from fastapi import FastAPI, status, WebSocket, WebSocketDisconnect
from fastapi import Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from taximobile_api.api.v1.router import router as v1_router
from taximobile_api.core.config import ConfigurationError, Settings
from taximobile_api.core.errors import error_response, register_error_handlers
from taximobile_api.core.http_security import ResponseSecurityMiddleware
from taximobile_api.core.rate_limit import InMemoryRateLimiter, PostgresRateLimiter, RateLimiter
from taximobile_api.core.logging import configure_logging, RequestAuditMiddleware
from taximobile_api.core.live_events import (
    LocalLiveEventPublisher,
    PostgresLiveEventListener,
    PostgresLiveEventPublisher,
)
from taximobile_api.core.metrics import MetricsRegistry, OutboxMetrics
from taximobile_api.domains.outbox.metrics import collect_outbox_metrics, OutboxMetricsUnavailable
from taximobile_api.core.realtime import EventHub
from taximobile_api.db.session import create_session_factory
from taximobile_api.domains.auth.models import Session, User, UserStatus
from taximobile_api.domains.auth.security import InvalidAccessToken, TokenService
from taximobile_api.workers.application import BackgroundWorkerRuntime
from taximobile_api.integrations.routing import RoutingProvider, create_routing_provider
from taximobile_api.integrations.push import FcmPushProvider, GoogleAdcAccessTokenProvider, PushProvider


def create_app(
    settings: Settings | None = None,
    session_factory: async_sessionmaker | None = None,
    routing_provider: RoutingProvider | None = None,
    push_provider: PushProvider | None = None,
    rate_limiter: RateLimiter | None = None,
) -> FastAPI:
    active_settings = settings or Settings.from_environment()
    if active_settings.process_role == "worker":
        raise ConfigurationError(
            "The public API application cannot run with TAXIMOBILE_PROCESS_ROLE=worker."
        )
    sessions = session_factory or create_session_factory(active_settings)
    routing = routing_provider or create_routing_provider(
        active_settings.routing_provider,
        active_settings.routing_base_url,
        timeout_seconds=active_settings.routing_timeout_seconds,
    )
    push = push_provider
    if (
        push is None
        and active_settings.process_role == "all"
        and active_settings.firebase_project_id is not None
    ):
        push = FcmPushProvider(
            active_settings.firebase_project_id,
            GoogleAdcAccessTokenProvider(),
            timeout_seconds=active_settings.fcm_timeout_seconds,
        )
    limiter = rate_limiter
    if limiter is None:
        limiter = (
            PostgresRateLimiter(sessions)
            if active_settings.environment in {"staging", "production"}
            else InMemoryRateLimiter()
        )
    event_hub = EventHub()
    live_event_listener = None
    if active_settings.environment in {"staging", "production"}:
        live_event_publisher = PostgresLiveEventPublisher(sessions)
        live_event_listener = PostgresLiveEventListener(active_settings.database_url, event_hub)
    else:
        live_event_publisher = LocalLiveEventPublisher(event_hub)
    worker_runtime = (
        BackgroundWorkerRuntime(sessions, active_settings, live_event_publisher, push)
        if active_settings.process_role == "all"
        else None
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if worker_runtime is not None:
            worker_runtime.start(app.state.metrics)
        listener_task = asyncio.create_task(live_event_listener.run()) if live_event_listener is not None else None
        if live_event_listener is not None:
            try:
                await live_event_listener.wait_until_ready(10)
            except Exception:
                listener_task.cancel()
                if worker_runtime is not None:
                    await worker_runtime.stop()
                try:
                    await listener_task
                except asyncio.CancelledError:
                    pass
                raise RuntimeError("The shared live-event listener could not become ready.")
        try:
            yield
        finally:
            if listener_task is not None:
                listener_task.cancel()
            if worker_runtime is not None:
                await worker_runtime.stop()
            if listener_task is not None:
                try:
                    await listener_task
                except asyncio.CancelledError:
                    pass
            await routing.aclose()
            if push is not None:
                await push.aclose()

    app = FastAPI(
        title="TaxiMobile API",
        version="0.1.0",
        openapi_url=f"{active_settings.api_prefix}/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = active_settings
    app.state.session_factory = sessions
    app.state.rate_limiter = limiter
    app.state.metrics = MetricsRegistry(workers_enabled=worker_runtime is not None)
    app.state.event_hub = event_hub
    app.state.live_event_publisher = live_event_publisher
    app.state.routing_provider = routing
    app.state.push_provider = push
    app.state.worker_runtime = worker_runtime
    logger = configure_logging(active_settings.log_level)
    register_error_handlers(app)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(active_settings.allowed_hosts))
    if active_settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(active_settings.cors_origins),
            allow_credentials=True,
            allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=[
                "Authorization",
                "Content-Type",
                "Idempotency-Key",
                "X-Request-ID",
            ],
        )
    app.add_middleware(
        ResponseSecurityMiddleware,
        hsts_enabled=active_settings.environment == "production",
    )
    app.add_middleware(RequestAuditMiddleware, metrics=app.state.metrics, logger=logger)
    app.include_router(v1_router, prefix=active_settings.api_prefix)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready", tags=["system"], response_model=None)
    async def ready() -> JSONResponse | dict[str, str]:
        try:
            async with sessions() as session:
                await session.execute(text("SELECT 1"))
        except Exception:
            # Connection/authentication failures are not consistently wrapped
            # by every async database driver. Readiness is a dependency
            # boundary, so return only the stable operational condition.
            return error_response(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                code="DEPENDENCY_UNAVAILABLE",
                message="The service is not ready.",
            )
        return {"status": "ready"}

    @app.get("/internal/metrics", include_in_schema=False, response_model=None)
    async def metrics(request: Request) -> PlainTextResponse | JSONResponse:
        configured_token = active_settings.monitoring_token
        authorization = request.headers.get("Authorization", "")
        supplied_token = authorization[7:] if authorization.lower().startswith("bearer ") else ""
        if configured_token is None:
            return error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                code="NOT_FOUND",
                message="The requested resource was not found.",
            )
        if not supplied_token or not compare_digest(supplied_token, configured_token):
            response = error_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="UNAUTHORIZED",
                message="Monitoring authorization is required.",
            )
            response.headers["WWW-Authenticate"] = "Bearer"
            return response
        try:
            outbox_metrics = await collect_outbox_metrics(sessions)
        except OutboxMetricsUnavailable:
            # HTTP/process telemetry remains scrapeable during a database
            # incident; an explicit gauge marks the aggregate snapshot absent.
            outbox_metrics = OutboxMetrics(available=False)
        return PlainTextResponse(
            app.state.metrics.render_prometheus(outbox=outbox_metrics),
            media_type="text/plain; version=0.0.4",
        )

    @app.websocket(f"{active_settings.api_prefix}/events")
    async def live_events(websocket: WebSocket) -> None:
        """Connected apps receive hints and must reload REST resources afterward."""
        authorization = websocket.headers.get("authorization", "")
        if not authorization.lower().startswith("bearer ") or active_settings.jwt_secret is None:
            await websocket.close(code=4401)
            return
        try:
            user_id, session_id = TokenService(active_settings.jwt_secret).parse_access_token(authorization[7:])
        except InvalidAccessToken:
            await websocket.close(code=4401)
            return
        async with sessions() as session:
            valid_session = await session.scalar(
                select(Session.id)
                .join(User, User.id == Session.user_id)
                .where(
                    Session.id == session_id,
                    Session.user_id == user_id,
                    Session.revoked_at.is_(None),
                    User.status == UserStatus.ACTIVE,
                )
            )
        if valid_session is None:
            await websocket.close(code=4401)
            return
        hub: EventHub = app.state.event_hub
        await hub.connect(user_id, websocket)
        try:
            while True:
                # Commands remain HTTP API operations; inbound socket data is discarded.
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            await hub.disconnect(user_id, websocket)

    return app


app = create_app()
