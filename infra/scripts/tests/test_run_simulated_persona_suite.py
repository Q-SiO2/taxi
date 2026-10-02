from __future__ import annotations

import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import run_simulated_persona_suite
import t2_no_network
from run_simulated_persona_suite import (
    BACKEND_ROOT,
    DEFAULT_CATALOG,
    SimulatedPersonaError,
    junit_summary,
    load_and_validate_catalog,
    run_suite,
)


class SimulatedPersonaSuiteTests(unittest.TestCase):
    def _changed_catalog(self, root: Path, mutate) -> Path:
        catalog = json.loads(DEFAULT_CATALOG.read_text(encoding="utf-8"))
        mutate(catalog)
        output = root / "catalog.json"
        output.write_text(json.dumps(catalog), encoding="utf-8")
        return output

    def test_committed_catalog_has_exact_category_and_selector_coverage(self) -> None:
        catalog = load_and_validate_catalog(DEFAULT_CATALOG)
        selectors = [item for scenario in catalog["scenarios"] for item in scenario["selectors"]]
        self.assertEqual(20, len(catalog["scenarios"]))
        self.assertEqual(66, len(selectors))
        self.assertEqual(66, len(set(selectors)))

    def test_notification_personas_include_ongoing_session_authority(self) -> None:
        catalog = load_and_validate_catalog(DEFAULT_CATALOG)
        scenario = next(item for item in catalog["scenarios"] if item["id"] == "SIM-NOTIFY-001")
        self.assertTrue({
            "SESSION_REVOCATION_IS_ISOLATED", "IDLE_AUTHORITY_IS_RECHECKED",
            "JWT_DEADLINE_IS_ENFORCED", "AUTHORITY_OUTAGE_FAILS_CLOSED",
            "EACH_HINT_IS_REAUTHORIZED", "OBSOLETE_OWNER_CANNOT_SEND",
        }.issubset(scenario["invariants"]))
        self.assertEqual(6, sum("test_realtime.py::" in node for node in scenario["selectors"]))

    def test_validate_only_never_requires_or_writes_run_evidence(self) -> None:
        self.assertEqual(0, run_simulated_persona_suite.main(["--validate-only"]))

    def test_network_guard_recognizes_only_literal_loopback_hosts(self) -> None:
        self.assertTrue(t2_no_network._literal_loopback("127.0.0.1"))
        self.assertTrue(t2_no_network._literal_loopback("::1"))
        self.assertFalse(t2_no_network._literal_loopback("localhost"))
        self.assertFalse(t2_no_network._literal_loopback("192.0.2.1"))

    def test_network_guard_denies_dns_and_non_loopback_socket_connect(self) -> None:
        t2_no_network.pytest_sessionstart(None)
        try:
            with self.assertRaisesRegex(OSError, "forbids network access"):
                socket.getaddrinfo("example.invalid", 443)
            with socket.socket() as outbound:
                with self.assertRaisesRegex(OSError, "forbids network access"):
                    outbound.connect(("192.0.2.1", 443))
        finally:
            t2_no_network.pytest_sessionfinish(None, 0)

    def test_catalog_cannot_enable_external_or_real_activity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._changed_catalog(
                Path(directory),
                lambda catalog: catalog["safety"].update({"live_money_allowed": True}),
            )
            with self.assertRaisesRegex(SimulatedPersonaError, "cannot enable external or real"):
                load_and_validate_catalog(path)

    def test_catalog_cannot_drop_a_required_persona_category(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._changed_catalog(
                Path(directory),
                lambda catalog: catalog["scenarios"].pop(),
            )
            with self.assertRaisesRegex(SimulatedPersonaError, "every required category"):
                load_and_validate_catalog(path)

    def test_runner_report_never_claims_phase_or_deployment_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "report.json"
            junit = root / "report.junit.xml"

            def fake_pytest(command, **_kwargs):
                junit_argument = next(item for item in command if item.startswith("--junitxml="))
                junit_path = Path(junit_argument.split("=", 1)[1])
                junit_path.write_text(
                    '<testsuite tests="66" failures="0" errors="0" skipped="0"/>',
                    encoding="utf-8",
                )
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

            with patch.object(run_simulated_persona_suite.subprocess, "run", fake_pytest):
                report, return_code = run_suite(
                    catalog_path=DEFAULT_CATALOG,
                    output_path=output,
                    junit_path=junit,
                    backend_root=BACKEND_ROOT,
                )

            self.assertEqual(0, return_code)
            self.assertEqual("PASS", report["result"])
            self.assertFalse(report["phase_accepted"])
            self.assertFalse(report["phase_evidence_complete"])
            self.assertFalse(report["deployment_accepted"])
            self.assertEqual(66, junit_summary(junit)["tests"])


if __name__ == "__main__":
    unittest.main()
