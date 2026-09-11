from __future__ import annotations

import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from emit_ci_failure_annotation import DiagnosticError, diagnostic_tail, emit_annotation


class CiFailureAnnotationTests(unittest.TestCase):
    def test_diagnostic_tail_redacts_secrets_urls_and_workspace(self) -> None:
        diagnostic = diagnostic_tail(
            "\n".join(
                (
                    "Authorization: Bearer abc.def",
                    "token=plain-token",
                    "https://runner:password@example.test/path",
                    "/work/taxi/shared/src/File.kt: failure",
                )
            ),
            workspace="/work/taxi",
        )
        self.assertNotIn("abc.def", diagnostic)
        self.assertNotIn("plain-token", diagnostic)
        self.assertNotIn("password@example", diagnostic)
        self.assertNotIn("/work/taxi", diagnostic)
        self.assertIn("<workspace>/shared/src/File.kt: failure", diagnostic)

    def test_diagnostic_tail_is_bounded_to_recent_lines_and_characters(self) -> None:
        text = "\n".join(f"line-{index}-" + ("x" * 50) for index in range(150))
        diagnostic = diagnostic_tail(text, maximum_characters=500)
        self.assertLessEqual(len(diagnostic), 500)
        self.assertIn("line-149", diagnostic)
        self.assertNotIn("line-0-", diagnostic)

    def test_emit_annotation_writes_encoded_stdout_and_bounded_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / "failure.log"
            summary = root / "summary.md"
            log.write_text("FAILURE: task failed\nreason=bad%state\n", encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                diagnostic = emit_annotation(
                    log,
                    title="iOS shared failure",
                    summary_path=summary,
                )
            self.assertIn("::error title=iOS shared failure::", stdout.getvalue())
            self.assertIn("%0A", stdout.getvalue())
            self.assertIn("%25", stdout.getvalue())
            self.assertIn(diagnostic, summary.read_text(encoding="utf-8"))

    def test_missing_or_oversized_log_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(DiagnosticError, "does not exist"):
                emit_annotation(root / "missing.log", title="failure")
            oversized = root / "oversized.log"
            oversized.write_bytes(b"x" * (4 * 1024 * 1024 + 1))
            with self.assertRaisesRegex(DiagnosticError, "exceeds"):
                emit_annotation(oversized, title="failure")


if __name__ == "__main__":
    unittest.main()
