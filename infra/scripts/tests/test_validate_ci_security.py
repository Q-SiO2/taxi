from pathlib import Path
import sys
import unittest


SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from validate_ci_security import CiSecurityError, WORKFLOW_PATH, validate_ci_security


class CiSecurityValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    def test_committed_workflow_passes(self) -> None:
        validate_ci_security(self.workflow)

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


if __name__ == "__main__":
    unittest.main()
