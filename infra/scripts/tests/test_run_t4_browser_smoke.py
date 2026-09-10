from __future__ import annotations

import copy
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_t4_browser_smoke import (
    BrowserInstallation,
    BrowserSmokeError,
    SCENARIOS,
    _browser_command,
    _browser_version,
    _firefox_screenshot_command,
    _png_metadata,
    evaluate_scenario,
    network_boundary_observed,
)


def _png(width: int = 1280, height: int = 900) -> bytes:
    # The collector only needs a valid PNG signature and IHDR dimensions; the
    # browser creates complete images in real executions.
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", width, height)


class T4BrowserSmokeTests(unittest.TestCase):
    def _screenshot(self, root: Path) -> Path:
        path = root / "smoke.png"
        path.write_bytes(_png())
        return path

    def _requests(self, scenario) -> list[dict]:
        requests = [
            {"path": scenario.route},
            {"path": "/compatibility.js"},
            {
                "path": "/api/v1/client-compatibility",
                "client_surface": scenario.expected_surface,
                "client_version": "1.0.0",
                "client_build": "1",
            },
        ]
        if scenario.expect_application_boot:
            requests.extend([{"path": "/webApp.js"}, {"path": "/originWasmWebApp.js"}])
        return requests

    def test_scenario_map_is_bounded_and_contains_both_surfaces(self) -> None:
        self.assertEqual(4, len(SCENARIOS))
        self.assertEqual({"WEB_APPLICANT", "WEB_OPERATIONS"}, {item.expected_surface for item in SCENARIOS})
        self.assertEqual(2, sum(item.expect_application_boot for item in SCENARIOS))

    def test_supported_browser_boot_passes_with_exact_identity_and_one_branch(self) -> None:
        scenario = SCENARIOS[0]
        with tempfile.TemporaryDirectory() as directory:
            result = evaluate_scenario(
                scenario,
                self._requests(scenario),
                {"return_code": 0, "timed_out": False},
                self._screenshot(Path(directory)),
            )
        self.assertEqual("PASS", result["status"])
        self.assertEqual("/originWasmWebApp.js", result["runtime_branch"])
        self.assertTrue(result["observations"]["client_identity_headers_match"])

    def test_blocked_preflight_passes_only_without_application_assets(self) -> None:
        scenario = SCENARIOS[-1]
        with tempfile.TemporaryDirectory() as directory:
            result = evaluate_scenario(
                scenario,
                self._requests(scenario),
                {"return_code": 0, "timed_out": False},
                self._screenshot(Path(directory)),
            )
        self.assertEqual("PASS", result["status"])
        self.assertTrue(result["observations"]["application_remained_blocked"])

    def test_cross_surface_identity_fails(self) -> None:
        scenario = SCENARIOS[0]
        requests = self._requests(scenario)
        requests[2] = {**requests[2], "client_surface": "WEB_OPERATIONS"}
        with tempfile.TemporaryDirectory() as directory:
            result = evaluate_scenario(
                scenario,
                requests,
                {"return_code": 0, "timed_out": False},
                self._screenshot(Path(directory)),
            )
        self.assertEqual("FAIL", result["status"])
        self.assertFalse(result["observations"]["client_identity_headers_match"])

    def test_two_runtime_branches_fail(self) -> None:
        scenario = SCENARIOS[1]
        requests = self._requests(scenario) + [{"path": "/originJsWebApp.js"}]
        with tempfile.TemporaryDirectory() as directory:
            result = evaluate_scenario(
                scenario,
                requests,
                {"return_code": 0, "timed_out": False},
                self._screenshot(Path(directory)),
            )
        self.assertEqual("FAIL", result["status"])

    def test_missing_screenshot_fails_even_when_network_boundary_passes(self) -> None:
        scenario = SCENARIOS[0]
        with tempfile.TemporaryDirectory() as directory:
            result = evaluate_scenario(
                scenario,
                self._requests(scenario),
                {"return_code": 0, "timed_out": False},
                Path(directory) / "missing.png",
            )
        self.assertEqual("FAIL", result["status"])
        self.assertFalse(result["observations"]["screenshot_retained"])
        self.assertEqual("SCREENSHOT_NOT_RETAINED_OR_INVALID", result["screenshot_error"])

    def test_screenshot_dimensions_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._screenshot(Path(directory))
            record = _png_metadata(path)
            self.assertEqual(1280, record["width"])
            self.assertEqual(900, record["height"])
            self.assertEqual(64, len(record["sha256"]))

    def test_tiny_or_invalid_screenshot_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.png"
            path.write_bytes(_png(100, 100))
            with self.assertRaisesRegex(BrowserSmokeError, "unexpectedly small"):
                _png_metadata(path)

    def test_network_probe_waits_for_runtime_branch_on_supported_boot(self) -> None:
        scenario = SCENARIOS[0]
        requests = self._requests(scenario)
        self.assertTrue(network_boundary_observed(scenario, requests))
        self.assertFalse(network_boundary_observed(scenario, requests[:-1]))

    def test_network_probe_allows_blocked_preflight_then_settle_interval(self) -> None:
        scenario = SCENARIOS[-1]
        self.assertTrue(network_boundary_observed(scenario, self._requests(scenario)))

    def test_commands_use_isolated_profiles_without_exposing_credentials(self) -> None:
        installation = BrowserInstallation("CHROME", Path("chrome"), "1")
        command = _browser_command(
            installation,
            profile=Path("isolated-profile"),
            screenshot=Path("result.png"),
            url="http://127.0.0.1:8000/apply",
            virtual_time_ms=10_000,
        )
        joined = " ".join(str(item) for item in command)
        self.assertIn("--headless=new", joined)
        self.assertIn("isolated-profile", joined)
        self.assertIn(str(Path("result.png").resolve()), joined)
        self.assertNotIn("password", joined.casefold())
        self.assertNotIn("token", joined.casefold())

    def test_firefox_uses_persistent_observation_then_separate_screenshot(self) -> None:
        installation = BrowserInstallation("FIREFOX", Path("firefox"), "1")
        screenshot = Path("firefox-result.png")
        observation_command = _browser_command(
            installation,
            profile=Path("isolated-firefox-profile"),
            screenshot=screenshot,
            url="http://127.0.0.1:8000/operations",
            virtual_time_ms=10_000,
        )
        screenshot_command = _firefox_screenshot_command(
            installation,
            profile=Path("isolated-firefox-profile"),
            screenshot=screenshot,
            url="http://127.0.0.1:8000/operations",
        )
        self.assertIn("--headless", observation_command)
        self.assertNotIn("--screenshot", observation_command)
        self.assertIn("--screenshot", screenshot_command)
        self.assertIn(str(screenshot.resolve()), screenshot_command)
        self.assertIn(
            "isolated-firefox-profile",
            " ".join(str(item) for item in screenshot_command),
        )

    @patch("run_t4_browser_smoke.os.name", "nt")
    @patch("run_t4_browser_smoke.subprocess.run")
    def test_windows_version_lookup_uses_environment_not_command_arguments(self, run) -> None:
        run.return_value.returncode = 0
        run.return_value.stdout = "152.0.1\n"
        run.return_value.stderr = ""
        executable = Path("C:/Program Files/Browser/browser.exe")
        version = _browser_version(executable)
        self.assertEqual("152.0.1", version)
        command = run.call_args.args[0]
        environment = run.call_args.kwargs["env"]
        self.assertNotIn(str(executable), command)
        self.assertEqual(
            str(executable),
            environment["TAXIMOBILE_BROWSER_VERSION_PATH"],
        )


if __name__ == "__main__":
    unittest.main()
