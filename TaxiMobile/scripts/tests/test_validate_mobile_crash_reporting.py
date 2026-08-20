from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "validate_mobile_crash_reporting.py"
SPEC = importlib.util.spec_from_file_location("validate_mobile_crash_reporting", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class MobileCrashReportingValidationTest(unittest.TestCase):
    def test_repository_wiring_is_valid(self) -> None:
        MODULE.validate_mobile_crash_reporting()

    def test_identity_attachment_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative in (
                "gradle/libs.versions.toml",
                "androidApp/build.gradle.kts",
                "androidApp/src/main/AndroidManifest.xml",
                "iosApp/iosApp.xcodeproj/project.pbxproj",
                "scripts/upload-ios-crash-symbols.sh",
            ):
                source = MODULE.ROOT / relative
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source.read_bytes())
            swift = root / "iosApp/iosApp/Unsafe.swift"
            swift.parent.mkdir(parents=True, exist_ok=True)
            swift.write_text('Crashlytics.crashlytics().setUserID("passenger")', encoding="utf-8")

            with self.assertRaises(MODULE.CrashReportingConfigurationError):
                MODULE.validate_mobile_crash_reporting(root)


if __name__ == "__main__":
    unittest.main()
