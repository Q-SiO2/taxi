"""Retain exact OpenAPI payload contracts for GAP-001 without starting services.

Two explicitly selected route profiles avoid mistaking the development-only
global /admin surface for the launch contract. Canonical UTF-8/LF bytes bind the
entire schema, not merely operation names. No lifespan, request or provider call
is executed. CI must bind all three output files to clean source evidence.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Mapping, Sequence

from generate_source_contract_inventory import api_inventory, InventoryError


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
PROFILES = {"launch-api": False, "local-compatibility-api": True}
MANIFEST_NAME = "openapi-manifest.json"


class OpenApiEvidenceError(RuntimeError):
    pass


def canonical_schema(document: Mapping[str, object]) -> bytes:
    """Stable key order; preserve list order because lists may encode semantics."""
    if not isinstance(document.get("openapi"), str):
        raise OpenApiEvidenceError("Missing OpenAPI version.")
    try:
        api_inventory(document, ())
        return (json.dumps(document, sort_keys=True, indent=2, ensure_ascii=False,
                           allow_nan=False) + "\n").encode("utf-8")
    except (InventoryError, ValueError, TypeError) as error:
        raise OpenApiEvidenceError("Invalid OpenAPI source contract.") from error


def contract_bundle(documents: Mapping[str, Mapping[str, object]]) -> tuple[dict, dict[str, bytes]]:
    if set(documents) != set(PROFILES):
        raise OpenApiEvidenceError("Both exact OpenAPI route profiles are required.")
    files: dict[str, bytes] = {}
    records = []
    for profile, legacy in PROFILES.items():
        document = documents[profile]
        inventory = api_inventory(document, ())
        operations = inventory["http_operations"]
        legacy_operations = [item for item in operations
                             if item["path"] == "/api/v1/admin"
                             or item["path"].startswith("/api/v1/admin/")]
        if bool(legacy_operations) != legacy:
            raise OpenApiEvidenceError("OpenAPI profile has incorrect legacy-admin exposure.")
        if not any(item["path"].startswith("/api/v1/operations/") for item in operations):
            raise OpenApiEvidenceError("OpenAPI profile is missing scoped operations contracts.")
        encoded = canonical_schema(document)
        filename = f"{profile}.openapi.json"
        files[filename] = encoded
        records.append({"profile": profile, "path": filename, "bytes": len(encoded),
                        "sha256": hashlib.sha256(encoded).hexdigest(),
                        "legacy_admin_api_enabled": legacy,
                        "http_operation_count": inventory["http_operation_count"]})
    # FastAPI can qualify component names differently when legacy models with
    # overlapping names are mounted. Retain both entire schemas and their own
    # digests; raw $ref spelling is not proof of payload equivalence. Behavioral
    # compatibility still needs the API/negative-authorization contract tests.
    launch = api_inventory(documents["launch-api"], ())["http_operations"]
    compatibility = api_inventory(documents["local-compatibility-api"], ())["http_operations"]
    keys = lambda rows: {(item["method"], item["path"], item["operation_id"]) for item in rows}
    if not keys(launch) <= keys(compatibility):
        raise OpenApiEvidenceError("Compatibility profile omits a launch operation.")
    return ({"schema_version": 1, "evidence_level": "SOURCE_OPENAPI_CONTRACTS",
             "deployment_accepted": False, "authorization_accepted": False,
             "contracts": records,
             "limitations": ["Source schemas do not prove runtime authorization or deployment configuration.",
                             "WebSocket payloads are outside OpenAPI and require separate tests.",
                             "Bind these exact files to one clean candidate before promotion."]}, files)


def load_documents(root: Path = WORKSPACE_ROOT) -> dict[str, dict]:
    # Importing main constructs its module-level app. Isolate *that import* as
    # well as explicit factories; do not just replace settings after importing.
    # Inherit only OS/runtime necessities, never provider/DB/auth/log settings.
    environment = {key: os.environ[key] for key in
                   ("PATH", "SystemRoot", "WINDIR", "TEMP", "TMP", "LANG", "LC_ALL")
                   if key in os.environ}
    environment.update({"PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
                        "TAXIMOBILE_ENV": "test", "TAXIMOBILE_PROCESS_ROLE": "api"})
    try:
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()),
                                 "--schema-worker", str(root.resolve())],
                                env=environment, capture_output=True, timeout=45, check=False)
        if result.returncode != 0:
            raise OpenApiEvidenceError("Isolated schema generation failed.")
        documents = json.loads(result.stdout)
        if not isinstance(documents, dict) or set(documents) != set(PROFILES) or any(
            not isinstance(value, dict) for value in documents.values()
        ):
            raise OpenApiEvidenceError("Isolated schema generation failed.")
        return documents
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        raise OpenApiEvidenceError("Isolated schema generation failed.") from error


def _load_documents_in_worker(root: Path) -> dict[str, dict]:
    if {key for key in os.environ if key.upper().startswith("TAXIMOBILE_")} != {
        "TAXIMOBILE_ENV", "TAXIMOBILE_PROCESS_ROLE"
    } or os.environ.get("TAXIMOBILE_ENV") != "test" or os.environ.get("TAXIMOBILE_PROCESS_ROLE") != "api":
        raise OpenApiEvidenceError("Schema worker requires its isolated test environment.")
    source = str(root / "backend" / "src")
    if source not in sys.path:
        sys.path.insert(0, source)
    from taximobile_api.core.config import Settings
    from taximobile_api.main import create_app

    # Only source defaults plus explicit route-profile flags are used. Never
    # start a TestClient/lifespan, read local secret files or query a database.
    settings = replace(Settings.from_environment(), process_role="api", api_prefix="/api/v1")
    return {profile: create_app(settings=replace(settings, legacy_admin_api_enabled=legacy)).openapi()
            for profile, legacy in PROFILES.items()}


def write_bundle(directory: Path, manifest: dict, files: Mapping[str, bytes]) -> None:
    targets = [directory / name for name in (*files, MANIFEST_NAME)]
    if any(target.exists() for target in targets):
        raise OpenApiEvidenceError("Refusing to overwrite retained OpenAPI evidence; choose a fresh output directory.")
    directory.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also refuses a concurrent writer. Partial failures are
    # explicit; never replace an earlier report or present partial output as PASS.
    for name, encoded in files.items():
        with (directory / name).open("xb") as output:
            output.write(encoded)
    with (directory / MANIFEST_NAME).open("xb") as output:
        output.write((json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    arguments = parser.parse_args(argv)
    try:
        manifest, files = contract_bundle(load_documents())
        write_bundle(arguments.output_dir, manifest, files)
    except OpenApiEvidenceError as error:
        print(f"OpenAPI evidence failed: {error}", file=sys.stderr)
        return 1
    except (InventoryError, OSError) as error:
        # Do not serialize runtime configuration, exception causes or credentials.
        print(f"OpenAPI evidence failed: {type(error).__name__}.", file=sys.stderr)
        return 1
    print("Retained two OpenAPI source contracts; authorization/deployment acceptance remain false.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--schema-worker":
        try:
            documents = _load_documents_in_worker(Path(sys.argv[2]))
            sys.stdout.buffer.write(json.dumps(documents, ensure_ascii=False, allow_nan=False).encode("utf-8"))
        except Exception:
            # The parent never prints captured stderr or unbounded exceptions.
            print("Isolated OpenAPI generation failed.", file=sys.stderr)
            raise SystemExit(1)
        raise SystemExit(0)
    raise SystemExit(main())
