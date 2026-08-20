"""Drive a bounded registration/login smoke through an installed Android debug app.

The harness uses Android's built-in accessibility hierarchy and input commands.
It does not capture screenshots, write device files, print credentials, or infer
success from local UI state: registration and the subsequent login must both be
confirmed by backend-driven screens.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
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

    def run(self) -> None:
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


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run TaxiMobile Android registration/login acceptance.")
    parser.add_argument("--adb", type=Path, required=True)
    parser.add_argument("--role", choices=sorted(ROLE_PACKAGES), required=True)
    parser.add_argument("--timeout-seconds", type=float, default=30)
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    try:
        RegistrationSmoke(
            AdbClient(arguments.adb),
            arguments.role,
            arguments.timeout_seconds,
        ).run()
    except (SmokeFailure, ValueError) as error:
        print(f"Android registration smoke failed: {error}")
        return 1
    print(f"TaxiMobile {arguments.role} registration and login passed on Android.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
