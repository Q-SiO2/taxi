"""Emit a bounded, redacted GitHub Actions annotation from a failed command log.

GitHub may withhold raw job logs from unauthenticated reviewers even for a public
repository. This helper exposes only a small diagnostic tail, strips common
credential forms and workspace paths, and optionally appends the same bounded
text to the job summary. It never changes the failed command's outcome.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import sys
from typing import Iterable


MAX_LOG_BYTES = 4 * 1024 * 1024
MAX_ANNOTATION_CHARACTERS = 3_500
MAX_DIAGNOSTIC_LINES = 80
CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
FAILURE_ANCHOR = re.compile(
    r"(?i)^\s*(?:\*\s*what went wrong:|caused by:|execution failed for task|"
    r"error:|e:\s+.+|exception in thread)"
)
SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(authorization|password|passwd|secret|token|api[_-]?key)"
    r"(\s*(?::|=)\s*)([^\s,;]+)"
)
BEARER_VALUE = re.compile(r"(?i)\b(Bearer)\s+[A-Za-z0-9._~+\-/]+=*")
URL_CREDENTIALS = re.compile(r"(://[^\s/:@]+:)[^\s/@]+(@)")


class DiagnosticError(RuntimeError):
    """Raised when a CI log cannot be handled within the safe boundary."""


def _redact(text: str, *, workspace: str | None = None) -> str:
    text = CONTROL_CHARACTERS.sub("", text)
    text = BEARER_VALUE.sub(r"\1 <redacted>", text)
    text = SECRET_ASSIGNMENT.sub(lambda match: f"{match.group(1)}{match.group(2)}<redacted>", text)
    text = URL_CREDENTIALS.sub(r"\1<redacted>\2", text)
    if workspace:
        normalized = workspace.rstrip("/\\")
        if normalized:
            text = re.sub(re.escape(normalized), "<workspace>", text, flags=re.IGNORECASE)
    return text


def diagnostic_tail(
    text: str,
    *,
    workspace: str | None = None,
    maximum_characters: int = MAX_ANNOTATION_CHARACTERS,
) -> str:
    if not 200 <= maximum_characters <= MAX_ANNOTATION_CHARACTERS:
        raise DiagnosticError(
            f"maximum characters must be between 200 and {MAX_ANNOTATION_CHARACTERS}."
        )
    redacted = _redact(text.replace("\r\n", "\n").replace("\r", "\n"), workspace=workspace)
    lines = [line.rstrip() for line in redacted.splitlines() if line.strip()]
    tail = "\n".join(lines[-MAX_DIAGNOSTIC_LINES:]) or "No diagnostic output was captured."
    anchors = [index for index, line in enumerate(lines) if FAILURE_ANCHOR.search(line)]
    selected: list[str] = []
    for index in anchors[:1] + anchors[-2:]:
        window = lines[max(0, index - 2) : min(len(lines), index + 9)]
        if window and window not in selected:
            selected.extend(window)
    primary = "\n".join(dict.fromkeys(selected))
    if primary:
        primary_budget = min(maximum_characters // 2, 1_700)
        if len(primary) > primary_budget:
            primary = "…\n" + primary[-(primary_budget - 2) :]
        tail_budget = maximum_characters - len(primary) - 2
        if len(tail) > tail_budget:
            tail = "…\n" + tail[-(tail_budget - 2) :]
        diagnostic = f"{primary}\n\n{tail}"
    else:
        diagnostic = tail
    if len(diagnostic) > maximum_characters:
        diagnostic = "…\n" + diagnostic[-(maximum_characters - 2) :]
    return diagnostic


def _annotation_value(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def emit_annotation(
    log_path: Path,
    *,
    title: str,
    maximum_characters: int = MAX_ANNOTATION_CHARACTERS,
    workspace: str | None = None,
    summary_path: Path | None = None,
) -> str:
    if not log_path.is_file():
        raise DiagnosticError("The requested CI diagnostic log does not exist.")
    size = log_path.stat().st_size
    if size > MAX_LOG_BYTES:
        raise DiagnosticError(f"The CI diagnostic log exceeds {MAX_LOG_BYTES} bytes.")
    diagnostic = diagnostic_tail(
        log_path.read_text(encoding="utf-8", errors="replace"),
        workspace=workspace,
        maximum_characters=maximum_characters,
    )
    print(f"::error title={_annotation_value(title)}::{_annotation_value(diagnostic)}")
    if summary_path is not None:
        with summary_path.open("a", encoding="utf-8", newline="\n") as summary:
            summary.write("## Bounded failure diagnostic\n\n")
            summary.write("Sensitive assignment forms and workspace paths are redacted.\n\n")
            summary.write("```text\n")
            summary.write(diagnostic)
            summary.write("\n```\n")
    return diagnostic


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument(
        "--maximum-characters",
        type=int,
        default=MAX_ANNOTATION_CHARACTERS,
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    arguments = _parser().parse_args(list(argv) if argv is not None else None)
    summary_value = os.environ.get("GITHUB_STEP_SUMMARY")
    try:
        emit_annotation(
            arguments.input,
            title=arguments.title,
            maximum_characters=arguments.maximum_characters,
            workspace=os.environ.get("GITHUB_WORKSPACE"),
            summary_path=Path(summary_value) if summary_value else None,
        )
    except (OSError, DiagnosticError) as error:
        print(f"CI diagnostic annotation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
