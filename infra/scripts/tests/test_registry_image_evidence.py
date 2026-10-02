from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import registry_image_evidence as registry
from generate_release_evidence import sha256_file


SHA = "a" * 40
IMAGE_ID = "sha256:" + "b" * 64
REFERENCE = "ghcr.io/q-sio2/taxi-api@sha256:" + "c" * 64
ENV = {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "push", "GITHUB_REF": "refs/heads/main",
       "GITHUB_SHA": SHA, "GITHUB_RUN_ID": "42", "GITHUB_RUN_ATTEMPT": "1",
       "GITHUB_REPOSITORY": "Q-SiO2/taxi"}


class RegistryImageEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.bundle = Path(self.temp.name) / "bundle"
        self.bundle.mkdir()
        (self.bundle / "image.tar").write_bytes(b"synthetic archive, never load into Docker")
        registry.write_json(self.bundle / "image.json", {"schema_version": 1, "image_id": IMAGE_ID,
                                                       "os": "linux", "architecture": "amd64"})
        registry.write_json(self.bundle / "image.spdx.json", {"spdxVersion": "SPDX-2.3"})
        self.evidence = {"schema_version": 1, "evidence_level": "SOURCE_CANDIDATE",
            "deployment_accepted": False,
            "source": {"commit": SHA, "tree": "d" * 40, "clean": True,
                       "tracked_change_count": 0, "untracked_file_count": 0},
            "ci": {"provider": "github-actions", "reported_sha": SHA, "ref": "refs/heads/main",
                   "run_id": "42", "run_attempt": "1"}, "artifacts": []}
        self.rebind()

    def rebind(self):
        self.evidence["artifacts"] = [{"path": f"/tmp/fixed/{name}",
            "bytes": (self.bundle / name).stat().st_size,
            "sha256": sha256_file(self.bundle / name)} for name in
            sorted(registry.BUNDLE_FILES - {"source-evidence.json"})]
        self.save()

    def save(self):
        (self.bundle / "source-evidence.json").write_text(json.dumps(self.evidence), encoding="utf-8")

    def test_complete_packet_checks_without_invoking_docker(self):
        with patch.object(registry, "docker") as docker:
            self.assertEqual(IMAGE_ID, registry.verify(self.bundle, SHA, "42", "1")["image_id"])
            docker.assert_not_called()

    def test_identity_drift_and_acceptance_claims_rejected(self):
        original = copy.deepcopy(self.evidence)
        mutations = [("source", "commit", "e" * 40), ("source", "clean", False),
                     ("source", "tracked_change_count", 1), ("source", "tree", None),
                     ("ci", "reported_sha", "e" * 40), ("ci", "run_id", "43"),
                     ("ci", "run_attempt", "2"), ("ci", "ref", "refs/pull/43/merge")]
        for section, key, value in mutations:
            with self.subTest(section=section, key=key):
                self.evidence = copy.deepcopy(original)
                self.evidence[section][key] = value
                self.save()
                with self.assertRaises(registry.RegistryEvidenceError):
                    registry.verify(self.bundle, SHA, "42", "1")
        for key, value in (("deployment_accepted", True), ("evidence_level", "WORKSPACE_SNAPSHOT")):
            self.evidence = copy.deepcopy(original)
            self.evidence[key] = value
            self.save()
            with self.assertRaises(registry.RegistryEvidenceError):
                registry.verify(self.bundle, SHA, "42", "1")

    def test_every_payload_requires_exact_hash_and_size(self):
        for name in registry.BUNDLE_FILES - {"source-evidence.json"}:
            with self.subTest(name=name):
                path = self.bundle / name
                original = path.read_bytes()
                path.write_bytes(original + b"tamper")
                with self.assertRaisesRegex(registry.RegistryEvidenceError, "hash/size"):
                    registry.verify(self.bundle, SHA, "42", "1")
                path.write_bytes(original)

    def test_duplicate_or_foreign_artifact_binding_rejected(self):
        original = copy.deepcopy(self.evidence)
        for path in ("../../unknown.tar", self.evidence["artifacts"][1]["path"]):
            self.evidence = copy.deepcopy(original)
            self.evidence["artifacts"][0]["path"] = path
            self.save()
            with self.assertRaises(registry.RegistryEvidenceError):
                registry.verify(self.bundle, SHA, "42", "1")

    def test_extra_or_missing_bundle_files_rejected(self):
        extra = self.bundle / "unexpected"
        extra.write_bytes(b"extra")
        with self.assertRaises(registry.RegistryEvidenceError):
            registry.verify(self.bundle, SHA, "42", "1")
        extra.unlink()
        (self.bundle / "image.tar").unlink()
        with self.assertRaises(registry.RegistryEvidenceError):
            registry.verify(self.bundle, SHA, "42", "1")

    def test_duplicate_json_keys_rejected(self):
        (self.bundle / "image.json").write_text('{"image_id":"one","image_id":"two"}')
        with self.assertRaisesRegex(registry.RegistryEvidenceError, "Duplicate"):
            registry.read_json(self.bundle / "image.json")

    def test_wrong_loaded_image_rejected(self):
        with patch.object(registry, "inspect", return_value={"Id": "sha256:" + "f" * 64}):
            with self.assertRaisesRegex(registry.RegistryEvidenceError, "Loaded"):
                registry.verify(self.bundle, SHA, "42", "1", loaded=True)

    def test_operations_require_main_push_not_pr_or_feature(self):
        with patch.dict(os.environ, ENV, clear=True):
            self.assertEqual((SHA, "42", "1"), registry.context())
            for key, value in (("GITHUB_EVENT_NAME", "pull_request"),
                               ("GITHUB_REF", "refs/heads/codex/candidate"),
                               ("GITHUB_SHA", "short"), ("GITHUB_RUN_ATTEMPT", "0")):
                with patch.dict(os.environ, {key: value}):
                    with self.assertRaises(registry.RegistryEvidenceError):
                        registry.context()

    def test_registry_record_verifies_remote_identity_and_stays_unaccepted(self):
        output = Path(self.temp.name) / "record.json"
        with patch.dict(os.environ, ENV, clear=True), patch.object(registry, "docker") as docker:
            with patch.object(registry, "inspect", return_value={"Id": IMAGE_ID, "RepoDigests": [REFERENCE]}):
                registry.record(self.bundle, "q-sio2/taxi", output)
            docker.assert_called_once_with("image", "pull", REFERENCE)
        result = registry.read_json(output)
        self.assertEqual(REFERENCE, result["registry_reference"])
        self.assertFalse(result["deployment_accepted"])
        self.assertFalse(result["phase_accepted"])
        self.assertEqual(sha256_file(self.bundle / "image.spdx.json"), result["sbom_sha256"])

    def test_missing_foreign_ambiguous_or_wrong_registry_digest_rejected(self):
        output = Path(self.temp.name) / "record.json"
        with patch.dict(os.environ, ENV, clear=True), patch.object(registry, "docker") as docker:
            for refs in ([], [REFERENCE, REFERENCE], [REFERENCE.replace("taxi-api", "foreign")], ["invalid"]):
                with patch.object(registry, "inspect", return_value={"Id": IMAGE_ID, "RepoDigests": refs}):
                    with self.assertRaises(registry.RegistryEvidenceError):
                        registry.record(self.bundle, "q-sio2/taxi", output)
            docker.assert_not_called()
            self.assertFalse(output.exists())

    def test_registry_pull_identity_mismatch_rejected(self):
        output = Path(self.temp.name) / "record.json"
        values = [{"Id": IMAGE_ID}, {"Id": IMAGE_ID, "RepoDigests": [REFERENCE]},
                  {"Id": "sha256:" + "f" * 64}]
        with patch.dict(os.environ, ENV, clear=True), patch.object(registry, "docker"), \
                patch.object(registry, "inspect", side_effect=values):
            with self.assertRaisesRegex(registry.RegistryEvidenceError, "Registry pull"):
                registry.record(self.bundle, "q-sio2/taxi", output)
        self.assertFalse(output.exists())

    def test_docker_failure_does_not_leak_diagnostics(self):
        result = type("Result", (), {"returncode": 1, "stderr": "private-token", "stdout": "private-token"})()
        with patch.object(registry.subprocess, "run", return_value=result):
            with self.assertRaises(registry.RegistryEvidenceError) as error:
                registry.docker("image", "inspect", "synthetic")
        self.assertNotIn("private-token", str(error.exception))

    def test_prepare_hands_off_existing_image_and_refuses_overwrite(self):
        target = Path(self.temp.name) / "prepared"
        archive = (self.bundle / "image.tar").read_bytes()

        def fake_docker(*args):
            self.assertEqual(("image", "save", "--output", str(target / "image.tar"), registry.IMAGE), args)
            (target / "image.tar").write_bytes(archive)
            return ""

        with patch.dict(os.environ, ENV, clear=True), \
                patch.object(registry, "inspect", return_value={"Id": IMAGE_ID}), \
                patch.object(registry, "generate_evidence", return_value=self.evidence) as generated, \
                patch.object(registry, "docker", side_effect=fake_docker) as docker:
            registry.prepare(target, self.bundle / "image.spdx.json")
            self.assertEqual(IMAGE_ID, registry.verify(target, SHA, "42", "1")["image_id"])
            self.assertEqual(3, len(generated.call_args.kwargs["artifacts"]))
            self.assertNotIn("allow_dirty", generated.call_args.kwargs)
            with self.assertRaises(FileExistsError):
                registry.prepare(target, self.bundle / "image.spdx.json")
            self.assertEqual(1, docker.call_count)

    def test_invalid_descriptor_platform_and_sbom_rejected(self):
        original = (self.bundle / "image.json").read_bytes()
        for key, value in (("image_id", "bad"), ("os", "windows"), ("architecture", "arm64")):
            document = json.loads(original)
            document[key] = value
            (self.bundle / "image.json").write_text(json.dumps(document))
            self.rebind()
            with self.assertRaises(registry.RegistryEvidenceError):
                registry.verify(self.bundle, SHA, "42", "1")
        (self.bundle / "image.json").write_bytes(original)
        (self.bundle / "image.spdx.json").write_text('{"spdxVersion":"unknown"}')
        self.rebind()
        with self.assertRaises(registry.RegistryEvidenceError):
            registry.verify(self.bundle, SHA, "42", "1")

    def test_foreign_registry_namespace_rejected_without_docker(self):
        with patch.dict(os.environ, ENV, clear=True), patch.object(registry, "docker") as docker:
            with self.assertRaises(registry.RegistryEvidenceError):
                registry.record(self.bundle, "other/repo", Path(self.temp.name) / "record.json")
            docker.assert_not_called()


if __name__ == "__main__":
    unittest.main()
