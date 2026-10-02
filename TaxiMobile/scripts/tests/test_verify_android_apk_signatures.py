from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import verify_android_apk_signatures as signing
import generate_android_verification_manifest as android


class AndroidSignatureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.apk = self.root / "role & spaces.apk"
        self.apk.write_bytes(b"synthetic apk")
        self.jar = self.root / "apksigner.jar"
        self.jar.write_bytes(b"synthetic SDK")
        self.hash = hashlib.sha256(self.apk.read_bytes()).hexdigest()
        self.fingerprint = "a" * 64
        self.output = ("Verifies\nVerified using v2 scheme (APK Signature Scheme v2): true\n"
                       "Number of signers: 1\nSigner #1 certificate DN: private-subject\n"
                       f"Signer #1 certificate SHA-256 digest: {self.fingerprint}\n")

    def test_fingerprints_normalize_only_complete_hex_or_colon_hex(self):
        for value in ("A" * 64, ":".join(["AA"] * 32), self.fingerprint):
            self.assertEqual(self.fingerprint, signing.certificate_sha256(value))
        for value in ("", "a" * 63, "g" * 64, " " + self.fingerprint, "AA:AA", None):
            with self.assertRaises(signing.AndroidSignatureError):
                signing.certificate_sha256(value)

    def test_parser_retains_digest_and_false_approval_not_subjects(self):
        result = signing.parse_verified_signature(self.output, self.fingerprint)
        self.assertEqual(self.fingerprint, result["certificate_sha256"])
        self.assertTrue(result["signature_scheme_v2_verified"])
        self.assertFalse(result["signer_approval_accepted"])
        self.assertEqual("APK_MANIFEST_DEFAULT", result["platform_range"])
        self.assertNotIn("private", json.dumps(result))

    def test_failed_ambiguous_wrong_signer_or_weak_scheme_reports_rejected(self):
        cases = (self.output.replace("Verifies\n", "DOES NOT VERIFY\n"),
                 self.output + "Verifies\n", self.output.replace("true", "false"),
                 self.output.replace("Number of signers: 1", "Number of signers: 2"),
                 self.output.replace(self.fingerprint, "b" * 64),
                 self.output.replace("Signer #1 certificate SHA-256", "Signer #2 certificate SHA-256"),
                 self.output + f"Signer #2 certificate SHA-256 digest: {self.fingerprint}\n",
                 self.output + f"Signer #1 certificate SHA-256 digest: {self.fingerprint}\n",
                 self.output.replace("Number of signers: 1", ""),
                 self.output + "x" * (64 * 1024))
        for text in cases:
            with self.subTest(report=text[:30]), self.assertRaises(signing.AndroidSignatureError) as error:
                signing.parse_verified_signature(text, self.fingerprint)
            self.assertNotIn("private-subject", str(error.exception))

    def test_real_command_shape_preserves_platform_range_and_shell_free_paths(self):
        result = subprocess.CompletedProcess([], 0, self.output, "")
        with patch.object(signing, "_java", return_value="java"), patch.object(signing.subprocess, "run", return_value=result) as run:
            record = signing.verify_apk_signature(self.apk, self.jar, self.fingerprint, self.hash)
        self.assertEqual(["java", "-jar", str(self.jar), "verify", "--verbose", "--print-certs",
                          "-Werr", "--in", str(self.apk)], run.call_args.args[0])
        self.assertNotIn("shell", run.call_args.kwargs)
        self.assertEqual(45, run.call_args.kwargs["timeout"])
        self.assertEqual(hashlib.sha256(self.jar.read_bytes()).hexdigest(), record["verifier_artifact_sha256"])
        self.assertEqual(self.jar.stat().st_size, record["verifier_artifact_bytes"])

    def test_tool_errors_timeouts_bad_encoding_or_warning_status_are_redacted(self):
        cases = (OSError("private-path"), subprocess.TimeoutExpired("private-tool", 45),
                 UnicodeError("private-output"), subprocess.CompletedProcess([], 1, "private-output", "private-token"))
        for value in cases:
            kwargs = {"side_effect": value} if isinstance(value, Exception) else {"return_value": value}
            with patch.object(signing, "_java", return_value="java"), patch.object(signing.subprocess, "run", **kwargs):
                with self.assertRaises(signing.AndroidSignatureError) as error:
                    signing.verify_apk_signature(self.apk, self.jar, self.fingerprint, self.hash)
                self.assertNotIn("private", str(error.exception))

    def test_changed_apk_before_inspection_never_runs_verifier(self):
        self.apk.write_bytes(b"changed")
        with patch.object(signing.subprocess, "run") as run, self.assertRaises(signing.AndroidSignatureError):
            signing.verify_apk_signature(self.apk, self.jar, self.fingerprint, self.hash)
        run.assert_not_called()

    def test_changed_apk_or_verifier_during_inspection_rejected(self):
        for target in (self.apk, self.jar):
            original = target.read_bytes()
            def mutate(*args, **kwargs):
                target.write_bytes(b"changed during inspection")
                return subprocess.CompletedProcess([], 0, self.output, "")
            with patch.object(signing, "_java", return_value="java"), patch.object(signing.subprocess, "run", side_effect=mutate):
                with self.assertRaises(signing.AndroidSignatureError):
                    signing.verify_apk_signature(self.apk, self.jar, self.fingerprint, self.hash)
            target.write_bytes(original)

    def test_missing_empty_oversized_verifier_or_bad_hash_rejected(self):
        for jar, digest in ((self.root / "absent.jar", self.hash), (self.jar, "invalid")):
            with self.assertRaises(signing.AndroidSignatureError):
                signing.verify_apk_signature(self.apk, jar, self.fingerprint, digest)
        self.jar.write_bytes(b"")
        with self.assertRaises(signing.AndroidSignatureError):
            signing.verify_apk_signature(self.apk, self.jar, self.fingerprint, self.hash)
        with self.jar.open("wb") as output:
            output.truncate(16 * 1024 * 1024 + 1)
        with self.assertRaises(signing.AndroidSignatureError):
            signing.verify_apk_signature(self.apk, self.jar, self.fingerprint, self.hash)

    def test_java_configuration_is_explicit_or_discovered_without_shell(self):
        import os
        with patch.dict(os.environ, {"JAVA_HOME": str(self.root)}, clear=True):
            with self.assertRaises(signing.AndroidSignatureError):
                signing._java()
            java = self.root / "bin" / ("java.exe" if os.name == "nt" else "java")
            java.parent.mkdir()
            java.write_bytes(b"fixture")
            self.assertEqual(str(java), signing._java())
        with patch.dict(os.environ, {}, clear=True), patch.object(signing.shutil, "which", return_value=None):
            with self.assertRaises(signing.AndroidSignatureError):
                signing._java()

    def test_cli_partial_identity_or_tool_only_fails_before_apk_inspection(self):
        for flags in (("--expected-passenger-certificate-sha256", self.fingerprint),
                      ("--apksigner-jar", str(self.jar))):
            args = ["script", "--project-dir", str(self.root), *flags]
            with patch.object(sys, "argv", args), patch.object(android, "generate_manifest") as generate:
                self.assertEqual(1, android.main())
                generate.assert_not_called()

    def test_cli_checks_both_roles_preserves_no_acceptance_and_rejects_driver_failure(self):
        output = self.root / "report.json"
        manifest = {"artifacts": [{"role": role, "path": role + ".apk", "sha256": self.hash}
                                 for role in ("driver", "passenger")],
                    "distribution_eligible": False, "deployment_accepted": False,
                    "limitations": ["SIGNING_NOT_ACCEPTED", "PHYSICAL_DEVICE_NOT_ACCEPTED"]}
        args = ["script", "--project-dir", str(self.root), "--output", str(output), "--aapt2", "aapt2",
                "--expected-passenger-certificate-sha256", self.fingerprint,
                "--expected-driver-certificate-sha256", "b" * 64, "--apksigner-jar", str(self.jar)]
        with patch.object(sys, "argv", args), patch.object(android, "generate_manifest", return_value=manifest), patch.object(android, "verify_apk_signature", return_value={"signer_approval_accepted": False}) as verify:
            self.assertEqual(0, android.main())
        self.assertEqual(["b" * 64, self.fingerprint], [call.args[2] for call in verify.call_args_list])
        record = json.loads(output.read_text())
        self.assertFalse(record["distribution_eligible"])
        self.assertFalse(record["deployment_accepted"])
        self.assertFalse(record["signer_approval_accepted"])
        self.assertIn("SIGNER_APPROVAL_NOT_ACCEPTED", record["limitations"])
        self.assertIn("PHYSICAL_DEVICE_NOT_ACCEPTED", record["limitations"])
        output.unlink()
        manifest["artifacts"].reverse()  # Driver is second: never write a partial passenger-only report.
        with patch.object(sys, "argv", args), patch.object(android, "generate_manifest", return_value=manifest), patch.object(android, "verify_apk_signature", side_effect=[{}, signing.AndroidSignatureError("wrong signer")]):
            self.assertEqual(1, android.main())
        self.assertFalse(output.exists())

    def test_wrapper_forwards_public_identity_inputs_and_jar(self):
        text = (Path(__file__).resolve().parents[1] / "verify-android-release-artifacts.ps1").read_text()
        for flag in ("--expected-passenger-certificate-sha256", "--expected-driver-certificate-sha256", "--apksigner-jar"):
            self.assertIn(flag, text)
        self.assertIn("$PSBoundParameters.ContainsKey($_)", text)
