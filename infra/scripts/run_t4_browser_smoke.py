"""Run a bounded real-browser smoke against a reviewed TaxiMobile web release.

This collector intentionally covers only the release boot boundary. It serves a
packaged release from loopback, supplies synthetic compatibility responses, and
launches installed Chrome and/or Firefox binaries without credentials. The test
origin is loopback, but this collector does not independently firewall browser
egress. The resulting report and screenshots are partial T4 evidence; they never
satisfy a catalog case, accept T4, or accept deployment.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import platform
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Callable, Iterable, Sequence
from urllib.parse import unquote, urlsplit

from package_web_release import DEFAULT_INPUT, WebPackageError, validate_distribution


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_BROWSER_FAMILIES = ("CHROME", "FIREFOX", "SAFARI")
SUPPORTED_RUNNER_FAMILIES = ("CHROME", "FIREFOX")
CLIENT_VERSION_HEADER = "X-TaxiMobile-Version"
CLIENT_BUILD_HEADER = "X-TaxiMobile-Build"
CLIENT_SURFACE_HEADER = "X-TaxiMobile-Client"
MAX_CAPTURE_LINES = 2_000
MAX_REQUESTS = 512
LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "font-src 'self'; connect-src 'self'; object-src 'none'; "
        "base-uri 'none'; frame-ancestors 'none'"
    ),
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


@dataclass(frozen=True)
class BrowserInstallation:
    family: str
    executable: Path
    version: str


@dataclass(frozen=True)
class Scenario:
    identifier: str
    route: str
    compatibility_status: str
    expected_surface: str
    expect_application_boot: bool


SCENARIOS = (
    Scenario("SUPPORTED_APPLICANT", "/apply", "SUPPORTED", "WEB_APPLICANT", True),
    Scenario("SUPPORTED_OPERATIONS", "/operations", "SUPPORTED", "WEB_OPERATIONS", True),
    Scenario("UPGRADE_REQUIRED", "/operations", "UPGRADE_REQUIRED", "WEB_OPERATIONS", False),
    Scenario("PREFLIGHT_FAILURE", "/apply", "HTTP_503", "WEB_APPLICANT", False),
)


class BrowserSmokeError(RuntimeError):
    """Raised when the bounded browser collector cannot run safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _bounded_text(value: str, *, maximum: int = 160) -> str:
    normalized = " ".join(value.replace("\x00", "").split())
    printable = "".join(character for character in normalized if character.isprintable())
    return printable[:maximum]


def _candidate_paths(family: str) -> list[Path]:
    if family == "CHROME":
        names = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome")
        env_name = "TAXIMOBILE_CHROME_BINARY"
        windows = (
            Path(os.environ.get("ProgramFiles", "")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("ProgramFiles(x86)", "")) / "Google/Chrome/Application/chrome.exe",
        )
    elif family == "FIREFOX":
        names = ("firefox", "firefox-esr")
        env_name = "TAXIMOBILE_FIREFOX_BINARY"
        windows = (
            Path(os.environ.get("ProgramFiles", "")) / "Mozilla Firefox/firefox.exe",
            Path(os.environ.get("ProgramFiles(x86)", "")) / "Mozilla Firefox/firefox.exe",
        )
    else:
        return []
    result: list[Path] = []
    configured = os.environ.get(env_name)
    if configured:
        result.append(Path(configured))
    for name in names:
        discovered = shutil.which(name)
        if discovered:
            result.append(Path(discovered))
    if os.name == "nt":
        result.extend(windows)
    unique: list[Path] = []
    seen: set[str] = set()
    for path in result:
        key = str(path).casefold()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def _browser_version(executable: Path) -> str:
    if os.name == "nt":
        try:
            version_environment = os.environ.copy()
            version_environment["TAXIMOBILE_BROWSER_VERSION_PATH"] = str(executable)
            completed = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    "(Get-Item -LiteralPath $env:TAXIMOBILE_BROWSER_VERSION_PATH).VersionInfo.ProductVersion",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
                env=version_environment,
            )
            if completed.returncode == 0 and completed.stdout.strip():
                return _bounded_text(completed.stdout)
        except (OSError, subprocess.SubprocessError):
            pass
    try:
        completed = subprocess.run(
            [str(executable), "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise BrowserSmokeError(f"Could not read browser version for {executable.name}: {error}") from error
    version = _bounded_text(completed.stdout or completed.stderr)
    if completed.returncode != 0 or not version:
        raise BrowserSmokeError(f"Could not read browser version for {executable.name}.")
    return version


def discover_browser(family: str) -> BrowserInstallation | None:
    if family not in SUPPORTED_RUNNER_FAMILIES:
        return None
    for path in _candidate_paths(family):
        if path.is_file():
            return BrowserInstallation(family, path.resolve(), _browser_version(path.resolve()))
    return None


def _release_identity(release_dir: Path) -> dict[str, Any]:
    records: list[tuple[str, int, str]] = []
    for path in sorted(release_dir.rglob("*")):
        if path.is_file():
            records.append((path.relative_to(release_dir).as_posix(), path.stat().st_size, _sha256(path)))
    aggregate = hashlib.sha256()
    for relative, size, digest in records:
        aggregate.update(f"{relative}\0{size}\0{digest}\n".encode("utf-8"))
    manifest = release_dir / "release-manifest.json"
    return {
        "file_count": len(records),
        "aggregate_sha256": aggregate.hexdigest(),
        "release_manifest_sha256": _sha256(manifest) if manifest.is_file() else None,
    }


def _png_metadata(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != PNG_SIGNATURE or data[12:16] != b"IHDR":
        raise BrowserSmokeError(f"Browser screenshot is not a valid PNG: {path.name}")
    width, height = struct.unpack(">II", data[16:24])
    if width < 320 or height < 240:
        raise BrowserSmokeError(f"Browser screenshot is unexpectedly small: {path.name}")
    return {
        "reference": path.name,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "width": width,
        "height": height,
    }


class _LabState:
    def __init__(self, release_dir: Path) -> None:
        self.release_dir = release_dir.resolve()
        self.scenario = SCENARIOS[0]
        self.requests: list[dict[str, Any]] = []
        self.lock = threading.Lock()

    def select(self, scenario: Scenario) -> None:
        with self.lock:
            self.scenario = scenario
            self.requests = []

    def observe(self, handler: BaseHTTPRequestHandler, path: str) -> None:
        with self.lock:
            if len(self.requests) >= MAX_REQUESTS:
                return
            self.requests.append(
                {
                    "method": handler.command,
                    "path": path[:400],
                    "client_surface": _bounded_text(handler.headers.get(CLIENT_SURFACE_HEADER, "")),
                    "client_version": _bounded_text(handler.headers.get(CLIENT_VERSION_HEADER, "")),
                    "client_build": _bounded_text(handler.headers.get(CLIENT_BUILD_HEADER, "")),
                    "user_agent": _bounded_text(handler.headers.get("User-Agent", ""), maximum=300),
                }
            )

    def snapshot(self) -> list[dict[str, Any]]:
        with self.lock:
            return [dict(item) for item in self.requests]


def _handler_for(state: _LabState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "TaxiMobileT4Lab/1"
        sys_version = ""

        def log_message(self, _format: str, *_args: object) -> None:
            return

        def _headers(self, status: HTTPStatus, content_type: str, length: int) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(length))
            self.send_header("Cache-Control", "no-store")
            for name, value in SECURITY_HEADERS.items():
                self.send_header(name, value)
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
            raw_path = unquote(urlsplit(self.path).path)
            state.observe(self, raw_path)
            if raw_path == "/api/v1/client-compatibility":
                scenario = state.scenario
                if scenario.compatibility_status == "HTTP_503":
                    body = b'{"detail":"compatibility service unavailable"}'
                    self._headers(HTTPStatus.SERVICE_UNAVAILABLE, "application/json", len(body))
                else:
                    payload: dict[str, Any] = {
                        "status": scenario.compatibility_status,
                        "minimum_version": "1.0.0",
                        "policy_revision": "t4-browser-lab-v1",
                    }
                    if scenario.compatibility_status == "UPGRADE_REQUIRED":
                        payload["minimum_version"] = "2.0.0"
                    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
                    self._headers(HTTPStatus.OK, "application/json", len(body))
                self.wfile.write(body)
                return

            requested = raw_path.lstrip("/")
            if not requested or raw_path in {"/apply", "/operations"} or raw_path.startswith("/apply/"):
                requested = "index.html"
            candidate = (state.release_dir / requested).resolve()
            try:
                candidate.relative_to(state.release_dir)
            except ValueError:
                self._not_found()
                return
            if not candidate.is_file():
                self._not_found()
                return
            body = candidate.read_bytes()
            content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
            if candidate.suffix == ".wasm":
                content_type = "application/wasm"
            self._headers(HTTPStatus.OK, content_type, len(body))
            self.wfile.write(body)

        def _not_found(self) -> None:
            body = b'{"detail":"not found"}'
            self._headers(HTTPStatus.NOT_FOUND, "application/json", len(body))
            self.wfile.write(body)

    return Handler


class BrowserLabServer:
    def __init__(self, release_dir: Path, port: int) -> None:
        self.state = _LabState(release_dir)
        try:
            self.server = ThreadingHTTPServer(("127.0.0.1", port), _handler_for(self.state))
        except OSError as error:
            raise BrowserSmokeError(
                f"Loopback port {port} is unavailable. Stop the local backend or choose another "
                "port only after updating the local compatibility-loader contract: {error}"
            ) from error
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self) -> BrowserLabServer:
        self.thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def _browser_command(
    installation: BrowserInstallation,
    *,
    profile: Path,
    screenshot: Path,
    url: str,
    virtual_time_ms: int,
) -> list[str]:
    if installation.family == "CHROME":
        return [
            str(installation.executable),
            "--headless=new",
            "--disable-gpu",
            "--disable-background-networking",
            "--disable-component-update",
            "--disable-default-apps",
            "--disable-extensions",
            "--disable-sync",
            "--metrics-recording-only",
            "--no-default-browser-check",
            "--no-first-run",
            "--safebrowsing-disable-auto-update",
            f"--user-data-dir={profile.resolve()}",
            "--window-size=1280,900",
            f"--virtual-time-budget={virtual_time_ms}",
            f"--screenshot={screenshot.resolve()}",
            url,
        ]
    if installation.family == "FIREFOX":
        return [
            str(installation.executable),
            "--headless",
            "--no-remote",
            "--profile",
            str(profile),
            "--window-size",
            "1280,900",
            url,
        ]
    raise BrowserSmokeError(f"Unsupported browser runner family: {installation.family}")


def _firefox_screenshot_command(
    installation: BrowserInstallation,
    *,
    profile: Path,
    screenshot: Path,
    url: str,
) -> list[str]:
    if installation.family != "FIREFOX":
        raise BrowserSmokeError("The dedicated screenshot command is Firefox-only.")
    return [
        str(installation.executable),
        "--headless",
        "--no-remote",
        "--profile",
        str(profile),
        "--window-size",
        "1280,900",
        "--screenshot",
        str(screenshot.resolve()),
        url,
    ]


def _launch_browser(
    installation: BrowserInstallation,
    *,
    screenshot: Path,
    url: str,
    timeout_seconds: int,
    completion_probe: Callable[[], bool],
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="taximobile-t4-browser-", ignore_cleanup_errors=True) as directory:
        profile = Path(directory) / "profile"
        profile.mkdir()
        command = _browser_command(
            installation,
            profile=profile,
            screenshot=screenshot,
            url=url,
            virtual_time_ms=min(timeout_seconds * 1_000, 20_000),
        )
        controlled_termination = False
        observation_reached = False
        screenshot_capture_return_code: int | None = None
        try:
            if installation.family == "CHROME":
                try:
                    completed = subprocess.run(
                        command,
                        check=False,
                        capture_output=True,
                        text=True,
                        timeout=timeout_seconds,
                    )
                    timed_out = False
                    observation_reached = completion_probe()
                except subprocess.TimeoutExpired as error:
                    completed = subprocess.CompletedProcess(
                        command,
                        returncode=124,
                        stdout=error.stdout or "",
                        stderr=error.stderr or "",
                    )
                    timed_out = True
            else:
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                deadline = time.monotonic() + timeout_seconds
                while process.poll() is None and time.monotonic() < deadline:
                    if completion_probe():
                        observation_reached = True
                        # Retain a bounded interval in which an incorrectly late
                        # application boot can still be observed for blocked cases.
                        time.sleep(1.5)
                        break
                    time.sleep(0.1)
                timed_out = not observation_reached and process.poll() is None
                if process.poll() is None:
                    process.terminate()
                    controlled_termination = observation_reached
                try:
                    stdout, stderr = process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate(timeout=5)
                    controlled_termination = False
                completed = subprocess.CompletedProcess(
                    command,
                    returncode=process.returncode,
                    stdout=stdout,
                    stderr=stderr,
                )
                if observation_reached:
                    screenshot_command = _firefox_screenshot_command(
                        installation,
                        profile=profile,
                        screenshot=screenshot,
                        url=url,
                    )
                    try:
                        screenshot_capture = subprocess.run(
                            screenshot_command,
                            check=False,
                            capture_output=True,
                            text=True,
                            timeout=min(timeout_seconds, 20),
                        )
                        screenshot_capture_return_code = screenshot_capture.returncode
                    except subprocess.TimeoutExpired:
                        screenshot_capture_return_code = 124
        except OSError as error:
            raise BrowserSmokeError(f"Could not launch {installation.family}: {error}") from error
    stdout_lines = str(completed.stdout or "").splitlines()
    stderr_lines = str(completed.stderr or "").splitlines()
    return {
        "return_code": completed.returncode,
        "timed_out": timed_out,
        "controlled_termination": controlled_termination,
        "observation_reached": observation_reached,
        "screenshot_capture_return_code": screenshot_capture_return_code,
        "stdout_line_count": min(len(stdout_lines), MAX_CAPTURE_LINES),
        "stderr_line_count": min(len(stderr_lines), MAX_CAPTURE_LINES),
        "output_truncated": len(stdout_lines) > MAX_CAPTURE_LINES or len(stderr_lines) > MAX_CAPTURE_LINES,
    }


def evaluate_scenario(
    scenario: Scenario,
    requests: Sequence[dict[str, Any]],
    process: dict[str, Any],
    screenshot: Path,
) -> dict[str, Any]:
    compatibility = [item for item in requests if item.get("path") == "/api/v1/client-compatibility"]
    assets = {str(item.get("path")) for item in requests}
    app_loader_requested = "/webApp.js" in assets
    branch_assets = assets.intersection({"/originWasmWebApp.js", "/originJsWebApp.js"})
    identity_headers_match = bool(compatibility) and all(
        item.get("client_surface") == scenario.expected_surface
        and item.get("client_version") == "1.0.0"
        and item.get("client_build") == "1"
        for item in compatibility
    )
    screenshot_record: dict[str, Any] | None = None
    screenshot_error: str | None = None
    try:
        screenshot_record = _png_metadata(screenshot)
    except (OSError, BrowserSmokeError):
        # Evidence records a closed diagnostic code, never a host path emitted
        # by an operating-system exception.
        screenshot_error = "SCREENSHOT_NOT_RETAINED_OR_INVALID"
    observations = {
        "browser_process_completed": (
            process.get("timed_out") is False
            and (
                process.get("return_code") == 0
                or process.get("controlled_termination") is True
            )
        ),
        "compatibility_request_observed": bool(compatibility),
        "client_identity_headers_match": identity_headers_match,
        "application_loader_requested": app_loader_requested,
        "exactly_one_runtime_branch_requested": len(branch_assets) == 1,
        "application_remained_blocked": not app_loader_requested and not branch_assets,
        "screenshot_retained": screenshot_record is not None,
    }
    required = (
        "browser_process_completed",
        "compatibility_request_observed",
        "client_identity_headers_match",
        "screenshot_retained",
        "application_loader_requested" if scenario.expect_application_boot else "application_remained_blocked",
        "exactly_one_runtime_branch_requested" if scenario.expect_application_boot else "application_remained_blocked",
    )
    passed = all(observations[name] for name in required)
    return {
        "id": scenario.identifier,
        "route": scenario.route,
        "compatibility_response": scenario.compatibility_status,
        "expected_surface": scenario.expected_surface,
        "status": "PASS" if passed else "FAIL",
        "observations": observations,
        "runtime_branch": next(iter(branch_assets), None),
        "request_count": len(requests),
        "requested_paths": sorted(assets)[:80],
        "process": process,
        "screenshot": screenshot_record,
        "screenshot_error": screenshot_error,
    }


Launcher = Callable[..., dict[str, Any]]


def network_boundary_observed(scenario: Scenario, requests: Sequence[dict[str, Any]]) -> bool:
    compatibility = [item for item in requests if item.get("path") == "/api/v1/client-compatibility"]
    if not compatibility:
        return False
    if not all(
        item.get("client_surface") == scenario.expected_surface
        and item.get("client_version") == "1.0.0"
        and item.get("client_build") == "1"
        for item in compatibility
    ):
        return False
    paths = {str(item.get("path")) for item in requests}
    if not scenario.expect_application_boot:
        return True
    return "/webApp.js" in paths and len(
        paths.intersection({"/originWasmWebApp.js", "/originJsWebApp.js"})
    ) == 1


def collect_browser_smoke(
    release_dir: Path,
    *,
    installations: Sequence[BrowserInstallation],
    output: Path,
    artifact_dir: Path,
    candidate_label: str,
    port: int = 8000,
    timeout_seconds: int = 45,
    launcher: Launcher = _launch_browser,
) -> dict[str, Any]:
    if output.exists():
        raise BrowserSmokeError(f"Output already exists: {output}")
    if artifact_dir.exists():
        raise BrowserSmokeError(f"Artifact directory already exists: {artifact_dir}")
    if LABEL.fullmatch(candidate_label) is None:
        raise BrowserSmokeError("Candidate label must be 1-96 safe filename characters.")
    if not 1 <= port <= 65_535:
        raise BrowserSmokeError("Port must be between 1 and 65535.")
    if not 10 <= timeout_seconds <= 120:
        raise BrowserSmokeError("Browser timeout must be between 10 and 120 seconds.")
    if not installations:
        raise BrowserSmokeError("At least one installed browser is required.")
    families = [installation.family for installation in installations]
    if len(families) != len(set(families)) or any(
        family not in SUPPORTED_RUNNER_FAMILIES for family in families
    ):
        raise BrowserSmokeError("Browser installations must be unique Chrome/Firefox families.")
    release_dir = release_dir.resolve()
    try:
        distribution = validate_distribution(release_dir)
    except WebPackageError as error:
        raise BrowserSmokeError(f"Web release validation failed: {error}") from error
    if port != 8000:
        raise BrowserSmokeError(
            "The current localhost compatibility contract requires port 8000; a different port "
            "would not exercise the shipped loader."
        )

    artifact_dir.mkdir(parents=True)
    browser_results: list[dict[str, Any]] = []
    with BrowserLabServer(release_dir, port) as lab:
        for installation in installations:
            scenarios: list[dict[str, Any]] = []
            for scenario in SCENARIOS:
                lab.state.select(scenario)
                screenshot = artifact_dir / f"{installation.family.lower()}-{scenario.identifier.lower()}.png"
                started_at = _utc_now()
                process = launcher(
                    installation,
                    screenshot=screenshot,
                    url=f"http://127.0.0.1:{port}{scenario.route}",
                    timeout_seconds=timeout_seconds,
                    completion_probe=lambda selected=scenario: network_boundary_observed(
                        selected, lab.state.snapshot()
                    ),
                )
                scenarios.append(
                    {
                        **evaluate_scenario(scenario, lab.state.snapshot(), process, screenshot),
                        "started_at": started_at,
                    }
                )
            browser_results.append(
                {
                    "family": installation.family,
                    "version": installation.version,
                    "executable_name": installation.executable.name,
                    "status": "PASS" if all(item["status"] == "PASS" for item in scenarios) else "FAIL",
                    "scenarios": scenarios,
                }
            )

    passed = all(result["status"] == "PASS" for result in browser_results)
    executed_families = [result["family"] for result in browser_results]
    missing_families = [family for family in REQUIRED_BROWSER_FAMILIES if family not in executed_families]
    report = {
        "schema_version": 1,
        "phase": "T4",
        "evidence_kind": "BROWSER_COMPATIBILITY_REPORT",
        "evidence_level": "PARTIAL_REAL_BROWSER_BOOT_SMOKE",
        "status": "EXECUTED" if passed else "FAILED",
        "candidate_label": candidate_label,
        "executed_at": _utc_now(),
        "environment": {
            "operating_system": platform.system().upper(),
            "architecture": platform.machine().upper(),
            "test_origin_scope": "LOOPBACK_ONLY",
            "browser_egress_control": "NOT_INDEPENDENTLY_ENFORCED",
            "synthetic_compatibility_policy": True,
            "public_users": False,
            "live_money": False,
            "production_credentials": False,
            "real_personal_data": False,
        },
        "release": {
            **_release_identity(release_dir),
            "client_version": distribution["client_version"],
            "client_build": distribution["client_build"],
        },
        "required_browser_families": list(REQUIRED_BROWSER_FAMILIES),
        "executed_browser_families": executed_families,
        "missing_browser_families": missing_families,
        "browser_results": browser_results,
        "smoke_passed": passed,
        "covered_catalog_cases": [],
        "partial_catalog_cases": ["T4-WEB-001", "T4-WEB-006", "T4-WEB-008"],
        "phase_evidence_complete": False,
        "phase_accepted": False,
        "deployment_accepted": False,
        "limitations": [
            "BOOT_BOUNDARY_ONLY_NO_AUTH_SCOPE_DOCUMENT_HISTORY_OR_MUTATION_JOURNEYS",
            "BROWSER_EGRESS_NOT_INDEPENDENTLY_FIREWALLED",
            "SCREENSHOT_AND_NETWORK_OBSERVATIONS_DO_NOT_PROVE_ACCESSIBILITY_OR_VISUAL_ACCEPTANCE",
            "BROWSER_CONSOLE_AND_SOURCE_MAP_POLICY_REQUIRE_SEPARATE_RETAINED_EVIDENCE",
            "SAFARI_REQUIRES_MACOS_REAL_BROWSER_EXECUTION",
            "NO_T4_CATALOG_CASE_OR_PHASE_ACCEPTANCE_CLAIM",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return report


def _family(value: str) -> str:
    normalized = value.strip().upper()
    if normalized not in SUPPORTED_RUNNER_FAMILIES:
        raise argparse.ArgumentTypeError("browser must be chrome or firefox")
    return normalized


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--candidate-label", required=True)
    parser.add_argument("--browser", action="append", type=_family, dest="browsers")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--timeout-seconds", type=int, default=45)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    arguments = _parser().parse_args(list(argv) if argv is not None else None)
    artifact_dir = arguments.artifact_dir or arguments.output.with_name(
        f"{arguments.output.stem}-artifacts"
    )
    requested = arguments.browsers or list(SUPPORTED_RUNNER_FAMILIES)
    if len(requested) != len(set(requested)):
        print("T4 browser smoke failed: each browser family may be selected once.", file=sys.stderr)
        return 1
    installations: list[BrowserInstallation] = []
    missing: list[str] = []
    try:
        for family in requested:
            installation = discover_browser(family)
            if installation is None:
                missing.append(family)
            else:
                installations.append(installation)
    except BrowserSmokeError as error:
        print(f"T4 browser smoke failed: {error}", file=sys.stderr)
        return 1
    if missing:
        print(
            "T4 browser smoke failed: requested browser not installed: " + ", ".join(missing),
            file=sys.stderr,
        )
        return 1
    try:
        report = collect_browser_smoke(
            arguments.release_dir,
            installations=installations,
            output=arguments.output,
            artifact_dir=artifact_dir,
            candidate_label=arguments.candidate_label,
            port=arguments.port,
            timeout_seconds=arguments.timeout_seconds,
        )
    except (OSError, BrowserSmokeError) as error:
        print(f"T4 browser smoke failed: {error}", file=sys.stderr)
        return 1
    print(
        f"T4 partial real-browser smoke {report['status']}: "
        f"{len(installations)} browser families, {len(installations) * len(SCENARIOS)} scenarios; "
        "zero catalog-case, phase, or deployment acceptance claims."
    )
    return 0 if report["smoke_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
