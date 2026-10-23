"""Bounded Railway alpha process roles and least-privilege migration setup.

Secrets stay in the process environment. This adapter never seeds or resets data,
opens public database access, or relaxes the staging application's own checks.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from collections.abc import MutableMapping
from urllib.parse import urlparse

import asyncpg

from taximobile_api.core.config import _is_valid_http_host

DEPLOY_LOCK_NAMESPACE = 0x54415849  # TAXI
DEPLOY_LOCK_RESOURCE = 0x5241494C  # RAIL; distinct from Alembic's MIGR lock


class RailwayConfigurationError(RuntimeError):
    """The isolated Railway alpha deployment cannot start safely."""


def configure_environment(environment: MutableMapping[str, str], role: str) -> None:
    if not environment.get("RAILWAY_PROJECT_ID") or not environment.get("RAILWAY_ENVIRONMENT_ID"):
        raise RailwayConfigurationError("Railway project and environment identity are required.")
    if environment.get("TAXIMOBILE_ENV") != "staging":
        raise RailwayConfigurationError("This alpha entrypoint requires staging configuration.")
    if role not in {"api", "worker", "migrate"}:
        raise RailwayConfigurationError("Unknown Railway process role.")
    environment["TAXIMOBILE_PROCESS_ROLE"] = "api" if role == "api" else "worker"
    if role == "api":
        hostname = environment.get("RAILWAY_PUBLIC_DOMAIN", "").strip().lower()
        if not hostname or not _is_valid_http_host(hostname):
            raise RailwayConfigurationError("An exact public API hostname is required.")
        # Railway's healthcheck uses this explicit Host header. Keep public and
        # readiness traffic inside the same TrustedHost boundary, without '*'.
        environment["TAXIMOBILE_ALLOWED_HOSTS"] = f"{hostname},healthcheck.railway.app"
    if role != "migrate":
        environment.pop("TAXIMOBILE_MIGRATION_DATABASE_URL", None)
        environment.pop("TAXIMOBILE_RUNTIME_DATABASE_PASSWORD", None)
        environment.pop("TAXIMOBILE_ALPHA_SEED_PASSWORD", None)
        environment.pop("TAXIMOBILE_ALPHA_SEED_SUFFIX", None)
        environment.pop("TAXIMOBILE_ALPHA_MFA_SECRET", None)
        environment.pop("TAXIMOBILE_ALPHA_MFA_RECOVERY_CODES", None)


def command_for(role: str, environment: MutableMapping[str, str]) -> list[str]:
    if role not in {"api", "worker"}:
        raise RailwayConfigurationError("Only API and worker roles serve traffic.")
    try:
        port = int(environment.get("PORT", "8000" if role == "api" else "8001"))
    except ValueError as error:
        raise RailwayConfigurationError("Railway port must be an integer.") from error
    if not 1024 <= port <= 65535:
        raise RailwayConfigurationError("Railway port must be between 1024 and 65535.")
    module = "taximobile_api.main:app" if role == "api" else "taximobile_api.worker:app"
    return ["uvicorn", module, "--host", "0.0.0.0", "--port", str(port),
            "--workers", "1", "--no-access-log"]


def migration_target(environment: MutableMapping[str, str]) -> tuple[str, str]:
    url = environment.get("TAXIMOBILE_MIGRATION_DATABASE_URL", "")
    password = environment.get("TAXIMOBILE_RUNTIME_DATABASE_PASSWORD", "")
    parsed = urlparse(url.replace("postgresql+asyncpg://", "postgresql://", 1))
    expected_database = "taximobile_alpha_" + environment["RAILWAY_ENVIRONMENT_ID"].replace("-", "")[:12]
    if (parsed.scheme != "postgresql" or parsed.hostname != "alpha-postgis.railway.internal"
            or parsed.path != "/" + expected_database or not parsed.username or not parsed.password):
        raise RailwayConfigurationError("Migration target must be the isolated alpha PostGIS database.")
    if len(password) < 32:
        raise RailwayConfigurationError("A dedicated 32+ character runtime password is required.")
    return url, password


async def provision_runtime(url: str, password: str, *, grant: bool) -> None:
    connection = await asyncpg.connect(url.replace("postgresql+asyncpg://", "postgresql://", 1))
    try:
        async with connection.transaction():
            if grant:
                await connection.execute("GRANT USAGE ON SCHEMA public TO taximobile_runtime")
                # Do not re-grant the worker-owned materialized projection:
                # REFRESH updates its catalog tuple and can race GRANT ALL
                # TABLES. Grant only missing ordinary-table/view privileges.
                tables = await connection.fetch("""
                    SELECT format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE %I.%I TO taximobile_runtime', n.nspname, c.relname) AS command
                    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                    WHERE n.nspname='public' AND c.relkind IN ('r','p','v')
                    AND NOT (has_table_privilege('taximobile_runtime',c.oid,'SELECT')
                        AND has_table_privilege('taximobile_runtime',c.oid,'INSERT')
                        AND has_table_privilege('taximobile_runtime',c.oid,'UPDATE')
                        AND has_table_privilege('taximobile_runtime',c.oid,'DELETE'))
                """)
                sequences = await connection.fetch("""
                    SELECT format('GRANT USAGE, SELECT ON SEQUENCE %I.%I TO taximobile_runtime', n.nspname, c.relname) AS command
                    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                    WHERE n.nspname='public' AND c.relkind='S'
                    AND NOT (has_sequence_privilege('taximobile_runtime',c.oid,'USAGE')
                        AND has_sequence_privilege('taximobile_runtime',c.oid,'SELECT'))
                """)
                for row in [*tables, *sequences]:
                    await connection.execute(row["command"])
                await connection.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO taximobile_runtime")
                await connection.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO taximobile_runtime")
                # PostgreSQL 16 requires ownership to refresh a materialized
                # view. Grant ownership of this derived projection only; never
                # grant database/schema ownership or superuser to the runtime.
                owned = await connection.fetchval("SELECT pg_get_userbyid(relowner)='taximobile_runtime' FROM pg_class WHERE oid='public.operational_metric_facts_hourly_v1'::regclass")
                if not owned:
                    await connection.execute("ALTER MATERIALIZED VIEW public.operational_metric_facts_hourly_v1 OWNER TO taximobile_runtime")
            else:
                exists = await connection.fetchval("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='taximobile_runtime')")
                action = "ALTER" if exists else "CREATE"
                # Let PostgreSQL quote the password; never interpolate a secret
                # into an unescaped SQL literal or emit it in command output.
                statement = await connection.fetchval(
                    "SELECT format($1::text, $2::text)",
                    f"{action} ROLE taximobile_runtime LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS",
                    password,
                )
                await connection.execute(statement)
    finally:
        await connection.close()


async def verify_runtime(environment: MutableMapping[str, str]) -> dict[str, object]:
    """Prove the migrated schema is reachable with the restricted app login."""
    url = environment.get("TAXIMOBILE_DATABASE_URL", "")
    connection = await asyncpg.connect(url.replace("postgresql+asyncpg://", "postgresql://", 1))
    try:
        identity = await connection.fetchrow(
            "SELECT current_user AS name, rolsuper, rolcreatedb, rolcreaterole, "
            "rolreplication, rolbypassrls FROM pg_roles WHERE rolname=current_user"
        )
        if (identity is None or identity["name"] != "taximobile_runtime"
                or any(identity[field] for field in ("rolsuper", "rolcreatedb", "rolcreaterole", "rolreplication", "rolbypassrls"))
                or await connection.fetchval("SELECT has_schema_privilege(current_user,'public','CREATE')")):
            raise RailwayConfigurationError("The runtime login must not have schema or administrator authority.")
        await connection.execute("REFRESH MATERIALIZED VIEW public.operational_metric_facts_hourly_v1")
        return {
            "migration_head": await connection.fetchval("SELECT version_num FROM alembic_version"),
            "postgis_version": await connection.fetchval("SELECT PostGIS_Version()"),
            "public_tables": await connection.fetchval("SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'"),
            "runtime_role": "taximobile_runtime",
            "runtime_admin_or_public_schema_create": False,
            "analytics_projection_refresh": "verified",
            "database_bytes": await connection.fetchval("SELECT pg_database_size(current_database())"),
            "shared_buffers": await connection.fetchval("SHOW shared_buffers"),
            "max_wal_size": await connection.fetchval("SHOW max_wal_size"),
            "min_wal_size": await connection.fetchval("SHOW min_wal_size"),
            "checkpoint_timeout": await connection.fetchval("SHOW checkpoint_timeout"),
        }
    finally:
        await connection.close()


async def migrate_locked(environment: MutableMapping[str, str]) -> dict[str, object]:
    url, password = migration_target(environment)
    guard = await asyncpg.connect(url.replace("postgresql+asyncpg://", "postgresql://", 1))
    try:
        if not await guard.fetchval("SELECT pg_try_advisory_lock($1,$2)", DEPLOY_LOCK_NAMESPACE, DEPLOY_LOCK_RESOURCE):
            raise RailwayConfigurationError("Another alpha migrator is running; retry after it finishes.")
        await provision_runtime(url, password, grant=False)
        migration_environment = dict(environment)
        migration_environment["TAXIMOBILE_DATABASE_URL"] = url
        result = subprocess.run(["alembic", "upgrade", "head"], env=migration_environment, check=False)
        if result.returncode:
            raise RailwayConfigurationError("Railway alpha migration failed; traffic must not start.")
        await provision_runtime(url, password, grant=True)
        return await verify_runtime(environment)
    finally:
        # Session lock spans role setup, Alembic and grants; connection loss or
        # close releases it even if a subprocess or verification failed.
        await guard.close()


def migrate(environment: MutableMapping[str, str]) -> None:
    metadata = asyncio.run(migrate_locked(environment))
    print("Railway alpha database verified: " + json.dumps(metadata, sort_keys=True), flush=True)


def bootstrap(environment: MutableMapping[str, str]) -> None:
    """One explicit pre-deploy command; do not depend on platform shell chaining."""
    migrate(environment)
    for mode in ("cohort", "mfa"):
        result = subprocess.run(
            [sys.executable, "-m", "taximobile_api.operations.railway_alpha_seed",
             "--confirm", "CONFIRM_RAILWAY_SYNTHETIC_ALPHA", "--mode", mode],
            env=dict(environment), check=False,
        )
        if result.returncode:
            raise RailwayConfigurationError(f"Synthetic alpha {mode} bootstrap failed; preserve existing state and investigate.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one isolated Railway alpha process role.")
    parser.add_argument("role", choices=["api", "worker", "migrate", "bootstrap"])
    role = parser.parse_args().role
    configure_environment(os.environ, "migrate" if role == "bootstrap" else role)
    if role == "bootstrap":
        bootstrap(os.environ)
    elif role == "migrate":
        migrate(os.environ)
    else:
        command = command_for(role, os.environ)
        os.execvp(command[0], command)


if __name__ == "__main__":
    main()
