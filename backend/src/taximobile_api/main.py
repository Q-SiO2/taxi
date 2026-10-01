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

from taximobile_api.api.v1.router import create_v1_router
from taximobile_api.core.config import ConfigurationError, Settings
from taximobile_api.core.client_compatibility import (
    ClientCompatibilityMiddleware,
    ClientCompatibilityPolicy,
    ClientCompatibilityStatus,
    ClientIdentityError,
    parse_client_identity,
)
from taximobile_api.core.errors import error_response, register_error_handlers
from taximobile_api.core.http_security import ResponseSecurityMiddleware
from taximobile_api.core.rate_limit import InMemoryRateLimiter, PostgresRateLimiter, RateLimiter
from taximobile_api.core.request_limits import DriverDocumentBodyLimitMiddleware
from taximobile_api.core.logging import configure_logging, RequestAuditMiddleware
from taximobile_api.core.live_events import (
    LocalLiveEventPublisher,
    PostgresLiveEventListener,
    PostgresLiveEventPublisher,
)
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
from taximobile_api.domains.outbox.metrics import collect_outbox_metrics
from taximobile_api.domains.security_incidents.metrics import (
    collect_security_incident_metrics,
)
from taximobile_api.core.realtime import EventHub
from taximobile_api.db.session import create_session_factory
from taximobile_api.domains.auth.models import Session, User, UserStatus
from taximobile_api.domains.auth.security import InvalidAccessToken, TokenService
from taximobile_api.workers.application import BackgroundWorkerRuntime
from taximobile_api.integrations.routing import RoutingProvider, create_routing_provider
from taximobile_api.integrations.geocoding import GeocodingProvider, create_geocoding_provider
from taximobile_api.integrations.push import FcmPushProvider, GoogleAdcAccessTokenProvider, PushProvider
from taximobile_api.integrations.driver_documents import (
    ProtectedDriverDocumentStore,
    create_driver_document_store,
)


def create_app(
    settings: Settings | None = None,
    session_factory: async_sessionmaker | None = None,
    routing_provider: RoutingProvider | None = None,
    geocoding_provider: GeocodingProvider | None = None,
    push_provider: PushProvider | None = None,
    rate_limiter: RateLimiter | None = None,
    driver_document_store: ProtectedDriverDocumentStore | None = None,
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
    geocoding = geocoding_provider or create_geocoding_provider(
        active_settings.geocoding_provider,
        active_settings.geocoding_base_url,
        timeout_seconds=active_settings.geocoding_timeout_seconds,
        user_agent=active_settings.geocoding_user_agent,
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
    documents = driver_document_store or create_driver_document_store(
        root=active_settings.driver_document_storage_root,
        encryption_key=active_settings.driver_document_encryption_key,
        clamav_host=active_settings.driver_document_clamav_host,
        clamav_port=active_settings.driver_document_clamav_port,
        clamav_timeout_seconds=active_settings.driver_document_clamav_timeout_seconds,
        max_bytes=active_settings.driver_document_max_bytes,
    )
    worker_runtime = (
        BackgroundWorkerRuntime(
            sessions,
            active_settings,
            live_event_publisher,
            push,
            documents,
        )
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
            await geocoding.aclose()
            if push is not None:
                await push.aclose()

    app = FastAPI(
        title="TaxiMobile API",
        version="0.1.0",
        openapi_url=f"{active_settings.api_prefix}/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = active_settings
    app.state.client_compatibility_policy = ClientCompatibilityPolicy(
        revision=active_settings.client_policy_revision,
        minimum_versions=active_settings.client_minimum_versions,
        recommended_versions=active_settings.client_recommended_versions,
    )
    app.state.session_factory = sessions
    app.state.rate_limiter = limiter
    app.state.metrics = MetricsRegistry(workers_enabled=worker_runtime is not None)
    app.state.event_hub = event_hub
    app.state.live_event_publisher = live_event_publisher
    app.state.routing_provider = routing
    app.state.geocoding_provider = geocoding
    app.state.push_provider = push
    app.state.driver_document_store = documents
    app.state.worker_runtime = worker_runtime
    logger = configure_logging(
        active_settings.log_level,
        log_file=active_settings.log_file,
        log_file_max_bytes=active_settings.log_file_max_bytes,
        log_file_backup_count=active_settings.log_file_backup_count,
    )
    register_error_handlers(app)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(active_settings.allowed_hosts))
    app.add_middleware(
        ClientCompatibilityMiddleware,
        policy=app.state.client_compatibility_policy,
        api_prefix=active_settings.api_prefix,
        enforced=active_settings.client_compatibility_enforced,
    )
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
                "X-CSRF-Token",
                "X-Request-ID",
                "X-TaxiMobile-Client",
                "X-TaxiMobile-Version",
                "X-TaxiMobile-Build",
            ],
            expose_headers=[
                "X-TaxiMobile-Client-Policy",
                "X-TaxiMobile-Minimum-Version",
                "X-TaxiMobile-Recommended-Version",
            ],
        )
    app.add_middleware(
        ResponseSecurityMiddleware,
        hsts_enabled=active_settings.environment == "production",
    )
    app.add_middleware(
        DriverDocumentBodyLimitMiddleware,
        max_file_bytes=active_settings.driver_document_max_bytes,
    )
    app.add_middleware(
        RequestAuditMiddleware,
        metrics=app.state.metrics,
        logger=logger,
        api_prefix=active_settings.api_prefix,
        legacy_admin_api_enabled=active_settings.legacy_admin_api_enabled,
    )
    app.include_router(
        create_v1_router(
            legacy_admin_api_enabled=active_settings.legacy_admin_api_enabled,
        ),
        prefix=active_settings.api_prefix,
    )

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready", tags=["system"], response_model=None)
    async def ready() -> JSONResponse | dict[str, str]:
        try:
            if live_event_listener is not None and not live_event_listener.is_ready:
                raise RuntimeError("The shared live-event listener is not ready.")
            async with sessions() as session:
                await session.execute(text("SELECT 1"))
            if live_event_listener is not None and not live_event_listener.is_ready:
                raise RuntimeError("The shared live-event listener lost readiness.")
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
            # HTTP/process telemetry remains scrapeable during a database
            # incident; an explicit gauge marks the aggregate snapshot absent.
            outbox_metrics = OutboxMetrics(available=False)
        else:
            outbox_metrics = outbox_result
        if not isinstance(database_result, DatabaseMetrics):
            database_metrics = DatabaseMetrics(available=False)
        else:
            database_metrics = database_result
        if not isinstance(security_incident_result, SecurityIncidentMetrics):
            security_incident_metrics = SecurityIncidentMetrics(available=False)
        else:
            security_incident_metrics = security_incident_result
        try:
            database_pool_metrics = collect_database_pool_metrics(sessions)
        except Exception:
            database_pool_metrics = DatabasePoolMetrics(available=False)
        return PlainTextResponse(
            app.state.metrics.render_prometheus(
                outbox=outbox_metrics,
                database=database_metrics,
                database_pool=database_pool_metrics,
                security_incidents=security_incident_metrics,
            ),
            media_type="text/plain; version=0.0.4",
        )

    @app.websocket(f"{active_settings.api_prefix}/events")
    async def live_events(websocket: WebSocket) -> None:
        """Connected apps receive hints and must reload REST resources afterward."""
        if active_settings.client_compatibility_enforced:
            try:
                identity = parse_client_identity(
                    {key.lower(): value for key, value in websocket.headers.items()}
                )
                compatibility = app.state.client_compatibility_policy.assess(identity)
            except ClientIdentityError:
                await websocket.close(code=4406)
                return
            if compatibility.status == ClientCompatibilityStatus.UPGRADE_REQUIRED:
                await websocket.close(code=4406)
                return
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
