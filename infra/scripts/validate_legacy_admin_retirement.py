"""Reject production client source that calls the transitional ``/admin`` API.

The compatibility routers intentionally remain backend-local for development and
test fixtures. This gate scans only maintained mobile and browser source roots;
it never reads build output, caches, local secrets, or generated distributions.
Error output names files but does not echo source lines or possible credentials.
"""

from __future__ import annotations

from pathlib import Path
import re
import sys


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
CLIENT_SOURCE_ROOTS = (
    Path("TaxiMobile/shared/src"),
    Path("TaxiMobile/androidApp/src"),
    Path("TaxiMobile/iosApp/iosApp"),
    Path("TaxiMobile/webApp/src"),
)
SOURCE_SUFFIXES = {
    ".html",
    ".js",
    ".kts",
    ".kt",
    ".mjs",
    ".swift",
    ".ts",
}
IGNORED_PARTS = {
    "build",
    "kotlin-js-store",
    "node_modules",
    "test-results",
}

# Match endpoint literals such as "admin/users/...", "/admin/...", or
# "/api/v1/admin/...". ``administrative-grants`` deliberately does not match.
LEGACY_ADMIN_LITERAL = re.compile(
    r"(?i)(?:/api/v1)?/admin(?:/|[\"'`?])|[\"'`]admin(?:/|[\"'`?])"
)


class LegacyAdminCallerError(RuntimeError):
    """Raised when a maintained client depends on global legacy authority."""


def _client_source_files(workspace_root: Path) -> list[Path]:
    files: list[Path] = []
    for relative_root in CLIENT_SOURCE_ROOTS:
        root = workspace_root / relative_root
        if not root.is_dir():
            raise LegacyAdminCallerError(
                f"Required client source root is missing: {relative_root.as_posix()}"
            )
        files.extend(
            path
            for path in root.rglob("*")
            if path.is_file()
            and path.suffix.lower() in SOURCE_SUFFIXES
            and not IGNORED_PARTS.intersection(path.parts)
        )
    return sorted(set(files))


def validate_legacy_admin_callers(workspace_root: Path = WORKSPACE_ROOT) -> None:
    offenders: list[str] = []
    for path in _client_source_files(workspace_root):
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise LegacyAdminCallerError(
                f"Client source is not valid UTF-8: {path.relative_to(workspace_root)}"
            ) from error
        if LEGACY_ADMIN_LITERAL.search(source):
            offenders.append(path.relative_to(workspace_root).as_posix())
    if offenders:
        raise LegacyAdminCallerError(
            "Production client source must not call the transitional /admin API; "
            "files=" + ", ".join(offenders)
        )


def main() -> int:
    try:
        validate_legacy_admin_callers()
    except (OSError, LegacyAdminCallerError) as error:
        print(f"Legacy-admin retirement validation failed: {error}", file=sys.stderr)
        return 1
    print(
        "Legacy-admin retirement validation passed: maintained mobile and web "
        "source has zero /admin callers."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
