from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from validate_docs import (
    EXECUTION_PHASE_HEADING,
    discover_migration_head,
    extract_relative_links,
    validate_documentation,
)


class DocumentationValidatorTests(unittest.TestCase):
    def test_current_workspace_documentation_is_consistent(self) -> None:
        self.assertEqual([], validate_documentation())

    def test_discovers_latest_ordered_migration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "20260801_0001_first.py").write_text("", encoding="utf-8")
            (root / "20260831_0045_latest.py").write_text("", encoding="utf-8")
            (root / "README.txt").write_text("ignored", encoding="utf-8")
            self.assertEqual("20260831_0045", discover_migration_head(root))

    def test_extracts_only_relative_links(self) -> None:
        text = "[local](gaps.md#x) [web](https://example.test) [anchor](#same)"
        self.assertEqual([(1, "gaps.md")], list(extract_relative_links(text)))

    def test_execution_phase_heading_sequence_is_machine_readable(self) -> None:
        text = "\n".join(f"### T{index} — phase" for index in range(11))
        self.assertEqual(
            tuple(range(11)),
            tuple(int(match.group("id")) for match in EXECUTION_PHASE_HEADING.finditer(text)),
        )


if __name__ == "__main__":
    unittest.main()
