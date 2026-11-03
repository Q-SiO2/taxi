"""Launcher confinement/ownership checks; Windows ACL tests need native Windows."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[3]
HELPER = ROOT / "infra/scripts/_union-demo-common.ps1"
PWSH = shutil.which("pwsh")


def ps_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


@unittest.skipUnless(PWSH and os.name == "nt", "Native Windows PowerShell is required.")
class UnionDemoLauncherTests(unittest.TestCase):
    def run_ps(self, script):
        return subprocess.run(
            [PWSH, "-NoProfile", "-NonInteractive", "-Command",
             f". {ps_literal(HELPER)}; {script}"],
            capture_output=True, text=True, timeout=30,
        )

    def test_invalid_ids_refuse_before_accessing_database(self):
        for demo_id in ("../other", "main", "A" * 32, "a" * 31, "a" * 33):
            with self.subTest(demo_id=demo_id):
                result = self.run_ps(
                    f"Resolve-UnionDemoRoot -Layout @{{WorkspaceRoot={ps_literal(ROOT)}}} "
                    f"-DemoId {ps_literal(demo_id)}"
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("DemoId must", result.stderr)

    def test_valid_id_is_confined_to_ignored_workspace_runtime(self):
        demo_id = uuid4().hex
        result = self.run_ps(
            f"Resolve-UnionDemoRoot -Layout @{{WorkspaceRoot={ps_literal(ROOT)}}} "
            f"-DemoId '{demo_id}'"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()), ROOT / ".tools/union-demo" / demo_id)

    def test_junction_ancestor_is_rejected(self):
        with tempfile.TemporaryDirectory() as task_root, tempfile.TemporaryDirectory() as elsewhere:
            tools = Path(task_root) / ".tools"
            result = self.run_ps(
                f"New-Item -ItemType Junction -Path {ps_literal(tools)} "
                f"-Target {ps_literal(elsewhere)} | Out-Null; "
                f"Resolve-UnionDemoRoot -Layout @{{WorkspaceRoot={ps_literal(task_root)}}} "
                f"-DemoId '{uuid4().hex}'"
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not links", result.stderr)

    def test_directory_acl_limits_reader_to_current_account(self):
        with tempfile.TemporaryDirectory() as task_root:
            result = self.run_ps(
                f"Protect-UnionDemoRoot -Root {ps_literal(task_root)}; "
                f"$acl = Get-Acl -LiteralPath {ps_literal(task_root)}; "
                "[pscustomobject]@{protected=$acl.AreAccessRulesProtected;"
                "allows=@($acl.Access | Where-Object AccessControlType -eq Allow).Count} | ConvertTo-Json"
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {"protected": True, "allows": 1})

    def test_state_cannot_retarget_an_application_database(self):
        with tempfile.TemporaryDirectory() as task_root:
            demo_id = uuid4().hex
            directory = Path(task_root) / ".tools/union-demo" / demo_id
            directory.mkdir(parents=True)
            record = {
                "schema": 1, "demoId": demo_id, "database": "taximobile",
                "apiPort": 8000, "databasePort": 5432, "jwtSecret": uuid4().hex * 2,
            }
            (directory / "state.json").write_text(json.dumps(record), encoding="utf-8")
            result = self.run_ps(
                f"Read-UnionDemoState -Layout @{{WorkspaceRoot={ps_literal(task_root)}}} "
                f"-DemoId '{demo_id}'"
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not a valid isolated", result.stderr)

    def test_process_ownership_rejects_an_unrelated_live_pid(self):
        result = self.run_ps(
            f"Get-UnionDemoApiProcess -Layout @{{BackendRoot={ps_literal(ROOT / 'backend')}}} "
            "-State ([pscustomobject]@{api=[pscustomobject]@{pid=$PID;"
            "executable='unrelated';startTimeUtcTicks=1}})"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not match", result.stderr)

    def test_unconfirmed_start_fails_before_runtime_mutation(self):
        result = subprocess.run(
            [PWSH, "-NoProfile", "-NonInteractive", "-File",
             str(ROOT / "infra/scripts/start-union-demo.ps1")],
            capture_output=True, text=True, timeout=30,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ConfirmSyntheticDemo", result.stderr)


if __name__ == "__main__":
    unittest.main()
