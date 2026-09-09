"""Environment-backed configuration with safe defaults for local development."""

from __future__ import annotations

from base64 import b64decode
from binascii import Error as Base64Error
from dataclasses import dataclass
from ipaddress import ip_address
from math import isfinite
from os import getenv
from pathlib import Path
import re
from urllib.parse import urlparse
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from taximobile_api.core.client_compatibility import (
    ClientCompatibilityPolicy,
    ClientSurface,
    ClientVersion,
)


class ConfigurationError(ValueError):
    """Raised when a deployment is missing a required safe configuration."""


_HTTP_HOST_LABEL = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?")


def _is_valid_http_host(value: str) -> bool:
    """Accept an exact ASCII DNS/IPv4-style host, never a URL, port, or wildcard."""
    return (
        1 <= len(value) <= 253
        and not value.endswith(".")
        and all(_HTTP_HOST_LABEL.fullmatch(label) for label in value.split("."))
    )


def _is_valid_browser_origin(value: str, *, require_https: bool) -> bool:
    """Accept an exact HTTP origin, not a URL carrying path or credentials."""
    parsed = urlparse(value)
    try:
        parsed_port = parsed.port
    except ValueError:
        return False
    allowed_schemes = {"https"} if require_https else {"http", "https"}
    return (
        parsed.scheme in allowed_schemes
        and parsed.hostname is not None
        and _is_valid_http_host(parsed.hostname)
        and parsed.username is None
        and parsed.password is None
        and parsed.path == ""
        and parsed.params == ""
        and parsed.query == ""
        and parsed.fragment == ""
        and (parsed_port is None or 1 <= parsed_port <= 65535)
    )


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str
    process_role: str
    database_url: str
    database_pool_size: int
    database_pool_max_overflow: int
    database_pool_timeout_seconds: float
    api_prefix: str
    client_compatibility_enforced: bool
    client_policy_revision: str
    client_minimum_versions: tuple[tuple[str, str], ...]
    client_recommended_versions: tuple[tuple[str, str], ...]
    log_level: str
    log_file: Path | None
    log_file_max_bytes: int
    log_file_backup_count: int
    jwt_secret: str | None
    legacy_admin_api_enabled: bool
    operations_password_login_enabled: bool
    operations_mfa_encryption_key: str | None
    operations_secure_cookie_enabled: bool
    matching_radius_meters: int
    matching_location_freshness_seconds: int
    matching_candidate_limit: int
    matching_idle_cap_seconds: int
    matching_fairness_lookback_hours: int
    matching_assumed_pickup_speed_mps: float
    matching_proximity_weight: float
    matching_idle_weight: float
    matching_fairness_weight: float
    matching_algorithm_version: str
    matching_poll_seconds: float
    scheduling_poll_seconds: float
    analytics_poll_seconds: float
    case_alert_poll_seconds: float
    case_alert_max_delivery_attempts: int
    case_pager_url: str | None
    case_pager_token: str | None
    case_pager_timeout_seconds: float
    case_retention_poll_seconds: float
    case_retention_batch_size: int
    driver_document_storage_root: Path | None
    driver_document_encryption_key: bytes | None
    driver_document_clamav_host: str | None
    driver_document_clamav_port: int
    driver_document_clamav_timeout_seconds: float
    driver_document_max_bytes: int
    driver_document_retention_days: int
    driver_document_retention_poll_seconds: float
    driver_document_retention_batch_size: int
    driver_document_upload_rate_limit_per_hour: int
    driver_document_access_rate_limit_per_minute: int
    credential_poll_seconds: float
    credential_expiry_warning_days: int
    matching_timeout_seconds: int
    ride_offer_seconds: int
    routing_provider: str
    routing_base_url: str
    routing_timeout_seconds: float
    geocoding_provider: str
    geocoding_base_url: str | None
    geocoding_timeout_seconds: float
    geocoding_user_agent: str
    firebase_project_id: str | None
    fcm_timeout_seconds: float
    manual_transfer_enabled: bool
    manual_transfer_recipient_name: str | None
    manual_transfer_bank_account: str | None
    manual_transfer_wallet_id: str | None
    monitoring_token: str | None
    allowed_hosts: tuple[str, ...]
    cors_origins: tuple[str, ...]
    outbox_poll_seconds: float
    outbox_max_attempts: int
    registration_rate_limit_per_minute: int
    login_rate_limit_per_minute: int
    account_recovery_rate_limit_per_hour: int
    account_security_rate_limit_per_hour: int
    ride_creation_rate_limit_per_minute: int
    ride_message_rate_limit_per_minute: int
    support_ticket_rate_limit_per_minute: int
    location_update_rate_limit_per_minute: int
    verification_submission_rate_limit_per_hour: int
    routing_rate_limit_per_minute: int
    place_search_rate_limit_per_minute: int
    place_reverse_rate_limit_per_minute: int

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def manual_transfer_configured(self) -> bool:
        return (
            self.manual_transfer_enabled
            and self.manual_transfer_recipient_name is not None
            and (
                self.manual_transfer_bank_account is not None
                or self.manual_transfer_wallet_id is not None
            )
        )

    @property
    def case_pager_configured(self) -> bool:
        return self.case_pager_url is not None and self.case_pager_token is not None

    @classmethod
    def from_environment(cls) -> "Settings":
        def positive_integer(name: str, default: str) -> int:
            try:
                value = int(getenv(name, default))
            except ValueError as error:
                raise ConfigurationError(f"{name} must be a positive integer") from error
            if value < 1:
                raise ConfigurationError(f"{name} must be a positive integer")
            return value

        def bounded_integer(name: str, default: str, maximum: int) -> int:
            value = positive_integer(name, default)
            if value > maximum:
                raise ConfigurationError(f"{name} must not exceed {maximum}")
            return value

        def bounded_nonnegative_integer(name: str, default: str, maximum: int) -> int:
            try:
                value = int(getenv(name, default))
            except ValueError as error:
                raise ConfigurationError(
                    f"{name} must be a non-negative integer"
                ) from error
            if not 0 <= value <= maximum:
                raise ConfigurationError(f"{name} must be between 0 and {maximum}")
            return value

        def positive_float(name: str, default: str, minimum: float) -> float:
            try:
                value = float(getenv(name, default))
            except ValueError as error:
                raise ConfigurationError(f"{name} must be at least {minimum}") from error
            if not isfinite(value) or value < minimum:
                raise ConfigurationError(f"{name} must be at least {minimum}")
            return value

        def bounded_float(name: str, default: str, minimum: float, maximum: float) -> float:
            value = positive_float(name, default, minimum)
            if value > maximum:
                raise ConfigurationError(f"{name} must not exceed {maximum}")
            return value

        def nonnegative_float(name: str, default: str) -> float:
            try:
                value = float(getenv(name, default))
            except ValueError as error:
                raise ConfigurationError(f"{name} must be a non-negative number") from error
            if not isfinite(value) or value < 0:
                raise ConfigurationError(f"{name} must be a non-negative number")
            return value

        def boolean(name: str, default: str = "false") -> bool:
            value = getenv(name, default).strip().lower()
            if value in {"1", "true", "yes", "on"}:
                return True
            if value in {"0", "false", "no", "off"}:
                return False
            raise ConfigurationError(f"{name} must be true or false")

        def optional_transfer_text(name: str, maximum: int) -> str | None:
            value = getenv(name, "").strip() or None
            if value is None:
                return None
            if len(value) > maximum or any(not character.isprintable() for character in value):
                raise ConfigurationError(f"{name} must contain at most {maximum} printable characters")
            return value

        environment = getenv("TAXIMOBILE_ENV", "development").strip().lower()
        if environment not in {"development", "test", "staging", "production"}:
            raise ConfigurationError("TAXIMOBILE_ENV must be development, test, staging, or production")
        default_process_role = "api" if environment in {"staging", "production"} else "all"
        process_role = getenv("TAXIMOBILE_PROCESS_ROLE", default_process_role).strip().lower()
        if process_role not in {"all", "api", "worker"}:
            raise ConfigurationError("TAXIMOBILE_PROCESS_ROLE must be all, api, or worker")

        database_url = getenv(
            "TAXIMOBILE_DATABASE_URL",
            "postgresql+asyncpg://taximobile:taximobile@localhost:5432/taximobile",
        )
        if environment in {"staging", "production"}:
            try:
                database_host = make_url(database_url).host
            except ArgumentError as error:
                raise ConfigurationError("TAXIMOBILE_DATABASE_URL must be a valid database URL") from error
            if database_host is None or _is_loopback_host(database_host):
                raise ConfigurationError("Staging and production require a non-local TAXIMOBILE_DATABASE_URL")

        jwt_secret = getenv("TAXIMOBILE_JWT_SECRET")
        if (
            environment in {"staging", "production"}
            and process_role != "worker"
            and (jwt_secret is None or len(jwt_secret) < 32)
        ):
            raise ConfigurationError("Staging and production require a 32+ character TAXIMOBILE_JWT_SECRET")

        operations_password_login_enabled = boolean(
            "TAXIMOBILE_OPERATIONS_PASSWORD_LOGIN_ENABLED",
            "true" if environment in {"development", "test"} else "false",
        )
        if environment == "production" and operations_password_login_enabled:
            raise ConfigurationError(
                "Production cannot enable password-only operations login; reviewed MFA is required"
            )
        legacy_admin_api_enabled = boolean(
            "TAXIMOBILE_LEGACY_ADMIN_API_ENABLED",
            "true" if environment in {"development", "test"} else "false",
        )
        if environment in {"staging", "production"} and legacy_admin_api_enabled:
            raise ConfigurationError(
                "Staging and production cannot enable the transitional legacy admin API"
            )
        operations_mfa_encryption_key = (
            getenv("TAXIMOBILE_OPERATIONS_MFA_ENCRYPTION_KEY", "").strip() or None
        )
        if operations_mfa_encryption_key is not None:
            try:
                padding = "=" * (-len(operations_mfa_encryption_key) % 4)
                decoded_mfa_key = b64decode(
                    operations_mfa_encryption_key + padding,
                    altchars=b"-_",
                    validate=True,
                )
            except (Base64Error, ValueError) as error:
                raise ConfigurationError(
                    "TAXIMOBILE_OPERATIONS_MFA_ENCRYPTION_KEY must be base64url"
                ) from error
            if len(decoded_mfa_key) != 32:
                raise ConfigurationError(
                    "TAXIMOBILE_OPERATIONS_MFA_ENCRYPTION_KEY must decode to exactly 32 bytes"
                )
        if (
            process_role != "worker"
            and not operations_password_login_enabled
            and operations_mfa_encryption_key is None
        ):
            raise ConfigurationError(
                "Operations MFA login requires TAXIMOBILE_OPERATIONS_MFA_ENCRYPTION_KEY"
            )
        operations_secure_cookie_enabled = boolean(
            "TAXIMOBILE_OPERATIONS_SECURE_COOKIE_ENABLED",
            "true" if environment in {"staging", "production"} else "false",
        )
        if (
            environment == "production"
            and process_role != "worker"
            and not operations_secure_cookie_enabled
        ):
            raise ConfigurationError(
                "Production operations authentication requires secure refresh cookies"
            )

        allowed_hosts = tuple(
            host.strip().lower()
            for host in getenv(
                "TAXIMOBILE_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver"
            ).split(",")
            if host.strip()
        )
        cors_origins = tuple(
            origin.strip().lower()
            for origin in getenv("TAXIMOBILE_CORS_ORIGINS", "").split(",")
            if origin.strip()
        )
        if environment in {"staging", "production"} and process_role != "worker":
            if not allowed_hosts:
                raise ConfigurationError("Staging and production require explicit TAXIMOBILE_ALLOWED_HOSTS")
            if any("*" in host or not _is_valid_http_host(host) for host in allowed_hosts):
                raise ConfigurationError(
                    "TAXIMOBILE_ALLOWED_HOSTS must contain only exact DNS or IPv4 host names"
                )
        if environment in {"staging", "production"} and process_role != "worker":
            if any(
                "*" in origin or not _is_valid_browser_origin(origin, require_https=True)
                for origin in cors_origins
            ):
                raise ConfigurationError(
                    "TAXIMOBILE_CORS_ORIGINS must contain only exact HTTPS origins"
                )

        routing_provider = getenv("TAXIMOBILE_ROUTING_PROVIDER", "valhalla").strip().lower()
        if routing_provider not in {"valhalla", "graphhopper"}:
            raise ConfigurationError("TAXIMOBILE_ROUTING_PROVIDER must be valhalla or graphhopper")
        routing_base_url = getenv("TAXIMOBILE_ROUTING_BASE_URL", "http://localhost:8002").strip().rstrip("/")
        parsed_routing_url = urlparse(routing_base_url)
        if parsed_routing_url.scheme not in {"http", "https"} or not parsed_routing_url.hostname:
            raise ConfigurationError("TAXIMOBILE_ROUTING_BASE_URL must be an absolute HTTP or HTTPS URL")

        geocoding_provider = getenv("TAXIMOBILE_GEOCODING_PROVIDER", "disabled").strip().lower()
        if geocoding_provider not in {"disabled", "nominatim"}:
            raise ConfigurationError(
                "TAXIMOBILE_GEOCODING_PROVIDER must be disabled or nominatim"
            )
        geocoding_base_url = (
            getenv("TAXIMOBILE_GEOCODING_BASE_URL", "").strip().rstrip("/") or None
        )
        if geocoding_provider == "nominatim" and geocoding_base_url is None:
            raise ConfigurationError(
                "Nominatim requires TAXIMOBILE_GEOCODING_BASE_URL"
            )
        if geocoding_base_url is not None:
            parsed_geocoding_url = urlparse(geocoding_base_url)
            if (
                parsed_geocoding_url.scheme not in {"http", "https"}
                or parsed_geocoding_url.hostname is None
                or parsed_geocoding_url.username is not None
                or parsed_geocoding_url.password is not None
                or parsed_geocoding_url.query
                or parsed_geocoding_url.fragment
                or len(geocoding_base_url) > 512
            ):
                raise ConfigurationError(
                    "TAXIMOBILE_GEOCODING_BASE_URL must be an absolute URL without credentials, query, or fragment"
                )
            if environment in {"staging", "production"}:
                if parsed_geocoding_url.scheme != "https":
                    raise ConfigurationError("Staging and production geocoding requires HTTPS")
                if (
                    parsed_geocoding_url.hostname.lower().rstrip(".")
                    == "nominatim.openstreetmap.org"
                ):
                    raise ConfigurationError(
                        "Staging and production cannot use the shared public Nominatim endpoint"
                    )
        geocoding_user_agent = getenv(
            "TAXIMOBILE_GEOCODING_USER_AGENT",
            "TaxiMobile/0.1 (https://github.com/Q-SiO2/taxi)",
        ).strip()
        if (
            len(geocoding_user_agent) < 10
            or len(geocoding_user_agent) > 200
            or any(not character.isprintable() for character in geocoding_user_agent)
        ):
            raise ConfigurationError(
                "TAXIMOBILE_GEOCODING_USER_AGENT must contain 10-200 printable characters"
            )

        firebase_project_id = getenv("TAXIMOBILE_FIREBASE_PROJECT_ID", "").strip() or None
        if firebase_project_id is not None and (
            "/" in firebase_project_id or any(character.isspace() for character in firebase_project_id)
        ):
            raise ConfigurationError("TAXIMOBILE_FIREBASE_PROJECT_ID must be a project ID, not a path or URL")

        case_pager_url = getenv("TAXIMOBILE_CASE_PAGER_URL", "").strip() or None
        case_pager_token = getenv("TAXIMOBILE_CASE_PAGER_TOKEN", "").strip() or None
        if (case_pager_url is None) != (case_pager_token is None):
            raise ConfigurationError(
                "TAXIMOBILE_CASE_PAGER_URL and TAXIMOBILE_CASE_PAGER_TOKEN must be configured together"
            )
        if case_pager_url is not None:
            parsed_pager_url = urlparse(case_pager_url)
            if (
                parsed_pager_url.scheme not in {"http", "https"}
                or parsed_pager_url.hostname is None
                or parsed_pager_url.username is not None
                or parsed_pager_url.password is not None
                or parsed_pager_url.query
                or parsed_pager_url.fragment
                or len(case_pager_url) > 512
            ):
                raise ConfigurationError(
                    "TAXIMOBILE_CASE_PAGER_URL must be an absolute URL without credentials, query, or fragment"
                )
            if environment in {"staging", "production"} and parsed_pager_url.scheme != "https":
                raise ConfigurationError("Staging and production case pagers require HTTPS")
            if case_pager_token is None or len(case_pager_token) < 32:
                raise ConfigurationError(
                    "TAXIMOBILE_CASE_PAGER_TOKEN must contain at least 32 characters"
                )

        manual_transfer_enabled = boolean("TAXIMOBILE_MANUAL_TRANSFER_ENABLED")
        manual_transfer_recipient_name = optional_transfer_text(
            "TAXIMOBILE_TRANSFER_RECIPIENT_NAME", 120
        )
        manual_transfer_bank_account = optional_transfer_text(
            "TAXIMOBILE_TRANSFER_BANK_ACCOUNT", 120
        )
        manual_transfer_wallet_id = optional_transfer_text(
            "TAXIMOBILE_TRANSFER_WALLET_ID", 120
        )
        if manual_transfer_enabled and (
            manual_transfer_recipient_name is None
            or (
                manual_transfer_bank_account is None
                and manual_transfer_wallet_id is None
            )
        ):
            raise ConfigurationError(
                "Manual transfer requires TAXIMOBILE_TRANSFER_RECIPIENT_NAME and at least one "
                "of TAXIMOBILE_TRANSFER_BANK_ACCOUNT or TAXIMOBILE_TRANSFER_WALLET_ID"
            )

        driver_document_root_text = getenv(
            "TAXIMOBILE_DRIVER_DOCUMENT_STORAGE_ROOT", ""
        ).strip()
        driver_document_key_text = getenv(
            "TAXIMOBILE_DRIVER_DOCUMENT_ENCRYPTION_KEY", ""
        ).strip()
        driver_document_clamav_host = (
            getenv("TAXIMOBILE_DRIVER_DOCUMENT_CLAMAV_HOST", "").strip().lower()
            or None
        )
        document_security_values = (
            bool(driver_document_root_text),
            bool(driver_document_key_text),
            driver_document_clamav_host is not None,
        )
        if any(document_security_values) and not all(document_security_values):
            raise ConfigurationError(
                "Driver-document storage root, encryption key, and ClamAV host must be "
                "configured together"
            )
        driver_document_storage_root: Path | None = None
        driver_document_encryption_key: bytes | None = None
        if all(document_security_values):
            driver_document_storage_root = Path(driver_document_root_text).expanduser()
            if not driver_document_storage_root.is_absolute():
                raise ConfigurationError(
                    "TAXIMOBILE_DRIVER_DOCUMENT_STORAGE_ROOT must be an absolute path"
                )
            if driver_document_storage_root == Path(driver_document_storage_root.anchor):
                raise ConfigurationError(
                    "TAXIMOBILE_DRIVER_DOCUMENT_STORAGE_ROOT cannot be a filesystem root"
                )
            if not _is_valid_http_host(driver_document_clamav_host or ""):
                raise ConfigurationError(
                    "TAXIMOBILE_DRIVER_DOCUMENT_CLAMAV_HOST must be an exact host name or IPv4 address"
                )
            try:
                padding = "=" * (-len(driver_document_key_text) % 4)
                driver_document_encryption_key = b64decode(
                    driver_document_key_text + padding,
                    altchars=b"-_",
                    validate=True,
                )
            except (Base64Error, ValueError) as error:
                raise ConfigurationError(
                    "TAXIMOBILE_DRIVER_DOCUMENT_ENCRYPTION_KEY must be base64url"
                ) from error
            if len(driver_document_encryption_key) != 32:
                raise ConfigurationError(
                    "TAXIMOBILE_DRIVER_DOCUMENT_ENCRYPTION_KEY must decode to exactly 32 bytes"
                )

        monitoring_token = getenv("TAXIMOBILE_MONITORING_TOKEN", "").strip() or None
        if monitoring_token is not None and len(monitoring_token) < 32:
            raise ConfigurationError("TAXIMOBILE_MONITORING_TOKEN must contain at least 32 characters")
        if environment in {"staging", "production"} and monitoring_token is None:
            raise ConfigurationError("Staging and production require TAXIMOBILE_MONITORING_TOKEN")

        log_file_text = getenv("TAXIMOBILE_LOG_FILE", "").strip()
        log_file = Path(log_file_text) if log_file_text else None
        if log_file is not None and not log_file.is_absolute():
            raise ConfigurationError("TAXIMOBILE_LOG_FILE must be an absolute path")

        matching_proximity_weight = nonnegative_float("TAXIMOBILE_MATCHING_PROXIMITY_WEIGHT", "0.55")
        matching_idle_weight = nonnegative_float("TAXIMOBILE_MATCHING_IDLE_WEIGHT", "0.30")
        matching_fairness_weight = nonnegative_float("TAXIMOBILE_MATCHING_FAIRNESS_WEIGHT", "0.15")
        if matching_proximity_weight + matching_idle_weight + matching_fairness_weight <= 0:
            raise ConfigurationError("At least one matching score weight must be positive")
        matching_algorithm_version = getenv("TAXIMOBILE_MATCHING_ALGORITHM_VERSION", "mvp-v1").strip()
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,32}", matching_algorithm_version):
            raise ConfigurationError(
                "TAXIMOBILE_MATCHING_ALGORITHM_VERSION must contain 1-32 letters, digits, dots, underscores, or hyphens"
            )

        client_compatibility_enforced = boolean(
            "TAXIMOBILE_CLIENT_COMPATIBILITY_ENFORCED",
            "true" if environment in {"staging", "production"} else "false",
        )
        if environment in {"staging", "production"} and not client_compatibility_enforced:
            raise ConfigurationError(
                "Staging and production require client compatibility enforcement"
            )
        client_policy_revision = getenv(
            "TAXIMOBILE_CLIENT_POLICY_REVISION", "baseline-1"
        ).strip()

        def client_versions(kind: str) -> tuple[tuple[str, str], ...]:
            values: list[tuple[str, str]] = []
            for surface in ClientSurface:
                environment_name = f"TAXIMOBILE_CLIENT_{surface.value}_{kind}_VERSION"
                value = getenv(environment_name, "1.0.0").strip()
                try:
                    ClientVersion.parse(value)
                except ValueError as error:
                    raise ConfigurationError(
                        f"{environment_name} must be a numeric version such as 1.0.0"
                    ) from error
                values.append((surface.value, value))
            return tuple(values)

        client_minimum_versions = client_versions("MINIMUM")
        client_recommended_versions = client_versions("RECOMMENDED")
        try:
            ClientCompatibilityPolicy(
                revision=client_policy_revision,
                minimum_versions=client_minimum_versions,
                recommended_versions=client_recommended_versions,
            )
        except ValueError as error:
            raise ConfigurationError(f"Invalid client compatibility policy: {error}") from error

        return cls(
            environment=environment,
            process_role=process_role,
            database_url=database_url,
            database_pool_size=bounded_integer(
                "TAXIMOBILE_DATABASE_POOL_SIZE", "5", 100
            ),
            database_pool_max_overflow=bounded_nonnegative_integer(
                "TAXIMOBILE_DATABASE_POOL_MAX_OVERFLOW", "10", 100
            ),
            database_pool_timeout_seconds=bounded_float(
                "TAXIMOBILE_DATABASE_POOL_TIMEOUT_SECONDS", "30", 0.5, 60
            ),
            api_prefix="/api/v1",
            client_compatibility_enforced=client_compatibility_enforced,
            client_policy_revision=client_policy_revision,
            client_minimum_versions=client_minimum_versions,
            client_recommended_versions=client_recommended_versions,
            log_level=getenv("TAXIMOBILE_LOG_LEVEL", "INFO").upper(),
            log_file=log_file,
            log_file_max_bytes=bounded_integer(
                "TAXIMOBILE_LOG_FILE_MAX_BYTES", "10485760", 104857600
            ),
            log_file_backup_count=bounded_integer(
                "TAXIMOBILE_LOG_FILE_BACKUP_COUNT", "5", 20
            ),
            jwt_secret=jwt_secret,
            legacy_admin_api_enabled=legacy_admin_api_enabled,
            operations_password_login_enabled=operations_password_login_enabled,
            operations_mfa_encryption_key=operations_mfa_encryption_key,
            operations_secure_cookie_enabled=operations_secure_cookie_enabled,
            matching_radius_meters=positive_integer("TAXIMOBILE_MATCHING_RADIUS_METERS", "3000"),
            matching_location_freshness_seconds=positive_integer(
                "TAXIMOBILE_MATCHING_LOCATION_FRESHNESS_SECONDS", "30"
            ),
            matching_candidate_limit=positive_integer("TAXIMOBILE_MATCHING_CANDIDATE_LIMIT", "10"),
            matching_idle_cap_seconds=positive_integer("TAXIMOBILE_MATCHING_IDLE_CAP_SECONDS", "1800"),
            matching_fairness_lookback_hours=positive_integer(
                "TAXIMOBILE_MATCHING_FAIRNESS_LOOKBACK_HOURS", "24"
            ),
            matching_assumed_pickup_speed_mps=positive_float(
                "TAXIMOBILE_MATCHING_ASSUMED_PICKUP_SPEED_MPS", "6.944", 0.1
            ),
            matching_proximity_weight=matching_proximity_weight,
            matching_idle_weight=matching_idle_weight,
            matching_fairness_weight=matching_fairness_weight,
            matching_algorithm_version=matching_algorithm_version,
            matching_poll_seconds=bounded_float(
                "TAXIMOBILE_MATCHING_POLL_SECONDS", "1", 0.1, 60
            ),
            scheduling_poll_seconds=bounded_float(
                "TAXIMOBILE_SCHEDULING_POLL_SECONDS", "15", 1, 60
            ),
            analytics_poll_seconds=bounded_float(
                "TAXIMOBILE_ANALYTICS_POLL_SECONDS", "300", 30, 3600
            ),
            case_alert_poll_seconds=bounded_float(
                "TAXIMOBILE_CASE_ALERT_POLL_SECONDS", "60", 5, 300
            ),
            case_alert_max_delivery_attempts=bounded_integer(
                "TAXIMOBILE_CASE_ALERT_MAX_DELIVERY_ATTEMPTS", "8", 100
            ),
            case_pager_url=case_pager_url,
            case_pager_token=case_pager_token,
            case_pager_timeout_seconds=bounded_float(
                "TAXIMOBILE_CASE_PAGER_TIMEOUT_SECONDS", "5", 0.5, 30
            ),
            case_retention_poll_seconds=bounded_float(
                "TAXIMOBILE_CASE_RETENTION_POLL_SECONDS", "3600", 300, 86400
            ),
            case_retention_batch_size=bounded_integer(
                "TAXIMOBILE_CASE_RETENTION_BATCH_SIZE", "100", 1000
            ),
            driver_document_storage_root=driver_document_storage_root,
            driver_document_encryption_key=driver_document_encryption_key,
            driver_document_clamav_host=driver_document_clamav_host,
            driver_document_clamav_port=bounded_integer(
                "TAXIMOBILE_DRIVER_DOCUMENT_CLAMAV_PORT", "3310", 65535
            ),
            driver_document_clamav_timeout_seconds=bounded_float(
                "TAXIMOBILE_DRIVER_DOCUMENT_CLAMAV_TIMEOUT_SECONDS", "10", 0.5, 60
            ),
            driver_document_max_bytes=bounded_integer(
                "TAXIMOBILE_DRIVER_DOCUMENT_MAX_BYTES", str(10 * 1024 * 1024),
                20 * 1024 * 1024,
            ),
            driver_document_retention_days=bounded_integer(
                "TAXIMOBILE_DRIVER_DOCUMENT_RETENTION_DAYS", "730", 3650
            ),
            driver_document_retention_poll_seconds=bounded_float(
                "TAXIMOBILE_DRIVER_DOCUMENT_RETENTION_POLL_SECONDS", "3600", 300, 86400
            ),
            driver_document_retention_batch_size=bounded_integer(
                "TAXIMOBILE_DRIVER_DOCUMENT_RETENTION_BATCH_SIZE", "100", 1000
            ),
            driver_document_upload_rate_limit_per_hour=bounded_integer(
                "TAXIMOBILE_DRIVER_DOCUMENT_UPLOAD_RATE_LIMIT_PER_HOUR", "20", 1000
            ),
            driver_document_access_rate_limit_per_minute=bounded_integer(
                "TAXIMOBILE_DRIVER_DOCUMENT_ACCESS_RATE_LIMIT_PER_MINUTE", "30", 1000
            ),
            credential_poll_seconds=bounded_float(
                "TAXIMOBILE_CREDENTIAL_POLL_SECONDS", "60", 1, 300
            ),
            credential_expiry_warning_days=bounded_integer(
                "TAXIMOBILE_CREDENTIAL_EXPIRY_WARNING_DAYS", "30", 365
            ),
            matching_timeout_seconds=positive_integer("TAXIMOBILE_MATCHING_TIMEOUT_SECONDS", "300"),
            ride_offer_seconds=positive_integer("TAXIMOBILE_RIDE_OFFER_SECONDS", "45"),
            routing_provider=routing_provider,
            routing_base_url=routing_base_url,
            routing_timeout_seconds=positive_float("TAXIMOBILE_ROUTING_TIMEOUT_SECONDS", "5", 0.1),
            geocoding_provider=geocoding_provider,
            geocoding_base_url=geocoding_base_url,
            geocoding_timeout_seconds=bounded_float(
                "TAXIMOBILE_GEOCODING_TIMEOUT_SECONDS", "5", 0.5, 30
            ),
            geocoding_user_agent=geocoding_user_agent,
            firebase_project_id=firebase_project_id,
            fcm_timeout_seconds=positive_float("TAXIMOBILE_FCM_TIMEOUT_SECONDS", "5", 0.1),
            manual_transfer_enabled=manual_transfer_enabled,
            manual_transfer_recipient_name=manual_transfer_recipient_name,
            manual_transfer_bank_account=manual_transfer_bank_account,
            manual_transfer_wallet_id=manual_transfer_wallet_id,
            monitoring_token=monitoring_token,
            allowed_hosts=allowed_hosts,
            cors_origins=cors_origins,
            outbox_poll_seconds=bounded_float("TAXIMOBILE_OUTBOX_POLL_SECONDS", "1", 0.1, 60),
            outbox_max_attempts=positive_integer("TAXIMOBILE_OUTBOX_MAX_ATTEMPTS", "8"),
            registration_rate_limit_per_minute=positive_integer("TAXIMOBILE_REGISTRATION_RATE_LIMIT_PER_MINUTE", "5"),
            login_rate_limit_per_minute=positive_integer("TAXIMOBILE_LOGIN_RATE_LIMIT_PER_MINUTE", "5"),
            account_recovery_rate_limit_per_hour=positive_integer(
                "TAXIMOBILE_ACCOUNT_RECOVERY_RATE_LIMIT_PER_HOUR", "5"
            ),
            account_security_rate_limit_per_hour=positive_integer(
                "TAXIMOBILE_ACCOUNT_SECURITY_RATE_LIMIT_PER_HOUR", "10"
            ),
            ride_creation_rate_limit_per_minute=positive_integer("TAXIMOBILE_RIDE_CREATION_RATE_LIMIT_PER_MINUTE", "5"),
            ride_message_rate_limit_per_minute=bounded_integer(
                "TAXIMOBILE_RIDE_MESSAGE_RATE_LIMIT_PER_MINUTE", "12", 60
            ),
            support_ticket_rate_limit_per_minute=positive_integer("TAXIMOBILE_SUPPORT_TICKET_RATE_LIMIT_PER_MINUTE", "5"),
            location_update_rate_limit_per_minute=positive_integer("TAXIMOBILE_LOCATION_UPDATE_RATE_LIMIT_PER_MINUTE", "60"),
            verification_submission_rate_limit_per_hour=positive_integer("TAXIMOBILE_VERIFICATION_SUBMISSION_RATE_LIMIT_PER_HOUR", "5"),
            routing_rate_limit_per_minute=positive_integer("TAXIMOBILE_ROUTING_RATE_LIMIT_PER_MINUTE", "30"),
            place_search_rate_limit_per_minute=bounded_integer(
                "TAXIMOBILE_PLACE_SEARCH_RATE_LIMIT_PER_MINUTE", "20", 120
            ),
            place_reverse_rate_limit_per_minute=bounded_integer(
                "TAXIMOBILE_PLACE_REVERSE_RATE_LIMIT_PER_MINUTE", "30", 120
            ),
        )


def _is_loopback_host(host: str) -> bool:
    normalized_host = host.strip().rstrip(".").lower()
    if normalized_host == "localhost":
        return True
    try:
        return ip_address(normalized_host).is_loopback
    except ValueError:
        return False
