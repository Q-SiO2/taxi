from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import generate_android_verification_manifest as android


class AndroidVerificationManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        report = self.root / "build/reports/android-shrinker/resolved-shrinker.json"
        report.parent.mkdir(parents=True)
        self.shrinker = {"schema_version": 1, "evidence_level": "ANDROID_RESOLVED_SHRINKER",
            "deployment_accepted": False, "distribution_eligible": False,
            "kotlin_version": "2.4.10", "r8_version": android.R8_VERSION,
            "resolution_scope": "AGP_PLUGIN_CLASSLOADER", "compiler_artifact_bytes": 100,
            "compiler_artifact_sha256": "a" * 64}
        report.write_text(json.dumps(self.shrinker))
        self.paths, self.documents = {}, {}
        for role, variant, app_id in android.PRODUCTS:
            directory = self.root / "androidApp/build/outputs/apk" / role / "release"
            directory.mkdir(parents=True)
            apk = directory / f"{role}.apk"
            self.marker = {"backend": "dex", "compilation-mode": "release", "r8-mode": "full",
                           "version": android.R8_VERSION, "pg-map-id": "b" * 64}
            with zipfile.ZipFile(apk, "w") as archive:
                archive.writestr("classes.dex", b"dex\n039\x00~~R8" + json.dumps(self.marker).encode() + b"\x00")
                archive.writestr("fixture-padding", role.encode() + b"0" * 1024 * 1024)
            self.paths[role] = apk
            self.documents[role] = {"artifactType": {"type": "APK"}, "applicationId": app_id,
                "variantName": variant, "elements": [{"versionCode": 7, "versionName": "2.3.4",
                "filters": [], "type": "SINGLE", "outputFile": apk.name}]}
            self.save(role)
            mapping = self.root / "androidApp/build/outputs/mapping" / variant / "mapping.txt"
            mapping.parent.mkdir(parents=True)
            mapping.write_text(f"# compiler: R8\n# compiler_version: {android.R8_VERSION}\n# pg_map_id: {'b' * 64}\nsynthetic.Class -> x:\n")

    def save(self, role):
        (self.paths[role].parent / "output-metadata.json").write_text(json.dumps(self.documents[role]))

    def identity(self, apk, tool):
        role = apk.parent.parent.name
        return {"application_id": f"ma.taximobile.{role}", "version_code": 7, "version_name": "2.3.4"}

    def generate(self):
        return android.generate_manifest(self.root, version_code=7, version_name="2.3.4", aapt2=Path("synthetic-aapt2"))

    def test_both_actual_identities_hashed_and_never_distribution_accepted(self):
        with patch.object(android, "packaged_identity", side_effect=self.identity) as inspected:
            result = self.generate()
        self.assertEqual(2, inspected.call_count)
        self.assertFalse(result["distribution_eligible"])
        self.assertFalse(result["deployment_accepted"])
        self.assertEqual(3, len(result["limitations"]))
        for item in result["artifacts"]:
            self.assertEqual(android.sha256(self.paths[item["role"]]), item["sha256"])
            self.assertEqual("AAPT2_PACKAGED_MANIFEST", item["identity_verification"])

    def test_packaged_identity_mismatch_despite_correct_metadata(self):
        for key, value in (("application_id", "ma.foreign.app"), ("version_code", 8), ("version_name", "3.0.0")):
            actual = self.identity(self.paths["passenger"], None)
            actual[key] = value
            with patch.object(android, "packaged_identity", return_value=actual):
                with self.assertRaisesRegex(android.AndroidVerificationError, "actual passenger APK"):
                    self.generate()

    def test_unsafe_references_rejected_before_hash_or_tool_execution(self):
        for name in ("../driver.apk", "../../outside.apk", "/tmp/outside.apk", "C:\\outside.apk",
                     "subdir/app.apk", "\\\\host\\share\\app.apk", "-option.apk", "app.apk:stream", "x.txt"):
            self.documents["passenger"]["elements"][0]["outputFile"] = name
            self.save("passenger")
            with patch.object(android, "packaged_identity") as inspected:
                with self.subTest(name=name), self.assertRaisesRegex(android.AndroidVerificationError, "safe filename"):
                    self.generate()
                inspected.assert_not_called()

    def test_metadata_mismatch_malformed_and_split_inputs_rejected(self):
        original = json.loads(json.dumps(self.documents["passenger"]))
        mutations = [{**original, "applicationId": "other"}, {**original, "variantName": "driverRelease"},
                     {**original, "artifactType": []}, {**original, "elements": []},
                     {**original, "elements": [None]}, {**original, "elements": original["elements"] * 2}]
        for key, value in (("versionCode", True), ("versionCode", 8), ("versionName", "1.0.0"),
                           ("filters", [{"filterType": "ABI", "value": "arm64-v8a"}]),
                           ("type", "ONE_OF_MANY")):
            changed = json.loads(json.dumps(original))
            changed["elements"][0][key] = value
            mutations.append(changed)
        for document in mutations:
            self.documents["passenger"] = document
            self.save("passenger")
            with patch.object(android, "packaged_identity") as inspected:
                with self.assertRaises(android.AndroidVerificationError):
                    self.generate()
                inspected.assert_not_called()

    def test_missing_small_or_linked_apk_rejected(self):
        path = self.paths["passenger"]
        with patch.object(Path, "is_symlink", side_effect=lambda: True):
            with self.assertRaises(android.AndroidVerificationError):
                self.generate()
        path.write_bytes(b"small")
        with self.assertRaisesRegex(android.AndroidVerificationError, "small"):
            self.generate()
        path.unlink()
        with self.assertRaisesRegex(android.AndroidVerificationError, "Missing"):
            self.generate()

    def test_duplicate_product_bytes_and_mutation_during_inspection_rejected(self):
        self.paths["driver"].write_bytes(self.paths["passenger"].read_bytes())
        with patch.object(android, "packaged_identity", side_effect=self.identity):
            with self.assertRaisesRegex(android.AndroidVerificationError, "distinct"):
                self.generate()
        with patch.object(android, "packaged_identity", side_effect=self.identity), \
                patch.object(android, "sha256", side_effect=["report", "report", "before", "map", "map", "after"]):
            with self.assertRaisesRegex(android.AndroidVerificationError, "changed during"):
                self.generate()

    def test_badging_parser_handles_real_tool_shape_and_rejects_ambiguity(self):
        text = "package: name='ma.taximobile.passenger' versionCode='7' versionName='2.3.4' platformBuildVersionCode='36'\nminSdkVersion:'24'\n"
        self.assertEqual(self.identity(self.paths["passenger"], None), android.parse_badging(text))
        for malformed in ("", text + text, text.replace("versionCode='7'", "versionCode='0'"),
                          text.replace("platformBuildVersionCode=", "split='config.en' platformBuildVersionCode="),
                          text.replace("versionName='2.3.4'", "versionName='2.3.4-beta'"),
                          text.replace("versionCode='7'", "versionCode='7' versionCode='8'")):
            with self.assertRaises(android.AndroidVerificationError):
                android.parse_badging(malformed)

    def test_duplicate_or_nonobject_metadata_rejected(self):
        path = self.paths["passenger"].parent / "output-metadata.json"
        for text in ('{"applicationId":"one","applicationId":"two"}', "[]", "not-json"):
            path.write_text(text)
            with self.assertRaises(android.AndroidVerificationError):
                self.generate()

    def test_invalid_expected_versions_rejected(self):
        for code, version in ((True, "1.0.0"), (0, "1.0.0"), (2147483648, "1.0.0"),
                              (1, "01.2.3"), (1, "1.2"), (1, "1.2.3-beta")):
            with self.assertRaises(android.AndroidVerificationError):
                android.generate_manifest(self.root, version_code=code, version_name=version, aapt2=Path("fake"))

    def test_tool_failure_timeout_and_stderr_are_bounded(self):
        failed = subprocess.CompletedProcess([], 1, "private-output", "private-token")
        for result in (failed, subprocess.TimeoutExpired("tool", 45), OSError("private-path")):
            kwargs = {"side_effect": result} if isinstance(result, Exception) else {"return_value": result}
            with patch.object(android.subprocess, "run", **kwargs):
                with self.assertRaises(android.AndroidVerificationError) as error:
                    android.packaged_identity(self.paths["passenger"], Path("synthetic"))
                self.assertNotIn("private", str(error.exception))

    def test_sdk_lookup_prefers_environment_and_requires_pinned_tool(self):
        import os
        with patch.dict(os.environ, {"ANDROID_HOME": str(self.root)}, clear=True):
            with self.assertRaises(android.AndroidVerificationError):
                android.find_aapt2(self.root)
            tool = self.root / "build-tools" / "36.1.0" / ("aapt2.exe" if os.name == "nt" else "aapt2")
            tool.parent.mkdir(parents=True)
            tool.write_bytes(b"synthetic tool fixture")
            self.assertEqual(tool, android.find_aapt2(self.root))

    def test_wrapper_delegates_and_propagates_failure(self):
        wrapper = Path(__file__).resolve().parents[1] / "verify-android-release-artifacts.ps1"
        text = wrapper.read_text()
        for required in ("generate_android_verification_manifest.py", "--expected-version-code",
                         "--expected-version-name", "--output", "--aapt2", "$LASTEXITCODE -ne 0"):
            self.assertIn(required, text)

    def test_existing_evidence_is_preserved_without_inspecting_apks(self):
        output = self.root / "evidence.json"
        output.write_bytes(b"existing evidence")
        args = ["script", "--project-dir", str(self.root), "--output", str(output), "--aapt2", "synthetic"]
        with patch.object(sys, "argv", args), patch.object(android, "generate_manifest") as generated:
            self.assertEqual(1, android.main())
            generated.assert_not_called()
        self.assertEqual(b"existing evidence", output.read_bytes())

    def test_cli_failure_never_creates_manifest(self):
        output = self.root / "uncreated.json"
        args = ["script", "--project-dir", str(self.root), "--output", str(output), "--aapt2", "synthetic",
                "--expected-version-code", "7", "--expected-version-name", "2.3.4"]
        with patch.object(sys, "argv", args), patch.object(android, "packaged_identity", side_effect=android.AndroidVerificationError("fixture failure")) as inspected:
            self.assertEqual(1, android.main())
            inspected.assert_called_once()
        self.assertFalse(output.exists())

    def test_sdk_lookup_handles_windows_properties_and_missing_configuration(self):
        import os
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(android.AndroidVerificationError):
                android.find_aapt2(self.root)
            sdk = self.root / "sdk"
            tool = sdk / "build-tools" / "36.1.0" / ("aapt2.exe" if os.name == "nt" else "aapt2")
            tool.parent.mkdir(parents=True)
            tool.write_bytes(b"synthetic SDK tool")
            escaped = str(sdk).replace("\\", "\\\\").replace(":", "\\:")
            (self.root / "local.properties").write_text("sdk.dir=" + escaped + "\n")
            self.assertEqual(tool, android.find_aapt2(self.root))

    def test_resolved_shrinker_requires_reviewed_version_identity_and_no_acceptance(self):
        path = self.root / "build/reports/android-shrinker/resolved-shrinker.json"
        for key, value in (("r8_version", "9.0.32"), ("kotlin_version", "2.5.0"),
                           ("resolution_scope", "CLI_ONLY"), ("compiler_artifact_bytes", True),
                           ("compiler_artifact_sha256", "unknown"), ("deployment_accepted", True),
                           ("distribution_eligible", True)):
            changed = {**self.shrinker, key: value}
            path.write_text(json.dumps(changed))
            with self.subTest(key=key), self.assertRaises(android.AndroidVerificationError):
                android.shrinker_record(self.root)
        path.unlink()
        with self.assertRaises(android.AndroidVerificationError):
            android.shrinker_record(self.root)

    def test_mapping_header_rejects_old_missing_ambiguous_or_oversized_identity(self):
        path = self.root / "androidApp/build/outputs/mapping/passengerRelease/mapping.txt"
        original = path.read_text()
        cases = (original.replace(android.R8_VERSION, "9.0.32"),
                 original.replace("# compiler: R8", "# compiler: D8"),
                 original.replace("# compiler_version:", "# ignored_version:"),
                 original.replace("# compiler: R8", "# compiler: R8\n# compiler: R8"),
                 original.replace("# pg_map_id:", "# ignored_map_id:"), "# " + "x" * 4096)
        for text in cases:
            path.write_text(text)
            with self.assertRaises(android.AndroidVerificationError):
                android.mapping_record(self.root, "passengerRelease")

    def test_dex_marker_prevents_new_mapping_from_blessing_old_or_unminified_apk(self):
        path = self.root / "marker-fixture.apk"
        mapping = {"pg_map_id": "b" * 64}
        for key, value in (("version", "9.0.32"), ("pg-map-id", "c" * 64), ("backend", "cf"),
                           ("compilation-mode", "debug"), ("r8-mode", "compat")):
            marker = {**self.marker, key: value}
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("classes.dex", b"dex\n039\x00~~R8" + json.dumps(marker).encode() + b"\x00")
            with self.subTest(key=key), self.assertRaisesRegex(android.AndroidVerificationError, "embedded compiler"):
                android.verify_dex_compiler(path, mapping)
        for payload in (b"dex\n039\x00unminified", b"not-dex", b"dex\n039\x00~~R8{bad-json}\x00",
                        b'dex\n039\x00~~R8{"version":"9.1.56","version":"9.0.32"}\x00'):
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("classes.dex", payload)
            with self.assertRaises(android.AndroidVerificationError):
                android.verify_dex_compiler(path, mapping)

    def test_multiple_dex_markers_must_all_match_and_primary_dex_is_required(self):
        path = self.root / "multidex.apk"
        payload = b"dex\n039\x00~~R8" + json.dumps(self.marker).encode() + b"\x00"
        with zipfile.ZipFile(path, "w") as archive:
            for name in ("classes.dex", "classes2.dex", "classes10.dex"):
                archive.writestr(name, payload)
        android.verify_dex_compiler(path, {"pg_map_id": "b" * 64})
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("classes.dex", payload)
            old = {**self.marker, "version": "9.0.32"}
            archive.writestr("classes10.dex", b"dex\n039\x00~~R8" + json.dumps(old).encode() + b"\x00")
        with self.assertRaisesRegex(android.AndroidVerificationError, "embedded compiler"):
            android.verify_dex_compiler(path, {"pg_map_id": "b" * 64})
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("classes2.dex", payload)
        with self.assertRaisesRegex(android.AndroidVerificationError, "DEX entries"):
            android.verify_dex_compiler(path, {"pg_map_id": "b" * 64})

    def test_source_keeps_documented_override_loaded_compiler_probe_and_full_shrinking(self):
        project = Path(__file__).resolve().parents[2]
        settings = (project / "settings.gradle.kts").read_text()
        root_build = (project / "build.gradle.kts").read_text()
        app_build = (project / "androidApp/build.gradle.kts").read_text()
        self.assertEqual("9.1.56", android.R8_VERSION)
        self.assertEqual(1, settings.count('classpath("com.android.tools:r8:9.1.56")'))
        for required in ("com.android.build.gradle.AppPlugin::class.java.classLoader",
                         'expectedR8Version.set("9.1.56")', "outputs.upToDateWhen { false }",
                         "compiler_artifact_sha256", "AGP_PLUGIN_CLASSLOADER"):
            self.assertIn(required, root_build)
        self.assertIn('dependsOn(rootProject.tasks.named("verifyAndroidShrinker"))', app_build)
        self.assertIn("isMinifyEnabled = true", app_build)
        self.assertIn("isShrinkResources = true", app_build)


if __name__ == "__main__":
    unittest.main()
