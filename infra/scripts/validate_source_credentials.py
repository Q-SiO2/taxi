"""Reject high-confidence committed credential material without printing values.

CI scans Git-tracked files. Local candidate preparation can also include
non-ignored untracked files. A source archive without its own Git root falls back
to the documented source roots while skipping known local-only files, build
output, caches, backups, and generated environments.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable, NamedTuple, Sequence


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


def _git_tracked_files(
    workspace_root: Path, *, include_untracked: bool = False
) -> list[Path] | None:
    try:
        top_level = subprocess.run(
            ["git", "-C", str(workspace_root), "rev-parse", "--show-toplevel"],
            check=False,
            capture_output=True,
            timeout=15,
        )
        if top_level.returncode != 0:
            return None
        if Path(top_level.stdout.decode("utf-8").strip()).resolve() != workspace_root.resolve():
            # Git otherwise silently discovers a parent checkout and can return
            # zero tracked files for an ignored source archive inside it.
            return None
        arguments = ["git", "-C", str(workspace_root), "ls-files", "-z"]
        if include_untracked:
            arguments.extend(("--cached", "--others", "--exclude-standard"))
        result = subprocess.run(
            arguments,
            check=False,
            capture_output=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return [Path(item.decode("utf-8")) for item in result.stdout.split(b"\0") if item]


def discover_source_files(
    workspace_root: Path, *, include_untracked: bool = False
) -> tuple[list[Path], bool]:
    tracked = _git_tracked_files(workspace_root, include_untracked=include_untracked)
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


def validate_workspace(
    workspace_root: Path = WORKSPACE_ROOT, *, include_untracked: bool = False
) -> None:
    paths, tracked = discover_source_files(workspace_root, include_untracked=include_untracked)
    findings = scan_files(workspace_root, paths, tracked=tracked)
    if findings:
        summary = ", ".join(f"{finding.path} [{finding.rule}]" for finding in findings)
        raise ValueError(f"Credential source gate rejected: {summary}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-untracked",
        action="store_true",
        help="also scan non-ignored untracked source files during candidate preparation",
    )
    arguments = parser.parse_args(argv)
    try:
        validate_workspace(include_untracked=arguments.include_untracked)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    scope = "tracked and non-ignored untracked source" if arguments.include_untracked else "source"
    print(f"Validated {scope} credential hygiene without reading local-only secret files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
