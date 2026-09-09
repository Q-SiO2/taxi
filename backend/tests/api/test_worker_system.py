from fastapi.testclient import TestClient
import pytest

from taximobile_api.core.config import ConfigurationError, Settings
from taximobile_api.core.metrics import (
    DatabaseMetrics,
    OutboxMetrics,
    SecurityIncidentMetrics,
    SecurityIncidentSeverityMetrics,
)
from taximobile_api.worker import create_worker_app


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


class RecordingWorkerRuntime:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    @property
    def is_running(self) -> bool:
        return self.started and not self.stopped

    def start(self, metrics) -> None:
        self.started = True
        for worker in (
            "matching",
            "outbox",
            "credentials",
            "scheduling",
            "analytics",
            "case_alerts",
            "case_retention",
            "driver_document_retention",
        ):
            metrics.record_worker_success(worker, processed=0, observed_at=1_700_000_000)

    async def stop(self) -> None:
        self.stopped = True


def test_worker_operations_surface_is_private_bounded_and_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    token = "worker-monitoring-token-with-32-characters"
    monkeypatch.setenv("TAXIMOBILE_PROCESS_ROLE", "worker")
    monkeypatch.setenv("TAXIMOBILE_MONITORING_TOKEN", token)

    async def available_outbox_metrics(_sessions):
        return OutboxMetrics(available=True, pending_events=1)

    async def available_database_metrics(_sessions):
        return DatabaseMetrics(
            available=True,
            connections=4,
            active_connections=1,
            connection_limit=100,
        )

    async def available_security_incident_metrics(_sessions):
        return SecurityIncidentMetrics(
            available=True,
            severities=(
                SecurityIncidentSeverityMetrics("SEV1", 1, 1, 0, 0),
                SecurityIncidentSeverityMetrics("SEV2"),
                SecurityIncidentSeverityMetrics("SEV3"),
                SecurityIncidentSeverityMetrics("SEV4"),
            ),
        )

    monkeypatch.setattr("taximobile_api.worker.collect_outbox_metrics", available_outbox_metrics)
    monkeypatch.setattr(
        "taximobile_api.worker.collect_database_metrics",
        available_database_metrics,
    )
    monkeypatch.setattr(
        "taximobile_api.worker.collect_security_incident_metrics",
        available_security_incident_metrics,
    )
    runtime = RecordingWorkerRuntime()
    app = create_worker_app(
        settings=Settings.from_environment(),
        session_factory=ReadySessionFactory(),  # type: ignore[arg-type]
        worker_runtime=runtime,  # type: ignore[arg-type]
    )

    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok", "service": "taximobile-worker"}
        readiness = client.get("/ready")
        assert readiness.json() == {"status": "ready", "service": "taximobile-worker"}
        assert readiness.headers["Cache-Control"] == "no-store"
        assert readiness.headers["X-Content-Type-Options"] == "nosniff"
        assert client.get("/api/v1/meta").status_code == 404
        assert client.get("/openapi.json").status_code == 404
        unauthorized = client.get("/internal/metrics", headers={"Authorization": "Bearer wrong"})
        metrics = client.get("/internal/metrics", headers={"Authorization": f"Bearer {token}"})

        assert unauthorized.status_code == 401
        assert unauthorized.headers["WWW-Authenticate"] == "Bearer"
        assert metrics.status_code == 200
        assert "taximobile_outbox_metrics_available 1" in metrics.text
        assert "taximobile_database_connection_utilization_ratio 0.04" in metrics.text
        assert (
            'taximobile_security_incidents_open{incident_severity="SEV1"} 1'
            in metrics.text
        )
        assert (
            'taximobile_security_incidents_containment_overdue{incident_severity="SEV1"} 1'
            in metrics.text
        )
        assert 'taximobile_worker_iterations_total{worker="credentials",outcome="success"} 1' in metrics.text
        assert 'taximobile_worker_iterations_total{worker="scheduling",outcome="success"} 1' in metrics.text
        assert 'taximobile_worker_iterations_total{worker="analytics",outcome="success"} 1' in metrics.text
        assert 'taximobile_worker_iterations_total{worker="case_alerts",outcome="success"} 1' in metrics.text
        assert 'taximobile_worker_iterations_total{worker="case_retention",outcome="success"} 1' in metrics.text
        assert 'taximobile_worker_iterations_total{worker="driver_document_retention",outcome="success"} 1' in metrics.text
        assert token not in metrics.text

    assert runtime.started
    assert runtime.stopped


def test_worker_refuses_the_api_only_role(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAXIMOBILE_PROCESS_ROLE", "api")

    with pytest.raises(ConfigurationError, match="worker application"):
        create_worker_app(settings=Settings.from_environment())
