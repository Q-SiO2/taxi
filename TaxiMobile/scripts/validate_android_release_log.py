"""Fail closed on unsuccessful/stale minification or Kotlin metadata warnings.

The full log stays in the runner's protected diagnostics; only its hash/size and
fixed assertions are returned. This is source build evidence, not deployment.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re


class AndroidReleaseLogError(RuntimeError):
    pass


def validate_release_log(path: Path, r8_version: str) -> dict:
    if path.is_symlink() or not path.is_file() or not 1 <= path.stat().st_size <= 16 * 1024 * 1024:
        raise AndroidReleaseLogError("Missing, linked or oversized Android release build log.")
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        raise AndroidReleaseLogError("Android release build log must be UTF-8.") from None
    if (not re.search(r"^BUILD SUCCESSFUL in .+$", text, re.MULTILINE)
            or re.search(r"BUILD FAILED|FAILURE: Build failed", text)
            or re.search(r"(?:error occurred when parsing kotlin metadata|unsupported kotlin metadata|incompatible kotlin metadata)", text, re.IGNORECASE)):
        raise AndroidReleaseLogError("Android build failed or reported unsupported Kotlin metadata.")
    expected = f"Verified Android plugin R8 {r8_version} for Kotlin 2.4."
    if expected not in text:
        raise AndroidReleaseLogError("Android release log lacks the resolved compiler check.")
    for role in ("Passenger", "Driver"):
        # A cached/up-to-date mapping is not evidence of this invocation's compiler.
        if not re.search(rf"^> Task :androidApp:minify{role}ReleaseWithR8\s*$", text, re.MULTILINE):
            raise AndroidReleaseLogError("Both role minification tasks must actually execute.")
    return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
            "r8_version": r8_version, "both_minifiers_executed": True,
            "kotlin_metadata_warnings": False}
