"""Guarded Render entrypoint for TaxiMobile's staging services.

Render supplies standard PostgreSQL and private-service connection values.  The
application deliberately requires an explicit async SQLAlchemy URL and an
absolute routing URL.  This adapter performs only those mechanical conversions
inside the process environment before Alembic or the application is imported.
It never prints connection values or weakens the application's own validation.
"""

from __future__ import annotations

import argparse
from collections.abc import MutableMapping, Sequence
import os
import re
import sys
from urllib.parse import urlparse


class RenderConfigurationError(RuntimeError):
    """Raised when Render has not supplied a safe staging runtime boundary."""


_HOSTNAME = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?")


def async_database_url(render_url: str) -> str:
    """Convert Render's private PostgreSQL URL to the required async driver URL."""

    if render_url.startswith("postgresql://"):
        converted = "postgresql+asyncpg://" + render_url.removeprefix("postgresql://")
    elif render_url.startswith("postgres://"):
        converted = "postgresql+asyncpg://" + render_url.removeprefix("postgres://")
    else:
        raise RenderConfigurationError("Render database URL must use a PostgreSQL scheme.")

    parsed = urlparse(converted.replace("postgresql+asyncpg://", "postgresql://", 1))
    if parsed.hostname is None or not parsed.path.strip("/"):
        raise RenderConfigurationError("Render database URL is incomplete.")
    return converted


def private_routing_url(hostport: str) -> str:
    """Build a private HTTP URL without accepting paths, credentials, or fragments."""

    if "://" in hostport or any(character.isspace() for character in hostport):
        raise RenderConfigurationError("Render routing address must be a private host and port.")
    parsed = urlparse(f"http://{hostport}")
    try:
        port = parsed.port
    except ValueError as error:
        raise RenderConfigurationError("Render routing address has an invalid port.") from error
    if (
        parsed.hostname is None
        or port is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise RenderConfigurationError("Render routing address must be a private host and port.")
    return f"http://{hostport}"


def configure_render_environment(
    environment: MutableMapping[str, str],
    *,
    entrypoint_role: str | None = None,
) -> None:
    """Populate TaxiMobile settings from Render-generated, non-public values."""

    if environment.get("RENDER", "").lower() != "true":
        raise RenderConfigurationError("The Render entrypoint may run only on Render.")

    if not environment.get("TAXIMOBILE_DATABASE_URL"):
        render_database_url = environment.get("RENDER_DATABASE_URL", "")
        if not render_database_url:
            raise RenderConfigurationError("Render did not provide the private database URL.")
        environment["TAXIMOBILE_DATABASE_URL"] = async_database_url(render_database_url)

    process_role = entrypoint_role or environment.get("TAXIMOBILE_PROCESS_ROLE", "api").strip().lower()
    if process_role == "api":
        if not environment.get("TAXIMOBILE_ALLOWED_HOSTS"):
            external_hostname = environment.get("RENDER_EXTERNAL_HOSTNAME", "").strip().lower()
            if not external_hostname or not _HOSTNAME.fullmatch(external_hostname):
                raise RenderConfigurationError("Render did not provide a valid external API hostname.")
            environment["TAXIMOBILE_ALLOWED_HOSTS"] = external_hostname

        if not environment.get("TAXIMOBILE_ROUTING_BASE_URL"):
            routing_hostport = environment.get("RENDER_ROUTING_HOSTPORT", "")
            if not routing_hostport:
                raise RenderConfigurationError("Render did not provide the private routing address.")
            environment["TAXIMOBILE_ROUTING_BASE_URL"] = private_routing_url(routing_hostport)


def command_for(
    role: str,
    environment: MutableMapping[str, str],
    *,
    administrator_email: str | None = None,
) -> list[str]:
    """Return the fixed executable command for a declared deployment role."""

    if role == "migrate":
        return ["alembic", "upgrade", "head"]
    if role == "bootstrap-admin":
        if not administrator_email or any(character.isspace() for character in administrator_email):
            raise RenderConfigurationError("A single administrator email is required.")
        return [
            "taximobile-bootstrap-admin",
            "--email",
            administrator_email,
            "--confirm-initial-admin",
        ]
    if role == "worker":
        return [
            "uvicorn",
            "taximobile_api.worker:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8001",
            "--workers",
            "1",
            "--no-access-log",
        ]
    if role == "api":
        raw_port = environment.get("PORT", "10000")
        try:
            port = int(raw_port)
        except ValueError as error:
            raise RenderConfigurationError("Render API port must be an integer.") from error
        if not 1024 <= port <= 65535:
            raise RenderConfigurationError("Render API port is outside the allowed range.")
        return [
            "uvicorn",
            "taximobile_api.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(port),
            "--workers",
            "1",
            "--proxy-headers",
            "--no-access-log",
        ]
    raise RenderConfigurationError("Unknown Render process role.")


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Start one guarded TaxiMobile Render process.")
    parser.add_argument("role", choices=("migrate", "api", "worker", "bootstrap-admin"))
    parser.add_argument("--email", help="Initial administrator email for bootstrap-admin only.")
    parsed = parser.parse_args(arguments)

    try:
        configure_render_environment(os.environ, entrypoint_role=parsed.role)
        command = command_for(parsed.role, os.environ, administrator_email=parsed.email)
    except RenderConfigurationError as error:
        print(f"TaxiMobile Render configuration refused: {error}", file=sys.stderr)
        return 2

    os.execvp(command[0], command)
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by deployed process replacement
    raise SystemExit(main())
