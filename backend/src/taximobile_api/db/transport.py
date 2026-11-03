"""One explicit PostgreSQL transport policy for ORM and direct asyncpg users."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import os
from pathlib import Path
import ssl

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class DatabaseTLSConfigurationError(ValueError):
    """A fixed, credential-free database transport configuration error."""


@dataclass(frozen=True, slots=True)
class DatabaseTLS:
    mode: str = "disable"
    ca_file: Path | None = None
    ca_pem: str | None = None

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> "DatabaseTLS":
        values = os.environ if environment is None else environment
        deployment = values.get("TAXIMOBILE_ENV", "development").strip().lower()
        mode = values.get("TAXIMOBILE_DATABASE_TLS_MODE", "verify-full" if deployment == "production" else "disable").strip().lower()
        filename = values.get("TAXIMOBILE_DATABASE_CA_FILE", "").strip() or None
        pem = values.get("TAXIMOBILE_DATABASE_CA_PEM", "").strip() or None
        policy = cls(mode, Path(filename) if filename else None, pem)
        policy.validate_environment(deployment)
        return policy

    def validate_environment(self, deployment: str) -> None:
        if self.mode not in {"disable", "verify-full"}:
            raise DatabaseTLSConfigurationError("TAXIMOBILE_DATABASE_TLS_MODE must be disable or verify-full")
        if deployment == "production" and self.mode != "verify-full":
            raise DatabaseTLSConfigurationError("Production requires database TLS verify-full")
        if self.ca_file is not None and self.ca_pem is not None:
            raise DatabaseTLSConfigurationError("Supply one database CA source: CA_FILE or CA_PEM")
        if self.ca_file is not None and not self.ca_file.is_absolute():
            raise DatabaseTLSConfigurationError("TAXIMOBILE_DATABASE_CA_FILE must be an absolute path")
        if self.mode == "disable" and (self.ca_file is not None or self.ca_pem is not None):
            raise DatabaseTLSConfigurationError("Database CA configuration requires TLS verify-full")

    def connect_args(self, database_url: str) -> dict[str, object]:
        self.validate_environment("development")
        try:
            url = make_url(database_url)
        except (ArgumentError, ValueError):
            raise DatabaseTLSConfigurationError("Database TLS requires a valid PostgreSQL URL") from None
        if url.drivername not in {"postgresql", "postgresql+asyncpg"}:
            raise DatabaseTLSConfigurationError("Database TLS requires PostgreSQL/asyncpg")
        # DSN query options otherwise override host/transport or bypass the single
        # policy when the URL is passed to asyncpg versus split by SQLAlchemy.
        forbidden = {"host", "hostaddr", "port", "dsn", "service", "servicefile", "direct_tls"}
        if any(key.lower().startswith("ssl") or key.lower() in forbidden for key in url.query):
            raise DatabaseTLSConfigurationError("Database URL transport/host overrides are forbidden; use the database TLS settings")
        if self.mode == "disable":
            return {"ssl": False}
        if not url.host or url.host.startswith("/"):
            raise DatabaseTLSConfigurationError("TLS verify-full requires an explicit TCP database hostname")
        try:
            context = ssl.create_default_context(
                ssl.Purpose.SERVER_AUTH,
                cafile=str(self.ca_file) if self.ca_file is not None else None,
                cadata=self.ca_pem,
            )
        except (OSError, ValueError, ssl.SSLError):
            raise DatabaseTLSConfigurationError("Database CA could not be loaded; supply a readable PEM CA bundle") from None
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        return {"ssl": context}
