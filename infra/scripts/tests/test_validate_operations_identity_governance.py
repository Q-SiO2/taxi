from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest


SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from validate_operations_identity_governance import (
    DEFAULT_GOVERNANCE,
    OperationsIdentityGovernanceError,
    validate_governance,
)


class OperationsIdentityGovernanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.template = json.loads(DEFAULT_GOVERNANCE.read_text(encoding="utf-8"))

    def _accepted(self) -> dict:
        value = copy.deepcopy(self.template)
        value.update(
            {
                "status": "ACCEPTED",
                "candidate_label": "operations-governance-2026-09-29",
                "source_commit": "f" * 40,
                "environment_inventory_reference": "evidence/environment/GAP-002",
                "database_evidence_reference": "evidence/database/GAP-003",
                "gap_005_accepted": True,
                "limitations": ["NO_PHASE_OR_DEPLOYMENT_ACCEPTANCE"],
            }
        )
        value["submission"] = {
            "submitted_by_account_reference": "operations/accounts/governance-maker",
            "submitted_at": "2026-09-29T08:00:00Z",
            "change_reference": "changes/GAP-005",
        }
        value["governance"] = {
            "authoritative_staff_roster_reference": "evidence/roster/production-v1",
            "joiner_mover_leaver_policy_reference": "policies/jml-v1",
            "access_review_policy_reference": "policies/access-review-v1",
            "recovery_policy_reference": "policies/recovery-v1",
            "break_glass_policy_reference": "policies/break-glass-v1",
            "operations_origin_reference": "environment/operations-origin",
            "security_event_routing_reference": "evidence/security/event-routing",
            "access_review_interval_days": 30,
            "leaver_revocation_sla_minutes": 60,
            "minimum_active_platform_administrators": 3,
            "shared_accounts_prohibited": True,
            "production_password_login_disabled": True,
            "last_access_review_at": "2026-10-01T08:00:00Z",
            "next_access_review_due_at": "2026-10-31T08:00:00Z",
        }
        account_by_function = {
            "PLATFORM_ADMIN_MAKER": "operations/accounts/platform-maker",
            "PLATFORM_ADMIN_CHECKER": "operations/accounts/platform-checker",
            "PLATFORM_ADMIN_RECOVERY": "operations/accounts/platform-recovery",
            "CITY_ROLLOUT_MAKER": "operations/accounts/city-maker",
            "CITY_ROLLOUT_CHECKER": "operations/accounts/city-checker",
            "PRICING_POLICY_MAKER": "operations/accounts/pricing-maker",
            "PRICING_POLICY_CHECKER": "operations/accounts/pricing-checker",
            "PAYMENT_RECONCILIATION": "operations/accounts/payment-reconciler",
            "DRIVER_DOCUMENT_REVIEW": "operations/accounts/driver-reviewer",
            "SENSITIVE_ACCESS_AUDIT": "operations/accounts/access-auditor",
            "SUPPORT_DUTY": "operations/accounts/support-duty",
            "SAFETY_DUTY": "operations/accounts/safety-duty",
            "ACCESS_REVIEW": "operations/accounts/access-reviewer",
            "LEAVER_REVOCATION": "operations/accounts/leaver-owner",
            "BREAK_GLASS_PRIMARY": "operations/accounts/break-glass-primary",
            "BREAK_GLASS_SECONDARY": "operations/accounts/break-glass-secondary",
        }
        for row in value["duty_assignments"]:
            row.update(
                {
                    "account_reference": account_by_function[row["function"]],
                    "scope_reference": "operations/scopes/market-MA",
                    "roster_assignment_reference": f"evidence/roster/{row['function']}",
                    "effective_from": "2026-09-30T08:00:00Z",
                    "review_due_at": "2026-11-15T08:00:00Z",
                }
            )
        value["mfa_enrollments"] = [
            {
                "account_reference": account,
                "factor_method": "TOTP",
                "enrollment_audit_reference": f"audit/mfa/enrollment-{index}",
                "recovery_custody_reference": f"evidence/recovery/custody-{index}",
                "enrolled_at": "2026-09-29T09:00:00Z",
                "verified_at": "2026-09-29T09:05:00Z",
                "reviewer_account_reference": f"operations/accounts/mfa-reviewer-{index}",
                "review_due_at": "2026-11-15T08:00:00Z",
            }
            for index, account in enumerate(sorted(set(account_by_function.values())), start=1)
        ]
        for index, row in enumerate(value["control_drills"], start=1):
            row.update(
                {
                    "status": "PASSED",
                    "actor_account_reference": f"operations/accounts/drill-actor-{index}",
                    "reviewer_account_reference": f"operations/accounts/drill-reviewer-{index}",
                    "evidence_reference": f"evidence/drills/{row['drill']}",
                    "executed_at": "2026-10-02T08:00:00Z",
                    "review_due_at": "2026-11-15T08:00:00Z",
                }
            )
        value["audit_evidence"] = {
            key: f"audit/GAP-005/{key}" for key in value["audit_evidence"]
        }
        for index, row in enumerate(value["approvals"], start=1):
            row.update(
                {
                    "decision": "APPROVED",
                    "reviewer_account_reference": f"approvals/accounts/reviewer-{index}",
                    "evidence_reference": f"evidence/approvals/{row['function']}",
                    "decided_at": "2026-10-03T08:00:00Z",
                    "review_due_at": "2026-11-15T08:00:00Z",
                }
            )
        return value

    def test_committed_template_is_valid_and_unaccepted(self) -> None:
        summary = validate_governance(self.template)
        self.assertEqual("NOT_STARTED", summary["status"])
        self.assertFalse(summary["gap_005_accepted"])

    def test_require_accepted_rejects_template(self) -> None:
        with self.assertRaisesRegex(OperationsIdentityGovernanceError, "externally accepted"):
            validate_governance(self.template, require_accepted=True)

    def test_complete_record_accepts_only_gap_005(self) -> None:
        record = self._accepted()
        summary = validate_governance(record, require_accepted=True)
        self.assertTrue(summary["gap_005_accepted"])
        self.assertFalse(record["phase_accepted"])
        self.assertFalse(record["deployment_accepted"])

    def test_not_started_record_cannot_hide_governance_claims(self) -> None:
        record = copy.deepcopy(self.template)
        record["governance"]["shared_accounts_prohibited"] = True
        with self.assertRaisesRegex(OperationsIdentityGovernanceError, "governance claims"):
            validate_governance(record)

    def test_every_duty_is_required(self) -> None:
        record = self._accepted()
        record["duty_assignments"].pop()
        with self.assertRaisesRegex(OperationsIdentityGovernanceError, "every reviewed function"):
            validate_governance(record)

    def test_platform_quorum_must_be_three_distinct_accounts(self) -> None:
        record = self._accepted()
        record["duty_assignments"][1]["account_reference"] = record["duty_assignments"][0]["account_reference"]
        with self.assertRaisesRegex(OperationsIdentityGovernanceError, "Separation of duty"):
            validate_governance(record)

    def test_pricing_maker_cannot_check_same_policy(self) -> None:
        record = self._accepted()
        rows = {row["function"]: row for row in record["duty_assignments"]}
        rows["PRICING_POLICY_CHECKER"]["account_reference"] = rows["PRICING_POLICY_MAKER"]["account_reference"]
        with self.assertRaisesRegex(OperationsIdentityGovernanceError, "Separation of duty"):
            validate_governance(record)

    def test_every_assigned_account_requires_mfa(self) -> None:
        record = self._accepted()
        record["mfa_enrollments"].pop()
        with self.assertRaisesRegex(OperationsIdentityGovernanceError, "cover every assigned account"):
            validate_governance(record)

    def test_mfa_reviewer_must_be_independent(self) -> None:
        record = self._accepted()
        row = record["mfa_enrollments"][0]
        row["reviewer_account_reference"] = row["account_reference"]
        with self.assertRaisesRegex(OperationsIdentityGovernanceError, "independent reviewer"):
            validate_governance(record)

    def test_password_only_login_cannot_be_accepted(self) -> None:
        record = self._accepted()
        record["governance"]["production_password_login_disabled"] = False
        with self.assertRaisesRegex(OperationsIdentityGovernanceError, "password-only"):
            validate_governance(record)

    def test_access_review_cadence_is_bounded(self) -> None:
        record = self._accepted()
        record["governance"]["access_review_interval_days"] = 91
        with self.assertRaisesRegex(OperationsIdentityGovernanceError, "between 1 and 90"):
            validate_governance(record)

    def test_leaver_sla_is_bounded(self) -> None:
        record = self._accepted()
        record["governance"]["leaver_revocation_sla_minutes"] = 1441
        with self.assertRaisesRegex(OperationsIdentityGovernanceError, "between 1 and 1440"):
            validate_governance(record)

    def test_all_control_drills_are_required_and_passed(self) -> None:
        record = self._accepted()
        record["control_drills"][5]["status"] = "FAILED"
        with self.assertRaisesRegex(OperationsIdentityGovernanceError, "must be PASSED"):
            validate_governance(record)

    def test_approval_cannot_be_made_by_submitter(self) -> None:
        record = self._accepted()
        record["approvals"][0]["reviewer_account_reference"] = record["submission"]["submitted_by_account_reference"]
        with self.assertRaisesRegex(OperationsIdentityGovernanceError, "must differ"):
            validate_governance(record)

    def test_forbidden_secret_field_is_rejected(self) -> None:
        record = self._accepted()
        record["submission"]["password"] = "forbidden"
        with self.assertRaisesRegex(OperationsIdentityGovernanceError, "forbidden key"):
            validate_governance(record)

    def test_phase_acceptance_cannot_be_claimed(self) -> None:
        record = self._accepted()
        record["phase_accepted"] = True
        with self.assertRaisesRegex(OperationsIdentityGovernanceError, "cannot accept"):
            validate_governance(record)


if __name__ == "__main__":
    unittest.main()
