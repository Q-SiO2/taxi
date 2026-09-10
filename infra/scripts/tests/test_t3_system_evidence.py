from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from collect_t3_database_metadata import T3DatabaseMetadataError, build_metadata_report
from generate_t3_system_report import (
    REQUIRED_CASES,
    T3SystemEvidenceError,
    generate_report,
)
from run_t3_backup_restore_rehearsal import T3BackupRestoreError, _validate_fingerprints


def database_snapshot(**changes):
    result = {
        "database_name": "taximobile_ci",
        "migration_heads": ["20260908_0052"],
        "postgres_version": "16.4",
        "postgis_version": "3.4.2",
        "residual_clone_database_count": 0,
        "role_can_create_database": False,
        "role_is_superuser": False,
    }
    result.update(changes)
    return result


def backup_restore_report(**changes):
    result = {
        "schema_version": 1,
        "generated_at": "2026-09-09T00:00:00+00:00",
        "evidence_level": "T3_LOCAL_BACKUP_RESTORE_EXECUTION",
        "phase": "T3",
        "result": "PASS",
        "data_classification": "SYNTHETIC_AGGREGATES_ONLY",
        "supported_evidence_kind": "LOCAL_BACKUP_RESTORE_REPORT",
        "phase_accepted": False,
        "deployment_accepted": False,
        "source_database_scope": "taximobile_ci",
        "restore_target_scope": "EPHEMERAL_TAXIMOBILE_RESTORE_T3",
        "restore_target_removed": True,
        "temporary_dump_removed": True,
        "backup_bytes": 4096,
        "backup_sha256": "a" * 64,
        "reconciliation": {
            "migration_head": "20260908_0052",
            "postgis_version": "3.4.2",
            "public_table_count": 80,
            "aggregate_row_count": 140,
            "constraint_count": 120,
            "index_count": 160,
            "sequence_count": 0,
            "table_counts_match": True,
            "schema_object_counts_match": True,
        },
        "timings_seconds": {
            "backup": 1.0,
            "restore": 2.0,
            "verification": 0.5,
            "total": 3.5,
        },
        "limitations": ["NO_PHASE_ACCEPTANCE_CLAIM"],
    }
    result.update(changes)
    return result


class T3DatabaseMetadataTests(unittest.TestCase):
    def test_local_metadata_requires_revoked_authority(self) -> None:
        with self.assertRaisesRegex(T3DatabaseMetadataError, "retained broad"):
            build_metadata_report(
                database_snapshot(role_can_create_database=True),
                expected_head="20260908_0052",
                authority_mode="TEMPORARY_CREATEDB_REVOKED",
                database_lifecycle="RECREATED_BEFORE_MIGRATION",
            )

    def test_metadata_rejects_residual_clone_databases(self) -> None:
        with self.assertRaisesRegex(T3DatabaseMetadataError, "clone databases remain"):
            build_metadata_report(
                database_snapshot(residual_clone_database_count=1),
                expected_head="20260908_0052",
                authority_mode="TEMPORARY_CREATEDB_REVOKED",
                database_lifecycle="RECREATED_BEFORE_MIGRATION",
            )

    def test_metadata_never_claims_acceptance_or_restore(self) -> None:
        report = build_metadata_report(
            database_snapshot(),
            expected_head="20260908_0052",
            authority_mode="TEMPORARY_CREATEDB_REVOKED",
            database_lifecycle="RECREATED_BEFORE_MIGRATION",
        )
        self.assertFalse(report["phase_accepted"])
        self.assertFalse(report["deployment_accepted"])
        self.assertIn("NO_BACKUP_RESTORE_CLAIM", report["limitations"])

    def test_metadata_records_stale_clone_remediation(self) -> None:
        report = build_metadata_report(
            database_snapshot(),
            expected_head="20260908_0052",
            authority_mode="TEMPORARY_CREATEDB_REVOKED",
            database_lifecycle="RECREATED_BEFORE_MIGRATION",
            preexisting_clone_count=2,
        )
        self.assertEqual(2, report["preexisting_clone_databases_removed"])


class T3BackupRestoreTests(unittest.TestCase):
    def test_fingerprint_reconciliation_uses_aggregates_not_row_content(self) -> None:
        source = {
            "database_name": "taximobile_ci",
            "migration_heads": ["20260908_0052"],
            "postgis_version": "3.4.2",
            "table_counts": {"users": 2, "rides": 1},
            "constraint_count": 3,
            "index_count": 4,
            "sequence_count": 0,
        }
        restored = {**source, "database_name": "taximobile_restore_t3_test"}
        result = _validate_fingerprints(source, restored, expected_head="20260908_0052")
        self.assertEqual(3, result["aggregate_row_count"])
        self.assertNotIn("table_counts", result)

    def test_fingerprint_rejects_changed_table_counts(self) -> None:
        source = {
            "database_name": "taximobile_ci",
            "migration_heads": ["20260908_0052"],
            "postgis_version": "3.4.2",
            "table_counts": {"users": 2},
            "constraint_count": 3,
            "index_count": 4,
            "sequence_count": 0,
        }
        restored = {**source, "database_name": "taximobile_restore_t3_test", "table_counts": {"users": 1}}
        with self.assertRaisesRegex(T3BackupRestoreError, "do not match"):
            _validate_fingerprints(source, restored, expected_head="20260908_0052")


class T3SystemReportTests(unittest.TestCase):
    def _artifacts(self, root: Path, *, remove_case: str | None = None, skipped: int = 0):
        suite = ET.Element(
            "testsuite",
            tests="900",
            failures="0",
            errors="0",
            skipped=str(skipped),
        )
        ET.SubElement(suite, "testcase", classname="tests.unit.test_example", name="test_unit")
        for identifier in [item for values in REQUIRED_CASES.values() for item in values]:
            if identifier == remove_case:
                continue
            classname, name = identifier.split("::", 1)
            ET.SubElement(suite, "testcase", classname=classname, name=f"{name}[synthetic]")
        represented = len(list(suite.iter("testcase")))
        for index in range(represented, 900):
            ET.SubElement(
                suite,
                "testcase",
                classname="tests.unit.test_filler",
                name=f"test_filler_{index}",
            )
        junit = root / "full.junit.xml"
        ET.ElementTree(suite).write(junit, encoding="unicode")

        metadata = build_metadata_report(
            database_snapshot(),
            expected_head="20260908_0052",
            authority_mode="TEMPORARY_CREATEDB_REVOKED",
            database_lifecycle="RECREATED_BEFORE_MIGRATION",
        )
        metadata_path = root / "database.json"
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
        return junit, metadata_path

    def test_green_report_supports_five_kinds_but_never_accepts_t3(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            junit, metadata = self._artifacts(Path(directory))
            report = generate_report(junit, metadata)
        self.assertEqual("PASS", report["result"])
        self.assertEqual(5, len(report["supported_evidence_kinds"]))
        self.assertEqual(["LOCAL_BACKUP_RESTORE_REPORT"], report["missing_t3_evidence_kinds"])
        self.assertFalse(report["phase_evidence_complete"])
        self.assertFalse(report["phase_accepted"])
        self.assertFalse(report["deployment_accepted"])

    def test_backup_restore_completes_evidence_without_accepting_phase(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            junit, metadata = self._artifacts(root)
            backup = root / "backup.json"
            backup.write_text(json.dumps(backup_restore_report()), encoding="utf-8")
            report = generate_report(junit, metadata, backup)
        self.assertEqual(6, len(report["supported_evidence_kinds"]))
        self.assertEqual([], report["missing_t3_evidence_kinds"])
        self.assertTrue(report["phase_evidence_complete"])
        self.assertFalse(report["phase_accepted"])
        self.assertFalse(report["deployment_accepted"])

    def test_backup_restore_must_prove_target_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            junit, metadata = self._artifacts(root)
            backup = root / "backup.json"
            backup.write_text(
                json.dumps(backup_restore_report(restore_target_removed=False)),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(T3SystemEvidenceError, "not a passing"):
                generate_report(junit, metadata, backup)

    def test_missing_named_concurrency_case_is_rejected(self) -> None:
        missing = REQUIRED_CASES["CONCURRENT_AUTHORITY"][0]
        with tempfile.TemporaryDirectory() as directory:
            junit, metadata = self._artifacts(Path(directory), remove_case=missing)
            with self.assertRaisesRegex(T3SystemEvidenceError, "missing required"):
                generate_report(junit, metadata)

    def test_skipped_test_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            junit, metadata = self._artifacts(Path(directory), skipped=1)
            with self.assertRaisesRegex(T3SystemEvidenceError, "zero failures"):
                generate_report(junit, metadata)

    def test_declared_junit_count_must_match_represented_cases(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            junit, metadata = self._artifacts(root)
            tree = ET.parse(junit)
            tree.getroot().remove(list(tree.getroot())[-1])
            tree.write(junit, encoding="unicode")
            with self.assertRaisesRegex(T3SystemEvidenceError, "represented test cases"):
                generate_report(junit, metadata)


if __name__ == "__main__":
    unittest.main()
