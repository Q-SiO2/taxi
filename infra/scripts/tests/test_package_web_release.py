from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import package_web_release
from package_web_release import WebPackageError, package_distribution


class WebReleasePackageTests(unittest.TestCase):
    def _distribution(self, root: Path) -> Path:
        source = root / "distribution"
        source.mkdir()
        (source / "index.html").write_text(
            '<!doctype html><meta name="taximobile-client-version" content="1.0.0">'
            '<meta name="taximobile-client-build" content="1">'
            '<link rel="icon" href="favicon.svg">'
            '<script src="compatibility.js"></script>',
            encoding="utf-8",
        )
        (source / "favicon.svg").write_text("<svg></svg>", encoding="utf-8")
        (source / "styles.css").write_text("body {}", encoding="utf-8")
        (source / "compatibility.js").write_text(
            '/client-compatibility "X-TaxiMobile-Client" "X-TaxiMobile-Version" '
            '"X-TaxiMobile-Build" policy.status === "UPGRADE_REQUIRED" '
            'policy.status === "SUPPORTED" policy.status === "UPDATE_AVAILABLE" '
            'target.origin !== apiUrl.origin !target.pathname.startsWith(apiPathPrefix) window.fetch = '
            'return nativeFetch(input, init); return nativeFetch(input, { ...init, headers }); '
            'script.src = "webApp.js"',
            encoding="utf-8",
        )
        (source / "webApp.js").write_text("loader", encoding="utf-8")
        (source / "originJsWebApp.js").write_text("js", encoding="utf-8")
        (source / "originWasmWebApp.js").write_text("wasm", encoding="utf-8")
        (source / "app.wasm").write_bytes(b"app")
        (source / "skiko.wasm").write_bytes(b"skiko")
        (source / "originJsWebApp.js.map").write_text("private source map", encoding="utf-8")
        return source

    def test_packages_hashes_and_excludes_source_maps(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "release"
            manifest = package_distribution(self._distribution(root), output)

            self.assertFalse((output / "originJsWebApp.js.map").exists())
            self.assertTrue((output / "release-manifest.json").is_file())
            self.assertEqual(1, manifest["summary"]["excluded_source_map_count"])
            self.assertFalse(manifest["deployment_accepted"])
            self.assertEqual("1.0.0", manifest["summary"]["client_version"])
            self.assertEqual("1", manifest["summary"]["client_build"])
            saved = json.loads((output / "release-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["files"]), len(saved["files"]))

    def test_rejects_bundle_growth_over_reviewed_budget(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._distribution(root)
            with patch.dict(package_web_release.WEB_BUDGETS, {"originJsWebApp.js": 1}):
                with self.assertRaises(WebPackageError):
                    package_distribution(source, root / "release")

    def test_rejects_missing_or_malformed_client_build_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._distribution(root)
            index = source / "index.html"
            index.write_text(
                index.read_text(encoding="utf-8").replace(
                    'content="1.0.0"', 'content="latest"'
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(WebPackageError, "client version and build metadata"):
                package_distribution(source, root / "release")

    def test_rejects_direct_application_boot_that_bypasses_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._distribution(root)
            index = source / "index.html"
            index.write_text(
                index.read_text(encoding="utf-8").replace(
                    'src="compatibility.js"', 'src="webApp.js"'
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(WebPackageError, "compatibility.js"):
                package_distribution(source, root / "release")


if __name__ == "__main__":
    unittest.main()
