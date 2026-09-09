"""Private operational application for the standalone background-worker role."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from secrets import compare_digest

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from taximobile_api.core.config import ConfigurationError, Settings
from taximobile_api.core.http_security import ResponseSecurityMiddleware
from taximobile_api.core.live_events import PostgresLiveEventPublisher
from taximobile_api.core.logging import configure_logging
from taximobile_api.core.metrics import (
    DatabaseMetrics,
    DatabasePoolMetrics,
    MetricsRegistry,
    OutboxMetrics,
    SecurityIncidentMetrics,
)
from taximobile_api.db.metrics import (
    collect_database_metrics,
    collect_database_pool_metrics,
)
from taximobile_api.db.session import create_session_factory
from taximobile_api.domains.outbox.metrics import collect_outbox_metrics
from taximobile_api.domains.security_incidents.metrics import (
    collect_security_incident_metrics,
)
from taximobile_api.integrations.push import FcmPushProvider, GoogleAdcAccessTokenProvider, PushProvider
from taximobile_api.workers.application import BackgroundWorkerRuntime


def create_worker_app(
    settings: Settings | None = None,
    session_factory: async_sessionmaker | None = None,
    push_provider: PushProvider | None = None,
    worker_runtime: BackgroundWorkerRuntime | None = None,
) -> FastAPI:
    active_settings = settings or Settings.from_environment()
    if active_settings.process_role == "api":
        raise ConfigurationError(
            "The worker application cannot run with TAXIMOBILE_PROCESS_ROLE=api."
        )
    sessions = session_factory or create_session_factory(active_settings)
    push = push_provider
    if push is None and active_settings.firebase_project_id is not None:
        push = FcmPushProvider(
            active_settings.firebase_project_id,
            GoogleAdcAccessTokenProvider(),
            timeout_seconds=active_settings.fcm_timeout_seconds,
        )
    runtime = worker_runtime or BackgroundWorkerRuntime(
        sessions,
        active_settings,
        PostgresLiveEventPublisher(sessions),
        push,
    )
    metrics = MetricsRegistry()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        runtime.start(metrics)
        try:
            yield
        finally:
            await runtime.stop()
            if push is not None:
                await push.aclose()

    worker_app = FastAPI(
        title="TaxiMobile Worker Operations",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    worker_app.state.settings = active_settings
    worker_app.state.session_factory = sessions
    worker_app.state.metrics = metrics
    worker_app.state.worker_runtime = runtime
    configure_logging(
        active_settings.log_level,
        log_file=active_settings.log_file,
        log_file_max_bytes=active_settings.log_file_max_bytes,
        log_file_backup_count=active_settings.log_file_backup_count,
    )
    worker_app.add_middleware(
        ResponseSecurityMiddleware,
        hsts_enabled=active_settings.environment == "production",
    )

    @worker_app.get("/health", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "taximobile-worker"}

    @worker_app.get("/ready", include_in_schema=False)
    async def ready() -> JSONResponse:
        try:
            async with sessions() as session:
                await session.execute(text("SELECT 1"))
            if not runtime.is_running or not metrics.all_workers_have_succeeded():
                raise RuntimeError("worker startup is incomplete")
        except Exception:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "not_ready", "service": "taximobile-worker"},
            )
        return JSONResponse(content={"status": "ready", "service": "taximobile-worker"})

    @worker_app.get("/internal/metrics", include_in_schema=False)
    async def internal_metrics(request: Request):
        token = active_settings.monitoring_token
        if token is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": {"code": "NOT_FOUND", "message": "Resource not found.", "details": {}}},
            )
        authorization = request.headers.get("Authorization", "")
        scheme, _, submitted = authorization.partition(" ")
        if scheme.lower() != "bearer" or not submitted or not compare_digest(submitted, token):
            response = JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": {"code": "UNAUTHORIZED", "message": "Monitoring authorization is required.", "details": {}}},
            )
            response.headers["WWW-Authenticate"] = "Bearer"
            return response
        (
            outbox_result,
            database_result,
            security_incident_result,
        ) = await asyncio.gather(
            collect_outbox_metrics(sessions),
            collect_database_metrics(sessions),
            collect_security_incident_metrics(sessions),
            return_exceptions=True,
        )
        if not isinstance(outbox_result, OutboxMetrics):
            outbox = OutboxMetrics(available=False)
        else:
            outbox = outbox_result
        if not isinstance(database_result, DatabaseMetrics):
            database = DatabaseMetrics(available=False)
        else:
            database = database_result
        if not isinstance(security_incident_result, SecurityIncidentMetrics):
            security_incidents = SecurityIncidentMetrics(available=False)
        else:
            security_incidents = security_incident_result
        try:
            database_pool = collect_database_pool_metrics(sessions)
        except Exception:
            database_pool = DatabasePoolMetrics(available=False)
        return PlainTextResponse(
            metrics.render_prometheus(
                outbox=outbox,
                database=database,
                database_pool=database_pool,
                security_incidents=security_incidents,
            ),
            media_type="text/plain; version=0.0.4",
        )

    return worker_app


app = create_worker_app()
