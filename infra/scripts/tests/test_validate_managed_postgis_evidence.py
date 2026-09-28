from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest


SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from validate_docs import discover_migration_head
from validate_managed_postgis_evidence import (
    DEFAULT_EVIDENCE,
    MIGRATIONS_ROOT,
    ManagedPostgisEvidenceError,
    validate_evidence,
)


class ManagedPostgisEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.template = json.loads(DEFAULT_EVIDENCE.read_text(encoding="utf-8"))
        cls.migration_head = discover_migration_head(MIGRATIONS_ROOT)

    def _accepted_evidence(self) -> dict:
        value = copy.deepcopy(self.template)
        value.update(
            {
                "status": "ACCEPTED",
                "candidate_label": "managed-postgis-candidate-2026-09-28",
                "source_commit": "d" * 40,
                "environment_inventory_reference": "evidence/environment/GAP-002",
                "gap_003_accepted": True,
                "limitations": ["NO_PHASE_OR_DEPLOYMENT_ACCEPTANCE"],
            }
        )
        value["database"] = {
            "service_reference": "provider/databases/production",
            "network_policy_reference": "evidence/network/DATABASE",
            "compatibility_report_reference": "evidence/database/COMPATIBILITY",
            "postgres_major": 16,
            "postgis_version": "3.5.3",
            "private_access_only": True,
            "tls_in_transit": True,
            "encryption_at_rest": True,
            "automated_failover_enabled": True,
        }
        value["least_privilege"] = {
            "role_review_reference": "evidence/database/ROLE-REVIEW",
            "application_role_non_superuser": True,
            "application_role_no_createdb": True,
            "application_role_no_createrole": True,
            "migration_role_separate": True,
            "backup_authority_separate": True,
            "monitoring_role_read_only": True,
        }
        value["objectives"] = {
            "approval_reference": "evidence/database/OBJECTIVES",
            "approved_rpo_seconds": 60,
            "approved_rto_seconds": 300,
        }
        value["capacity"] = {
            "report_reference": "evidence/database/CAPACITY",
            "monitoring_reference": "evidence/database/MONITORING",
            "alerting_reference": "evidence/database/ALERTING",
            "server_connection_limit": 500,
            "application_connection_budget": 240,
            "headroom_percent": 40,
        }
        value["migration_rehearsal"] = {
            "source_copy_reference": "evidence/database/SOURCE-COPY",
            "report_reference": "evidence/database/MIGRATION-REHEARSAL",
            "migration_head": self.migration_head,
            "duration_seconds": 120,
            "advisory_lock_verified": True,
            "timeouts_verified": True,
            "conflicting_data_count": 0,
            "old_new_compatibility_reference": "evidence/database/OLD-NEW-COMPATIBILITY",
            "forward_fix_reference": "evidence/database/FORWARD-FIX",
        }
        value["backup_policy"] = {
            "policy_reference": "evidence/database/BACKUP-POLICY",
            "access_review_reference": "evidence/database/BACKUP-ACCESS",
            "provider_audit_reference": "evidence/database/BACKUP-AUDIT",
            "encrypted": True,
            "automated_snapshots_enabled": True,
            "snapshot_frequency_hours": 6,
            "continuous_pitr_enabled": True,
            "pitr_window_days": 7,
            "backup_retention_days": 30,
            "cross_failure_domain_copy": True,
        }
        value["restore_rehearsal"] = {
            "report_reference": "evidence/database/RESTORE",
            "restored_at": "2026-09-28T14:00:00Z",
            "isolated_staging_target": True,
            "migration_head": self.migration_head,
            "postgis_version_match": True,
            "table_counts_match": True,
            "schema_object_counts_match": True,
            "application_readiness_passed": True,
            "measured_data_loss_seconds": 30,
            "measured_recovery_seconds": 240,
            "restore_target_disposition_reference": "evidence/database/RESTORE-DISPOSITION",
        }
        value["failover_rehearsal"] = {
            "report_reference": "evidence/database/FAILOVER",
            "executed_at": "2026-09-28T15:00:00Z",
            "provider_failover_completed": True,
            "api_recovery_verified": True,
            "worker_recovery_verified": True,
            "alerts_acknowledged": True,
            "measured_data_loss_seconds": 20,
            "measured_recovery_seconds": 180,
        }
        value["retention_reconciliation"] = {
            "policy_reference": "evidence/privacy/RETENTION-POLICY",
            "legal_hold_review_reference": "evidence/privacy/LEGAL-HOLD",
            "expiry_test_reference": "evidence/privacy/BACKUP-EXPIRY",
            "held_records_survived_restore": True,
            "expired_personal_fields_absent_after_backup_expiry": True,
            "provider_backup_deletion_verified": True,
        }
        for approval in value["approvals"]:
            approval.update(
                {
                    "decision": "APPROVED",
                    "evidence_reference": f"evidence/approvals/{approval['function']}",
                    "decided_at": "2026-09-28T16:00:00Z",
                }
            )
        return value

    def test_committed_template_is_valid_and_unaccepted(self) -> None:
        summary = validate_evidence(self.template)
        self.assertEqual("NOT_STARTED", summary["status"])
        self.assertFalse(summary["gap_003_accepted"])
        self.assertFalse(self.template["phase_accepted"])
        self.assertFalse(self.template["deployment_accepted"])

    def test_require_accepted_rejects_template(self) -> None:
        with self.assertRaisesRegex(ManagedPostgisEvidenceError, "externally accepted"):
            validate_evidence(self.template, require_accepted=True)

    def test_complete_evidence_accepts_only_gap_003(self) -> None:
        evidence = self._accepted_evidence()
        summary = validate_evidence(evidence, require_accepted=True)
        self.assertTrue(summary["gap_003_accepted"])
        self.assertFalse(evidence["phase_accepted"])
        self.assertFalse(evidence["deployment_accepted"])

    def test_current_migration_head_is_required(self) -> None:
        evidence = self._accepted_evidence()
        evidence["migration_rehearsal"]["migration_head"] = "20260101_0001"
        with self.assertRaisesRegex(ManagedPostgisEvidenceError, "current head"):
            validate_evidence(evidence)

    def test_private_encrypted_database_is_required(self) -> None:
        evidence = self._accepted_evidence()
        evidence["database"]["private_access_only"] = False
        with self.assertRaisesRegex(ManagedPostgisEvidenceError, "private_access_only=true"):
            validate_evidence(evidence)

    def test_least_privilege_cannot_be_claimed_with_createdb(self) -> None:
        evidence = self._accepted_evidence()
        evidence["least_privilege"]["application_role_no_createdb"] = False
        with self.assertRaisesRegex(ManagedPostgisEvidenceError, "application_role_no_createdb=true"):
            validate_evidence(evidence)

    def test_restore_must_meet_rpo(self) -> None:
        evidence = self._accepted_evidence()
        evidence["restore_rehearsal"]["measured_data_loss_seconds"] = 61
        with self.assertRaisesRegex(ManagedPostgisEvidenceError, "exceeds approved RPO"):
            validate_evidence(evidence)

    def test_failover_must_meet_rto(self) -> None:
        evidence = self._accepted_evidence()
        evidence["failover_rehearsal"]["measured_recovery_seconds"] = 301
        with self.assertRaisesRegex(ManagedPostgisEvidenceError, "exceeds approved RTO"):
            validate_evidence(evidence)

    def test_retention_expiry_must_be_proved(self) -> None:
        evidence = self._accepted_evidence()
        evidence["retention_reconciliation"][
            "expired_personal_fields_absent_after_backup_expiry"
        ] = False
        with self.assertRaisesRegex(
            ManagedPostgisEvidenceError,
            "expired_personal_fields_absent_after_backup_expiry=true",
        ):
            validate_evidence(evidence)

    def test_not_started_evidence_cannot_hide_operational_claims(self) -> None:
        evidence = copy.deepcopy(self.template)
        evidence["database"]["private_access_only"] = True
        with self.assertRaisesRegex(ManagedPostgisEvidenceError, "operational claims"):
            validate_evidence(evidence)

    def test_not_started_evidence_cannot_hide_zero_measurement(self) -> None:
        evidence = copy.deepcopy(self.template)
        evidence["objectives"]["approved_rpo_seconds"] = 0
        with self.assertRaisesRegex(ManagedPostgisEvidenceError, "operational claims"):
            validate_evidence(evidence)

    def test_secret_bearing_fields_are_rejected(self) -> None:
        evidence = self._accepted_evidence()
        evidence["database"]["database_url"] = "forbidden"
        with self.assertRaisesRegex(ManagedPostgisEvidenceError, "forbidden key"):
            validate_evidence(evidence)

    def test_application_budget_must_leave_reserve(self) -> None:
        evidence = self._accepted_evidence()
        evidence["capacity"]["application_connection_budget"] = 500
        with self.assertRaisesRegex(ManagedPostgisEvidenceError, "leave capacity"):
            validate_evidence(evidence)

    def test_declared_headroom_must_match_connection_budget(self) -> None:
        evidence = self._accepted_evidence()
        evidence["capacity"]["application_connection_budget"] = 400
        evidence["capacity"]["headroom_percent"] = 40
        with self.assertRaisesRegex(ManagedPostgisEvidenceError, "declared connection headroom"):
            validate_evidence(evidence)


if __name__ == "__main__":
    unittest.main()
