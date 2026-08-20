"""Reject high-confidence committed credential material without printing values.

CI scans Git-tracked files. A source archive or workspace without Git metadata
falls back to the documented source roots while skipping known local-only files,
build output, caches, backups, and generated environments.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable, NamedTuple


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOTS = (".github", "backend", "docs", "infra", "TaxiMobile")
EXCLUDED_DIRECTORIES = {
    ".git",
    ".gradle",
    ".idea",
    ".kotlin",
    ".pip-cache",
    ".pytest_cache",
    ".tools",
    ".venv",
    "__pycache__",
    "backups",
    "build",
    "captures",
    "node_modules",
    "test-results",
}
LOCAL_ONLY_NAMES = {".env", "local.properties"}
FORBIDDEN_TRACKED_NAMES = {
    ".env",
    "google-services.json",
    "GoogleService-Info.plist",
    "keystore.properties",
    "local.properties",
}
FORBIDDEN_TRACKED_SUFFIXES = {
    ".jks",
    ".key",
    ".keystore",
    ".mobileprovision",
    ".p12",
    ".pfx",
}
MAX_TEXT_BYTES = 2 * 1024 * 1024


class Finding(NamedTuple):
    path: Path
    rule: str


TOKEN_RULES = (
    ("private-key-material", re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----")),
    ("aws-access-key-id", re.compile(r"(?<![A-Z0-9])(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])")),
    ("google-api-key", re.compile(r"(?<![A-Za-z0-9_-])AIza[A-Za-z0-9_-]{35}(?![A-Za-z0-9_-])")),
    ("github-access-token", re.compile(r"(?<![A-Za-z0-9_])gh(?:p|o|u|s|r)_[A-Za-z0-9]{36,255}")),
    ("slack-access-token", re.compile(r"(?<![A-Za-z0-9-])xox(?:b|p|a|r|s)-[A-Za-z0-9-]{10,}")),
    ("stripe-live-secret", re.compile(r"(?<![A-Za-z0-9_])sk_live_[A-Za-z0-9]{16,}")),
)


def _within_source_roots(relative_path: Path) -> bool:
    return bool(relative_path.parts) and relative_path.parts[0] in SOURCE_ROOTS


def _excluded(relative_path: Path) -> bool:
    return any(part in EXCLUDED_DIRECTORIES for part in relative_path.parts)


def _git_tracked_files(workspace_root: Path) -> list[Path] | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(workspace_root), "ls-files", "-z"],
            check=False,
            capture_output=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return [Path(item.decode("utf-8")) for item in result.stdout.split(b"\0") if item]


def discover_source_files(workspace_root: Path) -> tuple[list[Path], bool]:
    tracked = _git_tracked_files(workspace_root)
    if tracked is not None:
        return (
            [
                workspace_root / relative
                for relative in tracked
                if _within_source_roots(relative) and not _excluded(relative)
            ],
            True,
        )

    files: list[Path] = []
    for source_root_name in SOURCE_ROOTS:
        source_root = workspace_root / source_root_name
        if not source_root.exists():
            continue
        for directory, directory_names, file_names in os.walk(source_root, followlinks=False):
            directory_path = Path(directory)
            directory_names[:] = [
                name
                for name in directory_names
                if name not in EXCLUDED_DIRECTORIES and not (directory_path / name).is_symlink()
            ]
            for name in file_names:
                path = directory_path / name
                if name not in LOCAL_ONLY_NAMES and not path.is_symlink():
                    files.append(path)
    return files, False


def _text(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_TEXT_BYTES:
            return None
        raw = path.read_bytes()
    except OSError:
        return None
    if b"\0" in raw:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def scan_files(workspace_root: Path, paths: Iterable[Path], *, tracked: bool) -> list[Finding]:
    findings: list[Finding] = []
    resolved_root = workspace_root.resolve()
    for path in paths:
        try:
            resolved = path.resolve()
            relative = resolved.relative_to(resolved_root)
        except (OSError, ValueError):
            continue
        if path.is_symlink() or _excluded(relative) or not _within_source_roots(relative):
            continue
        if tracked and (
            path.name in FORBIDDEN_TRACKED_NAMES or path.suffix.lower() in FORBIDDEN_TRACKED_SUFFIXES
        ):
            findings.append(Finding(relative, "forbidden-credential-file"))
            continue

        content = _text(path)
        if content is None:
            continue
        for rule, pattern in TOKEN_RULES:
            if pattern.search(content):
                findings.append(Finding(relative, rule))
        if path.suffix.lower() == ".json":
            try:
                document = json.loads(content)
            except json.JSONDecodeError:
                document = None
            if isinstance(document, dict) and (
                document.get("type") == "service_account"
                or "private_key" in document
                or "private_key_id" in document
            ):
                findings.append(Finding(relative, "service-account-document"))
    return sorted(set(findings), key=lambda finding: (str(finding.path), finding.rule))


def validate_workspace(workspace_root: Path = WORKSPACE_ROOT) -> None:
    paths, tracked = discover_source_files(workspace_root)
    findings = scan_files(workspace_root, paths, tracked=tracked)
    if findings:
        summary = ", ".join(f"{finding.path} [{finding.rule}]" for finding in findings)
        raise ValueError(f"Credential source gate rejected: {summary}")


def main() -> int:
    try:
        validate_workspace()
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    print("Validated source credential hygiene without reading local-only secret files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
