from __future__ import annotations

import copy
from contextlib import redirect_stdout
import hashlib
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from validate_maps_routing_navigation import (
    DEFAULT_EVIDENCE,
    MapsRoutingNavigationError,
    main,
    validate_evidence,
)


class MapsRoutingNavigationEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.template = json.loads(DEFAULT_EVIDENCE.read_text(encoding="utf-8"))

    @staticmethod
    def _report(provider: str = "graphhopper") -> tuple[dict, str]:
        scenarios = ("casablanca_urban", "rabat_urban", "marrakech_urban")
        report = {
            "provider": provider,
            "passed": True,
            "scenario_count": len(scenarios),
            "required_languages": ["en", "fr", "ar"],
            "checks": [
                {"scenario": scenario, "language": language, "passed": True, "failures": []}
                for scenario in scenarios
                for language in ("en", "fr", "ar")
            ],
            "failure_counts": {},
        }
        payload = json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
        return report, hashlib.sha256(payload).hexdigest()

    def _accepted(self) -> tuple[dict, dict, str]:
        value = copy.deepcopy(self.template)
        report, report_sha = self._report()
        value.update(
            {
                "status": "ACCEPTED",
                "candidate_label": "morocco-routing-candidate-2026-09-29",
                "source_commit": "f" * 40,
                "environment_inventory_reference": "evidence/environment/GAP-002",
                "database_evidence_reference": "evidence/database/GAP-003",
                "pilot_city_approval_reference": "evidence/city/GAP-004",
                "gap_006_accepted": True,
                "limitations": ["NO_PHASE_OR_DEPLOYMENT_ACCEPTANCE"],
            }
        )
        value["submission"] = {
            "submitted_by_account_reference": "operations/accounts/maps-release-maker",
            "submitted_at": "2026-09-29T09:00:00Z",
            "change_reference": "changes/maps-routing-006",
        }
        value["launch_scope"] = {
            "market_code": "MA",
            "country_code": "MA",
            "city_id": "10000000-0000-4000-8000-000000000112",
            "city_configuration_id": "10000000-0000-4000-8000-000000000111",
            "service_area_reference": "evidence/service-area/pilot-v1",
            "quality_threshold_reference": "evidence/routing/thresholds-v1",
            "accepted_languages": ["ar", "fr", "en"],
            "acceptance_valid_until": "2026-12-31T23:59:59Z",
        }
        value["map_delivery"] = {
            "renderer": "MAPLIBRE",
            "style_artifact_reference": "artifacts/maps/style-v1",
            "style_version": "morocco-neutral-v1",
            "style_sha256": "1" * 64,
            "tile_source_reference": "providers/maps/tiles-v1",
            "tile_source_version": "2026-09-20",
            "tile_catalog_sha256": "2" * 64,
            "morocco_coverage_reference": "evidence/maps/morocco-coverage-v1",
            "license_review_reference": "evidence/legal/map-license-v1",
            "attribution_review_reference": "evidence/legal/map-attribution-v1",
            "cache_policy_reference": "policies/maps/cache-v1",
            "offline_policy_reference": "policies/maps/offline-v1",
            "privacy_review_reference": "evidence/privacy/map-egress-v1",
            "capacity_and_cost_reference": "evidence/capacity/map-tiles-v1",
            "visual_accessibility_review_reference": "evidence/design/map-neutral-v1",
        }
        value["routing_artifact"] = {
            "selected_provider": "graphhopper",
            "engine_version": "11.0",
            "engine_image_digest": "sha256:" + "3" * 64,
            "morocco_extract_source_reference": "providers/osm/morocco-2026-09-20",
            "morocco_extract_version": "2026-09-20",
            "morocco_extract_sha256": "4" * 64,
            "graph_build_reference": "artifacts/routing/build-006",
            "graph_artifact_digest": "sha256:" + "5" * 64,
            "routing_origin_reference": "environments/production/routing-origin",
            "routing_acceptance_report_reference": "evidence/routing/acceptance-006",
            "routing_acceptance_report_sha256": report_sha,
        }
        value["refresh_and_rollback"] = {
            "graph_refresh_cadence_days": 30,
            "map_refresh_cadence_days": 30,
            "maximum_source_age_days": 60,
            "refresh_runbook_reference": "runbooks/maps/refresh-v1",
            "license_change_review_reference": "runbooks/maps/license-change-v1",
            "traffic_policy_reference": "policies/routing/no-live-traffic-v1",
            "routing_outage_policy_reference": "policies/routing/outage-v1",
            "traffic_data_enabled": False,
            "traffic_data_source_reference": None,
            "previous_graph_digest": "sha256:" + "6" * 64,
            "previous_style_sha256": "7" * 64,
            "rollback_runbook_reference": "runbooks/maps/rollback-v1",
            "rollback_target_reference": "artifacts/maps/previous-accepted",
        }
        for index, row in enumerate(value["benchmark_cases"]):
            row.update(
                {
                    "case_reference": f"cases/routing/{row['category']}",
                    "expected_route_reference": f"evidence/routes/expected-{index + 1}",
                    "result_reference": f"evidence/routes/result-{index + 1}",
                    "status": "PASSED",
                    "maximum_distance_error_percent": 20,
                    "measured_distance_error_percent": 8 + index,
                    "maximum_duration_error_percent": 30,
                    "measured_duration_error_percent": 12 + index,
                    "restricted_road_violations": 0,
                    "executed_at": "2026-10-01T10:00:00Z",
                }
            )
        for index, row in enumerate(value["device_navigation"]):
            row.update(
                {
                    "status": "PASSED",
                    "build_digest": "sha256:" + str(index + 1) * 64,
                    "device_matrix_reference": f"evidence/devices/matrix-{index + 1}",
                    "route_trace_reference": f"evidence/devices/trace-{index + 1}",
                    "narration_reference": f"evidence/devices/narration-{index + 1}",
                    "reroute_reference": f"evidence/devices/reroute-{index + 1}",
                    "degraded_network_reference": f"evidence/devices/network-{index + 1}",
                    "accessibility_reference": f"evidence/devices/accessibility-{index + 1}",
                    "languages": ["ar", "fr", "en"],
                    "tested_at": "2026-10-02T10:00:00Z",
                }
            )
        for index, row in enumerate(value["operational_drills"]):
            row.update(
                {
                    "status": "PASSED",
                    "operator_account_reference": f"operations/accounts/maps-operator-{index % 2 + 1}",
                    "evidence_reference": f"evidence/drills/{row['drill']}",
                    "executed_at": "2026-10-03T10:00:00Z",
                    "recovery_minutes": 15,
                    "review_due_at": "2027-01-31T00:00:00Z",
                }
            )
        for index, row in enumerate(value["approvals"]):
            row.update(
                {
                    "decision": "APPROVED",
                    "reviewer_account_reference": f"operations/accounts/maps-reviewer-{index + 1}",
                    "evidence_reference": f"evidence/approvals/{row['function']}",
                    "decided_at": "2026-10-05T10:00:00Z",
                    "review_due_at": "2027-01-31T00:00:00Z",
                }
            )
        return value, report, report_sha

    def test_committed_template_is_valid_and_unaccepted(self) -> None:
        summary = validate_evidence(self.template)
        self.assertEqual("NOT_STARTED", summary["status"])
        self.assertFalse(summary["gap_006_accepted"])

    def test_require_accepted_rejects_template(self) -> None:
        with self.assertRaisesRegex(MapsRoutingNavigationError, "externally accepted"):
            validate_evidence(self.template, require_accepted=True)

    def test_complete_record_accepts_only_gap_006(self) -> None:
        value, report, digest = self._accepted()
        summary = validate_evidence(
            value,
            routing_report=report,
            routing_report_sha256=digest,
            require_accepted=True,
        )
        self.assertTrue(summary["gap_006_accepted"])
        self.assertFalse(value["phase_accepted"])
        self.assertFalse(value["deployment_accepted"])

    def test_cli_binds_exact_report_file_bytes(self) -> None:
        value, report, _ = self._accepted()
        report_bytes = (json.dumps(report, sort_keys=True) + "\n").encode()
        value["routing_artifact"]["routing_acceptance_report_sha256"] = hashlib.sha256(
            report_bytes
        ).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence_path = root / "evidence.json"
            report_path = root / "routing.json"
            evidence_path.write_text(json.dumps(value), encoding="utf-8")
            report_path.write_bytes(report_bytes)
            output = StringIO()
            with redirect_stdout(output):
                result = main(
                    [
                        "--evidence",
                        str(evidence_path),
                        "--routing-report",
                        str(report_path),
                        "--require-accepted",
                    ]
                )
        self.assertEqual(0, result)
        self.assertIn("status ACCEPTED", output.getvalue())

    def test_accepted_record_requires_exact_routing_report(self) -> None:
        value, _, _ = self._accepted()
        with self.assertRaisesRegex(MapsRoutingNavigationError, "exact routing acceptance report"):
            validate_evidence(value)

    def test_routing_report_hash_mismatch_is_rejected(self) -> None:
        value, report, _ = self._accepted()
        with self.assertRaisesRegex(MapsRoutingNavigationError, "do not match"):
            validate_evidence(value, routing_report=report, routing_report_sha256="0" * 64)

    def test_routing_report_must_match_selected_provider(self) -> None:
        value, report, digest = self._accepted()
        report["provider"] = "valhalla"
        with self.assertRaisesRegex(MapsRoutingNavigationError, "selected provider"):
            validate_evidence(value, routing_report=report, routing_report_sha256=digest)

    def test_routing_report_cannot_hide_arabic_failure(self) -> None:
        value, report, _ = self._accepted()
        report["passed"] = False
        report["checks"][-1].update({"passed": False, "failures": ["provider_language_unsupported"]})
        report["failure_counts"] = {"provider_language_unsupported": 1}
        payload = json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(payload).hexdigest()
        value["routing_artifact"]["routing_acceptance_report_sha256"] = digest
        with self.assertRaisesRegex(MapsRoutingNavigationError, "must pass"):
            validate_evidence(value, routing_report=report, routing_report_sha256=digest)

    def test_every_benchmark_category_is_required(self) -> None:
        value, report, digest = self._accepted()
        value["benchmark_cases"].pop()
        with self.assertRaisesRegex(MapsRoutingNavigationError, "every reviewed item"):
            validate_evidence(value, routing_report=report, routing_report_sha256=digest)

    def test_benchmark_must_stay_within_approved_tolerance(self) -> None:
        value, report, digest = self._accepted()
        value["benchmark_cases"][0]["measured_distance_error_percent"] = 21
        with self.assertRaisesRegex(MapsRoutingNavigationError, "exceeds"):
            validate_evidence(value, routing_report=report, routing_report_sha256=digest)

    def test_benchmark_categories_cannot_reuse_one_result(self) -> None:
        value, report, digest = self._accepted()
        value["benchmark_cases"][1]["result_reference"] = value["benchmark_cases"][0][
            "result_reference"
        ]
        with self.assertRaisesRegex(MapsRoutingNavigationError, "distinct result evidence"):
            validate_evidence(value, routing_report=report, routing_report_sha256=digest)

    def test_restricted_road_violation_is_rejected(self) -> None:
        value, report, digest = self._accepted()
        value["benchmark_cases"][2]["restricted_road_violations"] = 1
        with self.assertRaisesRegex(MapsRoutingNavigationError, "zero restricted-road"):
            validate_evidence(value, routing_report=report, routing_report_sha256=digest)

    def test_every_device_surface_requires_ar_fr_en(self) -> None:
        value, report, digest = self._accepted()
        value["device_navigation"][3]["languages"] = ["fr", "en"]
        with self.assertRaisesRegex(MapsRoutingNavigationError, "exact ar/fr/en"):
            validate_evidence(value, routing_report=report, routing_report_sha256=digest)

    def test_device_surfaces_cannot_reuse_one_trace(self) -> None:
        value, report, digest = self._accepted()
        value["device_navigation"][1]["route_trace_reference"] = value[
            "device_navigation"
        ][0]["route_trace_reference"]
        with self.assertRaisesRegex(MapsRoutingNavigationError, "distinct route trace"):
            validate_evidence(value, routing_report=report, routing_report_sha256=digest)

    def test_map_policy_reference_cannot_be_omitted(self) -> None:
        value, report, digest = self._accepted()
        value["map_delivery"]["attribution_review_reference"] = None
        with self.assertRaisesRegex(MapsRoutingNavigationError, "attribution_review_reference"):
            validate_evidence(value, routing_report=report, routing_report_sha256=digest)

    def test_disabled_traffic_cannot_retain_source_claim(self) -> None:
        value, report, digest = self._accepted()
        value["refresh_and_rollback"]["traffic_data_source_reference"] = "providers/traffic/hidden"
        with self.assertRaisesRegex(MapsRoutingNavigationError, "cannot retain"):
            validate_evidence(value, routing_report=report, routing_report_sha256=digest)

    def test_every_operational_drill_is_required(self) -> None:
        value, report, digest = self._accepted()
        value["operational_drills"].pop(0)
        with self.assertRaisesRegex(MapsRoutingNavigationError, "every reviewed item"):
            validate_evidence(value, routing_report=report, routing_report_sha256=digest)

    def test_operational_drills_cannot_reuse_one_result(self) -> None:
        value, report, digest = self._accepted()
        value["operational_drills"][1]["evidence_reference"] = value[
            "operational_drills"
        ][0]["evidence_reference"]
        with self.assertRaisesRegex(MapsRoutingNavigationError, "distinct evidence"):
            validate_evidence(value, routing_report=report, routing_report_sha256=digest)

    def test_rollback_artifacts_must_be_previous_versions(self) -> None:
        value, report, digest = self._accepted()
        value["refresh_and_rollback"]["previous_graph_digest"] = value[
            "routing_artifact"
        ]["graph_artifact_digest"]
        with self.assertRaisesRegex(MapsRoutingNavigationError, "must differ"):
            validate_evidence(value, routing_report=report, routing_report_sha256=digest)

    def test_drill_review_must_cover_acceptance_window(self) -> None:
        value, report, digest = self._accepted()
        value["operational_drills"][0]["review_due_at"] = "2026-11-01T00:00:00Z"
        with self.assertRaisesRegex(MapsRoutingNavigationError, "does not cover"):
            validate_evidence(value, routing_report=report, routing_report_sha256=digest)

    def test_submitter_cannot_approve_own_evidence(self) -> None:
        value, report, digest = self._accepted()
        value["approvals"][0]["reviewer_account_reference"] = value["submission"][
            "submitted_by_account_reference"
        ]
        with self.assertRaisesRegex(MapsRoutingNavigationError, "must differ"):
            validate_evidence(value, routing_report=report, routing_report_sha256=digest)

    def test_acceptance_requires_three_independent_reviewers(self) -> None:
        value, report, digest = self._accepted()
        for row in value["approvals"]:
            row["reviewer_account_reference"] = "operations/accounts/maps-reviewer-one"
        with self.assertRaisesRegex(MapsRoutingNavigationError, "three independent"):
            validate_evidence(value, routing_report=report, routing_report_sha256=digest)

    def test_secret_bearing_fields_are_rejected(self) -> None:
        value, report, digest = self._accepted()
        value["submission"]["api_key"] = "forbidden"
        with self.assertRaisesRegex(MapsRoutingNavigationError, "forbidden key"):
            validate_evidence(value, routing_report=report, routing_report_sha256=digest)

    def test_phase_acceptance_cannot_be_claimed(self) -> None:
        value, report, digest = self._accepted()
        value["phase_accepted"] = True
        with self.assertRaisesRegex(MapsRoutingNavigationError, "cannot accept"):
            validate_evidence(value, routing_report=report, routing_report_sha256=digest)


if __name__ == "__main__":
    unittest.main()
