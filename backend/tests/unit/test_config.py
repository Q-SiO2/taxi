from base64 import urlsafe_b64encode

import pytest

from taximobile_api.core.config import ConfigurationError, Settings
from taximobile_api.core.live_events import PostgresLiveEventPublisher
from taximobile_api.core.rate_limit import PostgresRateLimiter
from taximobile_api.main import create_app


@pytest.fixture(autouse=True)
def configured_operations_mfa_key(monkeypatch: pytest.MonkeyPatch) -> None:
    key = urlsafe_b64encode(bytes(range(32))).decode().rstrip("=")
    monkeypatch.setenv("TAXIMOBILE_OPERATIONS_MFA_ENCRYPTION_KEY", key)


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
    assert settings.operations_password_login_enabled is False
    assert settings.operations_secure_cookie_enabled is True
    assert settings.client_compatibility_enforced is True


def test_client_compatibility_policy_is_closed_and_production_enforced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings.from_environment()
    assert settings.client_compatibility_enforced is False
    assert settings.client_policy_revision == "baseline-1"
    assert len(settings.client_minimum_versions) == 6
    assert len(settings.client_recommended_versions) == 6

    monkeypatch.setenv("TAXIMOBILE_CLIENT_ANDROID_PASSENGER_MINIMUM_VERSION", "2.0.0")
    monkeypatch.setenv("TAXIMOBILE_CLIENT_ANDROID_PASSENGER_RECOMMENDED_VERSION", "1.9.9")
    with pytest.raises(ConfigurationError, match="Recommended version cannot be below minimum"):
        Settings.from_environment()

    monkeypatch.setenv("TAXIMOBILE_CLIENT_ANDROID_PASSENGER_RECOMMENDED_VERSION", "2.1.0")
    monkeypatch.setenv("TAXIMOBILE_CLIENT_POLICY_REVISION", "invalid revision")
    with pytest.raises(ConfigurationError, match="Invalid client compatibility policy"):
        Settings.from_environment()


def test_production_cannot_disable_client_compatibility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TAXIMOBILE_ENV", "production")
    monkeypatch.setenv(
        "TAXIMOBILE_DATABASE_URL",
        "postgresql+asyncpg://taxi:secret@database.internal/taxi",
    )
    monkeypatch.setenv("TAXIMOBILE_JWT_SECRET", "x" * 32)
    monkeypatch.setenv("TAXIMOBILE_ALLOWED_HOSTS", "api.example.test")
    monkeypatch.setenv("TAXIMOBILE_MONITORING_TOKEN", "m" * 32)
    monkeypatch.setenv("TAXIMOBILE_CLIENT_COMPATIBILITY_ENFORCED", "false")

    with pytest.raises(ConfigurationError, match="require client compatibility enforcement"):
        Settings.from_environment()


def test_database_pool_defaults_and_reviewed_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings.from_environment()
    assert settings.database_pool_size == 5
    assert settings.database_pool_max_overflow == 10
    assert settings.database_pool_timeout_seconds == 30

    monkeypatch.setenv("TAXIMOBILE_DATABASE_POOL_SIZE", "12")
    monkeypatch.setenv("TAXIMOBILE_DATABASE_POOL_MAX_OVERFLOW", "4")
    monkeypatch.setenv("TAXIMOBILE_DATABASE_POOL_TIMEOUT_SECONDS", "2.5")
    settings = Settings.from_environment()
    assert settings.database_pool_size == 12
    assert settings.database_pool_max_overflow == 4
    assert settings.database_pool_timeout_seconds == 2.5


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("TAXIMOBILE_DATABASE_POOL_SIZE", "0"),
        ("TAXIMOBILE_DATABASE_POOL_SIZE", "101"),
        ("TAXIMOBILE_DATABASE_POOL_MAX_OVERFLOW", "-1"),
        ("TAXIMOBILE_DATABASE_POOL_MAX_OVERFLOW", "101"),
        ("TAXIMOBILE_DATABASE_POOL_TIMEOUT_SECONDS", "0"),
        ("TAXIMOBILE_DATABASE_POOL_TIMEOUT_SECONDS", "61"),
        ("TAXIMOBILE_DATABASE_POOL_TIMEOUT_SECONDS", "nan"),
    ],
)
def test_database_pool_configuration_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    value: str,
) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ConfigurationError):
        Settings.from_environment()


def test_log_file_configuration_is_absolute_and_bounded(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("TAXIMOBILE_LOG_FILE", "relative/events.jsonl")
    with pytest.raises(ConfigurationError, match="absolute path"):
        Settings.from_environment()

    log_file = tmp_path / "events.jsonl"
    monkeypatch.setenv("TAXIMOBILE_LOG_FILE", str(log_file))
    monkeypatch.setenv("TAXIMOBILE_LOG_FILE_MAX_BYTES", "2048")
    monkeypatch.setenv("TAXIMOBILE_LOG_FILE_BACKUP_COUNT", "3")
    settings = Settings.from_environment()
    assert settings.log_file == log_file
    assert settings.log_file_max_bytes == 2048
    assert settings.log_file_backup_count == 3

    monkeypatch.setenv("TAXIMOBILE_LOG_FILE_BACKUP_COUNT", "21")
    with pytest.raises(ConfigurationError, match="must not exceed 20"):
        Settings.from_environment()


def test_operations_password_only_login_is_local_and_production_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert Settings.from_environment().operations_password_login_enabled is True

    monkeypatch.setenv("TAXIMOBILE_ENV", "production")
    monkeypatch.setenv("TAXIMOBILE_DATABASE_URL", "postgresql+asyncpg://taxi:secret@database/taxi")
    monkeypatch.setenv("TAXIMOBILE_JWT_SECRET", "x" * 32)
    monkeypatch.setenv("TAXIMOBILE_ALLOWED_HOSTS", "api.example.test")
    monkeypatch.setenv("TAXIMOBILE_MONITORING_TOKEN", "m" * 32)
    monkeypatch.setenv("TAXIMOBILE_OPERATIONS_PASSWORD_LOGIN_ENABLED", "true")

    with pytest.raises(ConfigurationError, match="reviewed MFA"):
        Settings.from_environment()


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_legacy_admin_api_is_local_only_and_production_like_environments_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    monkeypatch.setenv("TAXIMOBILE_ENV", environment)
    monkeypatch.setenv(
        "TAXIMOBILE_DATABASE_URL",
        "postgresql+asyncpg://taxi:secret@database.internal/taxi",
    )
    monkeypatch.setenv("TAXIMOBILE_JWT_SECRET", "x" * 32)
    monkeypatch.setenv("TAXIMOBILE_ALLOWED_HOSTS", "api.example.test")
    monkeypatch.setenv("TAXIMOBILE_MONITORING_TOKEN", "m" * 32)

    assert Settings.from_environment().legacy_admin_api_enabled is False

    monkeypatch.setenv("TAXIMOBILE_LEGACY_ADMIN_API_ENABLED", "true")
    with pytest.raises(ConfigurationError, match="cannot enable.*legacy admin API"):
        Settings.from_environment()


def test_legacy_admin_api_can_be_disabled_in_local_compatibility_environments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert Settings.from_environment().legacy_admin_api_enabled is True

    monkeypatch.setenv("TAXIMOBILE_LEGACY_ADMIN_API_ENABLED", "false")
    assert Settings.from_environment().legacy_admin_api_enabled is False


def test_mfa_login_requires_one_valid_aes_256_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAXIMOBILE_ENV", "production")
    monkeypatch.setenv("TAXIMOBILE_DATABASE_URL", "postgresql+asyncpg://taxi:secret@database/taxi")
    monkeypatch.setenv("TAXIMOBILE_JWT_SECRET", "x" * 32)
    monkeypatch.setenv("TAXIMOBILE_ALLOWED_HOSTS", "api.example.test")
    monkeypatch.setenv("TAXIMOBILE_MONITORING_TOKEN", "m" * 32)
    monkeypatch.delenv("TAXIMOBILE_OPERATIONS_MFA_ENCRYPTION_KEY")
    with pytest.raises(ConfigurationError, match="MFA_ENCRYPTION_KEY"):
        Settings.from_environment()


def test_driver_document_dependencies_are_all_or_none_and_key_is_aes_256(
    monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> None:
    monkeypatch.setenv("TAXIMOBILE_DRIVER_DOCUMENT_STORAGE_ROOT", str(tmp_path))
    with pytest.raises(ConfigurationError, match="configured together"):
        Settings.from_environment()

    monkeypatch.setenv("TAXIMOBILE_DRIVER_DOCUMENT_CLAMAV_HOST", "clamav.internal")
    monkeypatch.setenv("TAXIMOBILE_DRIVER_DOCUMENT_ENCRYPTION_KEY", "not-base64!")
    with pytest.raises(ConfigurationError, match="base64url"):
        Settings.from_environment()

    key = urlsafe_b64encode(bytes(range(32))).decode().rstrip("=")
    monkeypatch.setenv("TAXIMOBILE_DRIVER_DOCUMENT_ENCRYPTION_KEY", key)
    settings = Settings.from_environment()

    assert settings.driver_document_storage_root == tmp_path
    assert settings.driver_document_encryption_key == bytes(range(32))
    assert settings.driver_document_clamav_host == "clamav.internal"
    assert settings.driver_document_max_bytes == 10 * 1024 * 1024


def test_driver_document_storage_root_must_be_absolute(monkeypatch: pytest.MonkeyPatch) -> None:
    key = urlsafe_b64encode(bytes(range(32))).decode().rstrip("=")
    monkeypatch.setenv("TAXIMOBILE_DRIVER_DOCUMENT_STORAGE_ROOT", "relative/documents")
    monkeypatch.setenv("TAXIMOBILE_DRIVER_DOCUMENT_CLAMAV_HOST", "clamav.internal")
    monkeypatch.setenv("TAXIMOBILE_DRIVER_DOCUMENT_ENCRYPTION_KEY", key)

    with pytest.raises(ConfigurationError, match="absolute path"):
        Settings.from_environment()

    monkeypatch.setenv("TAXIMOBILE_OPERATIONS_MFA_ENCRYPTION_KEY", "not-base64!")
    with pytest.raises(ConfigurationError, match="base64url"):
        Settings.from_environment()


def test_production_requires_secure_operations_refresh_cookies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TAXIMOBILE_ENV", "production")
    monkeypatch.setenv("TAXIMOBILE_DATABASE_URL", "postgresql+asyncpg://taxi:secret@database/taxi")
    monkeypatch.setenv("TAXIMOBILE_JWT_SECRET", "x" * 32)
    monkeypatch.setenv("TAXIMOBILE_ALLOWED_HOSTS", "api.example.test")
    monkeypatch.setenv("TAXIMOBILE_MONITORING_TOKEN", "m" * 32)
    monkeypatch.setenv("TAXIMOBILE_OPERATIONS_SECURE_COOKIE_ENABLED", "false")

    with pytest.raises(ConfigurationError, match="secure refresh cookies"):
        Settings.from_environment()


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
    monkeypatch.setenv("TAXIMOBILE_ACCOUNT_RECOVERY_RATE_LIMIT_PER_HOUR", "4")
    monkeypatch.setenv("TAXIMOBILE_ACCOUNT_SECURITY_RATE_LIMIT_PER_HOUR", "8")

    settings = Settings.from_environment()
    assert settings.login_rate_limit_per_minute == 9
    assert settings.account_recovery_rate_limit_per_hour == 4
    assert settings.account_security_rate_limit_per_hour == 8

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


def test_geocoding_is_fail_closed_and_validates_production_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings.from_environment()
    assert settings.geocoding_provider == "disabled"
    assert settings.geocoding_base_url is None
    assert settings.place_search_rate_limit_per_minute == 20
    assert settings.place_reverse_rate_limit_per_minute == 30

    monkeypatch.setenv("TAXIMOBILE_GEOCODING_PROVIDER", "nominatim")
    with pytest.raises(ConfigurationError, match="GEOCODING_BASE_URL"):
        Settings.from_environment()

    monkeypatch.setenv("TAXIMOBILE_GEOCODING_BASE_URL", "https://geo.example.test/")
    monkeypatch.setenv("TAXIMOBILE_GEOCODING_TIMEOUT_SECONDS", "2.5")
    monkeypatch.setenv("TAXIMOBILE_GEOCODING_USER_AGENT", "TaxiMobile staging contact")
    configured = Settings.from_environment()
    assert configured.geocoding_provider == "nominatim"
    assert configured.geocoding_base_url == "https://geo.example.test"
    assert configured.geocoding_timeout_seconds == 2.5

    monkeypatch.setenv("TAXIMOBILE_GEOCODING_PROVIDER", "pelias")
    with pytest.raises(ConfigurationError, match="disabled or nominatim"):
        Settings.from_environment()

    monkeypatch.setenv("TAXIMOBILE_GEOCODING_PROVIDER", "nominatim")
    monkeypatch.setenv("TAXIMOBILE_GEOCODING_BASE_URL", "geo.example.test")
    with pytest.raises(ConfigurationError, match="absolute URL"):
        Settings.from_environment()

    monkeypatch.setenv("TAXIMOBILE_ENV", "production")
    monkeypatch.setenv("TAXIMOBILE_DATABASE_URL", "postgresql+asyncpg://u:p@database.internal/taxi")
    monkeypatch.setenv("TAXIMOBILE_JWT_SECRET", "x" * 32)
    monkeypatch.setenv("TAXIMOBILE_MONITORING_TOKEN", "m" * 32)
    monkeypatch.setenv("TAXIMOBILE_OPERATIONS_MFA_ENCRYPTION_KEY", "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA")
    monkeypatch.setenv("TAXIMOBILE_GEOCODING_BASE_URL", "https://nominatim.openstreetmap.org")
    with pytest.raises(ConfigurationError, match="shared public Nominatim"):
        Settings.from_environment()

    monkeypatch.setenv("TAXIMOBILE_GEOCODING_BASE_URL", "https://nominatim.openstreetmap.org.")
    with pytest.raises(ConfigurationError, match="shared public Nominatim"):
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


def test_case_pager_is_fail_closed_and_requires_a_protected_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TAXIMOBILE_CASE_PAGER_URL", raising=False)
    monkeypatch.delenv("TAXIMOBILE_CASE_PAGER_TOKEN", raising=False)
    settings = Settings.from_environment()
    assert settings.case_pager_configured is False
    assert settings.case_alert_poll_seconds == 60

    monkeypatch.setenv("TAXIMOBILE_CASE_PAGER_URL", "https://pager.example.test/cases")
    with pytest.raises(ConfigurationError, match="configured together"):
        Settings.from_environment()

    monkeypatch.setenv("TAXIMOBILE_CASE_PAGER_TOKEN", "p" * 32)
    settings = Settings.from_environment()
    assert settings.case_pager_configured is True

    monkeypatch.setenv("TAXIMOBILE_CASE_PAGER_URL", "https://user@pager.example.test/cases")
    with pytest.raises(ConfigurationError, match="without credentials"):
        Settings.from_environment()

    monkeypatch.setenv("TAXIMOBILE_CASE_PAGER_URL", "https://pager.example.test/cases?secret=x")
    with pytest.raises(ConfigurationError, match="without credentials"):
        Settings.from_environment()

    monkeypatch.setenv("TAXIMOBILE_CASE_PAGER_URL", "https://pager.example.test/cases")
    monkeypatch.setenv("TAXIMOBILE_CASE_ALERT_POLL_SECONDS", "2")
    with pytest.raises(ConfigurationError, match="at least 5"):
        Settings.from_environment()

    monkeypatch.delenv("TAXIMOBILE_CASE_ALERT_POLL_SECONDS")
    monkeypatch.setenv("TAXIMOBILE_CASE_RETENTION_POLL_SECONDS", "299")
    with pytest.raises(ConfigurationError, match="at least 300"):
        Settings.from_environment()

    monkeypatch.delenv("TAXIMOBILE_CASE_RETENTION_POLL_SECONDS")
    monkeypatch.setenv("TAXIMOBILE_CASE_RETENTION_BATCH_SIZE", "1001")
    with pytest.raises(ConfigurationError, match="must not exceed 1000"):
        Settings.from_environment()

def test_manual_transfer_is_fail_closed_until_recipient_is_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TAXIMOBILE_MANUAL_TRANSFER_ENABLED", raising=False)
    settings = Settings.from_environment()
    assert settings.manual_transfer_enabled is False
    assert settings.manual_transfer_configured is False

    monkeypatch.setenv("TAXIMOBILE_MANUAL_TRANSFER_ENABLED", "true")
    with pytest.raises(ConfigurationError, match="Manual transfer requires"):
        Settings.from_environment()

    monkeypatch.setenv("TAXIMOBILE_TRANSFER_RECIPIENT_NAME", "TaxiMobile Pilot")
    monkeypatch.setenv("TAXIMOBILE_TRANSFER_WALLET_ID", "+212600000000")
    settings = Settings.from_environment()
    assert settings.manual_transfer_configured is True
    assert settings.manual_transfer_recipient_name == "TaxiMobile Pilot"
    assert settings.manual_transfer_wallet_id == "+212600000000"


def test_manual_transfer_flag_rejects_ambiguous_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAXIMOBILE_MANUAL_TRANSFER_ENABLED", "sometimes")
    with pytest.raises(ConfigurationError, match="must be true or false"):
        Settings.from_environment()


def test_manual_transfer_display_values_reject_invisible_controls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TAXIMOBILE_TRANSFER_RECIPIENT_NAME", "TaxiMobile Pilot")
    monkeypatch.setenv("TAXIMOBILE_TRANSFER_BANK_ACCOUNT", "ACCOUNT\u202e123")

    with pytest.raises(ConfigurationError, match="printable characters"):
        Settings.from_environment()
