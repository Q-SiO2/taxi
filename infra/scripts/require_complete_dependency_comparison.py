"""Fail closed when GitHub cannot compare both immutable PR dependency graphs.

The pinned review action reports snapshot warnings but does not itself fail on
them. This read-only guard checks every comparison page before and after review.
It uses only the standard library and never prints authentication or API bodies.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


WARNING_HEADER = "x-github-dependency-graph-snapshot-warnings"


class ComparisonError(ValueError):
    pass


def comparison_identity(event: dict, repository: str) -> tuple[str, str]:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ComparisonError("Invalid repository identity.")
    pull = event.get("pull_request", {})
    if any(pull.get(side, {}).get("repo", {}).get("full_name") != repository for side in ("base", "head")):
        raise ComparisonError("Fork dependency submission is not enabled; review remains unaccepted.")
    revisions = tuple(pull.get(side, {}).get("sha", "") for side in ("base", "head"))
    if not all(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) for value in revisions):
        raise ComparisonError("Dependency comparison requires immutable base and head revisions.")
    return revisions


def page_has_warning(header: str | None) -> bool:
    if not header:
        return False
    try:
        return bool(base64.b64decode(header, validate=True).decode("utf-8").strip())
    except (binascii.Error, UnicodeDecodeError) as error:
        raise ComparisonError("Malformed dependency snapshot warning header.") from error


def inspect_comparison(repository: str, base: str, head: str, token: str, *, opener=urlopen) -> dict:
    count = 0
    deadline = time.monotonic() + 30
    for page in range(1, 101):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ComparisonError("Dependency comparison exceeds the bounded request time.")
        request = Request(
            f"https://api.github.com/repos/{repository}/dependency-graph/compare/{base}...{head}?per_page=100&page={page}",
            headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}",
                     "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "TaxiMobile-dependency-completeness"},
        )
        try:
            with opener(request, timeout=min(15, remaining)) as response:
                if page_has_warning(response.headers.get(WARNING_HEADER)):
                    raise ComparisonError("Dependency graph snapshots are incomplete.")
                body = response.read(8_000_001)
        except HTTPError as error:
            status = error.code
            error.close()
            raise ComparisonError(f"Dependency comparison API returned HTTP {status}.") from None
        except (URLError, TimeoutError, OSError):
            raise ComparisonError("Dependency comparison API is unavailable.") from None
        if len(body) > 8_000_000:
            raise ComparisonError("Dependency comparison response exceeds the bounded size.")
        try:
            changes = json.loads(body)
        except (ValueError, UnicodeDecodeError):
            raise ComparisonError("Dependency comparison API returned malformed JSON.") from None
        if not isinstance(changes, list) or any(not isinstance(change, dict) for change in changes):
            raise ComparisonError("Dependency comparison API returned an unexpected shape.")
        count += len(changes)
        if len(changes) < 100:
            return {"repository": repository, "base_sha": base, "head_sha": head,
                    "pages": page, "changes": count, "snapshots_complete": True}
    raise ComparisonError("Dependency comparison exceeds the bounded page count.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wait-seconds", type=int, choices=range(0, 181), default=0)
    arguments = parser.parse_args()
    try:
        if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
            raise ComparisonError("This guard requires a pull_request event.")
        if os.environ.get("DEPENDENCY_SUBMISSION_RESULT") != "success":
            raise ComparisonError("Dependency graph submission did not succeed.")
        repository = os.environ.get("GITHUB_REPOSITORY", "")
        base, head = comparison_identity(json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text()), repository)
        token = os.environ.get("GITHUB_TOKEN", "")
        if not token:
            raise ComparisonError("Read-only dependency comparison token is unavailable.")
        deadline = time.monotonic() + arguments.wait_seconds
        while True:
            try:
                result = inspect_comparison(repository, base, head, token)
                print(json.dumps(result, sort_keys=True))
                return 0
            except ComparisonError:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise
                print("Dependency comparison is not complete; waiting within the finite budget.", flush=True)
                time.sleep(min(10, remaining))
    except (ComparisonError, KeyError, ValueError, OSError) as error:
        message = str(error) if isinstance(error, ComparisonError) else "Dependency comparison environment is invalid."
        print(f"::error::{message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
