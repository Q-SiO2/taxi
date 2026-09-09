from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from validate_test_phase_evidence import (
    DEFAULT_CATALOG,
    DEFAULT_TEMPLATE,
    PHASE_IDS,
    load_json,
    require_through,
    validate_catalog,
    validate_evidence_index,
)


DIGEST = "a" * 64
COLLECTED_AT = "2026-09-08T10:00:00Z"
RETAIN_UNTIL = "2027-09-08T10:00:00Z"


class TestPhaseEvidenceValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = load_json(DEFAULT_CATALOG)
        self.evidence = load_json(DEFAULT_TEMPLATE)

    def evidence_item(self, phase_id: str, kind: str, *, real: bool = False) -> dict[str, str]:
        return {
            "kind": kind,
            "reference": f"artifact:{phase_id}/{kind}",
            "sha256": DIGEST,
            "collected_at": COLLECTED_AT,
            "retention_until": RETAIN_UNTIL,
            "data_classification": "REAL_USER_AGGREGATE" if real else "SYNTHETIC",
        }

    def accepted_record(self, index: int) -> dict[str, object]:
        phase = self.catalog["phases"][index]
        phase_id = phase["id"]
        if index < 4:
            city_ids: list[str] = []
        elif index == 10:
            city_ids = ["city-one", "city-two"]
        else:
            city_ids = ["city-one"]
        return {
            "id": phase_id,
            "status": "ACCEPTED",
            "started_at": "2026-09-08T08:00:00Z",
            "completed_at": "2026-09-08T12:00:00Z",
            "scope": {
                "configuration_bundle_sha256": DIGEST,
                "city_ids": city_ids,
                "environment_class": phase["environment_classes"][0],
                "participant_mode": phase["participant_modes"][0],
                "public_users": index >= 9,
                "live_money": index >= 8,
                "intentional_failure_injection": index == 5,
            },
            "evidence": [
                self.evidence_item(phase_id, kind, real=index >= 8)
                for kind in phase["required_evidence"]
            ],
            "signoffs": [
                {
                    "authority": authority,
                    "decision": "ACCEPTED",
                    "approver_reference": f"approval:{phase_id}/{authority}",
                    "signed_at": "2026-09-08T12:30:00Z",
                }
                for authority in phase["required_authorities"]
            ],
            "defects": [],
            "gap_closures": [
                {
                    "gap_id": gap_id,
                    "reference": f"closure:{phase_id}/{gap_id}",
                    "sha256": DIGEST,
                    "authority_reference": f"approval:{gap_id}",
                    "accepted_at": "2026-09-08T11:00:00Z",
                }
                for gap_id in phase["required_gap_closures"]
            ],
        }

    def accepted_through(self, target: int) -> dict[str, object]:
        evidence = deepcopy(self.evidence)
        evidence["candidate"] = {
            "commit": "1" * 40,
            "clean": True,
            "migration_head": "20260908_0052",
            "release_label": "candidate:2026-09-08.1",
            "release_evidence_sha256": DIGEST,
            "artifact_manifest_sha256": DIGEST,
            "contract_inventory_sha256": DIGEST,
        }
        for index in range(target + 1):
            evidence["phase_records"][index] = self.accepted_record(index)
        return evidence

    def test_current_catalog_and_empty_template_are_valid(self) -> None:
        self.assertEqual([], validate_catalog(self.catalog))
        self.assertEqual([], validate_evidence_index(self.catalog, self.evidence))

    def test_complete_ordered_evidence_through_real_user_pilot_is_valid(self) -> None:
        evidence = self.accepted_through(8)
        self.assertEqual([], validate_evidence_index(self.catalog, evidence))
        self.assertEqual([], require_through(evidence, "T8"))

    def test_phase_cannot_start_before_predecessor_acceptance(self) -> None:
        evidence = self.accepted_through(0)
        evidence["phase_records"][1] = {
            "id": "T1",
            "status": "IN_PROGRESS",
            "started_at": COLLECTED_AT,
            "evidence": [],
            "defects": [],
        }
        evidence["phase_records"][0]["status"] = "INVALIDATED"
        evidence["phase_records"][0].pop("completed_at")
        evidence["phase_records"][0].pop("scope")
        evidence["phase_records"][0].pop("signoffs")
        evidence["phase_records"][0].pop("gap_closures")
        evidence["phase_records"][0]["decision_reference"] = "decision:T0/invalidated"

        issues = validate_evidence_index(self.catalog, evidence)
        self.assertTrue(any("cannot start before T0 is ACCEPTED" in issue for issue in issues))

    def test_accepted_phase_requires_exact_evidence_and_authorities(self) -> None:
        evidence = self.accepted_through(1)
        evidence["phase_records"][1]["evidence"].pop()
        evidence["phase_records"][1]["signoffs"] = []

        issues = validate_evidence_index(self.catalog, evidence)
        self.assertTrue(any("evidence kinds are" in issue for issue in issues))
        self.assertTrue(any("authorities are" in issue for issue in issues))

    def test_t8_requires_every_p0_gap_closure(self) -> None:
        evidence = self.accepted_through(8)
        evidence["phase_records"][8]["gap_closures"].pop()

        issues = validate_evidence_index(self.catalog, evidence)
        self.assertTrue(any("GAP-019" in issue and "expected" in issue for issue in issues))

    def test_real_user_evidence_is_rejected_before_t8(self) -> None:
        evidence = self.accepted_through(3)
        evidence["phase_records"][3]["evidence"][0]["data_classification"] = (
            "REAL_USER_AGGREGATE"
        )

        issues = validate_evidence_index(self.catalog, evidence)
        self.assertTrue(any("real-user evidence before T8" in issue for issue in issues))

    def test_public_users_live_money_and_failure_injection_cannot_cross_boundaries(self) -> None:
        evidence = self.accepted_through(7)
        scope = evidence["phase_records"][7]["scope"]
        scope["public_users"] = True
        scope["live_money"] = True
        scope["intentional_failure_injection"] = True

        issues = validate_evidence_index(self.catalog, evidence)
        self.assertTrue(any("public_users exceeds" in issue for issue in issues))
        self.assertTrue(any("live_money exceeds" in issue for issue in issues))
        self.assertTrue(any("failure_injection is unsafe" in issue for issue in issues))

    def test_sensitive_material_keys_are_refused(self) -> None:
        evidence = self.accepted_through(0)
        evidence["access_token"] = "must-never-be-stored"

        issues = validate_evidence_index(self.catalog, evidence)
        self.assertTrue(any("access_token is forbidden" in issue for issue in issues))

    def test_open_defect_prevents_phase_acceptance(self) -> None:
        evidence = self.accepted_through(0)
        evidence["phase_records"][0]["defects"] = [
            {"id": "DEFECT-1", "severity": "S1", "status": "OPEN"}
        ]

        issues = validate_evidence_index(self.catalog, evidence)
        self.assertTrue(any("cannot remain OPEN" in issue for issue in issues))

    def test_promotion_requirement_reports_every_unaccepted_phase(self) -> None:
        issues = require_through(self.evidence, "T3")
        self.assertEqual(4, len(issues))
        self.assertTrue(all(phase in " ".join(issues) for phase in PHASE_IDS[:4]))

    def test_catalog_cannot_move_public_users_or_live_money_earlier(self) -> None:
        catalog = deepcopy(self.catalog)
        catalog["phases"][3]["public_users_allowed"] = True
        catalog["phases"][5]["live_money_allowed"] = True

        issues = validate_catalog(catalog)
        self.assertTrue(any("public users before T9" in issue for issue in issues))
        self.assertTrue(any("live money before T8" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
