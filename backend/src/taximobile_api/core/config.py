"""Environment-backed configuration with safe defaults for local development."""

from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address
from math import isfinite
from os import getenv
import re
from urllib.parse import urlparse
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


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
    api_prefix: str
    log_level: str
    jwt_secret: str | None
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
    credential_poll_seconds: float
    credential_expiry_warning_days: int
    matching_timeout_seconds: int
    ride_offer_seconds: int
    routing_provider: str
    routing_base_url: str
    routing_timeout_seconds: float
    firebase_project_id: str | None
    fcm_timeout_seconds: float
    monitoring_token: str | None
    allowed_hosts: tuple[str, ...]
    cors_origins: tuple[str, ...]
    outbox_poll_seconds: float
    outbox_max_attempts: int
    registration_rate_limit_per_minute: int
    login_rate_limit_per_minute: int
    ride_creation_rate_limit_per_minute: int
    support_ticket_rate_limit_per_minute: int
    location_update_rate_limit_per_minute: int
    verification_submission_rate_limit_per_hour: int
    routing_rate_limit_per_minute: int

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

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

        firebase_project_id = getenv("TAXIMOBILE_FIREBASE_PROJECT_ID", "").strip() or None
        if firebase_project_id is not None and (
            "/" in firebase_project_id or any(character.isspace() for character in firebase_project_id)
        ):
            raise ConfigurationError("TAXIMOBILE_FIREBASE_PROJECT_ID must be a project ID, not a path or URL")

        monitoring_token = getenv("TAXIMOBILE_MONITORING_TOKEN", "").strip() or None
        if monitoring_token is not None and len(monitoring_token) < 32:
            raise ConfigurationError("TAXIMOBILE_MONITORING_TOKEN must contain at least 32 characters")
        if environment in {"staging", "production"} and monitoring_token is None:
            raise ConfigurationError("Staging and production require TAXIMOBILE_MONITORING_TOKEN")

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

        return cls(
            environment=environment,
            process_role=process_role,
            database_url=database_url,
            api_prefix="/api/v1",
            log_level=getenv("TAXIMOBILE_LOG_LEVEL", "INFO").upper(),
            jwt_secret=jwt_secret,
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
            firebase_project_id=firebase_project_id,
            fcm_timeout_seconds=positive_float("TAXIMOBILE_FCM_TIMEOUT_SECONDS", "5", 0.1),
            monitoring_token=monitoring_token,
            allowed_hosts=allowed_hosts,
            cors_origins=cors_origins,
            outbox_poll_seconds=bounded_float("TAXIMOBILE_OUTBOX_POLL_SECONDS", "1", 0.1, 60),
            outbox_max_attempts=positive_integer("TAXIMOBILE_OUTBOX_MAX_ATTEMPTS", "8"),
            registration_rate_limit_per_minute=positive_integer("TAXIMOBILE_REGISTRATION_RATE_LIMIT_PER_MINUTE", "5"),
            login_rate_limit_per_minute=positive_integer("TAXIMOBILE_LOGIN_RATE_LIMIT_PER_MINUTE", "5"),
            ride_creation_rate_limit_per_minute=positive_integer("TAXIMOBILE_RIDE_CREATION_RATE_LIMIT_PER_MINUTE", "5"),
            support_ticket_rate_limit_per_minute=positive_integer("TAXIMOBILE_SUPPORT_TICKET_RATE_LIMIT_PER_MINUTE", "5"),
            location_update_rate_limit_per_minute=positive_integer("TAXIMOBILE_LOCATION_UPDATE_RATE_LIMIT_PER_MINUTE", "60"),
            verification_submission_rate_limit_per_hour=positive_integer("TAXIMOBILE_VERIFICATION_SUBMISSION_RATE_LIMIT_PER_HOUR", "5"),
            routing_rate_limit_per_minute=positive_integer("TAXIMOBILE_ROUTING_RATE_LIMIT_PER_MINUTE", "30"),
        )


def _is_loopback_host(host: str) -> bool:
    normalized_host = host.strip().rstrip(".").lower()
    if normalized_host == "localhost":
        return True
    try:
        return ip_address(normalized_host).is_loopback
    except ValueError:
        return False
