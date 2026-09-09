"""Validate TaxiMobile's authoritative documentation as a release gate.

The documentation deliberately separates source delivery from deployment
acceptance. This validator prevents the status map, migration head, local links,
and gap/test sequences from silently drifting as implementation continues.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import Iterable


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = WORKSPACE_ROOT / "docs"
MIGRATIONS_ROOT = WORKSPACE_ROOT / "backend" / "migrations" / "versions"

AUTHORITATIVE_STATUS_DOCUMENTS = (
    "product.md",
    "operations.md",
    "architecture.md",
    "implementation.md",
    "roadmap.md",
    "api.md",
    "auth.md",
    "database.md",
    "drivers.md",
    "rides.md",
    "matching.md",
    "pricing.md",
    "payments.md",
    "design.md",
    "ui.md",
    "extended_ui.md",
    "security.md",
    "testing.md",
    "threat_model.md",
)
HEAD_REPORTING_DOCUMENTS = (
    "README.md",
    "gaps.md",
    "implementation.md",
    "roadmap.md",
    "database.md",
)
EXPECTED_GAP_IDS = tuple(range(1, 38))
EXPECTED_TEST_PHASES = tuple(range(0, 11))
EXPECTED_THREAT_IDS = tuple(
    [f"TM-ID-{index:02d}" for index in range(1, 7)]
    + [f"TM-AZ-{index:02d}" for index in range(1, 7)]
    + [f"TM-RD-{index:02d}" for index in range(1, 7)]
    + [f"TM-PY-{index:02d}" for index in range(1, 6)]
    + [f"TM-DT-{index:02d}" for index in range(1, 6)]
    + [f"TM-PL-{index:02d}" for index in range(1, 8)]
)
EXPECTED_SECURITY_PACK_IDS = tuple(f"SEC-{index:02d}" for index in range(1, 12))

MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\((?P<target>[^)]+)\)")
GAP_HEADING = re.compile(r"^### GAP-(?P<id>\d{3})\b", re.MULTILINE)
TEST_PHASE_HEADING = re.compile(r"^## \d+\. Phase T(?P<id>\d+)\b", re.MULTILINE)
EXECUTION_PHASE_HEADING = re.compile(r"^### T(?P<id>\d+)\b", re.MULTILINE)
THREAT_ROW = re.compile(r"^\| (?P<id>TM-[A-Z]{2}-\d{2}) \|", re.MULTILINE)
SECURITY_PACK_ROW = re.compile(r"^\| (?P<id>SEC-\d{2}) [^|]*\|", re.MULTILINE)
MIGRATION_FILENAME = re.compile(r"^(?P<revision>\d{8}_\d{4})_[a-z0-9_]+\.py$")
STANDING_HEADING = re.compile(
    r"(?:^## Current (?:implementation )?standing\b|^\*\*Current standing\b)",
    re.MULTILINE,
)


@dataclass(frozen=True, order=True)
class DocumentationIssue:
    path: str
    line: int
    reason: str


def _line(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def discover_migration_head(migrations_root: Path = MIGRATIONS_ROOT) -> str:
    revisions = []
    for path in migrations_root.glob("*.py"):
        match = MIGRATION_FILENAME.fullmatch(path.name)
        if match:
            revisions.append(match.group("revision"))
    if not revisions:
        raise ValueError(f"No ordered migration files found under {migrations_root}")
    return max(revisions)


def extract_relative_links(text: str) -> Iterable[tuple[int, str]]:
    for match in MARKDOWN_LINK.finditer(text):
        raw = match.group("target").strip().strip("<>")
        target = raw.split("#", 1)[0]
        if not target or re.match(r"^(?:https?://|mailto:|app://)", target):
            continue
        yield _line(text, match.start()), target


def _check_text_file(path: Path, docs_root: Path) -> list[DocumentationIssue]:
    issues: list[DocumentationIssue] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [DocumentationIssue(path.name, 1, "file is not valid UTF-8")]

    for line_number, line_text in enumerate(text.splitlines(), start=1):
        if line_text.endswith((" ", "\t")):
            issues.append(DocumentationIssue(path.name, line_number, "trailing whitespace"))

    if path.suffix.lower() == ".md":
        for line_number, target in extract_relative_links(text):
            resolved = path.parent / target
            if not resolved.exists():
                issues.append(
                    DocumentationIssue(
                        path.name,
                        line_number,
                        f"broken relative link: {target}",
                    )
                )
    return issues


def validate_documentation(
    docs_root: Path = DOCS_ROOT,
    migrations_root: Path = MIGRATIONS_ROOT,
) -> list[DocumentationIssue]:
    issues: list[DocumentationIssue] = []
    required = {
        "README.md",
        "gaps.md",
        "testing.md",
        "testing_execution_map.md",
        *AUTHORITATIVE_STATUS_DOCUMENTS,
    }
    for name in sorted(required):
        if not (docs_root / name).is_file():
            issues.append(DocumentationIssue(name, 1, "required document is missing"))

    for path in sorted(docs_root.iterdir() if docs_root.exists() else ()):
        if path.is_file() and path.suffix.lower() in {".md", ".txt"}:
            issues.extend(_check_text_file(path, docs_root))

    try:
        migration_head = discover_migration_head(migrations_root)
    except ValueError as error:
        issues.append(DocumentationIssue("database.md", 1, str(error)))
        migration_head = None

    for name in AUTHORITATIVE_STATUS_DOCUMENTS:
        path = docs_root / name
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            if not STANDING_HEADING.search(text):
                issues.append(DocumentationIssue(name, 1, "current standing block is missing"))

    if migration_head is not None:
        for name in HEAD_REPORTING_DOCUMENTS:
            path = docs_root / name
            if path.is_file() and migration_head not in path.read_text(encoding="utf-8"):
                issues.append(
                    DocumentationIssue(
                        name,
                        1,
                        f"current migration head {migration_head} is not reported",
                    )
                )

    gaps_path = docs_root / "gaps.md"
    if gaps_path.is_file():
        text = gaps_path.read_text(encoding="utf-8")
        gap_ids = tuple(int(match.group("id")) for match in GAP_HEADING.finditer(text))
        if gap_ids != EXPECTED_GAP_IDS:
            issues.append(
                DocumentationIssue(
                    gaps_path.name,
                    1,
                    f"gap heading sequence is {gap_ids!r}, expected {EXPECTED_GAP_IDS!r}",
                )
            )
        if "not ready for a public launch or live city pilot" not in text:
            issues.append(
                DocumentationIssue(
                    gaps_path.name,
                    1,
                    "deployment decision must remain explicit while P0 gaps are open",
                )
            )

    testing_path = docs_root / "testing.md"
    if testing_path.is_file():
        text = testing_path.read_text(encoding="utf-8")
        phase_ids = tuple(int(match.group("id")) for match in TEST_PHASE_HEADING.finditer(text))
        if phase_ids != EXPECTED_TEST_PHASES:
            issues.append(
                DocumentationIssue(
                    testing_path.name,
                    1,
                    f"test phase sequence is {phase_ids!r}, expected {EXPECTED_TEST_PHASES!r}",
                )
            )

    execution_map_path = docs_root / "testing_execution_map.md"
    if execution_map_path.is_file():
        text = execution_map_path.read_text(encoding="utf-8")
        phase_ids = tuple(
            int(match.group("id")) for match in EXECUTION_PHASE_HEADING.finditer(text)
        )
        if phase_ids != EXPECTED_TEST_PHASES:
            issues.append(
                DocumentationIssue(
                    execution_map_path.name,
                    1,
                    f"execution-map phase sequence is {phase_ids!r}, expected {EXPECTED_TEST_PHASES!r}",
                )
            )

    threat_model_path = docs_root / "threat_model.md"
    if threat_model_path.is_file():
        text = threat_model_path.read_text(encoding="utf-8")
        threat_ids = tuple(match.group("id") for match in THREAT_ROW.finditer(text))
        if threat_ids != EXPECTED_THREAT_IDS:
            issues.append(
                DocumentationIssue(
                    threat_model_path.name,
                    1,
                    "threat register sequence does not match the reviewed 35-threat baseline",
                )
            )
        security_pack_ids = tuple(
            match.group("id") for match in SECURITY_PACK_ROW.finditer(text)
        )
        if security_pack_ids != EXPECTED_SECURITY_PACK_IDS:
            issues.append(
                DocumentationIssue(
                    threat_model_path.name,
                    1,
                    "security test-pack sequence must remain SEC-01 through SEC-11",
                )
            )

    return sorted(set(issues))


def main() -> int:
    issues = validate_documentation()
    if issues:
        print("Documentation validation failed:", file=sys.stderr)
        for issue in issues:
            print(f"- docs/{issue.path}:{issue.line}: {issue.reason}", file=sys.stderr)
        return 1

    print(
        "Documentation validation passed: links, standing blocks, gap phases, "
        f"test phases, and migration head {discover_migration_head()} are consistent."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
