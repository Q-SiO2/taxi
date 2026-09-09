from dataclasses import replace

from fastapi.testclient import TestClient
import pytest

from taximobile_api.core.config import Settings
from taximobile_api.core.client_compatibility import ClientSurface
from taximobile_api.main import create_app


class UnavailableRateLimiter:
    async def allow(self, *_, **__) -> bool:
        from taximobile_api.core.rate_limit import RateLimitUnavailable

        raise RateLimitUnavailable("private database detail")


class UnavailableSessionContext:
    async def __aenter__(self):
        raise RuntimeError("private database connection detail")

    async def __aexit__(self, *_):
        return False


class UnavailableSessionFactory:
    def __call__(self):
        return UnavailableSessionContext()


class ReadySession:
    async def execute(self, _statement):
        return None


class ReadySessionContext:
    async def __aenter__(self):
        return ReadySession()

    async def __aexit__(self, *_):
        return False


class ReadySessionFactory:
    def __call__(self):
        return ReadySessionContext()


def compatibility_versions(value: str) -> tuple[tuple[str, str], ...]:
    return tuple((surface.value, value) for surface in ClientSurface)


def compatibility_headers(
    *,
    surface: str = "ANDROID_PASSENGER",
    version: str = "2.0.0",
    build: str = "20",
) -> dict[str, str]:
    return {
        "X-TaxiMobile-Client": surface,
        "X-TaxiMobile-Version": version,
        "X-TaxiMobile-Build": build,
    }


def compatibility_settings() -> Settings:
    return replace(
        Settings.from_environment(),
        client_compatibility_enforced=True,
        client_policy_revision="pilot-2",
        client_minimum_versions=compatibility_versions("2.0.0"),
        client_recommended_versions=compatibility_versions("2.1.0"),
    )


def test_health_does_not_depend_on_database() -> None:
    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]


def test_http_responses_are_non_cacheable_and_browser_hardened() -> None:
    response = TestClient(create_app()).get("/health")

    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Pragma"] == "no-cache"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "Strict-Transport-Security" not in response.headers


def test_hsts_is_emitted_only_for_production_https_requests() -> None:
    production_settings = replace(
        Settings.from_environment(),
        environment="production",
        process_role="api",
        allowed_hosts=("api.example.test",),
    )
    app = create_app(
        settings=production_settings,
        session_factory=ReadySessionFactory(),  # type: ignore[arg-type]
    )

    secure = TestClient(app, base_url="https://api.example.test").get("/health")
    cleartext = TestClient(app, base_url="http://api.example.test").get("/health")

    assert secure.headers["Strict-Transport-Security"] == "max-age=31536000"
    assert "Strict-Transport-Security" not in cleartext.headers


def test_configured_browser_origin_can_preflight_documented_command_contract() -> None:
    origin = "https://console.example.test"
    settings = replace(
        Settings.from_environment(),
        process_role="api",
        cors_origins=(origin,),
    )
    client = TestClient(create_app(settings=settings))
    common_headers = {
        "Origin": origin,
        "Access-Control-Request-Headers": (
            "authorization,content-type,idempotency-key,x-request-id"
        ),
    }

    create_preflight = client.options(
        "/api/v1/rides",
        headers={**common_headers, "Access-Control-Request-Method": "POST"},
    )
    delete_preflight = client.options(
        "/api/v1/devices",
        headers={**common_headers, "Access-Control-Request-Method": "DELETE"},
    )
    rejected_origin = client.options(
        "/api/v1/rides",
        headers={
            **common_headers,
            "Origin": "https://untrusted.example.test",
            "Access-Control-Request-Method": "POST",
        },
    )

    for response in (create_preflight, delete_preflight):
        assert response.status_code == 200
        assert response.headers["Access-Control-Allow-Origin"] == origin
        assert response.headers["Access-Control-Allow-Credentials"] == "true"
        assert "DELETE" in response.headers["Access-Control-Allow-Methods"]
        allowed_headers = response.headers["Access-Control-Allow-Headers"].lower()
        assert "idempotency-key" in allowed_headers
        assert "x-request-id" in allowed_headers
        assert response.headers["Cache-Control"] == "no-store"
    assert rejected_origin.status_code == 400
    assert "Access-Control-Allow-Origin" not in rejected_origin.headers


def test_readiness_database_failure_is_a_safe_service_unavailable_response() -> None:
    response = TestClient(
        create_app(session_factory=UnavailableSessionFactory()),  # type: ignore[arg-type]
        raise_server_exceptions=False,
    ).get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "DEPENDENCY_UNAVAILABLE",
            "message": "The service is not ready.",
            "details": {},
        }
    }
    assert "private database connection detail" not in response.text


def test_readiness_accepts_reviewed_host_and_rejects_loopback_host_header() -> None:
    settings = replace(
        Settings.from_environment(),
        process_role="api",
        allowed_hosts=("api.example.test",),
    )
    app = create_app(
        settings=settings,
        session_factory=ReadySessionFactory(),  # type: ignore[arg-type]
    )

    allowed = TestClient(app, base_url="http://api.example.test").get("/ready")
    rejected = TestClient(app, base_url="http://127.0.0.1").get("/ready")

    assert allowed.status_code == 200
    assert allowed.json() == {"status": "ready"}
    assert rejected.status_code == 400


def test_unhandled_errors_use_a_safe_correlated_envelope() -> None:
    app = create_app()

    @app.get("/failure")
    async def failure() -> None:
        raise RuntimeError("private-provider-secret")

    request_id = "11111111-1111-4111-8111-111111111111"
    response = TestClient(app, raise_server_exceptions=False).get(
        "/failure", headers={"X-Request-ID": request_id}
    )

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred.",
            "details": {},
        }
    }
    assert response.headers["X-Request-ID"] == request_id
    assert "private-provider-secret" not in response.text


def test_shared_rate_limit_failure_is_a_safe_service_unavailable_response() -> None:
    app = create_app(rate_limiter=UnavailableRateLimiter())
    request_id = "22222222-2222-4222-8222-222222222222"
    response = TestClient(app, raise_server_exceptions=False).post(
        "/api/v1/auth/register",
        headers={"X-Request-ID": request_id},
        json={
            "email": "passenger@example.com",
            "password": "a-long-passenger-password",
            "display_name": "Passenger",
        },
    )

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "DEPENDENCY_UNAVAILABLE",
            "message": "The service is temporarily unavailable.",
            "details": {},
        }
    }
    assert response.headers["X-Request-ID"] == request_id
    assert "private database detail" not in response.text


def test_untrusted_correlation_id_is_not_reflected(capsys) -> None:
    private_value = "passenger@example.com"

    response = TestClient(create_app()).get(
        "/health",
        headers={"X-Request-ID": private_value},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != private_value
    assert private_value not in capsys.readouterr().err


def test_validation_errors_never_echo_passwords_or_submitted_values() -> None:
    submitted_password = "short-key"
    submitted_email = "not-an-email"

    response = TestClient(create_app()).post(
        "/api/v1/auth/register",
        json={
            "email": submitted_email,
            "password": submitted_password,
            "display_name": "Passenger",
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "The request contains invalid data.",
            "details": {
                "fields": [
                    {"field": "body.email", "code": "value_error"},
                    {"field": "body.password", "code": "string_too_short"},
                ]
            },
        }
    }
    assert submitted_password not in response.text
    assert submitted_email not in response.text


def test_metrics_are_disabled_without_a_monitoring_token() -> None:
    response = TestClient(create_app()).get("/internal/metrics")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_metrics_require_the_dedicated_token_and_never_label_raw_paths(monkeypatch) -> None:
    from taximobile_api.core.metrics import (
        DatabaseMetrics,
        OutboxMetrics,
        SecurityIncidentMetrics,
    )

    async def unavailable_outbox_metrics(_sessions):
        return OutboxMetrics(available=False)

    async def unavailable_database_metrics(_sessions):
        return DatabaseMetrics(available=False)

    async def unavailable_security_incident_metrics(_sessions):
        return SecurityIncidentMetrics(available=False)

    token = "monitoring-test-token-with-32-characters"
    monkeypatch.setenv("TAXIMOBILE_MONITORING_TOKEN", token)
    monkeypatch.setattr("taximobile_api.main.collect_outbox_metrics", unavailable_outbox_metrics)
    monkeypatch.setattr(
        "taximobile_api.main.collect_database_metrics",
        unavailable_database_metrics,
    )
    monkeypatch.setattr(
        "taximobile_api.main.collect_security_incident_metrics",
        unavailable_security_incident_metrics,
    )
    app = create_app(settings=Settings.from_environment())
    client = TestClient(app)

    client.get("/health")
    client.get("/api/v1/missing-private-ride-id")
    unauthorized = client.get("/internal/metrics", headers={"Authorization": "Bearer wrong-token"})
    response = client.get("/internal/metrics", headers={"Authorization": f"Bearer {token}"})

    assert unauthorized.status_code == 401
    assert unauthorized.headers["WWW-Authenticate"] == "Bearer"
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain; version=0.0.4")
    assert 'route="/health",status_class="2xx"} 1' in response.text
    assert 'route="_unmatched",status_class="4xx"} 1' in response.text
    assert "taximobile_outbox_metrics_available 0" in response.text
    assert "taximobile_database_metrics_available 0" in response.text
    assert "taximobile_security_incident_metrics_available 0" in response.text
    assert "missing-private-ride-id" not in response.text
    assert token not in response.text


def test_metrics_database_failure_keeps_process_telemetry_scrapeable(monkeypatch) -> None:
    from taximobile_api.db.metrics import DatabaseMetricsUnavailable
    from taximobile_api.domains.outbox.metrics import OutboxMetricsUnavailable
    from taximobile_api.domains.security_incidents.metrics import (
        SecurityIncidentMetricsUnavailable,
    )

    async def unavailable_outbox_metrics(_sessions):
        raise OutboxMetricsUnavailable("private database connection detail")

    async def unavailable_database_metrics(_sessions):
        raise DatabaseMetricsUnavailable("private capacity connection detail")

    async def unavailable_security_incident_metrics(_sessions):
        raise SecurityIncidentMetricsUnavailable("private incident schema detail")

    token = "monitoring-test-token-with-32-characters"
    monkeypatch.setenv("TAXIMOBILE_MONITORING_TOKEN", token)
    monkeypatch.setattr("taximobile_api.main.collect_outbox_metrics", unavailable_outbox_metrics)
    monkeypatch.setattr(
        "taximobile_api.main.collect_database_metrics",
        unavailable_database_metrics,
    )
    monkeypatch.setattr(
        "taximobile_api.main.collect_security_incident_metrics",
        unavailable_security_incident_metrics,
    )
    client = TestClient(create_app(settings=Settings.from_environment()))

    response = client.get("/internal/metrics", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert "taximobile_outbox_metrics_available 0" in response.text
    assert "taximobile_outbox_pending_events" not in response.text
    assert "taximobile_database_metrics_available 0" in response.text
    assert "taximobile_database_connections" not in response.text
    assert "taximobile_security_incident_metrics_available 0" in response.text
    assert "taximobile_security_incidents_open" not in response.text
    assert "private database connection detail" not in response.text
    assert "private capacity connection detail" not in response.text
    assert "private incident schema detail" not in response.text


def test_v1_metadata_exposes_the_versioned_contract() -> None:
    response = TestClient(create_app()).get("/api/v1/meta")

    assert response.status_code == 200
    assert response.json() == {"service": "taximobile-api", "version": "v1"}


def test_enforced_api_rejects_missing_unknown_and_obsolete_client_builds() -> None:
    client = TestClient(create_app(settings=compatibility_settings()))

    missing = client.get("/api/v1/meta")
    unknown = client.get(
        "/api/v1/meta",
        headers=compatibility_headers(surface="UNREVIEWED_CLIENT"),
    )
    obsolete = client.get(
        "/api/v1/meta",
        headers=compatibility_headers(version="1.9.9"),
    )

    for response in (missing, unknown):
        assert response.status_code == 426
        assert response.json()["error"]["code"] == "CLIENT_IDENTITY_REQUIRED"
        assert response.headers["X-TaxiMobile-Client-Policy"] == "pilot-2"
    assert obsolete.status_code == 426
    assert obsolete.json() == {
        "error": {
            "code": "CLIENT_UPGRADE_REQUIRED",
            "message": "This TaxiMobile client must be upgraded before it can continue.",
            "details": {
                "api_version": "v1",
                "policy_revision": "pilot-2",
                "minimum_version": "2.0.0",
                "recommended_version": "2.1.0",
            },
        }
    }
    assert obsolete.headers["X-TaxiMobile-Minimum-Version"] == "2.0.0"
    assert "1.9.9" not in obsolete.text


def test_supported_client_reaches_v1_and_receives_policy_headers() -> None:
    response = TestClient(create_app(settings=compatibility_settings())).get(
        "/api/v1/meta",
        headers=compatibility_headers(version="2.0.0"),
    )

    assert response.status_code == 200
    assert response.json() == {"service": "taximobile-api", "version": "v1"}
    assert response.headers["X-TaxiMobile-Client-Policy"] == "pilot-2"
    assert response.headers["X-TaxiMobile-Minimum-Version"] == "2.0.0"
    assert response.headers["X-TaxiMobile-Recommended-Version"] == "2.1.0"


def test_browser_can_read_upgrade_policy_through_the_reviewed_cors_boundary() -> None:
    origin = "https://console.example.test"
    settings = replace(compatibility_settings(), cors_origins=(origin,))
    response = TestClient(create_app(settings=settings)).get(
        "/api/v1/meta",
        headers={**compatibility_headers(version="1.0.0"), "Origin": origin},
    )

    assert response.status_code == 426
    assert response.headers["Access-Control-Allow-Origin"] == origin
    exposed = response.headers["Access-Control-Expose-Headers"].lower()
    assert "x-taximobile-minimum-version" in exposed
    assert "x-taximobile-client-policy" in exposed


def test_compatibility_preflight_reports_status_without_command_or_authentication() -> None:
    client = TestClient(create_app(settings=compatibility_settings()))

    required = client.get(
        "/api/v1/client-compatibility",
        headers=compatibility_headers(version="1.0.0"),
    )
    available = client.get(
        "/api/v1/client-compatibility",
        headers=compatibility_headers(version="2.0.0"),
    )
    malformed = client.get(
        "/api/v1/client-compatibility",
        headers=compatibility_headers(build="0"),
    )

    assert required.status_code == 200
    assert required.json()["status"] == "UPGRADE_REQUIRED"
    assert required.json()["minimum_version"] == "2.0.0"
    assert available.status_code == 200
    assert available.json()["status"] == "UPDATE_AVAILABLE"
    assert malformed.status_code == 400
    assert malformed.json()["error"]["code"] == "CLIENT_IDENTITY_INVALID"


def test_enforced_websocket_refuses_missing_client_identity_before_authentication() -> None:
    from starlette.websockets import WebSocketDisconnect

    client = TestClient(create_app(settings=compatibility_settings()))
    with pytest.raises(WebSocketDisconnect) as failure:
        with client.websocket_connect("/api/v1/events"):
            pass

    assert failure.value.code == 4406


def test_openapi_exposes_mobile_account_recovery_and_session_control() -> None:
    response = TestClient(create_app()).get("/api/v1/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/auth/recovery/reset" in paths
    assert "/api/v1/auth/recovery-codes" in paths
    assert "/api/v1/auth/password/change" in paths
    assert "/api/v1/auth/sessions" in paths
    assert "/api/v1/auth/sessions/{session_id}" in paths


def test_openapi_exposes_the_administration_contract() -> None:
    response = TestClient(create_app()).get("/api/v1/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/admin/drivers/{driver_id}/approve" in response.json()["paths"]
    assert "/api/v1/admin/pricing-rules/{pricing_rule_id}/activate" in response.json()["paths"]
    assert "/api/v1/admin/vehicles/{vehicle_id}/verify" in response.json()["paths"]
    assert "/api/v1/admin/users/{user_id}/sessions/revoke" in response.json()["paths"]
    assert "/api/v1/admin/users/{user_id}/suspend" in response.json()["paths"]
    assert "/api/v1/admin/users/{user_id}/reactivate" in response.json()["paths"]
    assert "/api/v1/admin/audit-logs" in response.json()["paths"]


def test_legacy_admin_requests_are_deprecated_and_counted_as_routed() -> None:
    app = create_app()
    response = TestClient(app).get("/api/v1/admin/audit-logs")

    assert response.status_code == 401
    assert response.headers["Deprecation"] == "true"
    assert "local/test-only" in response.headers["Warning"]
    assert (
        'taximobile_legacy_admin_http_requests_total{outcome="served"} 1'
        in app.state.metrics.render_prometheus()
    )


def test_openapi_removes_every_legacy_admin_route_when_compatibility_is_disabled() -> None:
    settings = replace(Settings.from_environment(), legacy_admin_api_enabled=False)

    response = TestClient(create_app(settings=settings)).get("/api/v1/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert not any(path.startswith("/api/v1/admin") for path in paths)
    assert "/api/v1/operations/markets" in paths
    assert "/api/v1/operations/payments/manual-transfers" in paths
    assert "/api/v1/operations/support/tickets" in paths
    assert "/api/v1/operations/safety/reports" in paths


def test_disabled_legacy_admin_probe_is_counted_without_advertising_the_surface() -> None:
    settings = replace(Settings.from_environment(), legacy_admin_api_enabled=False)
    app = create_app(settings=settings)
    response = TestClient(app).get("/api/v1/admin/audit-logs")

    assert response.status_code == 404
    assert "Deprecation" not in response.headers
    assert "Warning" not in response.headers
    metrics = app.state.metrics.render_prometheus()
    assert (
        'taximobile_legacy_admin_http_requests_total{outcome="blocked"} 1'
        in metrics
    )
    assert "/api/v1/admin/audit-logs" not in metrics


def test_openapi_exposes_the_isolated_national_operations_foundation() -> None:
    response = TestClient(create_app()).get("/api/v1/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    for path in (
        "/api/v1/operations/auth/login",
        "/api/v1/operations/auth/mfa/verify",
        "/api/v1/operations/auth/mfa/step-up",
        "/api/v1/operations/auth/refresh",
        "/api/v1/operations/auth/logout",
        "/api/v1/operations/auth/session",
        "/api/v1/operations/markets",
        "/api/v1/operations/cities",
        "/api/v1/operations/cities/{city_id}",
        "/api/v1/operations/cities/{city_id}/lifecycle-transitions",
        "/api/v1/operations/operators",
        "/api/v1/operations/operator-city-assignments",
        "/api/v1/operations/administrative-grants",
        "/api/v1/operations/administrative-grant-requests",
        "/api/v1/operations/administrative-grant-requests/create",
        "/api/v1/operations/administrative-grant-requests/revoke",
        "/api/v1/operations/administrative-grant-requests/{request_id}/approve",
        "/api/v1/operations/administrative-grant-requests/{request_id}/reject",
        "/api/v1/operations/administrative-grant-requests/{request_id}/cancel",
        "/api/v1/operations/markets/{market_id}/users/{user_id}/sessions/revoke",
        "/api/v1/operations/markets/{market_id}/users/{user_id}/suspend",
        "/api/v1/operations/markets/{market_id}/users/{user_id}/reactivate",
        "/api/v1/operations/cities/{city_id}/service-area-versions",
        "/api/v1/operations/cities/{city_id}/configuration-versions",
        "/api/v1/operations/city-configuration-versions/{version_id}/activate",
        "/api/v1/operations/cities/{city_id}/driver-requirement-versions",
        "/api/v1/operations/driver-requirement-versions/{version_id}",
        "/api/v1/operations/driver-requirement-versions/{version_id}/submit",
        "/api/v1/operations/driver-requirement-versions/{version_id}/activate",
        "/api/v1/operations/driver-applications",
        "/api/v1/operations/driver-applications/{application_id}",
        "/api/v1/operations/driver-applications/{application_id}/decisions",
        "/api/v1/operations/driver-applications/{application_id}/vehicles/{vehicle_id}/verify",
        "/api/v1/operations/cities/{city_id}/operational-aggregates",
        "/api/v1/operations/rollout-overview",
        "/api/v1/operations/audit-logs",
    ):
        assert path in paths


def test_openapi_exposes_city_driver_recruitment_contract() -> None:
    response = TestClient(create_app()).get("/api/v1/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/drivers/recruiting-cities" in paths
    assert "/api/v1/drivers/recruiting-cities/{city_id}/requirements" in paths
    assert {"get", "post"}.issubset(paths["/api/v1/drivers/me/city-applications"])
    assert {"get", "patch"}.issubset(
        paths["/api/v1/drivers/me/city-applications/{application_id}"]
    )
    assert "/api/v1/drivers/me/city-applications/{application_id}/submit" in paths
    assert "/api/v1/drivers/me/city-applications/{application_id}/withdraw" in paths
    assert "/api/v1/drivers/me/city-applications/{application_id}/documents" in paths


def test_openapi_exposes_scheduled_booking_and_driver_commitment_contracts() -> None:
    response = TestClient(create_app()).get("/api/v1/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert {"get", "post"}.issubset(paths["/api/v1/scheduled-bookings"])
    assert "/api/v1/scheduled-bookings/estimate" in paths
    assert "/api/v1/scheduled-bookings/{booking_id}" in paths
    assert "/api/v1/scheduled-bookings/{booking_id}/cancel" in paths
    assert "/api/v1/drivers/me/scheduled-offers" in paths
    assert "/api/v1/drivers/me/scheduled-offer-preference" in paths
    assert "/api/v1/drivers/me/scheduled-offer-preferences" in paths
    assert "/api/v1/scheduled-offers/{offer_id}/accept" in paths
    assert "/api/v1/scheduled-offers/{offer_id}/decline" in paths
    assert "/api/v1/drivers/me/scheduled-commitments" in paths


def test_openapi_exposes_scoped_aggregate_only_analytics_contracts() -> None:
    response = TestClient(create_app()).get("/api/v1/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/operations/analytics/definitions" in paths
    assert "/api/v1/operations/analytics/facts" in paths


def test_openapi_exposes_the_passenger_profile_contract() -> None:
    response = TestClient(create_app()).get("/api/v1/openapi.json")

    assert response.status_code == 200
    profile_path = response.json()["paths"]["/api/v1/passenger/profile"]
    assert {"get", "patch"}.issubset(profile_path)


def test_openapi_exposes_the_full_documented_vehicle_lifecycle() -> None:
    response = TestClient(create_app()).get("/api/v1/openapi.json")

    assert response.status_code == 200
    vehicle_path = response.json()["paths"]["/api/v1/drivers/me/vehicles/{vehicle_id}"]
    assert {"patch", "delete"}.issubset(vehicle_path)


def test_openapi_exposes_driver_verification_submission() -> None:
    response = TestClient(create_app()).get("/api/v1/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/drivers/me/verification" in response.json()["paths"]


def test_openapi_exposes_the_fare_estimate_and_receipt_contract() -> None:
    response = TestClient(create_app()).get("/api/v1/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/rides/estimate" in paths
    assert "/api/v1/rides/{ride_id}/fare" in paths
    assert "/api/v1/rides/{ride_id}/receipt" in paths
    ride_schema = paths["/api/v1/rides/{ride_id}"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert ride_schema["$ref"].endswith("/RideResponse")
    assert "/api/v1/rides/{ride_id}/payments/manual-transfer/submit" in paths
    assert "/api/v1/admin/payments/manual-transfers" in paths
    assert "/api/v1/admin/payments/{payment_id}/manual-transfer/verify" in paths
    assert "/api/v1/admin/payments/{payment_id}/manual-transfer/reject" in paths
    assert "/api/v1/admin/payments/refunds" in paths
    assert "/api/v1/admin/payments/{payment_id}/refunds" in paths


def test_openapi_exposes_authorized_completed_ride_ratings() -> None:
    response = TestClient(create_app()).get("/api/v1/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/rides/{ride_id}/rating" in paths
    assert "/api/v1/rides/{ride_id}/ratings" in paths


def test_openapi_exposes_participant_owned_support_tickets() -> None:
    response = TestClient(create_app()).get("/api/v1/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/support/tickets" in paths
    assert "/api/v1/support/tickets/{ticket_id}" in paths
    assert "/api/v1/admin/support/tickets" in paths
    assert "/api/v1/admin/support/tickets/{ticket_id}" in paths
    assert "/api/v1/admin/support/tickets/{ticket_id}/triage" in paths
    assert "/api/v1/admin/support/tickets/{ticket_id}/transition" in paths
    assert "/api/v1/admin/support/tickets/{ticket_id}/escalate-safety" in paths
    assert "/api/v1/operations/support/tickets" in paths
    assert "/api/v1/operations/support/tickets/{ticket_id}" in paths
    assert "/api/v1/operations/support/tickets/{ticket_id}/triage" in paths
    assert "/api/v1/operations/support/tickets/{ticket_id}/transition" in paths
    assert "/api/v1/operations/support/tickets/{ticket_id}/escalate-safety" in paths
    assert "/api/v1/safety/reports" in paths
    assert "/api/v1/safety/reports/{report_id}" in paths
    assert "/api/v1/admin/safety/reports" in paths
    assert "/api/v1/admin/safety/reports/{report_id}" in paths
    assert "/api/v1/admin/safety/reports/{report_id}/transition" in paths
    assert "/api/v1/operations/safety/reports" in paths
    assert "/api/v1/operations/safety/reports/{report_id}" in paths
    assert "/api/v1/operations/safety/reports/{report_id}/transition" in paths
    assert "/api/v1/operations/case-alerts" in paths
    assert "/api/v1/operations/case-alerts/{alert_id}/acknowledge" in paths
    assert "/api/v1/operations/case-retention/holds" in paths
    assert "/api/v1/operations/case-retention/holds/{hold_id}/release" in paths
    assert "/api/v1/operations/case-retention/actions" in paths


def test_openapi_exposes_notification_history_and_device_registration() -> None:
    response = TestClient(create_app()).get("/api/v1/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/notifications" in paths
    assert "/api/v1/notifications/{notification_id}/read" in paths
    assert {"post", "delete"}.issubset(paths["/api/v1/devices"])


def test_openapi_requires_idempotency_headers_for_retry_sensitive_commands() -> None:
    response = TestClient(create_app()).get("/api/v1/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    for path, method in (
        ("/api/v1/rides", "post"),
        ("/api/v1/rides/{ride_id}/cancel", "post"),
        ("/api/v1/rides/{ride_id}/driver-cancel", "post"),
        ("/api/v1/rides/{ride_id}/complete", "post"),
        ("/api/v1/rides/{ride_id}/payments/cash/settle", "post"),
        ("/api/v1/rides/{ride_id}/payments/manual-transfer/submit", "post"),
        ("/api/v1/admin/payments/{payment_id}/manual-transfer/verify", "post"),
        ("/api/v1/admin/payments/{payment_id}/manual-transfer/reject", "post"),
        ("/api/v1/admin/payments/{payment_id}/refunds", "post"),
        (
            "/api/v1/operations/driver-applications/{application_id}/vehicles/{vehicle_id}/verify",
            "post",
        ),
        ("/api/v1/operations/markets/{market_id}/users/{user_id}/sessions/revoke", "post"),
        ("/api/v1/operations/markets/{market_id}/users/{user_id}/suspend", "post"),
        ("/api/v1/operations/markets/{market_id}/users/{user_id}/reactivate", "post"),
        ("/api/v1/support/tickets", "post"),
        ("/api/v1/admin/support/tickets/{ticket_id}/triage", "post"),
        ("/api/v1/admin/support/tickets/{ticket_id}/transition", "post"),
        ("/api/v1/admin/support/tickets/{ticket_id}/escalate-safety", "post"),
        ("/api/v1/operations/support/tickets/{ticket_id}/triage", "post"),
        ("/api/v1/operations/support/tickets/{ticket_id}/transition", "post"),
        ("/api/v1/operations/support/tickets/{ticket_id}/escalate-safety", "post"),
        ("/api/v1/safety/reports", "post"),
        ("/api/v1/admin/safety/reports/{report_id}/transition", "post"),
        ("/api/v1/operations/safety/reports/{report_id}/transition", "post"),
        ("/api/v1/operations/case-alerts/{alert_id}/acknowledge", "post"),
        ("/api/v1/operations/case-retention/holds", "post"),
        ("/api/v1/operations/case-retention/holds/{hold_id}/release", "post"),
    ):
        assert any(
            parameter["in"] == "header"
            and parameter["name"] == "Idempotency-Key"
            and parameter["required"]
            for parameter in paths[path][method]["parameters"]
        )


def test_openapi_exposes_driver_history_and_earnings_contracts() -> None:
    response = TestClient(create_app()).get("/api/v1/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/drivers/me/rides" in paths
    assert "/api/v1/drivers/me/earnings" in paths
    assert "/api/v1/drivers/me/credentials" in paths
    assert "/api/v1/cooperative/membership" in paths


def test_openapi_exposes_provider_neutral_routing_contract() -> None:
    response = TestClient(create_app()).get("/api/v1/openapi.json")

    assert response.status_code == 200
    route = response.json()["paths"]["/api/v1/routing/route"]["post"]
    assert route["tags"] == ["routing"]
    assert route["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/RouteResponse"
    )


def test_unknown_route_uses_the_documented_error_envelope() -> None:
    response = TestClient(create_app()).get("/api/v1/missing")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "NOT_FOUND",
            "message": "The requested resource was not found.",
            "details": {},
        }
    }


def test_login_fails_safely_when_authentication_is_not_configured(monkeypatch) -> None:
    monkeypatch.delenv("TAXIMOBILE_JWT_SECRET", raising=False)
    response = TestClient(create_app()).post(
        "/api/v1/auth/login",
        json={"identifier": "passenger@example.test", "password": "a-secure-enough-password"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "REQUEST_REJECTED"
