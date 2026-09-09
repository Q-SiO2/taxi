from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from generate_release_evidence import (
    SOURCE_INPUTS,
    EvidenceError,
    generate_evidence,
    sha256_file,
)


class ReleaseEvidenceTests(unittest.TestCase):
    def test_sha256_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact.bin"
            path.write_bytes(b"taximobile")
            self.assertEqual(
                "c0458d9cea629dd5180a718eb7ead900782db7b69fcd9c270d0d03f9cf97bb57",
                sha256_file(path),
            )

    def _repository(self, root: Path) -> None:
        for relative in SOURCE_INPUTS:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"fixture for {relative}\n", encoding="utf-8")
        migration = root / "backend/migrations/versions/20260831_0045_latest.py"
        migration.parent.mkdir(parents=True, exist_ok=True)
        migration.write_text("revision = '20260831_0045'\n", encoding="utf-8")
        commands = (
            ("git", "init", "-q"),
            ("git", "config", "user.name", "TaxiMobile Test"),
            ("git", "config", "user.email", "test@example.invalid"),
            ("git", "add", "."),
            ("git", "commit", "-q", "-m", "fixture"),
        )
        for command in commands:
            subprocess.run(command, cwd=root, check=True, capture_output=True)

    def test_clean_candidate_and_explicit_dirty_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._repository(root)

            clean = generate_evidence(root, label="clean", allow_dirty=False)
            self.assertEqual("SOURCE_CANDIDATE", clean["evidence_level"])
            self.assertTrue(clean["source"]["clean"])
            self.assertFalse(clean["deployment_accepted"])
            self.assertEqual("20260831_0045", clean["source"]["migration_head"])

            (root / SOURCE_INPUTS[0]).write_text("dirty\n", encoding="utf-8")
            with self.assertRaises(EvidenceError):
                generate_evidence(root, label="dirty", allow_dirty=False)

            dirty = generate_evidence(root, label="snapshot", allow_dirty=True)
            self.assertEqual("WORKSPACE_SNAPSHOT", dirty["evidence_level"])
            self.assertFalse(dirty["source"]["clean"])
            self.assertFalse(dirty["deployment_accepted"])


if __name__ == "__main__":
    unittest.main()
