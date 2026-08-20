import importlib.util
from pathlib import Path
import sys
import unittest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "android_registration_smoke.py"
RUNNER_PATH = Path(__file__).resolve().parents[1] / "run-android-device.ps1"
SPEC = importlib.util.spec_from_file_location("android_registration_smoke", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
SMOKE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SMOKE
SPEC.loader.exec_module(SMOKE)


class AndroidRegistrationSmokeTest(unittest.TestCase):
    def test_launcher_guards_debug_data_and_requires_backend_readiness(self) -> None:
        runner = RUNNER_PATH.read_text(encoding="utf-8")

        self.assertIn('"http://127.0.0.1:$ApiPort/ready"', runner)
        self.assertNotIn('$healthUrl =', runner)
        guard = runner.index("if ($RegistrationSmoke -and -not $ConfirmClearAppData)")
        clear = runner.index("Invoke-CheckedCommand $adb shell pm clear $packageName")
        self.assertLess(guard, clear)
        self.assertIn('"-PtaximobileDebugApiBaseUrl=$apiBaseUrl"', runner)
        self.assertIn('"android_registration_smoke.py"', runner)

    def test_localization_catalog_contains_every_acceptance_state(self) -> None:
        values = SMOKE.load_localized_values()

        for key in (
            "create_account",
            "display_name",
            "email_optional",
            "password",
            "sign_in",
            "message_account_created",
            "message_network_unavailable",
            "where_to",
            "apply_to_drive",
        ):
            self.assertGreaterEqual(len(values[key]), 3)

    def test_hierarchy_parser_ignores_tool_prefix_and_selects_bottom_action(self) -> None:
        raw = b"warning\n<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>\n" + (
            b"<hierarchy rotation='0'>"
            b"<node text='Create account' enabled='true' bounds='[10,20][200,80]' />"
            b"<node text='Create account' enabled='true' bounds='[10,700][500,780]' />"
            b"</hierarchy>\nUI hierarchy dumped"
        )
        hierarchy = SMOKE.extract_hierarchy(raw)
        matches = SMOKE.matching_bounds(hierarchy, {"Create account"}, enabled_only=True)

        self.assertEqual(2, len(matches))
        self.assertEqual((255, 740), max(matches, key=lambda item: item.top).center)

    def test_adb_input_is_restricted_to_non_shell_synthetic_values(self) -> None:
        self.assertEqual("DeviceSmoke2026", SMOKE.encode_adb_input("DeviceSmoke2026"))
        self.assertEqual(
            "android-smoke@example.test",
            SMOKE.encode_adb_input("android-smoke@example.test"),
        )
        for invalid in ("contains space", "secret;command", "$(command)", "quote'input"):
            with self.assertRaises(ValueError):
                SMOKE.encode_adb_input(invalid)

        source = SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertNotIn("/sdcard", source)


if __name__ == "__main__":
    unittest.main()
