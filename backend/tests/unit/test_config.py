import pytest

from taximobile_api.core.config import ConfigurationError, Settings
from taximobile_api.core.live_events import PostgresLiveEventPublisher
from taximobile_api.core.rate_limit import PostgresRateLimiter
from taximobile_api.main import create_app


@pytest.mark.parametrize(
    "database_host",
    ["localhost", "LOCALHOST.", "127.0.0.1", "127.0.0.2", "::1"],
)
def test_staging_and_production_reject_loopback_database_hosts(
    monkeypatch: pytest.MonkeyPatch, database_host: str
) -> None:
    monkeypatch.setenv("TAXIMOBILE_ENV", "production")
    if ":" in database_host:
        database_host = f"[{database_host}]"
    monkeypatch.setenv("TAXIMOBILE_DATABASE_URL", f"postgresql+asyncpg://taxi:secret@{database_host}/taxi")

    with pytest.raises(ConfigurationError):
        Settings.from_environment()

    monkeypatch.setenv("TAXIMOBILE_ENV", "staging")
    monkeypatch.setenv("TAXIMOBILE_JWT_SECRET", "x" * 32)
    with pytest.raises(ConfigurationError):
        Settings.from_environment()


def test_production_accepts_a_remote_database_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAXIMOBILE_ENV", "production")
    monkeypatch.setenv("TAXIMOBILE_DATABASE_URL", "postgresql+asyncpg://taxi:secret@database.internal/taxi")
    monkeypatch.setenv("TAXIMOBILE_JWT_SECRET", "x" * 32)
    monkeypatch.setenv("TAXIMOBILE_ALLOWED_HOSTS", "API.Example.Test")
    monkeypatch.setenv("TAXIMOBILE_MONITORING_TOKEN", "m" * 32)

    settings = Settings.from_environment()
    assert settings.database_url.endswith("@database.internal/taxi")
    assert settings.allowed_hosts == ("api.example.test",)


def test_production_uses_the_shared_postgres_rate_limiter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAXIMOBILE_ENV", "production")
    monkeypatch.setenv("TAXIMOBILE_DATABASE_URL", "postgresql+asyncpg://taxi:secret@database.internal/taxi")
    monkeypatch.setenv("TAXIMOBILE_JWT_SECRET", "x" * 32)
    monkeypatch.setenv("TAXIMOBILE_ALLOWED_HOSTS", "api.example.test")
    monkeypatch.setenv("TAXIMOBILE_MONITORING_TOKEN", "m" * 32)
    monkeypatch.setenv("TAXIMOBILE_FIREBASE_PROJECT_ID", "taximobile-production")

    app = create_app(settings=Settings.from_environment())

    assert isinstance(app.state.rate_limiter, PostgresRateLimiter)
    assert isinstance(app.state.live_event_publisher, PostgresLiveEventPublisher)
    assert app.state.worker_runtime is None
    assert app.state.push_provider is None


def test_monitoring_token_is_strong_and_required_outside_development(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAXIMOBILE_MONITORING_TOKEN", "short")
    with pytest.raises(ConfigurationError, match="at least 32"):
        Settings.from_environment()

    monkeypatch.setenv("TAXIMOBILE_ENV", "production")
    monkeypatch.setenv("TAXIMOBILE_DATABASE_URL", "postgresql+asyncpg://taxi:secret@database.internal/taxi")
    monkeypatch.setenv("TAXIMOBILE_JWT_SECRET", "x" * 32)
    monkeypatch.setenv("TAXIMOBILE_ALLOWED_HOSTS", "api.example.test")
    monkeypatch.delenv("TAXIMOBILE_MONITORING_TOKEN")
    with pytest.raises(ConfigurationError, match="require TAXIMOBILE_MONITORING_TOKEN"):
        Settings.from_environment()

    monkeypatch.setenv("TAXIMOBILE_MONITORING_TOKEN", "m" * 32)
    assert Settings.from_environment().monitoring_token == "m" * 32


def test_development_has_an_isolated_default_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TAXIMOBILE_ENV", raising=False)
    monkeypatch.delenv("TAXIMOBILE_DATABASE_URL", raising=False)

    settings = Settings.from_environment()

    assert settings.environment == "development"
    assert settings.database_url.endswith("/taximobile")
    assert settings.allowed_hosts == ("localhost", "127.0.0.1", "testserver")
    assert settings.process_role == "all"


def test_process_role_is_closed_and_production_defaults_to_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAXIMOBILE_PROCESS_ROLE", "worker")
    assert Settings.from_environment().process_role == "worker"

    with pytest.raises(ConfigurationError, match="must be all, api, or worker"):
        monkeypatch.setenv("TAXIMOBILE_PROCESS_ROLE", "scheduler")
        Settings.from_environment()

    monkeypatch.delenv("TAXIMOBILE_PROCESS_ROLE")
    monkeypatch.setenv("TAXIMOBILE_ENV", "production")
    monkeypatch.setenv("TAXIMOBILE_DATABASE_URL", "postgresql+asyncpg://taxi:secret@database.internal/taxi")
    monkeypatch.setenv("TAXIMOBILE_JWT_SECRET", "x" * 32)
    monkeypatch.setenv("TAXIMOBILE_ALLOWED_HOSTS", "api.example.test")
    monkeypatch.setenv("TAXIMOBILE_MONITORING_TOKEN", "m" * 32)
    assert Settings.from_environment().process_role == "api"


def test_public_api_refuses_the_worker_only_role(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAXIMOBILE_PROCESS_ROLE", "worker")

    with pytest.raises(ConfigurationError, match="public API application"):
        create_app(settings=Settings.from_environment())


def test_production_worker_does_not_require_api_jwt_or_host_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAXIMOBILE_ENV", "production")
    monkeypatch.setenv("TAXIMOBILE_PROCESS_ROLE", "worker")
    monkeypatch.setenv("TAXIMOBILE_DATABASE_URL", "postgresql+asyncpg://taxi:secret@database.internal/taxi")
    monkeypatch.setenv("TAXIMOBILE_MONITORING_TOKEN", "m" * 32)
    monkeypatch.delenv("TAXIMOBILE_JWT_SECRET", raising=False)
    monkeypatch.delenv("TAXIMOBILE_ALLOWED_HOSTS", raising=False)

    settings = Settings.from_environment()

    assert settings.jwt_secret is None
    assert settings.process_role == "worker"


@pytest.mark.parametrize(
    "allowed_hosts",
    ["*", "*.example.test", "https://api.example.test", "api.example.test:443", "api_example.test"],
)
def test_production_rejects_non_exact_or_malformed_hosts(
    monkeypatch: pytest.MonkeyPatch, allowed_hosts: str
) -> None:
    monkeypatch.setenv("TAXIMOBILE_ENV", "production")
    monkeypatch.setenv("TAXIMOBILE_DATABASE_URL", "postgresql+asyncpg://taxi:secret@database/taxi")
    monkeypatch.setenv("TAXIMOBILE_JWT_SECRET", "x" * 32)
    monkeypatch.setenv("TAXIMOBILE_MONITORING_TOKEN", "m" * 32)
    monkeypatch.setenv("TAXIMOBILE_ALLOWED_HOSTS", allowed_hosts)

    with pytest.raises(ConfigurationError, match="exact DNS or IPv4 host names"):
        Settings.from_environment()


def test_production_rejects_wildcard_browser_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAXIMOBILE_ENV", "production")
    monkeypatch.setenv("TAXIMOBILE_DATABASE_URL", "postgresql+asyncpg://taxi:secret@database/taxi")
    monkeypatch.setenv("TAXIMOBILE_JWT_SECRET", "x" * 32)
    monkeypatch.setenv("TAXIMOBILE_MONITORING_TOKEN", "m" * 32)
    monkeypatch.setenv("TAXIMOBILE_ALLOWED_HOSTS", "api.example.test")
    monkeypatch.setenv("TAXIMOBILE_CORS_ORIGINS", "*")

    with pytest.raises(ConfigurationError, match="exact HTTPS origins"):
        Settings.from_environment()


@pytest.mark.parametrize(
    "origin",
    [
        "http://console.example.test",
        "https://*.example.test",
        "https://user:password@console.example.test",
        "https://console.example.test/",
        "https://console.example.test/path",
        "https://console.example.test?private=query",
        "https://console_example.test",
        "null",
    ],
)
def test_production_rejects_insecure_or_non_origin_cors_values(
    monkeypatch: pytest.MonkeyPatch, origin: str
) -> None:
    monkeypatch.setenv("TAXIMOBILE_ENV", "production")
    monkeypatch.setenv("TAXIMOBILE_DATABASE_URL", "postgresql+asyncpg://taxi:secret@database/taxi")
    monkeypatch.setenv("TAXIMOBILE_JWT_SECRET", "x" * 32)
    monkeypatch.setenv("TAXIMOBILE_MONITORING_TOKEN", "m" * 32)
    monkeypatch.setenv("TAXIMOBILE_ALLOWED_HOSTS", "api.example.test")
    monkeypatch.setenv("TAXIMOBILE_CORS_ORIGINS", origin)

    with pytest.raises(ConfigurationError, match="exact HTTPS origins"):
        Settings.from_environment()


def test_production_normalizes_exact_cors_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAXIMOBILE_ENV", "production")
    monkeypatch.setenv("TAXIMOBILE_DATABASE_URL", "postgresql+asyncpg://taxi:secret@database/taxi")
    monkeypatch.setenv("TAXIMOBILE_JWT_SECRET", "x" * 32)
    monkeypatch.setenv("TAXIMOBILE_MONITORING_TOKEN", "m" * 32)
    monkeypatch.setenv("TAXIMOBILE_ALLOWED_HOSTS", "api.example.test")
    monkeypatch.setenv("TAXIMOBILE_CORS_ORIGINS", "HTTPS://Console.Example.Test:8443")

    assert Settings.from_environment().cors_origins == (
        "https://console.example.test:8443",
    )


def test_rate_limits_are_environment_configurable_and_must_be_positive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAXIMOBILE_LOGIN_RATE_LIMIT_PER_MINUTE", "9")

    assert Settings.from_environment().login_rate_limit_per_minute == 9

    monkeypatch.setenv("TAXIMOBILE_LOGIN_RATE_LIMIT_PER_MINUTE", "0")
    with pytest.raises(ConfigurationError):
        Settings.from_environment()


@pytest.mark.parametrize(
    ("setting", "valid_value"),
    [
        ("TAXIMOBILE_MATCHING_RADIUS_METERS", "1500"),
        ("TAXIMOBILE_MATCHING_LOCATION_FRESHNESS_SECONDS", "15"),
        ("TAXIMOBILE_RIDE_OFFER_SECONDS", "20"),
        ("TAXIMOBILE_MATCHING_CANDIDATE_LIMIT", "5"),
        ("TAXIMOBILE_MATCHING_IDLE_CAP_SECONDS", "900"),
        ("TAXIMOBILE_MATCHING_FAIRNESS_LOOKBACK_HOURS", "12"),
        ("TAXIMOBILE_MATCHING_TIMEOUT_SECONDS", "120"),
    ],
)
def test_matching_settings_must_be_positive_integers(
    monkeypatch: pytest.MonkeyPatch, setting: str, valid_value: str
) -> None:
    monkeypatch.setenv(setting, valid_value)
    Settings.from_environment()

    for invalid_value in ("0", "-1", "invalid"):
        monkeypatch.setenv(setting, invalid_value)
        with pytest.raises(ConfigurationError):
            Settings.from_environment()


def test_outbox_poll_interval_must_be_a_safe_positive_duration(monkeypatch: pytest.MonkeyPatch) -> None:
    for setting in ("TAXIMOBILE_MATCHING_POLL_SECONDS", "TAXIMOBILE_OUTBOX_POLL_SECONDS"):
        for invalid_value in ("invalid", "NaN", "Infinity", "0.05", "60.1"):
            monkeypatch.setenv(setting, invalid_value)
            with pytest.raises(ConfigurationError):
                Settings.from_environment()
        monkeypatch.delenv(setting, raising=False)


def test_matching_score_weights_and_version_are_validated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAXIMOBILE_MATCHING_PROXIMITY_WEIGHT", "0")
    monkeypatch.setenv("TAXIMOBILE_MATCHING_IDLE_WEIGHT", "0")
    monkeypatch.setenv("TAXIMOBILE_MATCHING_FAIRNESS_WEIGHT", "0")
    with pytest.raises(ConfigurationError):
        Settings.from_environment()

    monkeypatch.setenv("TAXIMOBILE_MATCHING_PROXIMITY_WEIGHT", "1")
    monkeypatch.setenv("TAXIMOBILE_MATCHING_ALGORITHM_VERSION", "invalid version")
    with pytest.raises(ConfigurationError):
        Settings.from_environment()

    monkeypatch.setenv("TAXIMOBILE_MATCHING_ALGORITHM_VERSION", "cooperative-v2")
    assert Settings.from_environment().matching_algorithm_version == "cooperative-v2"


def test_outbox_attempt_limit_is_positive_and_configurable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAXIMOBILE_OUTBOX_MAX_ATTEMPTS", "12")
    assert Settings.from_environment().outbox_max_attempts == 12

    monkeypatch.setenv("TAXIMOBILE_OUTBOX_MAX_ATTEMPTS", "0")
    with pytest.raises(ConfigurationError):
        Settings.from_environment()


def test_credential_lifecycle_schedule_and_warning_window_are_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TAXIMOBILE_CREDENTIAL_POLL_SECONDS", "120")
    monkeypatch.setenv("TAXIMOBILE_CREDENTIAL_EXPIRY_WARNING_DAYS", "45")
    settings = Settings.from_environment()
    assert settings.credential_poll_seconds == 120
    assert settings.credential_expiry_warning_days == 45

    monkeypatch.setenv("TAXIMOBILE_CREDENTIAL_POLL_SECONDS", "301")
    with pytest.raises(ConfigurationError):
        Settings.from_environment()
    monkeypatch.setenv("TAXIMOBILE_CREDENTIAL_POLL_SECONDS", "60")
    monkeypatch.setenv("TAXIMOBILE_CREDENTIAL_EXPIRY_WARNING_DAYS", "366")
    with pytest.raises(ConfigurationError):
        Settings.from_environment()


def test_routing_configuration_requires_absolute_url_and_positive_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TAXIMOBILE_ROUTING_PROVIDER", "graphhopper")
    monkeypatch.setenv("TAXIMOBILE_ROUTING_BASE_URL", "https://routing.example.test/")
    monkeypatch.setenv("TAXIMOBILE_ROUTING_TIMEOUT_SECONDS", "2.5")
    monkeypatch.setenv("TAXIMOBILE_ROUTING_RATE_LIMIT_PER_MINUTE", "12")

    settings = Settings.from_environment()

    assert settings.routing_provider == "graphhopper"
    assert settings.routing_base_url == "https://routing.example.test"
    assert settings.routing_timeout_seconds == 2.5
    assert settings.routing_rate_limit_per_minute == 12

    monkeypatch.setenv("TAXIMOBILE_ROUTING_BASE_URL", "routing.example.test")
    with pytest.raises(ConfigurationError):
        Settings.from_environment()

    monkeypatch.setenv("TAXIMOBILE_ROUTING_BASE_URL", "https://routing.example.test")
    monkeypatch.setenv("TAXIMOBILE_ROUTING_TIMEOUT_SECONDS", "0")
    with pytest.raises(ConfigurationError):
        Settings.from_environment()

    monkeypatch.setenv("TAXIMOBILE_ROUTING_TIMEOUT_SECONDS", "2.5")
    monkeypatch.setenv("TAXIMOBILE_ROUTING_PROVIDER", "osrm")
    with pytest.raises(ConfigurationError, match="valhalla or graphhopper"):
        Settings.from_environment()

    monkeypatch.setenv("TAXIMOBILE_OUTBOX_POLL_SECONDS", "0.05")
    with pytest.raises(ConfigurationError):
        Settings.from_environment()

    monkeypatch.setenv("TAXIMOBILE_ALLOWED_HOSTS", "api.example.test")
    monkeypatch.setenv("TAXIMOBILE_CORS_ORIGINS", "*")
    with pytest.raises(ConfigurationError):
        Settings.from_environment()


def test_fcm_configuration_is_optional_and_rejects_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TAXIMOBILE_FIREBASE_PROJECT_ID", raising=False)
    assert Settings.from_environment().firebase_project_id is None

    monkeypatch.setenv("TAXIMOBILE_FIREBASE_PROJECT_ID", "taximobile-staging")
    monkeypatch.setenv("TAXIMOBILE_FCM_TIMEOUT_SECONDS", "2.5")
    settings = Settings.from_environment()
    assert settings.firebase_project_id == "taximobile-staging"
    assert settings.fcm_timeout_seconds == 2.5

    monkeypatch.setenv("TAXIMOBILE_FIREBASE_PROJECT_ID", "https://firebase.example/project")
    with pytest.raises(ConfigurationError):
        Settings.from_environment()

    monkeypatch.setenv("TAXIMOBILE_FIREBASE_PROJECT_ID", "taximobile-staging")
    monkeypatch.setenv("TAXIMOBILE_FCM_TIMEOUT_SECONDS", "0")
    with pytest.raises(ConfigurationError):
        Settings.from_environment()
