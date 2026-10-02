"""Run a destructive, isolated TaxiMobile T3 logical backup/restore rehearsal.

The source is restricted to the local disposable ``taximobile_ci`` database.
The command creates one randomly named ``taximobile_restore_t3_*`` database,
restores a temporary custom-format dump, compares privacy-bounded schema/table
counts, runs a no-op migration to the current head, then drops the restored
database and deletes the dump. It never records credentials or row content.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterable, Sequence
from uuid import uuid4

from validate_docs import discover_migration_head


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = WORKSPACE_ROOT / "backend"
MIGRATIONS_ROOT = BACKEND_ROOT / "migrations" / "versions"
SAFE_TABLE = re.compile(r"[a-z][a-z0-9_]{0,62}")
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


class T3BackupRestoreError(RuntimeError):
    """Raised when the rehearsal cannot prove a complete safe restore."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_command_detail(completed: subprocess.CompletedProcess[str], environment: dict[str, str]) -> str:
    detail = (completed.stderr or completed.stdout or "no diagnostic output").strip()[-1600:]
    secret = environment.get("PGPASSWORD")
    if secret:
        detail = detail.replace(secret, "[REDACTED]")
    detail = re.sub(r"(?i)(password\s*[=:]\s*)\S+", r"\1[REDACTED]", detail)
    return " ".join(detail.splitlines())


def _run(
    executable: str,
    arguments: Sequence[str],
    *,
    environment: dict[str, str],
    cwd: Path | None = None,
) -> str:
    try:
        completed = subprocess.run(
            [executable, *arguments],
            cwd=cwd,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise T3BackupRestoreError(
            f"Required database command {Path(executable).name} could not run."
        ) from error
    if completed.returncode != 0:
        raise T3BackupRestoreError(
            f"Required database command {Path(executable).name} failed with "
            f"exit code {completed.returncode}: {_safe_command_detail(completed, environment)}"
        )
    return completed.stdout


async def _database_fingerprint(database_url: str) -> dict[str, Any]:
    try:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine
    except ImportError as error:
        raise T3BackupRestoreError(
            "Backend dependencies are required for backup/restore verification."
        ) from error

    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            database_name = await connection.scalar(text("SELECT current_database()"))
            migrations = list(
                (
                    await connection.execute(
                        text("SELECT version_num FROM alembic_version ORDER BY version_num")
                    )
                ).scalars()
            )
            postgis_version = await connection.scalar(
                text("SELECT extversion FROM pg_extension WHERE extname = 'postgis'")
            )
            tables = list(
                (
                    await connection.execute(
                        text(
                            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
                            "ORDER BY tablename"
                        )
                    )
                ).scalars()
            )
            if any(not isinstance(table, str) or SAFE_TABLE.fullmatch(table) is None for table in tables):
                raise T3BackupRestoreError("Public schema contains an unexpected table identifier.")
            table_counts: dict[str, int] = {}
            for table in tables:
                table_counts[table] = int(
                    await connection.scalar(text(f'SELECT count(*) FROM "{table}"')) or 0
                )
            constraint_count = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_constraint c "
                        "JOIN pg_namespace n ON n.oid = c.connamespace "
                        "WHERE n.nspname = 'public'"
                    )
                )
                or 0
            )
            index_count = int(
                await connection.scalar(
                    text("SELECT count(*) FROM pg_indexes WHERE schemaname = 'public'")
                )
                or 0
            )
            sequence_count = int(
                await connection.scalar(
                    text("SELECT count(*) FROM pg_sequences WHERE schemaname = 'public'")
                )
                or 0
            )
    except T3BackupRestoreError:
        raise
    except Exception as error:
        raise T3BackupRestoreError(
            f"Backup/restore verification query failed ({type(error).__name__})."
        ) from error
    finally:
        await engine.dispose()
    return {
        "database_name": database_name,
        "migration_heads": migrations,
        "postgis_version": postgis_version,
        "table_counts": table_counts,
        "constraint_count": constraint_count,
        "index_count": index_count,
        "sequence_count": sequence_count,
    }


def _validate_fingerprints(
    source: dict[str, Any], restored: dict[str, Any], *, expected_head: str
) -> dict[str, Any]:
    if source.get("database_name") != "taximobile_ci":
        raise T3BackupRestoreError("Backup source must be exactly taximobile_ci.")
    if source.get("migration_heads") != [expected_head] or restored.get("migration_heads") != [
        expected_head
    ]:
        raise T3BackupRestoreError("Source and restored databases must share one current head.")
    if not source.get("postgis_version") or source.get("postgis_version") != restored.get(
        "postgis_version"
    ):
        raise T3BackupRestoreError("PostGIS version is missing or changed during restore.")
    comparable = (
        "table_counts",
        "constraint_count",
        "index_count",
        "sequence_count",
    )
    if any(source.get(key) != restored.get(key) for key in comparable):
        raise T3BackupRestoreError("Restored schema or aggregate table counts do not match source.")
    table_counts = source.get("table_counts")
    if not isinstance(table_counts, dict) or not table_counts:
        raise T3BackupRestoreError("Backup source contains no application tables.")
    return {
        "migration_head": expected_head,
        "postgis_version": source["postgis_version"],
        "public_table_count": len(table_counts),
        "aggregate_row_count": sum(table_counts.values()),
        "constraint_count": source["constraint_count"],
        "index_count": source["index_count"],
        "sequence_count": source["sequence_count"],
        "table_counts_match": True,
        "schema_object_counts_match": True,
    }


def _connection_arguments(url: Any, user: str) -> list[str]:
    result = [f"--host={url.host}", f"--username={user}", "--no-password"]
    if url.port is not None:
        result.insert(1, f"--port={url.port}")
    return result


def run_rehearsal(
    *,
    output_path: Path,
    pg_dump: str,
    pg_restore: str,
    createdb: str,
    dropdb: str,
    psql: str,
    maintenance_user: str | None,
) -> dict[str, Any]:
    try:
        from sqlalchemy.engine import make_url
    except ImportError as error:
        raise T3BackupRestoreError(
            "Backend dependencies are required for backup/restore verification."
        ) from error

    if os.environ.get("TAXIMOBILE_ENV") != "test" or os.environ.get(
        "TAXIMOBILE_RUN_INTEGRATION"
    ) != "1":
        raise T3BackupRestoreError("Rehearsal requires explicit test/integration environment guards.")
    database_url = os.environ.get("TAXIMOBILE_DATABASE_URL", "")
    try:
        source_url = make_url(database_url)
    except Exception as error:
        raise T3BackupRestoreError("TAXIMOBILE_DATABASE_URL is invalid.") from error
    if source_url.database != "taximobile_ci" or source_url.host not in LOCAL_HOSTS:
        raise T3BackupRestoreError(
            "Rehearsal accepts only a loopback taximobile_ci source database."
        )
    if not source_url.username or not source_url.password:
        raise T3BackupRestoreError("The disposable database URL needs a user and password.")
    maintenance_user = maintenance_user or source_url.username
    if SAFE_TABLE.fullmatch(maintenance_user) is None or SAFE_TABLE.fullmatch(source_url.username) is None:
        raise T3BackupRestoreError("Database user identifiers are not safe for the rehearsal.")
    if output_path.exists():
        raise T3BackupRestoreError("Refusing to overwrite existing backup/restore evidence.")

    expected_head = discover_migration_head(MIGRATIONS_ROOT)
    target_database = f"taximobile_restore_t3_{uuid4().hex[:16]}"
    target_url = source_url.set(database=target_database)
    environment = {**os.environ, "PGPASSWORD": source_url.password}
    app_arguments = _connection_arguments(source_url, source_url.username)
    admin_arguments = _connection_arguments(source_url, maintenance_user)
    started = time.monotonic()
    target_created = False
    cleanup_verified = False
    report_parts: dict[str, Any] = {}

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="taximobile-t3-restore-") as temporary:
        dump_path = Path(temporary) / "taximobile-ci.dump"
        restore_list_path = Path(temporary) / "taximobile-ci.restore-list"
        try:
            source_fingerprint = asyncio.run(_database_fingerprint(database_url))
            dump_started = time.monotonic()
            _run(
                pg_dump,
                [
                    *app_arguments,
                    "--dbname=taximobile_ci",
                    "--format=custom",
                    "--no-owner",
                    "--no-privileges",
                    "--no-comments",
                    "--exclude-table-data=public.spatial_ref_sys",
                    f"--file={dump_path}",
                ],
                environment=environment,
            )
            dump_seconds = time.monotonic() - dump_started
            if not dump_path.is_file() or dump_path.stat().st_size <= 0:
                raise T3BackupRestoreError("Logical backup is missing or empty.")
            backup_bytes = dump_path.stat().st_size
            backup_sha256 = _sha256(dump_path)
            archive_list = _run(
                pg_restore,
                ["--list", str(dump_path)],
                environment=environment,
            )
            filtered_archive_lines = [
                line
                for line in archive_list.splitlines()
                if re.search(r"\bEXTENSION - postgis(?:\s|$)", line) is None
            ]
            if len(filtered_archive_lines) >= len(archive_list.splitlines()):
                raise T3BackupRestoreError(
                    "Logical backup did not contain the expected PostGIS extension entry."
                )
            restore_list_path.write_text(
                "\n".join(filtered_archive_lines) + "\n",
                encoding="utf-8",
                newline="\n",
            )

            restore_started = time.monotonic()
            _run(
                createdb,
                [*admin_arguments, f"--owner={source_url.username}", target_database],
                environment=environment,
            )
            target_created = True
            _run(
                psql,
                [
                    *admin_arguments,
                    f"--dbname={target_database}",
                    "--set=ON_ERROR_STOP=1",
                    "--quiet",
                    "--command=CREATE EXTENSION IF NOT EXISTS postgis;",
                ],
                environment=environment,
            )
            _run(
                pg_restore,
                [
                    *app_arguments,
                    f"--dbname={target_database}",
                    "--no-owner",
                    "--no-privileges",
                    "--exit-on-error",
                    f"--use-list={restore_list_path}",
                    str(dump_path),
                ],
                environment=environment,
            )
            restore_seconds = time.monotonic() - restore_started

            verify_started = time.monotonic()
            restored_fingerprint = asyncio.run(
                _database_fingerprint(target_url.render_as_string(hide_password=False))
            )
            reconciliation = _validate_fingerprints(
                source_fingerprint, restored_fingerprint, expected_head=expected_head
            )
            migration_environment = {
                **environment,
                "TAXIMOBILE_DATABASE_URL": target_url.render_as_string(hide_password=False),
            }
            _run(
                sys.executable,
                ["-m", "alembic", "upgrade", "head"],
                environment=migration_environment,
                cwd=BACKEND_ROOT,
            )
            after_migration = asyncio.run(
                _database_fingerprint(target_url.render_as_string(hide_password=False))
            )
            _validate_fingerprints(
                source_fingerprint, after_migration, expected_head=expected_head
            )
            verify_seconds = time.monotonic() - verify_started
            report_parts = {
                "backup_bytes": backup_bytes,
                "backup_sha256": backup_sha256,
                "reconciliation": reconciliation,
                "timings_seconds": {
                    "backup": round(dump_seconds, 3),
                    "restore": round(restore_seconds, 3),
                    "verification": round(verify_seconds, 3),
                },
            }
        finally:
            if target_created:
                _run(
                    psql,
                    [
                        *admin_arguments,
                        "--dbname=postgres",
                        "--set=ON_ERROR_STOP=1",
                        "--quiet",
                        "--command="
                        f"ALTER DATABASE \"{target_database}\" WITH ALLOW_CONNECTIONS false;",
                    ],
                    environment=environment,
                )
                _run(
                    dropdb,
                    [*admin_arguments, "--force", target_database],
                    environment=environment,
                )
                remaining_target = _run(
                    psql,
                    [
                        *admin_arguments,
                        "--dbname=postgres",
                        "--tuples-only",
                        "--no-align",
                        "--set=ON_ERROR_STOP=1",
                        "--command="
                        f"SELECT datname FROM pg_database WHERE datname = '{target_database}';",
                    ],
                    environment=environment,
                )
                if remaining_target.strip():
                    raise T3BackupRestoreError("Ephemeral restore target still exists after cleanup.")
                target_created = False
                cleanup_verified = True

    if not report_parts or not cleanup_verified:
        raise T3BackupRestoreError("Rehearsal did not complete and clean its restore target.")
    total_seconds = time.monotonic() - started
    report_parts["timings_seconds"]["total"] = round(total_seconds, 3)
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_level": "T3_LOCAL_BACKUP_RESTORE_EXECUTION",
        "phase": "T3",
        "result": "PASS",
        "data_classification": "SYNTHETIC_AGGREGATES_ONLY",
        "supported_evidence_kind": "LOCAL_BACKUP_RESTORE_REPORT",
        "phase_accepted": False,
        "deployment_accepted": False,
        "source_database_scope": "taximobile_ci",
        "restore_target_scope": "EPHEMERAL_TAXIMOBILE_RESTORE_T3",
        "restore_target_removed": True,
        "temporary_dump_removed": True,
        **report_parts,
        "limitations": [
            "LOCAL_LOGICAL_BACKUP_ONLY",
            "NO_ENCRYPTED_MANAGED_BACKUP_OR_PITR_CLAIM",
            "NO_HOSTED_FAILOVER_OR_RPO_RTO_ACCEPTANCE",
            "NO_ROW_CONTENT_CAPTURED",
            "NO_PHASE_ACCEPTANCE_CLAIM",
            "NO_DEPLOYMENT_ACCEPTANCE_CLAIM",
        ],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--maintenance-user")
    parser.add_argument("--pg-dump", default="pg_dump")
    parser.add_argument("--pg-restore", default="pg_restore")
    parser.add_argument("--createdb", default="createdb")
    parser.add_argument("--dropdb", default="dropdb")
    parser.add_argument("--psql", default="psql")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    arguments = _parser().parse_args(list(argv) if argv is not None else None)
    try:
        report = run_rehearsal(
            output_path=arguments.output.resolve(),
            pg_dump=arguments.pg_dump,
            pg_restore=arguments.pg_restore,
            createdb=arguments.createdb,
            dropdb=arguments.dropdb,
            psql=arguments.psql,
            maintenance_user=arguments.maintenance_user,
        )
    except (OSError, ValueError, T3BackupRestoreError) as error:
        print(f"T3 backup/restore rehearsal failed: {error}", file=sys.stderr)
        return 1
    output = arguments.output.resolve()
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"T3 backup/restore rehearsal PASS: {report['reconciliation']['public_table_count']} "
        f"tables at {report['reconciliation']['migration_head']}; temporary target and dump removed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
