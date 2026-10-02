from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest


SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from validate_pilot_city_launch_approval import (
    DEFAULT_APPROVAL,
    PilotCityLaunchApprovalError,
    validate_approval,
)


class PilotCityLaunchApprovalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.template = json.loads(DEFAULT_APPROVAL.read_text(encoding="utf-8"))

    def _accepted_approval(self) -> dict:
        value = copy.deepcopy(self.template)
        configuration_id = "10000000-0000-4000-8000-000000000111"
        value.update(
            {
                "status": "ACCEPTED",
                "candidate_label": "pilot-city-candidate-2026-09-29",
                "source_commit": "e" * 40,
                "environment_inventory_reference": "evidence/environment/GAP-002",
                "database_evidence_reference": "evidence/database/GAP-003",
                "gap_004_accepted": True,
                "limitations": ["NO_PHASE_OR_DEPLOYMENT_ACCEPTANCE"],
            }
        )
        value["submission"] = {
            "submitted_by_account_reference": "operations/accounts/configuration-maker",
            "submitted_at": "2026-09-29T09:00:00Z",
            "change_reference": "changes/pilot-city-004",
        }
        value["scope"] = {
            "market_code": "MA",
            "country_code": "MA",
            "city_id": "10000000-0000-4000-8000-000000000112",
            "city_code": "example-pilot-city",
            "city_display_name": "Example Pilot City",
            "city_timezone": "Africa/Casablanca",
            "city_lifecycle_status": "CONFIGURING",
            "operator_id": "10000000-0000-4000-8000-000000000113",
            "operator_legal_name": "Example Licensed Taxi Operator",
            "operator_type": "LOCAL_ENTITY",
            "operator_authority_reference": "evidence/legal/operator-authority",
            "operator_authority_valid_until": "2026-12-31T23:59:59Z",
            "active_configuration_id": configuration_id,
            "configuration_version": "pilot-v1",
            "configuration_status": "ACTIVE",
            "service_types": ["ON_DEMAND"],
            "service_area_approval_reference": "evidence/service-area/pilot-v1",
            "operating_hours_reference": "evidence/operations/pilot-hours",
            "tariff_and_fee_reference": "evidence/pricing/pilot-v1",
            "fixed_route_scope_reference": None,
            "scheduling_scope_reference": None,
            "payment_scope_reference": "evidence/payments/cash-only-v1",
            "payment_methods": ["CASH"],
        }
        value["public_terms"] = {
            "passenger_terms_reference": "public/terms/passenger-v1",
            "passenger_terms_version": "1.0",
            "driver_terms_reference": "public/terms/driver-v1",
            "driver_terms_version": "1.0",
            "privacy_notice_reference": "public/privacy/notice-v1",
            "privacy_notice_version": "1.0",
            "fare_disclosure_reference": "public/fares/pilot-v1",
            "complaint_and_safety_publication_reference": "public/support/pilot-v1",
            "localization_review_reference": "evidence/localization/ar-fr-en-v1",
            "effective_at": "2026-10-01T00:00:00Z",
            "languages": ["ar", "fr", "en"],
        }
        for row in value["accountability"]:
            row.update(
                {
                    "assignment_reference": f"evidence/owners/{row['function']}",
                    "duty_roster_reference": f"evidence/rosters/{row['function']}",
                    "effective_from": "2026-09-29T08:00:00Z",
                    "review_due_at": "2026-11-15T00:00:00Z",
                }
            )
        value["pilot_limits"] = {
            "cohort_plan_reference": "evidence/pilot/cohort-v1",
            "pilot_start_at": "2026-10-15T08:00:00Z",
            "pilot_end_at": "2026-10-31T20:00:00Z",
            "maximum_passengers": 100,
            "maximum_drivers": 20,
            "maximum_concurrent_rides": 10,
            "maximum_completed_rides": 500,
            "go_no_go_thresholds_reference": "evidence/pilot/thresholds-v1",
            "pause_runbook_reference": "runbooks/city-pause-v1",
            "rollback_reference": "runbooks/pilot-rollback-v1",
            "participant_communications_reference": "evidence/pilot/communications-v1",
        }
        for index, row in enumerate(value["readiness_decisions"]):
            row.update(
                {
                    "decision": "PASSED",
                    "configuration_id": configuration_id,
                    "reviewer_account_reference": f"operations/accounts/readiness-reviewer-{index % 2 + 1}",
                    "evidence_reference": f"evidence/readiness/{row['gate_code']}",
                    "decided_at": "2026-10-10T10:00:00Z",
                    "review_due_at": "2026-11-15T00:00:00Z",
                }
            )
        for index, row in enumerate(value["approvals"]):
            row.update(
                {
                    "decision": "APPROVED",
                    "reviewer_account_reference": f"operations/accounts/approver-{index + 1}",
                    "evidence_reference": f"evidence/approvals/{row['function']}",
                    "decided_at": "2026-10-11T10:00:00Z",
                    "review_due_at": "2026-11-15T00:00:00Z",
                }
            )
        return value

    def test_committed_template_is_valid_and_unaccepted(self) -> None:
        summary = validate_approval(self.template)
        self.assertEqual("NOT_STARTED", summary["status"])
        self.assertFalse(summary["gap_004_accepted"])
        self.assertFalse(self.template["phase_accepted"])
        self.assertFalse(self.template["deployment_accepted"])

    def test_require_accepted_rejects_template(self) -> None:
        with self.assertRaisesRegex(PilotCityLaunchApprovalError, "externally accepted"):
            validate_approval(self.template, require_accepted=True)

    def test_complete_record_accepts_only_gap_004(self) -> None:
        approval = self._accepted_approval()
        summary = validate_approval(approval, require_accepted=True)
        self.assertTrue(summary["gap_004_accepted"])
        self.assertFalse(approval["phase_accepted"])
        self.assertFalse(approval["deployment_accepted"])

    def test_not_started_record_cannot_hide_scope_claims(self) -> None:
        approval = copy.deepcopy(self.template)
        approval["scope"]["city_code"] = "hidden-city"
        with self.assertRaisesRegex(PilotCityLaunchApprovalError, "scope claims"):
            validate_approval(approval)

    def test_configuration_submitter_cannot_review_readiness(self) -> None:
        approval = self._accepted_approval()
        approval["readiness_decisions"][0]["reviewer_account_reference"] = approval[
            "submission"
        ]["submitted_by_account_reference"]
        with self.assertRaisesRegex(PilotCityLaunchApprovalError, "must differ"):
            validate_approval(approval)

    def test_configuration_submitter_cannot_approve_pilot(self) -> None:
        approval = self._accepted_approval()
        approval["approvals"][-1]["reviewer_account_reference"] = approval["submission"][
            "submitted_by_account_reference"
        ]
        with self.assertRaisesRegex(PilotCityLaunchApprovalError, "must differ"):
            validate_approval(approval)

    def test_every_pilot_entry_gate_is_required(self) -> None:
        approval = self._accepted_approval()
        approval["readiness_decisions"].pop()
        with self.assertRaisesRegex(PilotCityLaunchApprovalError, "every pilot-entry gate"):
            validate_approval(approval)

    def test_readiness_must_bind_active_configuration(self) -> None:
        approval = self._accepted_approval()
        approval["readiness_decisions"][0]["configuration_id"] = (
            "10000000-0000-4000-8000-000000000999"
        )
        with self.assertRaisesRegex(PilotCityLaunchApprovalError, "active configuration"):
            validate_approval(approval)

    def test_readiness_review_must_cover_pilot_end(self) -> None:
        approval = self._accepted_approval()
        approval["readiness_decisions"][0]["review_due_at"] = "2026-10-20T00:00:00Z"
        with self.assertRaisesRegex(PilotCityLaunchApprovalError, "expires before pilot end"):
            validate_approval(approval)

    def test_all_approval_functions_are_required(self) -> None:
        approval = self._accepted_approval()
        approval["approvals"].pop()
        with self.assertRaisesRegex(PilotCityLaunchApprovalError, "every reviewed function"):
            validate_approval(approval)

    def test_operator_authority_must_cover_pilot_end(self) -> None:
        approval = self._accepted_approval()
        approval["scope"]["operator_authority_valid_until"] = "2026-10-20T00:00:00Z"
        with self.assertRaisesRegex(PilotCityLaunchApprovalError, "expires before"):
            validate_approval(approval)

    def test_public_terms_must_be_effective_before_start(self) -> None:
        approval = self._accepted_approval()
        approval["public_terms"]["effective_at"] = "2026-10-16T00:00:00Z"
        with self.assertRaisesRegex(PilotCityLaunchApprovalError, "after the pilot starts"):
            validate_approval(approval)

    def test_cash_cannot_be_removed_from_pilot_scope(self) -> None:
        approval = self._accepted_approval()
        approval["scope"]["payment_methods"] = ["MANUAL_TRANSFER"]
        with self.assertRaisesRegex(PilotCityLaunchApprovalError, "retain CASH"):
            validate_approval(approval)

    def test_scheduling_requires_an_explicit_scope(self) -> None:
        approval = self._accepted_approval()
        approval["scope"]["service_types"].append("SCHEDULED")
        with self.assertRaisesRegex(PilotCityLaunchApprovalError, "scheduling_scope_reference"):
            validate_approval(approval)

    def test_full_service_scope_is_supported_when_explicit(self) -> None:
        approval = self._accepted_approval()
        approval["scope"].update(
            {
                "service_types": ["ON_DEMAND", "FIXED_ROUTE", "SCHEDULED"],
                "fixed_route_scope_reference": "evidence/routes/pilot-v1",
                "scheduling_scope_reference": "evidence/scheduling/pilot-v1",
                "payment_methods": ["CASH", "MANUAL_TRANSFER"],
            }
        )

        summary = validate_approval(approval, require_accepted=True)

        self.assertTrue(summary["gap_004_accepted"])

    def test_disabled_fixed_route_cannot_retain_hidden_scope(self) -> None:
        approval = self._accepted_approval()
        approval["scope"]["fixed_route_scope_reference"] = "evidence/routes/hidden"
        with self.assertRaisesRegex(PilotCityLaunchApprovalError, "FIXED_ROUTE is disabled"):
            validate_approval(approval)

    def test_cohort_concurrency_cannot_exceed_supply(self) -> None:
        approval = self._accepted_approval()
        approval["pilot_limits"]["maximum_concurrent_rides"] = 21
        with self.assertRaisesRegex(PilotCityLaunchApprovalError, "bounded passenger or driver"):
            validate_approval(approval)

    def test_secret_bearing_fields_are_rejected(self) -> None:
        approval = self._accepted_approval()
        approval["submission"]["api_key"] = "forbidden"
        with self.assertRaisesRegex(PilotCityLaunchApprovalError, "forbidden key"):
            validate_approval(approval)

    def test_phase_acceptance_cannot_be_claimed(self) -> None:
        approval = self._accepted_approval()
        approval["phase_accepted"] = True
        with self.assertRaisesRegex(PilotCityLaunchApprovalError, "cannot accept"):
            validate_approval(approval)


if __name__ == "__main__":
    unittest.main()
