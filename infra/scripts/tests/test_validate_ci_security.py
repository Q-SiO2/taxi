from pathlib import Path
import sys
import unittest


SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from validate_ci_security import (
    CiSecurityError,
    IOS_PACKAGE_RESOLVED_PATH,
    IOS_PROJECT_PATH,
    WORKFLOW_PATH,
    validate_ci_security,
    validate_ios_package_lock,
)


class CiSecurityValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        cls.ios_package_lock = IOS_PACKAGE_RESOLVED_PATH.read_text(encoding="utf-8")
        cls.ios_project = IOS_PROJECT_PATH.read_text(encoding="utf-8")

    def test_committed_workflow_passes(self) -> None:
        validate_ci_security(self.workflow)

    def test_committed_ios_package_lock_passes(self) -> None:
        validate_ios_package_lock(self.ios_package_lock, self.ios_project)

    def test_ios_package_revision_change_is_rejected(self) -> None:
        changed = self.ios_package_lock.replace(
            "bbe8b69694d7873315fd3a4ad41efe043e1c07c5",
            "0" * 40,
        )
        with self.assertRaisesRegex(CiSecurityError, "abseil-cpp-binary"):
            validate_ios_package_lock(changed, self.ios_project)

    def test_ios_package_branch_pin_is_rejected(self) -> None:
        changed = self.ios_package_lock.replace(
            '"revision" : "bbe8b69694d7873315fd3a4ad41efe043e1c07c5",',
            '"branch" : "main",\n        "revision" : '
            '"bbe8b69694d7873315fd3a4ad41efe043e1c07c5",',
        )
        with self.assertRaisesRegex(CiSecurityError, "mutable branch"):
            validate_ios_package_lock(changed, self.ios_project)

    def test_ios_root_package_version_drift_is_rejected(self) -> None:
        changed = self.ios_project.replace("version = 12.17.0;", "version = 12.18.0;")
        with self.assertRaisesRegex(CiSecurityError, "firebase-ios-sdk"):
            validate_ios_package_lock(self.ios_package_lock, changed)

    def test_mutable_action_reference_is_rejected(self) -> None:
        changed = self.workflow.replace(
            "anchore/sbom-action@3ad7283483fc7af8ff2b4ea19663c2d5ca935e26",
            "anchore/sbom-action@v0.24.2",
        )
        with self.assertRaisesRegex(CiSecurityError, "immutable commit SHA"):
            validate_ci_security(changed)

    def test_non_blocking_image_scan_is_rejected(self) -> None:
        changed = self.workflow.replace('exit-code: "1"', 'exit-code: "0"')
        with self.assertRaisesRegex(CiSecurityError, "must block CI"):
            validate_ci_security(changed)

    def test_missing_sbom_provenance_binding_is_rejected(self) -> None:
        changed = self.workflow.replace(
            "--artifact /tmp/taximobile-api.spdx.json",
            "--artifact /tmp/unrelated.spdx.json",
        )
        with self.assertRaisesRegex(CiSecurityError, "not bound to its SBOM"):
            validate_ci_security(changed)

    def test_missing_contract_inventory_binding_is_rejected(self) -> None:
        changed = self.workflow.replace(
            "--artifact /tmp/taximobile-source-contract-inventory.json",
            "--artifact /tmp/unrelated-contract-inventory.json",
        )
        with self.assertRaisesRegex(
            CiSecurityError,
            "Generated API/migration/permission inventory",
        ):
            validate_ci_security(changed)

    def test_missing_contract_inventory_generation_is_rejected(self) -> None:
        changed = self.workflow.replace(
            "python ../infra/scripts/generate_source_contract_inventory.py",
            "python ../infra/scripts/removed_contract_inventory.py",
        )
        with self.assertRaisesRegex(
            CiSecurityError,
            "Generated API/migration/permission inventory",
        ):
            validate_ci_security(changed)

    def test_legacy_admin_caller_gate_cannot_be_removed(self) -> None:
        changed = self.workflow.replace(
            "      - run: python ../infra/scripts/validate_legacy_admin_retirement.py\n",
            "",
        )
        with self.assertRaisesRegex(
            CiSecurityError,
            "caller validation must run once",
        ):
            validate_ci_security(changed)

    def test_test_phase_evidence_gate_cannot_be_removed(self) -> None:
        changed = self.workflow.replace(
            "      - run: python infra/scripts/validate_test_phase_evidence.py\n",
            "",
        )
        with self.assertRaisesRegex(
            CiSecurityError,
            "phase catalog and evidence template",
        ):
            validate_ci_security(changed)

    def test_web_compatibility_runtime_gate_cannot_be_removed(self) -> None:
        changed = self.workflow.replace(
            "      - run: node scripts/test-web-compatibility-loader.mjs\n",
            "",
        )
        with self.assertRaisesRegex(
            CiSecurityError,
            "web compatibility loader runtime scenarios",
        ):
            validate_ci_security(changed)

    def test_web_manifest_source_binding_cannot_be_removed(self) -> None:
        changed = self.workflow.replace(
            '--artifact "${RUNNER_TEMP}/taximobile-web-release/release-manifest.json"',
            '--artifact "${RUNNER_TEMP}/unrelated.json"',
        )
        with self.assertRaisesRegex(
            CiSecurityError,
            "packaged web manifest is not bound to source",
        ):
            validate_ci_security(changed)

    def test_real_browser_smoke_source_binding_cannot_be_removed(self) -> None:
        changed = self.workflow.replace(
            '--artifact "${RUNNER_TEMP}/taximobile-t4-browser-smoke.json"',
            '--artifact "${RUNNER_TEMP}/unrelated-browser-smoke.json"',
        )
        with self.assertRaisesRegex(
            CiSecurityError,
            "packaged web manifest is not bound to source",
        ):
            validate_ci_security(changed)

    def test_android_manifest_source_binding_cannot_be_removed(self) -> None:
        changed = self.workflow.replace(
            '--artifact "${RUNNER_TEMP}/taximobile-android-verification-manifest.json"',
            '--artifact "${RUNNER_TEMP}/unrelated-android.json"',
        )
        with self.assertRaisesRegex(
            CiSecurityError,
            "Android verification artifacts are not limitation-marked",
        ):
            validate_ci_security(changed)

    def test_ios_manifest_source_binding_cannot_be_removed(self) -> None:
        changed = self.workflow.replace(
            '--artifact "${RUNNER_TEMP}/taximobile-ios-verification-manifest.json"',
            '--artifact "${RUNNER_TEMP}/unrelated-ios.json"',
        )
        with self.assertRaisesRegex(
            CiSecurityError,
            "iOS simulator artifacts are not limitation-marked",
        ):
            validate_ci_security(changed)

    def test_ios_failure_annotation_cannot_be_removed(self) -> None:
        changed = self.workflow.replace(
            '--title "TaxiMobile iOS shared Gradle failure"',
            '--title "Removed iOS diagnostic"',
        )
        with self.assertRaisesRegex(
            CiSecurityError,
            "iOS simulator artifacts are not limitation-marked",
        ):
            validate_ci_security(changed)

    def test_ios_test_execution_limitation_cannot_be_hidden(self) -> None:
        changed = self.workflow.replace(
            "this run does not claim iOS test execution",
            "iOS tests passed",
        )
        with self.assertRaisesRegex(
            CiSecurityError,
            "iOS simulator artifacts are not limitation-marked",
        ):
            validate_ci_security(changed)

    def test_ios_automatic_package_resolution_cannot_be_restored(self) -> None:
        changed = self.workflow.replace("          -disableAutomaticPackageResolution\n", "", 1)
        with self.assertRaisesRegex(CiSecurityError, "automatic Swift package resolution"):
            validate_ci_security(changed)

    def test_ios_package_cache_cannot_ignore_the_lock(self) -> None:
        changed = self.workflow.replace(
            "project.xcworkspace/xcshareddata/swiftpm/Package.resolved",
            "project.pbxproj",
        )
        with self.assertRaisesRegex(CiSecurityError, "cache key"):
            validate_ci_security(changed)

    def test_android_shared_test_failure_annotation_cannot_be_removed(self) -> None:
        changed = self.workflow.replace(
            "      - name: Publish redacted Android shared-test failure annotation\n",
            "      - name: Removed Android shared-test diagnostic\n",
        )
        with self.assertRaisesRegex(
            CiSecurityError,
            "Android shared-test failures must publish a bounded redacted diagnostic",
        ):
            validate_ci_security(changed)

    def test_monitoring_failure_annotation_cannot_be_removed(self) -> None:
        changed = self.workflow.replace(
            "      - name: Publish redacted monitoring-tool failure annotation\n",
            "      - name: Removed monitoring diagnostic\n",
        )
        with self.assertRaisesRegex(
            CiSecurityError,
            "Monitoring CI failures must publish a bounded redacted diagnostic",
        ):
            validate_ci_security(changed)

    def test_monitoring_smoke_requires_full_reviewed_dashboard(self) -> None:
        changed = self.workflow.replace(
            'assert len(dashboard["panels"]) == 26',
            'assert len(dashboard["panels"]) == 13',
        )
        with self.assertRaisesRegex(
            CiSecurityError,
            "all 26 reviewed operations panels",
        ):
            validate_ci_security(changed)

    def test_t2_simulated_persona_binding_cannot_be_removed(self) -> None:
        changed = self.workflow.replace(
            "          --artifact /tmp/taximobile-t2-simulated-personas.json\n",
            "",
        )
        with self.assertRaisesRegex(
            CiSecurityError,
            "bounded T2 simulated-persona report",
        ):
            validate_ci_security(changed)

    def test_t2_catalog_source_gate_cannot_be_removed(self) -> None:
        changed = self.workflow.replace(
            "      - run: python infra/scripts/run_simulated_persona_suite.py --validate-only\n",
            "",
        )
        with self.assertRaisesRegex(
            CiSecurityError,
            "catalog must be validated once",
        ):
            validate_ci_security(changed)

    def test_t3_database_metadata_binding_cannot_be_removed(self) -> None:
        changed = self.workflow.replace(
            "          --artifact /tmp/taximobile-t3-database-metadata.json\n",
            "",
        )
        with self.assertRaisesRegex(CiSecurityError, "bounded T3 full-system report"):
            validate_ci_security(changed)

    def test_t3_acceptance_warning_cannot_be_removed(self) -> None:
        changed = self.workflow.replace(
            "          echo 'This complete evidence set does not accept T3 or deployment; formal engineering sign-off remains required.' >> \"${GITHUB_STEP_SUMMARY}\"\n",
            "",
        )
        with self.assertRaisesRegex(CiSecurityError, "bounded T3 full-system report"):
            validate_ci_security(changed)

    def test_t3_backup_restore_binding_cannot_be_removed(self) -> None:
        changed = self.workflow.replace(
            "          --artifact /tmp/taximobile-t3-backup-restore.json\n",
            "",
        )
        with self.assertRaisesRegex(CiSecurityError, "bounded T3 full-system report"):
            validate_ci_security(changed)

    def test_t4_lab_catalog_gate_cannot_be_removed(self) -> None:
        changed = self.workflow.replace(
            "      - run: python infra/scripts/validate_t4_lab_evidence.py\n",
            "",
        )
        with self.assertRaisesRegex(CiSecurityError, "T4 device/browser laboratory catalog"):
            validate_ci_security(changed)

    def test_gap_002_environment_inventory_gate_cannot_be_removed(self) -> None:
        changed = self.workflow.replace(
            "      - run: python infra/scripts/validate_production_environment_inventory.py\n",
            "",
        )
        with self.assertRaisesRegex(CiSecurityError, "GAP-002 production environment inventory"):
            validate_ci_security(changed)

    def test_gap_003_managed_postgis_gate_cannot_be_removed(self) -> None:
        changed = self.workflow.replace(
            "      - run: python infra/scripts/validate_managed_postgis_evidence.py\n",
            "",
        )
        with self.assertRaisesRegex(CiSecurityError, "GAP-003 managed PostGIS evidence"):
            validate_ci_security(changed)

    def test_gap_004_pilot_city_approval_gate_cannot_be_removed(self) -> None:
        changed = self.workflow.replace(
            "      - run: python infra/scripts/validate_pilot_city_launch_approval.py\n",
            "",
        )
        with self.assertRaisesRegex(CiSecurityError, "GAP-004 pilot-city approval"):
            validate_ci_security(changed)

    def test_gap_005_operations_identity_gate_cannot_be_removed(self) -> None:
        changed = self.workflow.replace(
            "      - run: python infra/scripts/validate_operations_identity_governance.py\n",
            "",
        )
        with self.assertRaisesRegex(CiSecurityError, "GAP-005 operations identity governance"):
            validate_ci_security(changed)

    def test_gap_006_maps_routing_navigation_gate_cannot_be_removed(self) -> None:
        changed = self.workflow.replace(
            "      - run: python infra/scripts/validate_maps_routing_navigation.py\n",
            "",
        )
        with self.assertRaisesRegex(CiSecurityError, "GAP-006 maps/routing/navigation"):
            validate_ci_security(changed)


if __name__ == "__main__":
    unittest.main()
