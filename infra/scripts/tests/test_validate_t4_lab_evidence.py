from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from validate_t4_lab_evidence import (
    DEFAULT_CATALOG,
    DEFAULT_TEMPLATE,
    REQUIRED_EVIDENCE_KINDS,
    T4LabEvidenceError,
    load_and_validate_catalog,
    validate_evidence,
)


class T4LabEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_and_validate_catalog(DEFAULT_CATALOG)
        cls.template = json.loads(DEFAULT_TEMPLATE.read_text(encoding="utf-8"))

    def _changed_catalog(self, mutate) -> Path:
        root = Path(tempfile.mkdtemp())
        value = copy.deepcopy(self.catalog)
        mutate(value)
        path = root / "catalog.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        self.addCleanup(lambda: root.rmdir())
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        return path

    def _complete_evidence(self) -> dict:
        value = copy.deepcopy(self.template)
        value.update(
            {
                "status": "EXECUTED",
                "candidate_label": "candidate-t4-example",
                "case_results": [
                    {
                        "id": case["id"],
                        "status": "PASS",
                        "evidence_reference": f"evidence/t4/{case['id']}.json",
                        "evidence_sha256": "a" * 64,
                        "executed_at": "2026-09-09T18:00:00Z",
                        "tester_reference": "testers/lab-operator-01",
                        "defect_references": [],
                    }
                    for case in self.catalog["cases"]
                ],
                "supported_evidence_kinds": list(REQUIRED_EVIDENCE_KINDS),
                "missing_evidence_kinds": [],
                "phase_evidence_complete": True,
                "limitations": ["NO_PHASE_OR_DEPLOYMENT_ACCEPTANCE_CLAIM"],
            }
        )
        return value

    def test_committed_catalog_has_balanced_complete_map(self) -> None:
        counts = {
            kind: sum(case["evidence_kind"] == kind for case in self.catalog["cases"])
            for kind in REQUIRED_EVIDENCE_KINDS
        }
        self.assertEqual(56, len(self.catalog["cases"]))
        self.assertEqual({8}, set(counts.values()))

    def test_template_is_not_started_and_cannot_claim_acceptance(self) -> None:
        summary = validate_evidence(self.template, self.catalog, DEFAULT_CATALOG)
        self.assertEqual("NOT_STARTED", summary["status"])
        self.assertFalse(summary["evidence_complete"])
        self.assertFalse(self.template["phase_accepted"])
        self.assertFalse(self.template["deployment_accepted"])

    def test_catalog_cannot_enable_live_or_public_activity(self) -> None:
        path = self._changed_catalog(
            lambda value: value["safety"].update({"live_money_allowed": True})
        )
        with self.assertRaisesRegex(T4LabEvidenceError, "safety flags"):
            load_and_validate_catalog(path)

    def test_catalog_cannot_drop_a_case(self) -> None:
        path = self._changed_catalog(lambda value: value["cases"].pop())
        with self.assertRaisesRegex(T4LabEvidenceError, "exactly 56"):
            load_and_validate_catalog(path)

    def test_complete_case_evidence_does_not_accept_phase(self) -> None:
        evidence = self._complete_evidence()
        summary = validate_evidence(evidence, self.catalog, DEFAULT_CATALOG)
        self.assertEqual(56, summary["passed"])
        self.assertTrue(summary["evidence_complete"])
        self.assertFalse(evidence["phase_accepted"])
        self.assertFalse(evidence["deployment_accepted"])

    def test_failed_case_requires_a_defect_reference(self) -> None:
        evidence = self._complete_evidence()
        evidence["case_results"][0]["status"] = "FAIL"
        evidence["supported_evidence_kinds"] = []
        evidence["missing_evidence_kinds"] = list(REQUIRED_EVIDENCE_KINDS)
        evidence["phase_evidence_complete"] = False
        with self.assertRaisesRegex(T4LabEvidenceError, "blocking defect"):
            validate_evidence(evidence, self.catalog, DEFAULT_CATALOG)

    def test_completed_evidence_kinds_are_credited_without_accepting_t4(self) -> None:
        evidence = self._complete_evidence()
        blocked = next(
            item
            for item in evidence["case_results"]
            if item["id"].startswith("T4-IOS-")
        )
        blocked["status"] = "BLOCKED"
        blocked["defect_references"] = ["defects/IOS-LAB-001"]
        evidence["supported_evidence_kinds"] = [
            kind for kind in REQUIRED_EVIDENCE_KINDS if kind != "IOS_DEVICE_REPORT"
        ]
        evidence["missing_evidence_kinds"] = ["IOS_DEVICE_REPORT"]
        evidence["phase_evidence_complete"] = False
        summary = validate_evidence(evidence, self.catalog, DEFAULT_CATALOG)
        self.assertEqual(55, summary["passed"])
        self.assertFalse(summary["evidence_complete"])
        self.assertFalse(evidence["phase_accepted"])

    def test_raw_device_identifier_key_is_rejected(self) -> None:
        evidence = self._complete_evidence()
        evidence["case_results"][0]["raw_serial"] = "forbidden"
        with self.assertRaisesRegex(T4LabEvidenceError, "forbidden key"):
            validate_evidence(evidence, self.catalog, DEFAULT_CATALOG)


if __name__ == "__main__":
    unittest.main()
