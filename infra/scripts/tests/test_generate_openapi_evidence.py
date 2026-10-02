from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from generate_openapi_evidence import (
    OpenApiEvidenceError, canonical_schema, contract_bundle, load_documents,
    write_bundle, MANIFEST_NAME,
    main,
)


def fixture_documents():
    launch = {"openapi": "3.1.0", "paths": {
        "/api/v1/operations/cities": {"get": {"operationId": "cities"}},
        "/api/v1/rides": {"post": {"operationId": "request_ride",
            "requestBody": {"description": "synthetic payload"}}}},
        "components": {"schemas": {"Money": {"type": "string"}}}}
    compatibility = deepcopy(launch)
    compatibility["paths"]["/api/v1/admin/users"] = {"get": {"operationId": "legacy_users"}}
    return {"launch-api": launch, "local-compatibility-api": compatibility}


class OpenApiEvidenceTests(unittest.TestCase):
    def test_exact_full_contract_bytes_and_hashes_are_retained_without_acceptance(self):
        documents = fixture_documents()
        manifest, files = contract_bundle(documents)
        self.assertFalse(manifest["deployment_accepted"])
        self.assertFalse(manifest["authorization_accepted"])
        for record in manifest["contracts"]:
            encoded = files[record["path"]]
            self.assertEqual(record["bytes"], len(encoded))
            self.assertEqual(record["sha256"], hashlib.sha256(encoded).hexdigest())
            self.assertEqual(documents[record["profile"]], json.loads(encoded))
            self.assertTrue(encoded.endswith(b"\n"))
            self.assertNotIn(b"\r\n", encoded)

    def test_key_order_does_not_change_digest(self):
        document = fixture_documents()["launch-api"]
        self.assertEqual(canonical_schema(document), canonical_schema(dict(reversed(list(document.items())))))

    def test_payload_component_and_list_order_changes_change_digest(self):
        source = fixture_documents()["launch-api"]
        for mutate in (
            lambda value: value["components"]["schemas"]["Money"].update({"type": "number"}),
            lambda value: value["paths"]["/api/v1/rides"]["post"]["requestBody"].update({"required": True}),
            lambda value: value.update({"security": [{"one": []}, {"two": []}]}),
        ):
            with self.subTest(mutation=mutate):
                changed = deepcopy(source)
                mutate(changed)
                self.assertNotEqual(canonical_schema(source), canonical_schema(changed))
        first = deepcopy(source)
        first["security"] = [{"one": []}, {"two": []}]
        second = deepcopy(first)
        second["security"].reverse()
        self.assertNotEqual(canonical_schema(first), canonical_schema(second))

    def test_invalid_or_non_json_schema_is_rejected(self):
        source = fixture_documents()["launch-api"]
        for update in ({"openapi": None}, {"paths": None}, {"extra": float("nan")}, {"extra": object()}):
            with self.subTest(update=update), self.assertRaises(OpenApiEvidenceError):
                canonical_schema({**source, **update})

    def test_duplicate_operation_ids_are_rejected(self):
        source = fixture_documents()["launch-api"]
        source["paths"]["/api/v1/rides"]["post"]["operationId"] = "cities"
        with self.assertRaises(OpenApiEvidenceError):
            canonical_schema(source)

    def test_missing_or_unknown_profile_is_rejected(self):
        for documents in ({}, {"launch-api": fixture_documents()["launch-api"]},
                          {**fixture_documents(), "unreviewed": {}}):
            with self.subTest(profiles=tuple(documents)), self.assertRaises(OpenApiEvidenceError):
                contract_bundle(documents)

    def test_launch_legacy_admin_exposure_is_rejected(self):
        documents = fixture_documents()
        documents["launch-api"] = deepcopy(documents["local-compatibility-api"])
        with self.assertRaisesRegex(OpenApiEvidenceError, "legacy-admin"):
            contract_bundle(documents)

    def test_compatibility_legacy_omission_is_rejected(self):
        documents = fixture_documents()
        documents["local-compatibility-api"] = deepcopy(documents["launch-api"])
        with self.assertRaisesRegex(OpenApiEvidenceError, "legacy-admin"):
            contract_bundle(documents)

    def test_missing_scoped_operations_is_rejected(self):
        documents = fixture_documents()
        del documents["launch-api"]["paths"]["/api/v1/operations/cities"]
        with self.assertRaisesRegex(OpenApiEvidenceError, "scoped operations"):
            contract_bundle(documents)

    def test_compatibility_cannot_omit_a_launch_operation(self):
        documents = fixture_documents()
        del documents["local-compatibility-api"]["paths"]["/api/v1/rides"]
        with self.assertRaisesRegex(OpenApiEvidenceError, "omits"):
            contract_bundle(documents)

    def test_write_retains_bytes_and_refuses_existing_partial_or_complete_evidence(self):
        manifest, files = contract_bundle(fixture_documents())
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            write_bundle(target, manifest, files)
            self.assertEqual(manifest, json.loads((target / MANIFEST_NAME).read_bytes()))
            for name, encoded in files.items():
                self.assertEqual(encoded, (target / name).read_bytes())
            with self.assertRaisesRegex(OpenApiEvidenceError, "overwrite"):
                write_bundle(target, manifest, files)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            first = next(iter(files))
            (target / first).write_bytes(b"retained")
            with self.assertRaisesRegex(OpenApiEvidenceError, "overwrite"):
                write_bundle(target, manifest, files)
            self.assertEqual(b"retained", (target / first).read_bytes())
            self.assertFalse((target / MANIFEST_NAME).exists())

    def test_worker_never_inherits_operational_environment(self):
        documents = fixture_documents()
        completed = subprocess.CompletedProcess([], 0, stdout=json.dumps(documents).encode(), stderr=b"")
        with patch.dict(os.environ, {"TAXIMOBILE_DATABASE_URL": "do-not-use", "TAXIMOBILE_LOG_FILE": "do-not-use",
                                     "TAXIMOBILE_JWT_SECRET": "do-not-use", "PYTHONPATH": "do-not-use"}), \
                patch("generate_openapi_evidence.subprocess.run", return_value=completed) as run:
            self.assertEqual(documents, load_documents())
        environment = run.call_args.kwargs["env"]
        self.assertEqual({"TAXIMOBILE_ENV", "TAXIMOBILE_PROCESS_ROLE"},
                         {key for key in environment if key.upper().startswith("TAXIMOBILE_")})
        self.assertNotIn("PYTHONPATH", environment)
        self.assertEqual("api", environment["TAXIMOBILE_PROCESS_ROLE"])
        self.assertEqual(45, run.call_args.kwargs["timeout"])

    def test_failed_or_timed_out_worker_does_not_leak_its_output(self):
        for response in (subprocess.CompletedProcess([], 1, stdout=b"private detail", stderr=b"private detail"),
                         subprocess.TimeoutExpired("worker", 45),
                         subprocess.CompletedProcess([], 0, stdout=b"invalid json", stderr=b"private detail")):
            options = {"side_effect": response} if isinstance(response, Exception) else {"return_value": response}
            with self.subTest(response=type(response).__name__), \
                    patch("generate_openapi_evidence.subprocess.run", **options), \
                    self.assertRaisesRegex(OpenApiEvidenceError, "Isolated schema generation failed") as failure:
                load_documents()
            self.assertNotIn("private detail", str(failure.exception))

    def test_worker_json_must_contain_both_object_profiles(self):
        for value in ([], {}, {"launch-api": {}, "local-compatibility-api": "wrong"}):
            result = subprocess.CompletedProcess([], 0, stdout=json.dumps(value).encode(), stderr=b"")
            with self.subTest(value=value), patch("generate_openapi_evidence.subprocess.run", return_value=result), \
                    self.assertRaises(OpenApiEvidenceError):
                load_documents()

    def test_cli_retention_failure_is_actionable_and_does_not_claim_success(self):
        manifest, files = contract_bundle(fixture_documents())
        with tempfile.TemporaryDirectory() as directory:
            write_bundle(Path(directory), manifest, files)
            with patch("generate_openapi_evidence.load_documents", return_value=fixture_documents()), \
                    patch("sys.stderr", new_callable=io.StringIO) as stderr, \
                    patch("sys.stdout", new_callable=io.StringIO) as stdout:
                self.assertEqual(1, main(["--output-dir", directory]))
            self.assertIn("fresh output directory", stderr.getvalue())
            self.assertEqual("", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
