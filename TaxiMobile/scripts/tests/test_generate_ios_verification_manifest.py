from __future__ import annotations

import json
from pathlib import Path
import plistlib
import sys
import tempfile
import unittest


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from generate_ios_verification_manifest import (
    IosVerificationError,
    PRODUCTS,
    generate_manifest,
    main,
)


class IosVerificationManifestTests(unittest.TestCase):
    def _products(self, root: Path) -> Path:
        products = root / "Release-iphonesimulator"
        products.mkdir()
        for role, app_name, bundle_id in PRODUCTS:
            app = products / app_name
            app.mkdir()
            executable = f"TaxiMobile-{role}"
            with (app / "Info.plist").open("wb") as target:
                plistlib.dump(
                    {
                        "CFBundleIdentifier": bundle_id,
                        "CFBundleShortVersionString": "1.0.0",
                        "CFBundleVersion": "7",
                        "CFBundleExecutable": executable,
                    },
                    target,
                )
            (app / executable).write_bytes(f"binary-{role}".encode())
        return products

    def test_records_two_distinct_non_distributable_products(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = generate_manifest(
                self._products(Path(directory)),
                expected_version_name="1.0.0",
                expected_version_code=7,
            )
            self.assertEqual("IOS_SIMULATOR_VERIFICATION_ARTIFACTS", manifest["evidence_level"])
            self.assertFalse(manifest["deployment_accepted"])
            self.assertFalse(manifest["distribution_eligible"])
            self.assertEqual(2, len(manifest["artifacts"]))
            self.assertEqual(
                {"ma.taximobile.passenger", "ma.taximobile.driver"},
                {artifact["bundle_id"] for artifact in manifest["artifacts"]},
            )
            self.assertEqual(2, len({artifact["bundle_sha256"] for artifact in manifest["artifacts"]}))

    def test_rejects_wrong_bundle_identity_or_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            products = self._products(Path(directory))
            info_path = products / "TaxiMobile Driver.app" / "Info.plist"
            with info_path.open("rb") as source:
                info = plistlib.load(source)
            info["CFBundleIdentifier"] = "ma.taximobile.passenger"
            with info_path.open("wb") as target:
                plistlib.dump(info, target)
            with self.assertRaisesRegex(IosVerificationError, "CFBundleIdentifier"):
                generate_manifest(
                    products,
                    expected_version_name="1.0.0",
                    expected_version_code=7,
                )

    def test_cli_refuses_to_overwrite_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            products = self._products(root)
            output = root / "manifest.json"
            arguments = [
                "--products-dir", str(products),
                "--output", str(output),
                "--expected-version-name", "1.0.0",
                "--expected-version-code", "7",
            ]
            self.assertEqual(0, main(arguments))
            saved = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(2, len(saved["artifacts"]))
            self.assertEqual(1, main(arguments))


if __name__ == "__main__":
    unittest.main()
