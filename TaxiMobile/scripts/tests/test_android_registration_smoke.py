import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from unittest.mock import Mock


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
        self.assertIn('"--output", $resolvedEvidencePath', runner)
        self.assertIn("EvidencePath requires RegistrationSmoke", runner)

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
            "driver_onboarding_title",
            "recruiting_cities",
            "use_current_location_pickup",
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

    def test_matching_does_not_tap_child_outside_scroll_viewport(self) -> None:
        hierarchy = SMOKE.extract_hierarchy(
            b"<?xml version='1.0'?><hierarchy>"
            b"<node class='android.widget.ScrollView' bounds='[0,1728][1080,2337]'>"
            b"<node text='Pickup latitude' enabled='true' bounds='[63,2334][1017,2400]'/>"
            b"</node></hierarchy>"
        )
        self.assertEqual([], SMOKE.matching_bounds(hierarchy, {"Pickup latitude"}, enabled_only=True))

    def test_matching_keeps_visible_child_and_ignores_unbounded_root(self) -> None:
        hierarchy = SMOKE.extract_hierarchy(
            b"<?xml version='1.0'?><hierarchy><node bounds='[0,0][0,0]'>"
            b"<node class='android.widget.ScrollView' bounds='[0,1728][1080,2337]'>"
            b"<node text='Pickup latitude' enabled='true' bounds='[63,2000][1017,2180]'/>"
            b"</node></node></hierarchy>"
        )
        self.assertEqual([SMOKE.Bounds(63, 2000, 1017, 2180)],
                         SMOKE.matching_bounds(hierarchy, {"Pickup latitude"}, enabled_only=True))

    def test_clamped_floating_label_cannot_hide_clipped_editable_parent(self) -> None:
        hierarchy = SMOKE.extract_hierarchy(
            b"<?xml version='1.0'?><hierarchy>"
            b"<node class='android.widget.ScrollView' bounds='[0,1728][1080,2337]'>"
            b"<node class='android.widget.EditText' text='33.5731' enabled='true' bounds='[63,2334][1017,2400]'>"
            b"<node text='Pickup latitude' enabled='true' bounds='[105,2334][330,2337]'/>"
            b"</node></node></hierarchy>"
        )
        self.assertEqual([], SMOKE.matching_bounds(hierarchy, {"Pickup latitude"}, enabled_only=True))

    def test_visible_floating_label_taps_editable_control_center(self) -> None:
        hierarchy = SMOKE.extract_hierarchy(
            b"<?xml version='1.0'?><hierarchy>"
            b"<node class='android.widget.ScrollView' bounds='[0,1728][1080,2337]'>"
            b"<node class='android.widget.EditText' enabled='true' bounds='[63,2000][1017,2180]'>"
            b"<node text='Pickup latitude' enabled='true' bounds='[105,2000][330,2040]'/>"
            b"</node></node></hierarchy>"
        )
        self.assertEqual([SMOKE.Bounds(63, 2000, 1017, 2180)],
                         SMOKE.matching_bounds(hierarchy, {"Pickup latitude"}, enabled_only=True))

    def test_generated_demo_password_is_quoted_without_relaxing_shell_guards(self) -> None:
        import shlex
        password = "Demo-synthetic-Aa9!"
        encoded = SMOKE.encode_adb_input(password)
        self.assertEqual("'" + password + "'", encoded)
        self.assertEqual([password], shlex.split(encoded))
        for invalid in ("bang!;command", "$(command)!", "'quoted!'", "space !", "a" * 257):
            with self.subTest(invalid_length=len(invalid)), self.assertRaises(ValueError):
                SMOKE.encode_adb_input(invalid)

    def test_existing_email_login_uses_actual_selector_and_field(self) -> None:
        adb = Mock()
        adb.hierarchy.return_value = SMOKE.extract_hierarchy(
            b"<?xml version='1.0'?><hierarchy><node text='Email' enabled='true' bounds='[0,0][100,50]'/></hierarchy>"
        )
        smoke = SMOKE.RegistrationSmoke(adb, "passenger", 10)
        smoke.values = {"welcome_artwork_description": {"Welcome artwork"}, "login_with_email": {"Email"}}
        with patch.object(smoke, "tap_key") as tap, patch.object(smoke, "fill") as fill:
            smoke.submit_existing_email_login("synthetic@example.test", "Demo-synthetic-Aa9!")
        self.assertEqual(["login_with_email", "sign_in"], [c.args[0] for c in tap.call_args_list])
        self.assertEqual(["email", "password"], [c.args[0] for c in fill.call_args_list])

    def test_existing_email_login_refuses_unknown_screen_without_mutation(self) -> None:
        adb = Mock()
        adb.hierarchy.return_value = SMOKE.extract_hierarchy(b"<?xml version='1.0'?><hierarchy></hierarchy>")
        smoke = SMOKE.RegistrationSmoke(adb, "passenger", 10)
        with patch.object(smoke, "tap_key") as tap, patch.object(smoke, "fill") as fill:
            with self.assertRaisesRegex(SMOKE.SmokeFailure, "known signed-out"):
                smoke.submit_existing_email_login("synthetic@example.test", "Demo-synthetic-Aa9!")
        tap.assert_not_called()
        fill.assert_not_called()

    def test_scroll_stays_inside_observed_passenger_peek_sheet_in_both_directions(self) -> None:
        hierarchy = SMOKE.extract_hierarchy(
            b"<?xml version='1.0'?><hierarchy>"
            b"<node scrollable='true' class='android.view.View' bounds='[0,1728][1080,2400]'/>"
            b"<node scrollable='true' class='android.widget.EditText' bounds='[0,0][1080,2400]'/>"
            b"</hierarchy>"
        )
        self.assertEqual((540, 2232, 540, 1896), SMOKE.scroll_gesture(hierarchy, forward=True))
        self.assertEqual((540, 1896, 540, 2232), SMOKE.scroll_gesture(hierarchy, forward=False))

    def test_no_scroll_container_never_falls_back_to_swiping_the_map(self) -> None:
        hierarchy = SMOKE.extract_hierarchy(b"<?xml version='1.0'?><hierarchy><node bounds='[0,0][1080,2400]'/></hierarchy>")
        self.assertIsNone(SMOKE.scroll_gesture(hierarchy, forward=True))
        adb = object.__new__(SMOKE.AdbClient)
        with patch.object(adb, "run") as run:
            self.assertFalse(adb.scroll(hierarchy, forward=True))
            run.assert_not_called()

    def test_focused_synthetic_input_replaces_retained_draft_without_clipboard_or_data_wipe(self) -> None:
        adb = object.__new__(SMOKE.AdbClient)
        focused = SMOKE.extract_hierarchy(b"<?xml version='1.0'?><hierarchy><node class='android.widget.EditText' focused='true' text='RetainedInput'/></hierarchy>")
        with patch.object(adb, "run", return_value=b"mInputShown=true") as run, patch.object(adb, "hierarchy", return_value=focused):
            adb.input_text("SyntheticInput")
        commands = [call.args for call in run.call_args_list]
        self.assertEqual(("shell", "input", "keyevent", "KEYCODE_MOVE_END"), commands[0])
        self.assertEqual(("shell", "input", "keyevent") + ("KEYCODE_DEL",) * len("RetainedInput"), commands[1])
        self.assertEqual(("shell", "input", "text", "SyntheticInput"), commands[2])
        self.assertEqual(("shell", "dumpsys", "input_method"), commands[3])
        self.assertEqual(("shell", "input", "keyevent", "KEYCODE_BACK"), commands[4])
        with patch.object(adb, "run") as run:
            with self.assertRaises(ValueError):
                adb.input_text("unsafe;input")
            run.assert_not_called()

    def test_synthetic_input_requires_unambiguous_focus_and_bounded_draft(self) -> None:
        def hierarchy(nodes):
            return SMOKE.extract_hierarchy(f"<?xml version='1.0'?><hierarchy>{nodes}</hierarchy>".encode())
        node = "<node class='android.widget.EditText' focused='true' text='{}'/>"
        for nodes in ("", node.format("one") + node.format("two"), node.format("x" * 257)):
            with self.assertRaises(SMOKE.SmokeFailure):
                SMOKE.focused_input_length(hierarchy(nodes))
        self.assertEqual(0, SMOKE.focused_input_length(hierarchy(node.format(""))))
        self.assertEqual(12, SMOKE.focused_input_length(hierarchy(node.format("•" * 12))))

    def test_hardware_keyboard_does_not_navigate_back_out_of_form(self) -> None:
        adb = object.__new__(SMOKE.AdbClient)
        focused = SMOKE.extract_hierarchy(b"<?xml version='1.0'?><hierarchy><node class='android.widget.EditText' focused='true' text=''/></hierarchy>")
        with patch.object(adb, "run", return_value=b"mInputShown=false\nmIsInputViewShown=true") as run, patch.object(adb, "hierarchy", return_value=focused):
            adb.input_text("SyntheticInput")
        self.assertNotIn(("shell", "input", "keyevent", "KEYCODE_BACK"), [call.args for call in run.call_args_list])

    def test_unknown_or_conflicting_ime_state_never_sends_back(self) -> None:
        adb = object.__new__(SMOKE.AdbClient)
        focused = SMOKE.extract_hierarchy(b"<?xml version='1.0'?><hierarchy><node class='android.widget.EditText' focused='true' text=''/></hierarchy>")
        for output in (b"mIsInputViewShown=true", b"mInputShown=true\nmInputShown=false"):
            with self.subTest(output=output), patch.object(adb, "run", return_value=output) as run, patch.object(adb, "hierarchy", return_value=focused):
                with self.assertRaisesRegex(SMOKE.SmokeFailure, "Back was not sent"):
                    adb.input_text("SyntheticInput")
                self.assertNotIn(("shell", "input", "keyevent", "KEYCODE_BACK"), [call.args for call in run.call_args_list])

    def test_long_retained_input_is_cleared_in_small_adb_batches(self) -> None:
        adb = object.__new__(SMOKE.AdbClient)
        with patch.object(adb, "run", return_value=b"mInputShown=false") as run, patch.object(SMOKE, "focused_input_length", return_value=70), patch.object(adb, "hierarchy"):
            adb.input_text("SyntheticInput")
        deletion_batches = [call.args[3:] for call in run.call_args_list if call.args[:3] == ("shell", "input", "keyevent") and call.args[3] == "KEYCODE_DEL"]
        self.assertEqual([32, 32, 6], [len(batch) for batch in deletion_batches])

    def test_null_root_retry_is_bounded_and_other_xml_errors_are_not_hidden(self) -> None:
        adb = object.__new__(SMOKE.AdbClient)
        valid = b"<?xml version='1.0'?><hierarchy></hierarchy>"
        transient = b"ERROR: null root node returned by UiTestAutomationBridge."
        with patch.object(adb, "run", side_effect=[transient, valid]) as run, patch.object(SMOKE.time, "sleep"):
            self.assertEqual("hierarchy", adb.hierarchy().tag)
            self.assertEqual(2, run.call_count)
        with patch.object(adb, "run", return_value=transient) as run, patch.object(SMOKE.time, "sleep"):
            with self.assertRaises(SMOKE.SmokeFailure):
                adb.hierarchy()
            self.assertEqual(3, run.call_count)
        with patch.object(adb, "run", return_value=b"malformed") as run:
            with self.assertRaises(SMOKE.SmokeFailure):
                adb.hierarchy()
            self.assertEqual(1, run.call_count)

    def test_driver_login_requires_current_city_onboarding_not_legacy_apply_gate(self) -> None:
        smoke = SMOKE.RegistrationSmoke(object(), "driver", 10)
        with patch.object(smoke, "tap_key"), patch.object(smoke, "fill"), patch.object(smoke, "find") as find:
            journeys = smoke.run()
        self.assertEqual(["message_account_created", "driver_onboarding_title", "recruiting_cities"], [call.args[0] for call in find.call_args_list])
        self.assertEqual(2, len(journeys))

    def test_opt_in_sessions_exercise_rejection_restart_logout_and_cleared_restart_on_each_role(self) -> None:
        for role in ("passenger", "driver"):
            with self.subTest(role=role):
                adb = Mock()
                smoke = SMOKE.RegistrationSmoke(adb, role, 10, session_checks=True)
                with patch.object(smoke, "tap_key") as tap, patch.object(smoke, "fill"), patch.object(smoke, "find") as find:
                    journeys = smoke.run()
                self.assertEqual(6, len(journeys))
                self.assertIn("message_invalid_credentials", [call.args[0] for call in find.call_args_list])
                self.assertEqual(2, [call.args[0] for call in find.call_args_list].count("welcome_artwork_description"))
                self.assertEqual(role == "passenger", "account" in [call.args[0] for call in tap.call_args_list])
                self.assertIn("sign_out", [call.args[0] for call in tap.call_args_list])
                self.assertEqual(4, adb.run.call_count)
                for command in adb.run.call_args_list:
                    self.assertIn(SMOKE.ROLE_PACKAGES[role], " ".join(command.args))
                    self.assertNotIn("clear", command.args)
                self.assertEqual("LOCAL_SESSION_CLEARED", journeys[-1]["authority"])
                evidence = SMOKE.build_evidence(role, {"device_kind": "EMULATOR"}, journeys)
                self.assertIn("NO_EXTERNAL_SESSION_REVOCATION_CLAIM", evidence["limitations"])
                self.assertNotIn("REGISTRATION_AND_LOGIN_ONLY", evidence["limitations"])

    def test_bidirectional_search_recovers_header_without_accepting_other_controls(self) -> None:
        class FakeAdb:
            directions = []

            def hierarchy(self):
                label = "Where to?" if False in self.directions else "Review fare"
                return SMOKE.extract_hierarchy(f"<?xml version='1.0'?><hierarchy><node text='{label}' bounds='[10,1800][300,1900]'/></hierarchy>".encode())

            def scroll(self, _hierarchy, *, forward):
                self.directions.append(forward)
                return True

        adb = FakeAdb()
        smoke = SMOKE.RegistrationSmoke(adb, "passenger", 10)
        with patch.object(smoke, "texts", return_value={"Where to?"}), patch.object(SMOKE.time, "sleep"):
            bounds = smoke.find("where_to", scroll=True)
        self.assertEqual(1800, bounds.top)
        self.assertEqual([True, True, False], adb.directions)

    def test_long_account_form_search_is_not_truncated_to_four_swipes(self) -> None:
        class FakeAdb:
            directions = []

            def hierarchy(self):
                step = len(self.directions)
                label = "Sign out" if step >= 7 else "Account section"
                # Different observed layout at each scroll step, like a long form.
                top = 100 + step
                return SMOKE.extract_hierarchy(f"<?xml version='1.0'?><hierarchy><node text='{label}' bounds='[10,{top}][300,400]'/></hierarchy>".encode())

            def scroll(self, _hierarchy, *, forward):
                self.directions.append(forward)
                return True

        adb = FakeAdb()
        smoke = SMOKE.RegistrationSmoke(adb, "passenger", 10)
        with patch.object(smoke, "texts", return_value={"Sign out"}), patch.object(SMOKE.time, "sleep"):
            self.assertEqual(107, smoke.find("sign_out", scroll=True).top)
        self.assertEqual([True] * 7, adb.directions)

    def test_disabled_parent_action_does_not_become_enabled_through_its_text_child(self) -> None:
        hierarchy = SMOKE.extract_hierarchy(
            b"<?xml version='1.0'?><hierarchy><node enabled='false'><node enabled='true' text='Sign in' bounds='[0,0][200,80]'/></node></hierarchy>"
        )
        self.assertEqual([], SMOKE.matching_bounds(hierarchy, {"Sign in"}, enabled_only=True))
        self.assertEqual(1, len(SMOKE.matching_bounds(hierarchy, {"Sign in"})))

    def test_device_profile_is_bounded_and_contains_no_raw_serial(self) -> None:
        class FakeAdb:
            serial = "synthetic-physical-transport"
            authorized_device_count = 1
            values = {
                ("shell", "getprop", "ro.kernel.qemu"): "",
                ("shell", "getprop", "ro.boot.qemu"): "0",
                ("shell", "getprop", "ro.hardware"): "synthetic-physical-hardware",
                ("shell", "getprop", "ro.build.version.sdk"): "35",
                ("shell", "wm", "size"): "Physical size: 1080x2400",
                ("shell", "getprop", "ro.product.cpu.abi"): "arm64-v8a",
                ("shell", "getprop", "ro.product.manufacturer"): "Example",
                ("shell", "getprop", "ro.product.model"): "Test Phone",
                ("shell", "getprop", "persist.sys.locale"): "fr-MA",
                ("shell", "dumpsys", "package", "ma.taximobile.passenger"): (
                    "  versionCode=7 minSdk=24 targetSdk=36\n  versionName=1.2.3"
                ),
                ("shell", "pm", "path", "ma.taximobile.passenger"): "package:/data/app/synthetic/base.apk",
                ("shell", "sha256sum", "/data/app/synthetic/base.apk"): "a" * 64 + "  /data/app/synthetic/base.apk",
            }

            def text(self, *arguments):
                return self.values[arguments]

            def bounded_output(self, *arguments, **_options):
                return self.values[arguments]

            def run(self, *arguments):
                return self.values[arguments].encode()

        profile = SMOKE.collect_device_profile(FakeAdb(), "passenger")
        self.assertEqual(35, profile["android_sdk"])
        self.assertEqual("1.2.3", profile["package_version_name"])
        self.assertEqual("PHYSICAL", profile["device_kind"])
        self.assertEqual(["a" * 64], profile["installed_apk_sha256"])
        self.assertNotIn("serial", " ".join(profile).lower())
        self.assertTrue(profile["bound_authorized_device_verified"])
        adb = FakeAdb()
        adb.authorized_device_count = 2
        self.assertFalse(SMOKE.collect_device_profile(adb, "passenger")["single_authorized_device_verified"])

    def test_installed_artifact_paths_are_validated_and_never_stored(self) -> None:
        adb = Mock()
        adb.bounded_output.side_effect = [
            "package:/data/app/synthetic/base.apk\npackage:/data/app/synthetic/split.apk",
            "b" * 64 + "  /data/app/synthetic/split.apk\n" + "a" * 64 + "  /data/app/synthetic/base.apk",
        ]
        self.assertEqual(["a" * 64, "b" * 64], SMOKE.collect_installed_apk_hashes(adb, "ma.taximobile.driver"))
        for invalid in (
            "package:/data/app/../base.apk", "package:/data/app/base.apk;echo", "package:/sdcard/base.apk", "garbage",
        ):
            with self.subTest(path=invalid):
                adb = Mock()
                adb.bounded_output.return_value = invalid
                with self.assertRaises(SMOKE.SmokeFailure):
                    SMOKE.collect_installed_apk_hashes(adb, "ma.taximobile.driver")
                self.assertEqual(1, adb.bounded_output.call_count)
        adb = Mock()
        adb.bounded_output.side_effect = ["package:/data/app/synthetic/base.apk", "a" * 64 + "  /data/app/other.apk"]
        with self.assertRaises(SMOKE.SmokeFailure):
            SMOKE.collect_installed_apk_hashes(adb, "ma.taximobile.driver")

    def test_device_evidence_is_partial_and_never_accepts_t4(self) -> None:
        evidence = SMOKE.build_evidence(
            "driver",
            {"android_sdk": 35, "single_authorized_device_verified": True, "device_kind": "PHYSICAL"},
            [{"id": "ANDROID_REGISTRATION", "result": "PASS", "authority": "BACKEND_CONFIRMED"}],
        )
        self.assertEqual(["ANDROID_DEVICE_REPORT"], evidence["supported_evidence_kinds"])
        self.assertFalse(evidence["phase_evidence_complete"])
        self.assertFalse(evidence["phase_accepted"])
        self.assertFalse(evidence["deployment_accepted"])
        self.assertNotIn("serial", json.dumps(evidence).lower())

    def test_emulator_evidence_never_supports_physical_device_report(self) -> None:
        evidence = SMOKE.build_evidence(
            "passenger", {"device_kind": "EMULATOR"},
            [{"id": "ANDROID_REGISTRATION", "result": "PASS", "authority": "BACKEND_CONFIRMED"}],
        )
        self.assertEqual(2, evidence["schema_version"])
        self.assertEqual("T4_ANDROID_REGISTRATION_SIMULATION", evidence["evidence_level"])
        self.assertEqual([], evidence["supported_evidence_kinds"])
        self.assertFalse(evidence["is_physical_device"])
        self.assertIn("NO_PHYSICAL_DEVICE_CLAIM", evidence["limitations"])

    def test_missing_device_fidelity_cannot_be_assumed_physical(self) -> None:
        with self.assertRaises(SMOKE.SmokeFailure):
            SMOKE.build_evidence("driver", {}, [{"result": "PASS"}])

    def test_transport_selection_is_explicit_and_ignores_unauthorized_devices(self) -> None:
        devices = "List of devices attached\nemulator-5554\tdevice\nphone-test\tdevice\nlocked\tunauthorized\n"
        with self.assertRaises(SMOKE.SmokeFailure):
            SMOKE.select_authorized_device(devices)
        self.assertEqual("emulator-5554", SMOKE.select_authorized_device(devices, "emulator-5554"))
        for missing in ("locked", "disconnected"):
            with self.assertRaises(SMOKE.SmokeFailure):
                SMOKE.select_authorized_device(devices, missing)

    def test_every_command_after_enumeration_stays_on_the_selected_transport(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "adb.exe"
            executable.touch()
            with patch.object(SMOKE.subprocess, "run") as run:
                run.side_effect = [
                    subprocess.CompletedProcess([], 0, b"List of devices attached\nphone-test\tdevice\nemulator-5554\tdevice\n", b""),
                    subprocess.CompletedProcess([], 0, b"ready", b""),
                ]
                adb = SMOKE.AdbClient(executable, "phone-test")
                adb.run("shell", "getprop", "ro.hardware")
            self.assertEqual([str(executable), "devices"], run.call_args_list[0].args[0])
            self.assertEqual([str(executable), "-s", "phone-test", "shell", "getprop", "ro.hardware"], run.call_args_list[1].args[0])
            self.assertEqual(2, adb.authorized_device_count)

    def test_emulator_detection_uses_transport_flags_and_hardware(self) -> None:
        class FakeAdb:
            serial = "synthetic-transport"
            flags = {"ro.kernel.qemu": "0", "ro.boot.qemu": "0"}
            hardware = "physical-test"

            def run(self, *_args):
                return self.flags[_args[-1]].encode()

            def text(self, *_args):
                return self.hardware

        adb = FakeAdb()
        self.assertEqual("PHYSICAL", SMOKE.detect_device_kind(adb))
        adb.serial = "emulator-5554"
        self.assertEqual("EMULATOR", SMOKE.detect_device_kind(adb))
        adb.serial = "synthetic-transport"
        adb.hardware = "ranchu"
        self.assertEqual("EMULATOR", SMOKE.detect_device_kind(adb))
        adb.hardware = "physical-test"
        adb.flags["ro.boot.qemu"] = "1"
        self.assertEqual("EMULATOR", SMOKE.detect_device_kind(adb))
        adb.flags["ro.boot.qemu"] = "unknown"
        with self.assertRaises(SMOKE.SmokeFailure):
            SMOKE.detect_device_kind(adb)

    def test_emulator_refusal_happens_before_registration_actions(self) -> None:
        with (
            patch.object(sys, "argv", ["smoke", "--adb", "unused", "--role", "passenger"]),
            patch.object(SMOKE, "AdbClient"),
            patch.object(SMOKE, "detect_device_kind", return_value="EMULATOR"),
            patch.object(SMOKE, "RegistrationSmoke") as registration,
        ):
            self.assertEqual(1, SMOKE.main())
            registration.assert_not_called()

    def test_existing_evidence_is_rejected_before_adb_access(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "existing.json"
            output.write_text("{}", encoding="utf-8")
            with patch.object(
                sys,
                "argv",
                [
                    "android_registration_smoke.py",
                    "--adb",
                    str(Path(directory) / "missing-adb"),
                    "--role",
                    "passenger",
                    "--output",
                    str(output),
                ],
            ):
                self.assertEqual(1, SMOKE.main())


if __name__ == "__main__":
    unittest.main()
