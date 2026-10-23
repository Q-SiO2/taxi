"""Native rehearsal boundaries, without importing maps or launching servers."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[3]
PWSH = shutil.which("pwsh")
HELPER = ROOT / "infra/scripts/_union-routing-common.ps1"


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


@unittest.skipUnless(PWSH and os.name == "nt", "Native Windows PowerShell required.")
class UnionRoutingTests(unittest.TestCase):
    def run_ps(self, script):
        return subprocess.run(
            [PWSH, "-NoProfile", "-NonInteractive", "-Command",
             f". {literal(HELPER)}; {script}"],
            text=True, capture_output=True, timeout=30,
        )

    def test_native_configuration_preserves_engine_and_confines_both_sockets(self):
        path = ROOT / "infra/routing/graphhopper/config.yml"
        result = self.run_ps(f"ConvertTo-UnionRoutingConfig -Source (Get-Content -Raw {literal(path)})")
        self.assertEqual(result.returncode, 0, result.stderr)
        native = yaml.safe_load(result.stdout)
        original = yaml.safe_load(path.read_text())
        self.assertEqual(native["graphhopper"], original["graphhopper"])
        self.assertEqual(native["logging"], original["logging"])
        for key, port in (("application_connectors", 8002), ("admin_connectors", 8003)):
            self.assertEqual(native["server"][key][0]["bind_host"], "127.0.0.1")
            self.assertEqual(native["server"][key][0]["port"], port)
        self.assertEqual(native["server"]["request_log"], {"appenders": []})

    def test_unknown_or_duplicated_socket_configuration_fails_closed(self):
        for source in ("unexpected", "port: 8989\nport: 8989\nport: 8990\nbind_host: 0.0.0.0"):
            result = self.run_ps(f"ConvertTo-UnionRoutingConfig -Source {literal(source)}")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("configuration changed", result.stderr)

    def test_inputs_cannot_escape_demo_routing_directory(self):
        with tempfile.TemporaryDirectory() as task_root:
            root = Path(task_root) / "routing"
            root.mkdir()
            outside = Path(task_root) / "outside.jar"
            outside.write_bytes(b"test")
            result = self.run_ps(f"Resolve-UnionRoutingFile -Root {literal(root)} -Path {literal(outside)}")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("inside this demo", result.stderr)

    def test_input_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as task_root:
            root = Path(task_root)
            real = root / "real"
            real.mkdir()
            (real / "map.pbf").write_bytes(b"test")
            link = root / "link"
            result = self.run_ps(
                f"New-Item -ItemType Junction -Path {literal(link)} -Target {literal(real)} | Out-Null; "
                f"Resolve-UnionRoutingFile -Root {literal(root)} -Path {literal(link / 'map.pbf')}"
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not contain links", result.stderr)

    def test_live_pid_is_not_adopted_without_ownership(self):
        result = self.run_ps(
            "Get-UnionRoutingProcess -State ([pscustomobject]@{pid=$PID;"
            "executable='unrelated';startTimeUtcTicks=1})"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ownership changed", result.stderr)

    def test_missing_provider_record_means_legacy_valhalla(self):
        result = self.run_ps("Resolve-UnionDemoRoutingProvider -State ([pscustomobject]@{}) -HasLiveApi $true")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "valhalla")

    def test_resume_preserves_explicit_selection(self):
        result = self.run_ps(
            "Resolve-UnionDemoRoutingProvider -State ([pscustomobject]@{routingProvider='graphhopper'}) -HasLiveApi $true"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "graphhopper")

    def test_live_api_cannot_be_retargeted(self):
        result = self.run_ps(
            "Resolve-UnionDemoRoutingProvider -State ([pscustomobject]@{}) -Requested graphhopper -HasLiveApi $true"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Stop this exact demo API", result.stderr)

    def test_stopped_api_allows_deliberate_selection(self):
        result = self.run_ps(
            "Resolve-UnionDemoRoutingProvider -State ([pscustomobject]@{}) -Requested graphhopper -HasLiveApi $false"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "graphhopper")

    def test_unknown_record_refused(self):
        result = self.run_ps(
            "Resolve-UnionDemoRoutingProvider -State ([pscustomobject]@{routingProvider='other'}) -HasLiveApi $false"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid recorded", result.stderr)

    def test_native_jar_pin_matches_docker(self):
        import re
        script = (ROOT / "infra/scripts/start-union-routing.ps1").read_text()
        digest = re.search(r'\$jarDigest -ne "([0-9a-f]{64})"', script).group(1)
        self.assertIn(digest, (ROOT / "infra/routing/graphhopper/Dockerfile").read_text())


if __name__ == "__main__":
    unittest.main()
