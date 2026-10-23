"""Drive a bounded registration/login smoke through an installed Android debug app.

The harness uses Android's built-in accessibility hierarchy and input commands.
It does not capture screenshots, write device files, print credentials, or infer
success from local UI state: registration and the subsequent login must both be
confirmed by backend-driven screens.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import time
from typing import Iterable
from uuid import uuid4
import xml.etree.ElementTree as ElementTree


SCRIPT_ROOT = Path(__file__).resolve().parent
RESOURCE_ROOT = SCRIPT_ROOT.parent / "shared" / "src" / "commonMain" / "composeResources"
BOUNDS_PATTERN = re.compile(r"^\[(\d+),(\d+)]\[(\d+),(\d+)]$")
SAFE_INPUT_PATTERN = re.compile(r"[A-Za-z0-9@._!-]{1,256}")
ROLE_PACKAGES = {
    "passenger": "ma.taximobile.passenger",
    "driver": "ma.taximobile.driver",
}
ROLE_READY_RESOURCES = {
    "passenger": ("where_to", "use_current_location_pickup"),
    # Current city-based onboarding is authenticated, but is not driver approval.
    "driver": ("driver_onboarding_title", "recruiting_cities"),
}
SAFE_PROFILE_TEXT = re.compile(r"[^\x00-\x1f\x7f]{1,120}", re.UNICODE)


class SmokeFailure(RuntimeError):
    """A safe, actionable acceptance failure without submitted values."""


def keyboard_shown_from_dump(raw_output: bytes) -> bool:
    # mInputShown is the system service's attached-IME state. The IME's own
    # mIsInputViewShown may remain true while a hardware keyboard suppresses
    # its window, so it must not trigger a Back navigation on its own.
    values = re.findall(rb"\bmInputShown\s*=\s*(true|false)\b", raw_output)
    if not values or len(set(values)) != 1:
        raise SmokeFailure("Android keyboard visibility is unavailable or ambiguous; Back was not sent.")
    return values[0] == b"true"


@dataclass(frozen=True, slots=True)
class Bounds:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def center(self) -> tuple[int, int]:
        return ((self.left + self.right) // 2, (self.top + self.bottom) // 2)


def parse_bounds(value: str) -> Bounds:
    match = BOUNDS_PATTERN.fullmatch(value)
    if match is None:
        raise ValueError("UI node has invalid bounds.")
    bounds = Bounds(*(int(part) for part in match.groups()))
    if bounds.right <= bounds.left or bounds.bottom <= bounds.top:
        raise ValueError("UI node has empty bounds.")
    return bounds


def extract_hierarchy(raw_output: bytes) -> ElementTree.Element:
    decoded = raw_output.decode("utf-8", errors="replace")
    start = decoded.find("<?xml")
    end_marker = "</hierarchy>"
    end = decoded.find(end_marker, start)
    if start < 0 or end < 0:
        raise SmokeFailure("Android did not return a readable accessibility hierarchy.")
    try:
        return ElementTree.fromstring(decoded[start : end + len(end_marker)])
    except ElementTree.ParseError as error:
        raise SmokeFailure("Android returned a malformed accessibility hierarchy.") from error


def load_localized_values(resource_root: Path = RESOURCE_ROOT) -> dict[str, set[str]]:
    values: dict[str, set[str]] = {}
    catalogs = sorted(resource_root.glob("values*/strings.xml"))
    if not catalogs:
        raise SmokeFailure("TaxiMobile localization catalogs are missing.")
    for catalog in catalogs:
        root = ElementTree.parse(catalog).getroot()
        for element in root.findall("string"):
            name = element.attrib.get("name")
            text = "".join(element.itertext()).strip()
            if name and text:
                values.setdefault(name, set()).add(text)
    return values


def matching_bounds(
    hierarchy: ElementTree.Element,
    accepted_text: Iterable[str],
    *,
    enabled_only: bool = False,
) -> list[Bounds]:
    accepted = set(accepted_text)
    matches: list[Bounds] = []
    parents = {child: parent for parent in hierarchy.iter() for child in parent}
    for node in hierarchy.iter("node"):
        if enabled_only and node.attrib.get("enabled") != "true":
            continue
        if enabled_only:
            ancestor = parents.get(node)
            disabled = False
            while ancestor is not None:
                disabled = disabled or ancestor.attrib.get("enabled") == "false"
                ancestor = parents.get(ancestor)
            if disabled:
                continue
        visible_values = {node.attrib.get("text", ""), node.attrib.get("content-desc", "")}
        if not accepted.intersection(visible_values):
            continue
        try:
            bounds = parse_bounds(node.attrib.get("bounds", ""))
        except ValueError:
            continue
        # Floating labels may themselves be clipped to a three-pixel strip
        # while their editable parent remains outside the viewport. The input
        # control, not that label strip, must supply the safe tap target.
        ancestor = parents.get(node)
        while ancestor is not None:
            if ancestor.attrib.get("class") == "android.widget.EditText":
                try:
                    bounds = parse_bounds(ancestor.attrib.get("bounds", ""))
                except ValueError:
                    pass
                break
            ancestor = parents.get(ancestor)
        # Compose can expose a child's nominal bounds beyond a scroll viewport
        # even though the child is clipped. Never tap that nominal center: it
        # can land on Android's navigation area rather than the intended field.
        # Discover the field by scrolling its observed container instead.
        x, y = bounds.center
        ancestor = parents.get(node)
        clipped = False
        while ancestor is not None:
            try:
                viewport = parse_bounds(ancestor.attrib.get("bounds", ""))
            except ValueError:
                ancestor = parents.get(ancestor)
                continue
            if not (viewport.left <= x < viewport.right and viewport.top <= y < viewport.bottom):
                clipped = True
                break
            ancestor = parents.get(ancestor)
        if not clipped:
            matches.append(bounds)
    return matches


def encode_adb_input(value: str) -> str:
    if not SAFE_INPUT_PATTERN.fullmatch(value):
        raise ValueError("Smoke input must use the bounded ADB-safe character set.")
    # The owned UX cohort uses a trailing '!'. Quote that bounded token for
    # Android's POSIX shell; quotes, spaces, substitutions and other shell
    # syntax remain forbidden. Never normalize or weaken a generated password.
    return "'" + value + "'" if "!" in value else value


def scroll_gesture(
    hierarchy: ElementTree.Element, *, forward: bool,
) -> tuple[int, int, int, int] | None:
    """Swipe inside the observed vertical scroller, never the operational map.

    The passenger peek sheet occupies only the bottom 28% of the screen. A
    screen-relative swipe can pan the map instead of searching sheet content.
    Text-field horizontal scrollers are not navigation containers.
    """
    candidates: list[Bounds] = []
    for node in hierarchy.iter("node"):
        if node.attrib.get("scrollable") != "true" or node.attrib.get("class") == "android.widget.EditText":
            continue
        try:
            bounds = parse_bounds(node.attrib.get("bounds", ""))
        except ValueError:
            continue
        if bounds.bottom - bounds.top >= 120 and bounds.right - bounds.left >= 120:
            candidates.append(bounds)
    if not candidates:
        return None
    bounds = max(candidates, key=lambda item: (item.right - item.left) * (item.bottom - item.top))
    x = bounds.center[0]
    height = bounds.bottom - bounds.top
    upper = bounds.top + int(height * 0.25)
    lower = bounds.top + int(height * 0.75)
    return (x, lower, x, upper) if forward else (x, upper, x, lower)


def focused_input_length(hierarchy: ElementTree.Element) -> int:
    focused = [node for node in hierarchy.iter("node") if
               node.attrib.get("class") == "android.widget.EditText" and
               node.attrib.get("focused") == "true"]
    if len(focused) != 1:
        raise SmokeFailure("Synthetic input requires exactly one focused Android text field.")
    length = len(focused[0].attrib.get("text", ""))
    if length > 256:
        raise SmokeFailure("Retained field draft exceeds the synthetic test input bound.")
    return length


class AdbClient:
    def __init__(self, executable: Path, serial: str | None = None) -> None:
        if not executable.is_file():
            raise SmokeFailure("Workspace Android platform tools are missing.")
        self.executable = executable
        self.serial: str | None = None
        devices = self.run("devices").decode("utf-8", errors="replace")
        self.serial = select_authorized_device(devices, serial)
        self.authorized_device_count = sum(
            len(fields := line.split()) >= 2 and fields[1] == "device"
            for line in devices.splitlines()
        )

    def run(self, *arguments: str, timeout: float = 20) -> bytes:
        try:
            result = subprocess.run(
                [str(self.executable), *(["-s", self.serial] if self.serial else []), *arguments],
                capture_output=True,
                check=False,
                timeout=timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise SmokeFailure("ADB did not complete the requested device action.") from error
        if result.returncode != 0:
            raise SmokeFailure("ADB rejected a requested device action.")
        return result.stdout + result.stderr

    def hierarchy(self) -> ElementTree.Element:
        # Activity transitions can temporarily have no accessibility root. Only
        # that specific Android response is retryable; malformed XML/ADB errors
        # remain visible, and an indefinitely absent root fails closed.
        for attempt in range(3):
            raw = self.run("exec-out", "uiautomator", "dump", "/dev/tty")
            if b"null root node returned" not in raw:
                return extract_hierarchy(raw)
            if attempt < 2:
                time.sleep(0.35)
        raise SmokeFailure("Android accessibility root remained unavailable during an activity transition.")

    def bounded_output(self, *arguments: str, max_length: int = 16000) -> str:
        value = self.run(*arguments).decode("utf-8", errors="replace").strip()
        if not value or len(value) > max_length or "\x00" in value:
            raise SmokeFailure("Android returned invalid bounded device metadata.")
        return value

    def text(self, *arguments: str) -> str:
        value = self.bounded_output(*arguments, max_length=120)
        if SAFE_PROFILE_TEXT.fullmatch(value) is None:
            raise SmokeFailure("Android returned invalid bounded device metadata.")
        return value

    def tap(self, bounds: Bounds) -> None:
        x, y = bounds.center
        self.run("shell", "input", "tap", str(x), str(y))

    def input_text(self, value: str) -> None:
        # Returning to a form after logout/retry may retain non-secret drafts.
        # Replace rather than append, but only in the field just focused by the
        # test. Measured, small key-event batches clear our synthetic inputs;
        # no clipboard, account file or physical app-data reset is involved.
        encoded = encode_adb_input(value)
        retained_length = focused_input_length(self.hierarchy())
        self.run("shell", "input", "keyevent", "KEYCODE_MOVE_END")
        for offset in range(0, retained_length, 32):
            self.run("shell", "input", "keyevent", *("KEYCODE_DEL" for _ in range(min(32, retained_length - offset))))
        self.run("shell", "input", "text", encoded)
        # Back dismisses a shown IME, but navigates out of the form when no
        # software keyboard is attached. Inspect the actual system state first.
        if keyboard_shown_from_dump(self.run("shell", "dumpsys", "input_method")):
            self.run("shell", "input", "keyevent", "KEYCODE_BACK")

    def scroll(self, hierarchy: ElementTree.Element, *, forward: bool) -> bool:
        gesture = scroll_gesture(hierarchy, forward=forward)
        if gesture is None:
            return False
        self.run("shell", "input", "swipe", *(str(value) for value in gesture), "250")
        return True


def select_authorized_device(devices: str, requested: str | None = None) -> str:
    """Bind all subsequent actions to one authorized transport; never print its ID."""
    authorized = [
        fields[0]
        for line in devices.splitlines()
        if len(fields := line.split()) >= 2 and fields[1] == "device"
    ]
    if requested is not None:
        if requested not in authorized:
            raise SmokeFailure("The selected Android transport is not authorized and connected.")
        return requested
    if len(authorized) != 1:
        raise SmokeFailure("Select exactly one authorized Android transport before testing.")
    return authorized[0]


def detect_device_kind(adb: AdbClient) -> str:
    # Empty qemu flags are normal on physical phones. Unknown values fail closed;
    # the transport prefix and Android hardware also catch an emulator that omits
    # the legacy kernel flag. This is test metadata, not hardware attestation.
    flags = [
        adb.run("shell", "getprop", name).decode("utf-8", errors="replace").strip()
        for name in ("ro.kernel.qemu", "ro.boot.qemu")
    ]
    if any(flag not in {"", "0", "1"} for flag in flags):
        raise SmokeFailure("Android device fidelity could not be determined.")
    hardware = adb.text("shell", "getprop", "ro.hardware").lower()
    if "1" in flags or (adb.serial or "").startswith("emulator-") or hardware in {"ranchu", "goldfish"}:
        return "EMULATOR"
    return "PHYSICAL"


class RegistrationSmoke:
    def __init__(self, adb: AdbClient, role: str, timeout_seconds: float, *, session_checks: bool = False) -> None:
        if role not in ROLE_PACKAGES:
            raise ValueError("Role must be passenger or driver.")
        if not 10 <= timeout_seconds <= 120:
            raise ValueError("Timeout must be between 10 and 120 seconds.")
        self.adb = adb
        self.role = role
        self.timeout_seconds = timeout_seconds
        self.session_checks = session_checks
        self.values = load_localized_values()

    def texts(self, resource_name: str) -> set[str]:
        values = self.values.get(resource_name)
        if not values:
            raise SmokeFailure(f"Required UI resource is missing: {resource_name}.")
        return values

    def find(
        self,
        resource_name: str,
        *,
        prefer_bottom: bool = False,
        enabled_only: bool = False,
        scroll: bool = False,
    ) -> Bounds:
        deadline = time.monotonic() + self.timeout_seconds
        scroll_attempts = 0
        forward = True
        previous_layout = None
        unchanged_layouts = 0
        while time.monotonic() < deadline:
            hierarchy = self.adb.hierarchy()
            matches = matching_bounds(
                hierarchy,
                self.texts(resource_name),
                enabled_only=enabled_only,
            )
            if matches:
                return max(matches, key=lambda item: item.top) if prefer_bottom else matches[0]
            if scroll and scroll_attempts < 24:
                # Long account/security forms exceed four half-page swipes.
                # Search to the observed edge, then back toward the header.
                # Progress uses layout metadata only, never field values.
                layout = tuple((node.attrib.get("class"), node.attrib.get("bounds"),
                                node.attrib.get("resource-id"), node.attrib.get("scrollable"))
                               for node in hierarchy.iter("node"))
                unchanged_layouts = unchanged_layouts + 1 if layout == previous_layout else 0
                if forward and unchanged_layouts >= 2:
                    forward = False
                    unchanged_layouts = 0
                if self.adb.scroll(hierarchy, forward=forward):
                    previous_layout = layout
                    scroll_attempts += 1
            time.sleep(0.35)
        failure_keys = (
            "message_network_unavailable",
            "message_registration_conflict",
            "message_registration_invalid",
            "message_registration_rate_limited",
            "message_registration_failed",
            "message_invalid_credentials",
        )
        hierarchy = self.adb.hierarchy()
        for key in failure_keys:
            if matching_bounds(hierarchy, self.values.get(key, ())):
                raise SmokeFailure(f"Android acceptance stopped with the safe UI state {key}.")
        raise SmokeFailure(f"Timed out waiting for the UI state {resource_name}.")

    def tap_key(self, resource_name: str, **options: bool) -> None:
        self.adb.tap(self.find(resource_name, **options))
        time.sleep(0.25)

    def fill(self, resource_name: str, value: str) -> None:
        self.tap_key(resource_name, scroll=True)
        self.adb.input_text(value)
        time.sleep(0.25)

    def assert_authenticated_screen(self) -> None:
        for key in ROLE_READY_RESOURCES[self.role]:
            self.find(key, scroll=True)

    def submit_existing_email_login(self, email: str, password: str) -> None:
        """Submit an owned synthetic login; caller must verify its role screen.

        Do not mistake recovery's account_identifier for login, or type an email
        into the default Moroccan-phone field. Refuse an unknown/authenticated
        screen instead of signing out an account to manufacture a precondition.
        """
        encode_adb_input(email)
        encode_adb_input(password)
        hierarchy = self.adb.hierarchy()
        if matching_bounds(hierarchy, self.texts("welcome_artwork_description")):
            self.tap_key("sign_in", enabled_only=True)
        else:
            if not matching_bounds(hierarchy, self.texts("login_with_email"), enabled_only=True):
                raise SmokeFailure("Existing login requires the known signed-out welcome or login screen.")
        self.tap_key("login_with_email", enabled_only=True, scroll=True)
        self.fill("email", email)
        self.fill("password", password)
        self.tap_key("sign_in", prefer_bottom=True, enabled_only=True, scroll=True)

    def restart_role_app(self) -> None:
        # An owned test application only: preserve its data and secure tokens,
        # and prove startup through the same backend-driven product gate.
        self.adb.run("shell", "am", "force-stop", ROLE_PACKAGES[self.role])
        self.adb.run("shell", "am", "start", "-n", f"{ROLE_PACKAGES[self.role]}/org.example.taximobile.MainActivity")

    def run(self) -> list[dict[str, str]]:
        suffix = uuid4().hex
        email = f"android-smoke-{suffix}@example.test"
        password = "DeviceSmoke2026"

        self.tap_key("create_account")
        self.fill("display_name", "DeviceSmoke")
        self.fill("email_optional", email)
        self.fill("password", password)
        self.tap_key("create_account", prefer_bottom=True, enabled_only=True, scroll=True)

        # This confirmation is emitted only after POST /auth/register succeeds.
        self.find("message_account_created", scroll=True)
        if self.session_checks:
            self.fill("password", password + "Invalid")
            self.tap_key("sign_in", prefer_bottom=True, enabled_only=True, scroll=True)
            self.find("message_invalid_credentials", scroll=True)
        self.fill("password", password)
        self.tap_key("sign_in", prefer_bottom=True, enabled_only=True, scroll=True)

        # Match the current product's authenticated screen, not the superseded
        # single-application driver gate. Onboarding does not confer eligibility.
        self.assert_authenticated_screen()
        journeys = [
            {"id": "ANDROID_REGISTRATION", "result": "PASS", "authority": "BACKEND_CONFIRMED"},
            {"id": "ANDROID_LOGIN_ROLE_GATE", "result": "PASS", "authority": "BACKEND_CONFIRMED"},
        ]
        if self.session_checks:
            journeys.append({"id": "ANDROID_INVALID_CREDENTIALS", "result": "PASS", "authority": "BACKEND_CONFIRMED"})
            self.restart_role_app()
            self.assert_authenticated_screen()
            journeys.append({"id": "ANDROID_AUTHENTICATED_RESTART", "result": "PASS", "authority": "BACKEND_CONFIRMED"})
            if self.role == "passenger":
                self.tap_key("account", enabled_only=True)
            self.tap_key("sign_out", enabled_only=True, scroll=True)
            self.find("create_account", scroll=True)
            self.find("welcome_artwork_description", scroll=True)
            journeys.append({"id": "ANDROID_SIGN_OUT", "result": "PASS", "authority": "LOCAL_SESSION_CLEARED"})
            self.restart_role_app()
            self.find("create_account", scroll=True)
            self.find("welcome_artwork_description", scroll=True)
            journeys.append({"id": "ANDROID_SIGNED_OUT_RESTART", "result": "PASS", "authority": "LOCAL_SESSION_CLEARED"})
        return journeys


def collect_device_profile(adb: AdbClient, role: str) -> dict[str, object]:
    if role not in ROLE_PACKAGES:
        raise ValueError("Role must be passenger or driver.")
    sdk_text = adb.text("shell", "getprop", "ro.build.version.sdk")
    if not sdk_text.isdigit() or not 24 <= int(sdk_text) <= 99:
        raise SmokeFailure("Android SDK is outside the configured supported range.")
    size_text = adb.text("shell", "wm", "size")
    size_match = re.search(r"(?:Physical|Override) size:\s*(\d+)x(\d+)", size_text)
    if size_match is None:
        raise SmokeFailure("Android did not report a bounded screen size.")
    width, height = (int(value) for value in size_match.groups())
    if not 240 <= width <= 10000 or not 240 <= height <= 10000:
        raise SmokeFailure("Android screen size is outside the evidence bounds.")

    package = ROLE_PACKAGES[role]
    package_text = adb.bounded_output(
        "shell", "dumpsys", "package", package, max_length=200000
    )
    version_name = re.search(r"(?m)^\s*versionName=([^\s]+)\s*$", package_text)
    version_code = re.search(r"(?m)^\s*versionCode=(\d+)(?:\s|$)", package_text)
    if version_name is None or version_code is None:
        raise SmokeFailure("Installed TaxiMobile package version could not be verified.")
    try:
        locale = adb.text("shell", "getprop", "persist.sys.locale")
    except SmokeFailure:
        locale = adb.text("shell", "getprop", "ro.product.locale")
    return {
        "device_kind": detect_device_kind(adb),
        "android_sdk": int(sdk_text),
        "abi": adb.text("shell", "getprop", "ro.product.cpu.abi"),
        "manufacturer": adb.text("shell", "getprop", "ro.product.manufacturer"),
        "model": adb.text("shell", "getprop", "ro.product.model"),
        "locale": locale,
        "screen_width_px": width,
        "screen_height_px": height,
        "package_name": package,
        "package_version_name": version_name.group(1),
        "package_version_code": int(version_code.group(1)),
        "installed_apk_sha256": collect_installed_apk_hashes(adb, package),
        "bound_authorized_device_verified": True,
        "single_authorized_device_verified": adb.authorized_device_count == 1,
    }


def collect_installed_apk_hashes(adb: AdbClient, package: str) -> list[str]:
    """Identify actual installed code, not just the reused 1.0.0 version label.

    Remote paths are validated before ADB shell use and never retained. Reading
    installed APKs does not read application data, credentials or device IDs.
    """
    if package not in ROLE_PACKAGES.values():
        raise SmokeFailure("Installed-artifact inspection requires a TaxiMobile role package.")
    lines = adb.bounded_output("shell", "pm", "path", package).splitlines()
    paths = [line.removeprefix("package:") for line in lines]
    if not 1 <= len(paths) <= 20 or any(
        not line.startswith("package:") or
        re.fullmatch(r"/data/app/[A-Za-z0-9_~=+/.-]+\.apk", path) is None or
        any(part in {".", ".."} for part in path.split("/"))
        for line, path in zip(lines, paths)
    ):
        raise SmokeFailure("Android returned unsupported installed-artifact paths.")
    output = adb.bounded_output("shell", "sha256sum", *paths)
    digests = []
    for line in output.splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})\s+(.+)", line)
        if match is None or match.group(2) not in paths:
            raise SmokeFailure("Android installed-artifact digest inspection failed.")
        digests.append((match.group(2), match.group(1)))
    if sorted(path for path, _ in digests) != sorted(paths):
        raise SmokeFailure("Android installed-artifact digest set is incomplete.")
    return sorted(digest for _, digest in digests)


def build_evidence(role: str, profile: dict[str, object], journeys: list[dict[str, str]]) -> dict[str, object]:
    if role not in ROLE_PACKAGES or not journeys or any(item.get("result") != "PASS" for item in journeys):
        raise SmokeFailure("Android evidence requires a passing bounded role journey.")
    device_kind = profile.get("device_kind")
    if device_kind not in {"PHYSICAL", "EMULATOR"}:
        raise SmokeFailure("Android evidence requires explicit device fidelity.")
    simulated = device_kind == "EMULATOR"
    session_checks = any(item.get("id") == "ANDROID_SIGNED_OUT_RESTART" for item in journeys)
    return {
        "schema_version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_level": (
            "T4_ANDROID_REGISTRATION_SIMULATION" if simulated
            else "T4_ANDROID_REGISTRATION_DEVICE_EXECUTION"
        ),
        "phase": "T4",
        "result": "PASS",
        "data_classification": "TEST_DEVICE_METADATA_ONLY",
        "role": role.upper(),
        "supported_evidence_kinds": [] if simulated else ["ANDROID_DEVICE_REPORT"],
        "is_physical_device": not simulated,
        "phase_evidence_complete": False,
        "phase_accepted": False,
        "deployment_accepted": False,
        "device": profile,
        "journeys": journeys,
        "limitations": (["EMULATOR_ONLY", "NO_PHYSICAL_DEVICE_CLAIM"] if simulated else []) + [
            "DEBUG_BUILD_ONLY",
            "REGISTRATION_LOGIN_INVALID_CREDENTIALS_AND_BOUNDED_RESTART_LOGOUT_ONLY" if session_checks else "REGISTRATION_AND_LOGIN_ONLY",
            "NO_EXTERNAL_SESSION_REVOCATION_CLAIM",
            "NO_IOS_OR_BROWSER_CLAIM",
            "NO_ACCESSIBILITY_OR_RTL_CLAIM",
            "NO_DEGRADED_NETWORK_OR_BACKGROUND_LIFECYCLE_ACCEPTANCE_CLAIM",
            "NO_CRASH_SYMBOLICATION_CLAIM",
            "NO_SCREENSHOT_OR_RAW_DEVICE_IDENTIFIER_CAPTURED",
            "NO_PHASE_OR_DEPLOYMENT_ACCEPTANCE_CLAIM",
        ],
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run TaxiMobile Android registration/login acceptance.")
    parser.add_argument("--adb", type=Path, required=True)
    parser.add_argument("--role", choices=sorted(ROLE_PACKAGES), required=True)
    parser.add_argument("--serial", help="Bind to one already authorized transport; never retained in evidence.")
    parser.add_argument("--allow-emulator", action="store_true", help="Permit explicitly labelled simulation, not device acceptance.")
    parser.add_argument("--session-checks", action="store_true", help="Also exercise wrong password, app restart, UI sign-out and signed-out restart; no external revocation acceptance.")
    parser.add_argument("--timeout-seconds", type=float, default=30)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    output = arguments.output.resolve() if arguments.output else None
    if output is not None and output.exists():
        print("Android registration smoke failed: refusing to overwrite existing evidence.")
        return 1
    try:
        adb = AdbClient(arguments.adb, arguments.serial)
        device_kind = detect_device_kind(adb)
        if device_kind == "EMULATOR" and not arguments.allow_emulator:
            raise SmokeFailure("An emulator requires --allow-emulator and cannot produce physical-device evidence.")
        journeys = RegistrationSmoke(
            adb,
            arguments.role,
            arguments.timeout_seconds,
            session_checks=arguments.session_checks,
        ).run()
        evidence = build_evidence(
            arguments.role,
            collect_device_profile(adb, arguments.role),
            journeys,
        )
    except (SmokeFailure, ValueError) as error:
        print(f"Android registration smoke failed: {error}")
        return 1
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    scope = "registration/login and bounded session checks" if arguments.session_checks else "registration and login"
    print(f"TaxiMobile {arguments.role} {scope} passed on Android ({device_kind}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
