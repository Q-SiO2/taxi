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
SAFE_INPUT_PATTERN = re.compile(r"[A-Za-z0-9@._-]+")
ROLE_PACKAGES = {
    "passenger": "ma.taximobile.passenger",
    "driver": "ma.taximobile.driver",
}
SAFE_PROFILE_TEXT = re.compile(r"[^\x00-\x1f\x7f]{1,120}", re.UNICODE)


class SmokeFailure(RuntimeError):
    """A safe, actionable acceptance failure without submitted values."""


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
    for node in hierarchy.iter("node"):
        if enabled_only and node.attrib.get("enabled") != "true":
            continue
        visible_values = {node.attrib.get("text", ""), node.attrib.get("content-desc", "")}
        if not accepted.intersection(visible_values):
            continue
        try:
            matches.append(parse_bounds(node.attrib.get("bounds", "")))
        except ValueError:
            continue
    return matches


def encode_adb_input(value: str) -> str:
    if not SAFE_INPUT_PATTERN.fullmatch(value):
        raise ValueError("Smoke input must use the bounded ADB-safe character set.")
    return value


class AdbClient:
    def __init__(self, executable: Path) -> None:
        if not executable.is_file():
            raise SmokeFailure("Workspace Android platform tools are missing.")
        self.executable = executable

    def run(self, *arguments: str, timeout: float = 20) -> bytes:
        try:
            result = subprocess.run(
                [str(self.executable), *arguments],
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
        return extract_hierarchy(self.run("exec-out", "uiautomator", "dump", "/dev/tty"))

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
        self.run("shell", "input", "text", encode_adb_input(value))
        # Hide the keyboard so the next field/button can be discovered and
        # tapped without relying on one manufacturer's IME action behavior.
        self.run("shell", "input", "keyevent", "KEYCODE_BACK")

    def scroll_forward(self) -> None:
        size_output = self.run("shell", "wm", "size").decode("utf-8", errors="replace")
        match = re.search(r"Physical size:\s*(\d+)x(\d+)", size_output)
        width, height = (1080, 1920) if match is None else (int(match.group(1)), int(match.group(2)))
        x = width // 2
        self.run(
            "shell",
            "input",
            "swipe",
            str(x),
            str(int(height * 0.75)),
            str(x),
            str(int(height * 0.35)),
            "250",
        )


class RegistrationSmoke:
    def __init__(self, adb: AdbClient, role: str, timeout_seconds: float) -> None:
        if role not in ROLE_PACKAGES:
            raise ValueError("Role must be passenger or driver.")
        if not 10 <= timeout_seconds <= 120:
            raise ValueError("Timeout must be between 10 and 120 seconds.")
        self.adb = adb
        self.role = role
        self.timeout_seconds = timeout_seconds
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
        while time.monotonic() < deadline:
            matches = matching_bounds(
                self.adb.hierarchy(),
                self.texts(resource_name),
                enabled_only=enabled_only,
            )
            if matches:
                return max(matches, key=lambda item: item.top) if prefer_bottom else matches[0]
            if scroll and scroll_attempts < 4:
                self.adb.scroll_forward()
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
        self.find("message_account_created")
        self.fill("password", password)
        self.tap_key("sign_in", prefer_bottom=True, enabled_only=True, scroll=True)

        # Product-role gates require a backend-authenticated session and roles.
        success_key = "where_to" if self.role == "passenger" else "apply_to_drive"
        self.find(success_key, scroll=True)
        return [
            {"id": "ANDROID_REGISTRATION", "result": "PASS", "authority": "BACKEND_CONFIRMED"},
            {"id": "ANDROID_LOGIN_ROLE_GATE", "result": "PASS", "authority": "BACKEND_CONFIRMED"},
        ]


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
        "single_authorized_device_verified": True,
    }


def build_evidence(role: str, profile: dict[str, object], journeys: list[dict[str, str]]) -> dict[str, object]:
    if role not in ROLE_PACKAGES or not journeys or any(item.get("result") != "PASS" for item in journeys):
        raise SmokeFailure("Android evidence requires a passing bounded role journey.")
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_level": "T4_ANDROID_REGISTRATION_DEVICE_EXECUTION",
        "phase": "T4",
        "result": "PASS",
        "data_classification": "TEST_DEVICE_METADATA_ONLY",
        "role": role.upper(),
        "supported_evidence_kinds": ["ANDROID_DEVICE_REPORT"],
        "phase_evidence_complete": False,
        "phase_accepted": False,
        "deployment_accepted": False,
        "device": profile,
        "journeys": journeys,
        "limitations": [
            "DEBUG_BUILD_ONLY",
            "REGISTRATION_AND_LOGIN_ONLY",
            "NO_IOS_OR_BROWSER_CLAIM",
            "NO_ACCESSIBILITY_OR_RTL_CLAIM",
            "NO_DEGRADED_NETWORK_OR_LIFECYCLE_CLAIM",
            "NO_CRASH_SYMBOLICATION_CLAIM",
            "NO_SCREENSHOT_OR_RAW_DEVICE_IDENTIFIER_CAPTURED",
            "NO_PHASE_OR_DEPLOYMENT_ACCEPTANCE_CLAIM",
        ],
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run TaxiMobile Android registration/login acceptance.")
    parser.add_argument("--adb", type=Path, required=True)
    parser.add_argument("--role", choices=sorted(ROLE_PACKAGES), required=True)
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
        adb = AdbClient(arguments.adb)
        journeys = RegistrationSmoke(
            adb,
            arguments.role,
            arguments.timeout_seconds,
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
    print(f"TaxiMobile {arguments.role} registration and login passed on Android.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
