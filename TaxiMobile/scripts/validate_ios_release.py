"""Fail-closed validation for public iOS release build settings."""

from __future__ import annotations

import argparse
import re
from urllib.parse import urlsplit


class ReleaseConfigurationError(ValueError):
    pass


def validate_url(name: str, value: str, *, origin_only: bool) -> None:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as error:
        raise ReleaseConfigurationError(f"{name} must be a valid absolute HTTPS URL.") from error
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or parsed.hostname.endswith(".invalid")
        or (port is not None and not 1 <= port <= 65535)
    ):
        raise ReleaseConfigurationError(
            f"{name} must use an explicit HTTPS host without credentials, fragments, or .invalid placeholders."
        )
    if origin_only and (parsed.path not in ("", "/") or parsed.query):
        raise ReleaseConfigurationError(f"{name} must be an API origin without a path or query.")


def validate_release_configuration(
    api_url: str,
    map_url: str,
    build_number: str,
    version: str,
    crash_reporting_enabled: str = "YES",
    providerless_verification: bool = False,
) -> None:
    validate_url("TAXIMOBILE_API_BASE_URL", api_url, origin_only=True)
    validate_url("TAXIMOBILE_MAP_STYLE_URL", map_url, origin_only=False)
    if not build_number.isdigit() or int(build_number) < 1:
        raise ReleaseConfigurationError("CURRENT_PROJECT_VERSION must be a positive integer.")
    if not re.fullmatch(
        r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
        r"(?:\.(?:0|[1-9][0-9]*))?",
        version,
    ):
        raise ReleaseConfigurationError(
            "MARKETING_VERSION must contain three or four numeric components, such as 1.0.0."
        )
    if crash_reporting_enabled not in {"YES", "NO"}:
        raise ReleaseConfigurationError("TAXIMOBILE_CRASH_REPORTING_ENABLED must be YES or NO.")
    if crash_reporting_enabled != "YES" and not providerless_verification:
        raise ReleaseConfigurationError(
            "Distributable releases require TAXIMOBILE_CRASH_REPORTING_ENABLED=YES."
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("api_url")
    parser.add_argument("map_url")
    parser.add_argument("build_number")
    parser.add_argument("version")
    parser.add_argument("crash_reporting_enabled", choices=("YES", "NO"))
    parser.add_argument("providerless_verification", choices=("YES", "NO"))
    arguments = parser.parse_args()
    try:
        validate_release_configuration(
            arguments.api_url,
            arguments.map_url,
            arguments.build_number,
            arguments.version,
            arguments.crash_reporting_enabled,
            arguments.providerless_verification == "YES",
        )
    except ReleaseConfigurationError as error:
        parser.exit(1, f"error: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
