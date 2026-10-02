"""Collect secret-free post-run database facts for TaxiMobile T3 evidence.

This command connects only to the disposable ``taximobile_ci`` database from
``TAXIMOBILE_DATABASE_URL``. It never renders the URL, credentials, rows, or
database identifiers other than the fixed test namespace. A successful output
is database metadata for a candidate test run; it is not phase or deployment
acceptance.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any, Iterable

from validate_docs import discover_migration_head


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_ROOT = WORKSPACE_ROOT / "backend" / "migrations" / "versions"
AUTHORITY_MODES = {
    "TEMPORARY_CREATEDB_REVOKED",
    "EPHEMERAL_CI_SERVICE_ROLE",
}
DATABASE_LIFECYCLES = {
    "RECREATED_BEFORE_MIGRATION",
    "EPHEMERAL_SERVICE_DATABASE",
}


class T3DatabaseMetadataError(RuntimeError):
    """Raised when the database cannot support a safe T3 metadata record."""


def build_metadata_report(
    snapshot: dict[str, Any],
    *,
    expected_head: str,
    authority_mode: str,
    database_lifecycle: str,
    preexisting_clone_count: int = 0,
) -> dict[str, Any]:
    if authority_mode not in AUTHORITY_MODES:
        raise T3DatabaseMetadataError("Unsupported database authority mode.")
    if database_lifecycle not in DATABASE_LIFECYCLES:
        raise T3DatabaseMetadataError("Unsupported database lifecycle assertion.")
    if not isinstance(preexisting_clone_count, int) or preexisting_clone_count < 0:
        raise T3DatabaseMetadataError("Preexisting clone count must be a non-negative integer.")
    if snapshot.get("database_name") != "taximobile_ci":
        raise T3DatabaseMetadataError(
            "T3 metadata collection refuses every database except taximobile_ci."
        )
    migration_heads = snapshot.get("migration_heads")
    if migration_heads != [expected_head]:
        raise T3DatabaseMetadataError(
            "The disposable database is not at the single documented migration head."
        )
    if not isinstance(snapshot.get("postgres_version"), str) or not snapshot["postgres_version"]:
        raise T3DatabaseMetadataError("PostgreSQL did not report a server version.")
    if not isinstance(snapshot.get("postgis_version"), str) or not snapshot["postgis_version"]:
        raise T3DatabaseMetadataError("PostGIS is not installed in the disposable database.")
    if snapshot.get("residual_clone_database_count") != 0:
        raise T3DatabaseMetadataError(
            "Disposable taximobile_ci_test_* clone databases remain after the suite."
        )
    if not isinstance(snapshot.get("role_can_create_database"), bool) or not isinstance(
        snapshot.get("role_is_superuser"), bool
    ):
        raise T3DatabaseMetadataError("Database role authority flags are missing.")
    if authority_mode == "TEMPORARY_CREATEDB_REVOKED" and (
        snapshot["role_can_create_database"] or snapshot["role_is_superuser"]
    ):
        raise T3DatabaseMetadataError(
            "The local test role retained broad database authority after the suite."
        )

    authority_note = (
        "The local application test role had temporary clone authority revoked before "
        "metadata collection."
        if authority_mode == "TEMPORARY_CREATEDB_REVOKED"
        else "The broad role belongs only to the ephemeral CI service and is not a production-role model."
    )
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_level": "T3_DATABASE_POST_RUN_METADATA",
        "phase": "T3",
        "result": "PASS",
        "data_classification": "SYNTHETIC_METADATA_ONLY",
        "phase_accepted": False,
        "deployment_accepted": False,
        "database_scope": "taximobile_ci",
        "database_lifecycle": database_lifecycle,
        "migration_head": expected_head,
        "postgres_version": snapshot["postgres_version"],
        "postgis_version": snapshot["postgis_version"],
        "preexisting_clone_databases_removed": preexisting_clone_count,
        "residual_clone_database_count": 0,
        "authority": {
            "mode": authority_mode,
            "role_can_create_database": snapshot["role_can_create_database"],
            "role_is_superuser": snapshot["role_is_superuser"],
            "note": authority_note,
        },
        "limitations": [
            "NO_OPERATIONAL_DATABASE_CONTACT",
            "NO_ROW_OR_CREDENTIAL_CONTENT_CAPTURED",
            "NO_BACKUP_RESTORE_CLAIM",
            "NO_PHASE_ACCEPTANCE_CLAIM",
            "NO_DEPLOYMENT_ACCEPTANCE_CLAIM",
        ],
    }


async def collect_snapshot(database_url: str) -> dict[str, Any]:
    try:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine
    except ImportError as error:
        raise T3DatabaseMetadataError(
            "Backend dependencies are required to collect live T3 database metadata."
        ) from error

    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            database_name = await connection.scalar(text("SELECT current_database()"))
            migration_result = await connection.execute(
                text("SELECT version_num FROM alembic_version ORDER BY version_num")
            )
            migration_heads = list(migration_result.scalars())
            postgres_version = await connection.scalar(text("SHOW server_version"))
            postgis_version = await connection.scalar(
                text("SELECT extversion FROM pg_extension WHERE extname = 'postgis'")
            )
            residual_clones = await connection.scalar(
                text(
                    "SELECT count(*) FROM pg_database "
                    "WHERE datname LIKE 'taximobile_ci_test_%'"
                )
            )
            role_result = await connection.execute(
                text(
                    "SELECT rolcreatedb, rolsuper FROM pg_roles "
                    "WHERE rolname = current_user"
                )
            )
            role = role_result.mappings().one()
    except Exception as error:
        raise T3DatabaseMetadataError(
            f"Disposable T3 database metadata query failed ({type(error).__name__})."
        ) from error
    finally:
        await engine.dispose()

    return {
        "database_name": database_name,
        "migration_heads": migration_heads,
        "postgres_version": postgres_version,
        "postgis_version": postgis_version,
        "residual_clone_database_count": residual_clones,
        "role_can_create_database": role["rolcreatedb"],
        "role_is_superuser": role["rolsuper"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--authority-mode", required=True, choices=sorted(AUTHORITY_MODES))
    parser.add_argument(
        "--database-lifecycle", required=True, choices=sorted(DATABASE_LIFECYCLES)
    )
    parser.add_argument("--preexisting-clone-count", type=int, default=0)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    arguments = _parser().parse_args(list(argv) if argv is not None else None)
    output = arguments.output.resolve()
    if output.exists():
        print("T3 database metadata failed: refusing to overwrite existing evidence.", file=sys.stderr)
        return 1
    database_url = os.environ.get("TAXIMOBILE_DATABASE_URL")
    if not database_url:
        print("T3 database metadata failed: TAXIMOBILE_DATABASE_URL is required.", file=sys.stderr)
        return 1
    try:
        snapshot = asyncio.run(collect_snapshot(database_url))
        report = build_metadata_report(
            snapshot,
            expected_head=discover_migration_head(MIGRATIONS_ROOT),
            authority_mode=arguments.authority_mode,
            database_lifecycle=arguments.database_lifecycle,
            preexisting_clone_count=arguments.preexisting_clone_count,
        )
    except (OSError, ValueError, T3DatabaseMetadataError) as error:
        print(f"T3 database metadata failed: {error}", file=sys.stderr)
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"T3 database metadata PASS: migration {report['migration_head']}, "
        "zero residual clone databases, zero acceptance claims."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
