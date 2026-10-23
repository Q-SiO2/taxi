"""Native launcher control-flow tests; no database process or data is touched."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[3]
HELPER = ROOT / "infra/scripts/_portable-common.ps1"
PWSH = shutil.which("pwsh")


@unittest.skipUnless(PWSH and os.name == "nt", "Native Windows PowerShell is required.")
class PortablePostgresStartupTests(unittest.TestCase):
    def run_case(self, probe_code, exited=False):
        helper = str(HELPER).replace("'", "''")
        # Dependency fakes execute the real function, not a copied timeout branch.
        script = f"""
. '{helper}'
$global:started = 0; $global:stopped = 0; $global:clockReads = 0
$global:ownedRunning = $false
$global:fakeServer = [pscustomobject]@{{HasExited=${str(exited).lower()};Id=12345}}
$global:fakeServer | Add-Member ScriptMethod Refresh {{ }}
function Test-PortablePostgresRunning {{ param($Layout) return $global:ownedRunning }}
function Join-Path {{ param($Path,$ChildPath) if ($ChildPath -eq 'bin\\pg_isready.exe') {{ 'Test-ReadinessProbe' }} else {{ 'synthetic-placeholder' }} }}
function New-Item {{ param($ItemType,[switch]$Force,$Path) }}
function Start-Process {{ param($FilePath,$ArgumentList,$WindowStyle,$RedirectStandardOutput,$RedirectStandardError,[switch]$PassThru) $global:started++; return $global:fakeServer }}
function Stop-Process {{ param($Id) $global:stopped++; $global:fakeServer.HasExited=$true }}
function Start-Sleep {{ param($Milliseconds) }}
function Get-Date {{ $global:clockReads++; return [datetime]'2026-10-04T12:00:00Z' + [timespan]::FromSeconds($global:clockReads * 31) }}
function Test-ReadinessProbe {{ {probe_code} }}
$failure = $null; $result = $null
try {{ $result = Start-PortablePostgres -Layout @{{PostgreSqlRoot='synthetic';DataRoot='synthetic';LogRoot='synthetic'}} -Port 5432 -WaitSeconds 30 }} catch {{ $failure=$_.Exception.Message }}
[pscustomobject]@{{started=$global:started;stopped=$global:stopped;stillLive=-not $global:fakeServer.HasExited;failure=$failure;result=$result}} | ConvertTo-Json -Compress
"""
        result = subprocess.run([PWSH, "-NoProfile", "-NonInteractive", "-Command", script],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(0, result.returncode, result.stderr)
        return json.loads(result.stdout)

    def test_slow_recovery_is_not_killed_or_replaced_on_observation_timeout(self):
        result = self.run_case("$global:LASTEXITCODE=1")
        self.assertEqual(1, result["started"])
        self.assertEqual(0, result["stopped"])
        self.assertTrue(result["stillLive"])
        self.assertIn("observation timed out", result["failure"])
        self.assertIn("Do not start a second server", result["failure"])

    def test_ready_owned_server_completes_without_stop(self):
        result = self.run_case("$global:LASTEXITCODE=0; $global:ownedRunning=$true")
        self.assertTrue(result["result"])
        self.assertIsNone(result["failure"])
        self.assertEqual(0, result["stopped"])

    def test_terminal_startup_exit_is_reported_as_exit_not_timeout(self):
        result = self.run_case("throw 'Probe must not run after terminal exit'", exited=True)
        self.assertFalse(result["stillLive"])
        self.assertIn("exited during startup", result["failure"])
        self.assertEqual(0, result["stopped"])


if __name__ == "__main__":
    unittest.main()
