from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest


SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from validate_production_environment_inventory import (
    DEFAULT_INVENTORY,
    ProductionEnvironmentInventoryError,
    validate_inventory,
)


class ProductionEnvironmentInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.template = json.loads(DEFAULT_INVENTORY.read_text(encoding="utf-8"))

    def _accepted_inventory(self) -> dict:
        value = copy.deepcopy(self.template)
        value.update(
            {
                "status": "ACCEPTED",
                "candidate_label": "production-candidate-2026-09-28",
                "source_commit": "b" * 40,
                "gap_002_accepted": True,
                "limitations": ["NO_PHASE_OR_DEPLOYMENT_ACCEPTANCE"],
            }
        )
        value["target"] = {
            "provider_name": "Example Hosting",
            "region_code": "ma-reviewed-1",
            "jurisdiction_code": "MA",
            "architecture_approval_reference": "evidence/architecture/ADR-002",
            "data_region_approval_reference": "evidence/privacy/REGION-002",
            "service_owner_role": "PLATFORM_OPERATIONS",
            "cost_owner_reference": "evidence/cost/COST-002",
            "monthly_cost_limit": 5000,
            "currency": "MAD",
        }
        for index, environment in enumerate(value["environments"]):
            name = environment["name"]
            environment.update(
                {
                    "account_reference": f"provider/accounts/{name}-{index}",
                    "network_reference": f"provider/networks/{name}-{index}",
                    "secret_scope_reference": f"provider/secret-scopes/{name}-{index}",
                    "database_reference": f"provider/databases/{name}-{index}",
                    "isolated": True,
                }
            )
        endpoint_origins = {
            "API_ORIGIN": "https://api.example.ma",
            "APPLICANT_WEB_ORIGIN": "https://apply.example.ma",
            "OPERATIONS_WEB_ORIGIN": "https://operations.example.ma",
            "LIVE_EVENTS_ORIGIN": "wss://api.example.ma",
        }
        for endpoint in value["public_endpoints"]:
            endpoint.update(
                {
                    "origin": endpoint_origins[endpoint["name"]],
                    "dns_evidence_reference": f"evidence/dns/{endpoint['name']}",
                    "tls_scan_evidence_reference": f"evidence/tls/{endpoint['name']}",
                }
            )
        value["application_policy"] = {
            "allowed_hosts": ["api.example.ma"],
            "cors_origins": ["https://apply.example.ma", "https://operations.example.ma"],
            "trusted_proxy_review_reference": "evidence/network/TRUSTED-PROXIES",
        }
        backend_image = "registry.example.ma/taximobile/backend@sha256:" + "a" * 64
        scanner_image = "registry.example.ma/taximobile/scanner@sha256:" + "c" * 64
        for service in value["services"]:
            name = service["name"]
            if name in {"API", "WORKER", "MIGRATOR"}:
                model, artifact = "CONTAINER_IMAGE", backend_image
            elif name == "SCANNER":
                model, artifact = "CONTAINER_IMAGE", scanner_image
            elif name in {"APPLICANT_WEB", "OPERATIONS_WEB"}:
                model, artifact = "STATIC_ARTIFACT", f"evidence/web/{name}-manifest"
            else:
                model, artifact = "MANAGED_SERVICE", f"evidence/services/{name}-version"
            service.update(
                {
                    "delivery_model": model,
                    "artifact_reference": artifact,
                    "service_reference": f"provider/services/{name}",
                    "owner_role": "PLATFORM_OPERATIONS",
                    "network_policy_reference": f"evidence/network/{name}",
                }
            )
        value["network"].update(
            {
                "ingress_policy_reference": "evidence/network/INGRESS",
                "egress_policy_reference": "evidence/network/EGRESS",
                "iam_review_reference": "evidence/security/IAM-REVIEW",
            }
        )
        value["secrets"].update(
            {
                "manager_reference": "provider/services/SECRET_MANAGER",
                "secret_inventory_reference": "evidence/secrets/INVENTORY",
                "rotation_evidence_reference": "evidence/secrets/ROTATION",
                "rotation_completed_at": "2026-09-28T12:00:00Z",
            }
        )
        value["recovery"] = {
            "staging_deployment_reference": "evidence/deploy/STAGING",
            "production_change_reference": "evidence/change/PRODUCTION",
            "migration_record_reference": "evidence/migrations/0052",
            "rollback_rehearsal_reference": "evidence/recovery/ROLLBACK",
            "forward_fix_reference": "evidence/recovery/FORWARD-FIX",
            "measured_rollback_seconds": 600,
            "approved_rto_seconds": 900,
        }
        for approval in value["approvals"]:
            approval.update(
                {
                    "decision": "APPROVED",
                    "evidence_reference": f"evidence/approvals/{approval['function']}",
                    "decided_at": "2026-09-28T13:00:00Z",
                }
            )
        return value

    def test_committed_template_is_valid_and_unaccepted(self) -> None:
        summary = validate_inventory(self.template)
        self.assertEqual("NOT_STARTED", summary["status"])
        self.assertFalse(summary["gap_002_accepted"])
        self.assertFalse(self.template["phase_accepted"])
        self.assertFalse(self.template["deployment_accepted"])

    def test_require_accepted_rejects_template(self) -> None:
        with self.assertRaisesRegex(ProductionEnvironmentInventoryError, "externally accepted"):
            validate_inventory(self.template, require_accepted=True)

    def test_not_started_inventory_cannot_hide_provider_claims(self) -> None:
        inventory = copy.deepcopy(self.template)
        inventory["target"]["provider_name"] = "Example Hosting"
        with self.assertRaisesRegex(ProductionEnvironmentInventoryError, "provider claims"):
            validate_inventory(inventory)

    def test_complete_inventory_accepts_only_gap_002(self) -> None:
        inventory = self._accepted_inventory()
        summary = validate_inventory(inventory, require_accepted=True)
        self.assertTrue(summary["gap_002_accepted"])
        self.assertFalse(inventory["phase_accepted"])
        self.assertFalse(inventory["deployment_accepted"])

    def test_mutable_container_image_is_rejected(self) -> None:
        inventory = self._accepted_inventory()
        api = next(service for service in inventory["services"] if service["name"] == "API")
        api["artifact_reference"] = "registry.example.ma/taximobile/backend:latest"
        with self.assertRaisesRegex(ProductionEnvironmentInventoryError, "immutable sha256"):
            validate_inventory(inventory)

    def test_private_service_cannot_be_exposed(self) -> None:
        inventory = self._accepted_inventory()
        worker = next(service for service in inventory["services"] if service["name"] == "WORKER")
        worker["exposure"] = "PUBLIC_HTTPS"
        with self.assertRaisesRegex(ProductionEnvironmentInventoryError, "exposure must remain PRIVATE"):
            validate_inventory(inventory)

    def test_environment_boundaries_must_be_distinct(self) -> None:
        inventory = self._accepted_inventory()
        inventory["environments"][1]["account_reference"] = inventory["environments"][0][
            "account_reference"
        ]
        with self.assertRaisesRegex(ProductionEnvironmentInventoryError, "must be distinct"):
            validate_inventory(inventory)

    def test_rollback_must_meet_approved_rto(self) -> None:
        inventory = self._accepted_inventory()
        inventory["recovery"]["measured_rollback_seconds"] = 901
        with self.assertRaisesRegex(ProductionEnvironmentInventoryError, "exceeds the approved RTO"):
            validate_inventory(inventory)

    def test_malformed_origin_fails_without_parser_traceback(self) -> None:
        inventory = self._accepted_inventory()
        inventory["public_endpoints"][0]["origin"] = "https://api.example.ma:not-a-port"
        with self.assertRaisesRegex(ProductionEnvironmentInventoryError, "well-formed"):
            validate_inventory(inventory)

    def test_non_finite_cost_limit_is_rejected(self) -> None:
        inventory = self._accepted_inventory()
        inventory["target"]["monthly_cost_limit"] = float("nan")
        with self.assertRaisesRegex(ProductionEnvironmentInventoryError, "positive number"):
            validate_inventory(inventory)


if __name__ == "__main__":
    unittest.main()
