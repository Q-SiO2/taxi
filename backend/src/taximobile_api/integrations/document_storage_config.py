"""Explicit, redacted configuration for private encrypted document objects."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from ipaddress import ip_address
from math import isfinite
import re
from urllib.parse import urlsplit


class DocumentStorageConfigurationError(ValueError):
    """A fixed actionable configuration error that never includes input values."""


@dataclass(frozen=True, slots=True)
class S3DocumentStorageSettings:
    endpoint: str
    bucket: str
    access_key_id: str = field(repr=False)
    secret_access_key: str = field(repr=False)
    region: str = "auto"
    addressing_style: str = "virtual"
    timeout_seconds: float = 5.0
    max_in_flight: int = 2

    @classmethod
    def from_environment(cls, environment: Mapping[str, str]) -> "S3DocumentStorageSettings":
        prefix = "TAXIMOBILE_DRIVER_DOCUMENT_S3_"
        def value(name: str, default: str = "") -> str:
            return environment.get(prefix + name, default).strip()
        try:
            timeout = float(value("TIMEOUT_SECONDS", "5"))
            concurrency = int(value("MAX_IN_FLIGHT", "2"))
        except ValueError:
            raise DocumentStorageConfigurationError("Document S3 timeout/concurrency must be valid numbers") from None
        settings = cls(endpoint=value("ENDPOINT"), bucket=value("BUCKET"),
                       access_key_id=value("ACCESS_KEY_ID"), secret_access_key=value("SECRET_ACCESS_KEY"),
                       region=value("REGION", "auto"), addressing_style=value("ADDRESSING_STYLE", "virtual"),
                       timeout_seconds=timeout, max_in_flight=concurrency)
        settings.validate()
        return settings

    def validate(self) -> None:
        try:
            parsed = urlsplit(self.endpoint)
            port = parsed.port
        except ValueError:
            raise DocumentStorageConfigurationError("Document S3 endpoint must be an exact HTTPS origin") from None
        host = parsed.hostname or ""
        labels = host.split(".")
        if (parsed.scheme != "https" or parsed.username is not None or parsed.password is not None
                or any(character.isspace() or ord(character) < 33 for character in self.endpoint)
                or parsed.path not in {"", "/"} or parsed.query or parsed.fragment
                or port not in {None, 443} or len(host) > 253 or len(labels) < 2
                or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels)
                or host.endswith((".localhost", ".local"))):
            raise DocumentStorageConfigurationError("Document S3 endpoint must be an exact HTTPS DNS origin")
        try:
            ip_address(host)
        except ValueError:
            pass
        else:
            raise DocumentStorageConfigurationError("Document S3 endpoint requires a reviewed DNS origin")
        if (not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", self.bucket)
                or ".." in self.bucket or ".-" in self.bucket or "-." in self.bucket):
            raise DocumentStorageConfigurationError("Document S3 bucket must be a valid explicit bucket name")
        try:
            ip_address(self.bucket)
        except ValueError:
            pass
        else:
            raise DocumentStorageConfigurationError("Document S3 bucket cannot be an IP address")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", self.region):
            raise DocumentStorageConfigurationError("Document S3 signing region must be explicit and valid")
        if self.addressing_style not in {"virtual", "path"}:
            raise DocumentStorageConfigurationError("Document S3 addressing style must be virtual or path")
        if (not 8 <= len(self.access_key_id) <= 256 or not 16 <= len(self.secret_access_key) <= 1024
                or any(not 33 <= ord(character) <= 126 for character in self.access_key_id + self.secret_access_key)):
            raise DocumentStorageConfigurationError("Document S3 requires explicit valid bucket credentials")
        if not isfinite(self.timeout_seconds) or not 0.5 <= self.timeout_seconds <= 30:
            raise DocumentStorageConfigurationError("Document S3 timeout must be between 0.5 and 30 seconds")
        if not isinstance(self.max_in_flight, int) or isinstance(self.max_in_flight, bool) or not 1 <= self.max_in_flight <= 8:
            raise DocumentStorageConfigurationError("Document S3 concurrency must be between 1 and 8")
