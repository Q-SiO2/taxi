from pathlib import Path
import hashlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validate_android_release_log import AndroidReleaseLogError, validate_release_log


class AndroidReleaseLogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "release.log"
        self.valid = ("Verified Android plugin R8 9.1.56 for Kotlin 2.4.10; distribution remains unaccepted.\n"
                      "> Task :androidApp:minifyPassengerReleaseWithR8\n"
                      "> Task :androidApp:minifyDriverReleaseWithR8\n"
                      "BUILD SUCCESSFUL in 2m 1s\n")

    def test_success_hashes_log_without_copying_diagnostics(self):
        self.path.write_text(self.valid)
        result = validate_release_log(self.path, "9.1.56")
        self.assertTrue(result["both_minifiers_executed"])
        self.assertFalse(result["kotlin_metadata_warnings"])
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), result["sha256"])
        self.assertEqual(self.path.stat().st_size, result["bytes"])
        self.assertEqual("9.1.56", result["r8_version"])
        self.assertNotIn("log_text", result)

    def test_failed_unsupported_missing_or_cached_execution_rejected(self):
        cases = (self.valid + "BUILD FAILED\n", self.valid.replace("BUILD SUCCESSFUL", "OTHER"),
                 self.valid.replace("9.1.56", "9.0.32"),
                 self.valid + "WARNING: R8: An error occurred when parsing kotlin metadata. private-token\n",
                 self.valid.replace("minifyDriverReleaseWithR8\n", "minifyDriverReleaseWithR8 UP-TO-DATE\n"),
                 self.valid.replace("minifyPassengerReleaseWithR8\n", "minifyPassengerReleaseWithR8 FROM-CACHE\n"))
        for text in cases:
            self.path.write_text(text)
            with self.assertRaises(AndroidReleaseLogError) as error:
                validate_release_log(self.path, "9.1.56")
            self.assertNotIn("private-token", str(error.exception))

    def test_missing_empty_or_invalid_encoding_rejected(self):
        with self.assertRaises(AndroidReleaseLogError):
            validate_release_log(self.path, "9.1.56")
        for raw in (b"", b"\xff\xfe"):
            self.path.write_bytes(raw)
            with self.assertRaises(AndroidReleaseLogError):
                validate_release_log(self.path, "9.1.56")
