"""Generate a secret-free, machine-readable TaxiMobile source evidence record.

This is provenance for a candidate build, not deployment acceptance. The command
fails on a dirty tree unless the caller explicitly requests a workspace snapshot.
Optional artifacts are hashed without reading environment secrets or configuration
values.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Sequence

from validate_docs import discover_migration_head


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
SOURCE_INPUTS = (
    ".github/workflows/ci.yml",
    "backend/requirements.lock",
    "backend/requirements-dev.lock",
    "backend/requirements-linux.lock",
    "backend/Dockerfile",
    "TaxiMobile/gradle/libs.versions.toml",
    "TaxiMobile/gradle/wrapper/gradle-wrapper.properties",
    "TaxiMobile/settings.gradle.kts",
    "infra/deploy/compose.production.yaml",
    "infra/scripts/generate_release_evidence.py",
    "infra/scripts/generate_source_contract_inventory.py",
    "infra/scripts/package_web_release.py",
    "infra/scripts/validate_docs.py",
    "infra/scripts/validate_test_phase_evidence.py",
    "infra/testing/test-phase-catalog.json",
    "infra/testing/test-evidence-index.template.json",
    "docs/README.md",
    "docs/gaps.md",
    "docs/testing.md",
    "docs/testing_execution_map.md",
)


class EvidenceError(RuntimeError):
    pass


def _git(root: Path, *arguments: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise EvidenceError(f"Git invocation failed: {error}") from error
    if result.returncode != 0:
        reason = result.stderr.strip() or "unknown Git error"
        raise EvidenceError(f"Git {' '.join(arguments)} failed: {reason}")
    return result.stdout.strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _status_counts(root: Path) -> tuple[int, int]:
    porcelain = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
    tracked = 0
    untracked = 0
    for line in porcelain.splitlines():
        if line.startswith("??"):
            untracked += 1
        elif line:
            tracked += 1
    return tracked, untracked


def _relative_display(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _file_record(root: Path, path: Path) -> dict[str, object]:
    if not path.is_file():
        raise EvidenceError(f"Evidence input is not a file: {path}")
    return {
        "path": _relative_display(root, path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def generate_evidence(
    root: Path = WORKSPACE_ROOT,
    *,
    label: str,
    artifacts: Sequence[Path] = (),
    allow_dirty: bool = False,
) -> dict[str, object]:
    commit = _git(root, "rev-parse", "HEAD")
    tree = _git(root, "rev-parse", "HEAD^{tree}")
    commit_time = _git(root, "show", "-s", "--format=%cI", "HEAD")
    tracked_changes, untracked_files = _status_counts(root)
    clean = tracked_changes == 0 and untracked_files == 0
    if not clean and not allow_dirty:
        raise EvidenceError(
            "Refusing release evidence for a dirty tree. Commit/review the candidate "
            "or use --allow-dirty only for a clearly labeled workspace snapshot."
        )

    inputs = [_file_record(root, root / relative) for relative in SOURCE_INPUTS]
    artifact_records = [_file_record(root, path) for path in artifacts]
    ci = {
        "provider": "github-actions" if os.environ.get("GITHUB_ACTIONS") == "true" else "local",
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "ref": os.environ.get("GITHUB_REF"),
        "reported_sha": os.environ.get("GITHUB_SHA"),
    }
    ci = {key: value for key, value in ci.items() if value is not None}

    return {
        "schema_version": 1,
        "label": label,
        "evidence_level": "SOURCE_CANDIDATE" if clean else "WORKSPACE_SNAPSHOT",
        "deployment_accepted": False,
        "deployment_acceptance_note": (
            "This record proves source/artifact identity only. It cannot prove city, legal, "
            "provider, operational, security, device, payment, or real-user acceptance."
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "commit": commit,
            "tree": tree,
            "commit_time": commit_time,
            "clean": clean,
            "tracked_change_count": tracked_changes,
            "untracked_file_count": untracked_files,
            "migration_head": discover_migration_head(
                root / "backend" / "migrations" / "versions"
            ),
        },
        "ci": ci,
        "source_inputs": inputs,
        "artifacts": artifact_records,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True, help="Human-readable candidate/run label.")
    parser.add_argument(
        "--artifact",
        action="append",
        default=[],
        type=Path,
        help="Artifact to hash; repeat for multiple artifacts.",
    )
    parser.add_argument("--output", type=Path, help="Write JSON here instead of stdout.")
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Generate a non-release WORKSPACE_SNAPSHOT for diagnostics.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        evidence = generate_evidence(
            label=arguments.label,
            artifacts=arguments.artifact,
            allow_dirty=arguments.allow_dirty,
        )
    except EvidenceError as error:
        print(str(error), file=sys.stderr)
        return 1

    rendered = json.dumps(evidence, indent=2, sort_keys=True) + "\n"
    if arguments.output is None:
        print(rendered, end="")
    else:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered, encoding="utf-8", newline="\n")
        print(
            f"Wrote {evidence['evidence_level']} evidence to {arguments.output} "
            f"for migration {evidence['source']['migration_head']}."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
