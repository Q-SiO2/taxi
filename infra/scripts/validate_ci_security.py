"""Validate release-critical GitHub Actions supply-chain controls.

The validator intentionally uses only the Python standard library so it can run
before project dependencies are installed. It is not a general YAML parser; it
checks the committed workflow's immutable action references and the exact
security settings whose weakening would otherwise look like an ordinary CI edit.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
import sys


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = WORKSPACE_ROOT / ".github" / "workflows" / "ci.yml"
IOS_PROJECT_PATH = WORKSPACE_ROOT / "TaxiMobile" / "iosApp" / "iosApp.xcodeproj" / "project.pbxproj"
IOS_PACKAGE_RESOLVED_PATH = (
    WORKSPACE_ROOT
    / "TaxiMobile"
    / "iosApp"
    / "iosApp.xcodeproj"
    / "project.xcworkspace"
    / "xcshareddata"
    / "swiftpm"
    / "Package.resolved"
)

EXPECTED_IOS_PACKAGES = {
    "abseil-cpp-binary": (
        "https://github.com/google/abseil-cpp-binary.git",
        "1.2024072200.0",
        "bbe8b69694d7873315fd3a4ad41efe043e1c07c5",
    ),
    "app-check": (
        "https://github.com/google/app-check.git",
        "11.3.2",
        "97f7d74dd0e8f3d0fe5fc75cc8957aa73bdc948a",
    ),
    "firebase-ios-sdk": (
        "https://github.com/firebase/firebase-ios-sdk.git",
        "12.17.0",
        "33a468adfdb75b53f05a37e7c886ca7c962b5c17",
    ),
    "google-ads-on-device-conversion-ios-sdk": (
        "https://github.com/googleads/google-ads-on-device-conversion-ios-sdk",
        "3.6.1",
        "dc39082d8881109d35b94b1c122164c0e8d08a55",
    ),
    "googleappmeasurement": (
        "https://github.com/google/GoogleAppMeasurement.git",
        "12.17.0",
        "fceaffa07d22dcd5624d3639fd970351a4a5ad8c",
    ),
    "googledatatransport": (
        "https://github.com/google/GoogleDataTransport.git",
        "10.1.1",
        "ba3358d3c3dbae8ef230b58a46b97ad65e84e974",
    ),
    "googleutilities": (
        "https://github.com/google/GoogleUtilities.git",
        "8.1.3",
        "92c8f6dc3ac375d6febdfcb3db68bc3d10633db3",
    ),
    "grpc-binary": (
        "https://github.com/google/grpc-binary.git",
        "1.69.1",
        "75b31c842f664a0f46a2e590a570e370249fd8f6",
    ),
    "gtm-session-fetcher": (
        "https://github.com/google/gtm-session-fetcher.git",
        "5.3.1",
        "724a52eea6329b7e12d3ad8300d76ca9f3895fcc",
    ),
    "interop-ios-for-google-sdks": (
        "https://github.com/google/interop-ios-for-google-sdks.git",
        "101.0.0",
        "040d087ac2267d2ddd4cca36c757d1c6a05fdbfe",
    ),
    "leveldb": (
        "https://github.com/firebase/leveldb.git",
        "1.22.5",
        "a0bc79961d7be727d258d33d5a6b2f1023270ba1",
    ),
    "maplibre-gl-native-distribution": (
        "https://github.com/maplibre/maplibre-gl-native-distribution.git",
        "6.25.1",
        "40e1a0db6d055abf8a1b6e2f6127a8bb6e895cf8",
    ),
    "nanopb": (
        "https://github.com/firebase/nanopb.git",
        "2.30910.1",
        "3851d94a41890dea16dc3db34caf60e585cb4163",
    ),
    "promises": (
        "https://github.com/google/promises.git",
        "2.4.1",
        "f4a19a3c313dc2616c70bb49d29a799fb16be837",
    ),
}

USES_PATTERN = re.compile(r"^\s+(?:-\s+)?uses:\s+([^\s#]+)", re.MULTILINE)
PINNED_ACTION_PATTERN = re.compile(r"^[^/@\s]+/[^@\s]+@[0-9a-f]{40}$")


class CiSecurityError(RuntimeError):
    """Raised when a release-critical CI invariant is absent or weakened."""


def validate_ios_package_lock(package_lock: str, xcode_project: str) -> None:
    """Require a reviewed, revision-pinned SwiftPM graph matching the Xcode roots."""

    try:
        document = json.loads(package_lock)
    except (TypeError, json.JSONDecodeError) as exc:
        raise CiSecurityError("The iOS Package.resolved file is not valid JSON.") from exc

    if document.get("version") != 2:
        raise CiSecurityError(
            "The iOS Package.resolved file must use the reviewed version-2 lock format."
        )
    pins = document.get("pins")
    if not isinstance(pins, list):
        raise CiSecurityError("The iOS Package.resolved file has no pins list.")

    actual: dict[str, tuple[str | None, str | None, str | None]] = {}
    for pin in pins:
        if not isinstance(pin, dict) or not isinstance(pin.get("state"), dict):
            raise CiSecurityError("The iOS Package.resolved file contains a malformed pin.")
        identity = pin.get("identity")
        if not isinstance(identity, str) or identity in actual:
            raise CiSecurityError(
                "The iOS Package.resolved file contains a missing or duplicate identity."
            )
        if pin.get("kind") != "remoteSourceControl":
            raise CiSecurityError(f"The iOS package {identity} is not remote-source pinned.")
        state = pin["state"]
        if state.get("branch") is not None:
            raise CiSecurityError(f"The iOS package {identity} is pinned to a mutable branch.")
        actual[identity] = (
            pin.get("location"),
            state.get("version"),
            state.get("revision"),
        )

    if set(actual) != set(EXPECTED_IOS_PACKAGES):
        missing = sorted(set(EXPECTED_IOS_PACKAGES) - set(actual))
        unexpected = sorted(set(actual) - set(EXPECTED_IOS_PACKAGES))
        raise CiSecurityError(
            "The iOS package lock does not match the reviewed graph: "
            f"missing={missing}, unexpected={unexpected}."
        )

    for identity, expected in EXPECTED_IOS_PACKAGES.items():
        if actual[identity] != expected:
            raise CiSecurityError(
                f"The iOS package {identity} location, version, or revision changed "
                "without updating the reviewed lock contract."
            )
        revision = expected[2]
        if re.fullmatch(r"[0-9a-f]{40}", revision) is None:
            raise CiSecurityError(f"The iOS package {identity} has no immutable revision.")

    for identity in ("firebase-ios-sdk", "maplibre-gl-native-distribution"):
        location, version, _ = EXPECTED_IOS_PACKAGES[identity]
        root_pattern = re.compile(
            rf'repositoryURL = "{re.escape(location)}";\s*'
            rf'requirement = \{{\s*kind = exactVersion;\s*version = {re.escape(version)};\s*\}};',
            re.MULTILINE,
        )
        if root_pattern.search(xcode_project) is None:
            raise CiSecurityError(
                f"The Xcode root requirement for {identity} no longer matches Package.resolved."
            )


def _action_block(workflow: str, action: str) -> str:
    lines = workflow.splitlines()
    needle = f"uses: {action}@"
    matching = [index for index, line in enumerate(lines) if needle in line]
    if len(matching) != 1:
        raise CiSecurityError(
            f"Expected exactly one {action} step, found {len(matching)}."
        )
    start = matching[0]
    step_indent = len(lines[start]) - len(lines[start].lstrip())
    end = start + 1
    while end < len(lines):
        line = lines[end]
        if line.strip():
            indent = len(line) - len(line.lstrip())
            if indent <= step_indent and line.lstrip().startswith("-"):
                break
        end += 1
    return "\n".join(lines[start:end])


def _require(block: str, pattern: str, message: str) -> None:
    if re.search(pattern, block, flags=re.MULTILINE) is None:
        raise CiSecurityError(message)


def validate_ci_security(workflow: str) -> None:
    try:
        package_lock = IOS_PACKAGE_RESOLVED_PATH.read_text(encoding="utf-8")
        xcode_project = IOS_PROJECT_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        raise CiSecurityError(
            "The reviewed iOS Swift package lock and Xcode project must be committed."
        ) from exc
    validate_ios_package_lock(package_lock, xcode_project)

    action_references = USES_PATTERN.findall(workflow)
    if not action_references:
        raise CiSecurityError("The CI workflow contains no external action references.")
    mutable = [
        reference
        for reference in action_references
        if not reference.startswith("./") and PINNED_ACTION_PATTERN.fullmatch(reference) is None
    ]
    if mutable:
        raise CiSecurityError(
            "Every external action must use a full immutable commit SHA; mutable: "
            + ", ".join(sorted(mutable))
        )

    ios_package_cache = _action_block(workflow, "actions/cache")
    for pattern, message in (
        (
            r"^\s+path:\s+\$\{\{ runner\.temp \}\}/taximobile-ios-swift-packages\s*$",
            "The iOS SwiftPM cache must contain only the dedicated package directory.",
        ),
        (
            r"^\s+key:\s+taximobile-ios-spm-\$\{\{ runner\.os \}\}-xcode-26\.2-"
            r"\$\{\{ hashFiles\('TaxiMobile/iosApp/iosApp\.xcodeproj/"
            r"project\.xcworkspace/xcshareddata/swiftpm/Package\.resolved'\) \}\}\s*$",
            "The iOS SwiftPM cache key must be bound to Xcode and Package.resolved.",
        ),
    ):
        _require(ios_package_cache, pattern, message)

    dependency_review = _action_block(workflow, "actions/dependency-review-action")
    _require(
        dependency_review,
        r"^\s+fail-on-severity:\s+high\s*$",
        "Dependency review must reject newly introduced high and critical findings.",
    )
    if re.search(r"^\s+warn-only:\s+true\s*$", dependency_review, re.MULTILINE):
        raise CiSecurityError("Dependency review must not set warn-only true.")

    dependency_submission = _action_block(workflow, "gradle/actions/dependency-submission")
    _require(
        dependency_submission,
        r"^\s+build-root-directory:\s+TaxiMobile\s*$",
        "Gradle dependency submission must resolve the TaxiMobile build.",
    )
    _require(
        dependency_submission,
        r"^\s+dependency-graph:\s+generate-and-submit\s*$",
        "Gradle dependency graph generation must submit its resolved graph.",
    )

    sbom = _action_block(workflow, "anchore/sbom-action")
    for pattern, message in (
        (r"^\s+image:\s+taximobile-api:ci\s*$", "SBOM must scan the built backend image."),
        (r"^\s+format:\s+spdx-json\s*$", "Backend SBOM must use SPDX JSON."),
        (
            r"^\s+output-file:\s+/tmp/taximobile-api\.spdx\.json\s*$",
            "Backend SBOM output path changed without updating provenance binding.",
        ),
        (r"^\s+upload-artifact:\s+true\s*$", "Backend SBOM must be retained as evidence."),
        (
            r"^\s+upload-release-assets:\s+false\s*$",
            "CI verification must not publish an unapproved release asset.",
        ),
    ):
        _require(sbom, pattern, message)

    trivy = _action_block(workflow, "aquasecurity/trivy-action")
    for pattern, message in (
        (r"^\s+image-ref:\s+taximobile-api:ci\s*$", "Trivy must scan the built backend image."),
        (r'^\s+exit-code:\s+["\']1["\']\s*$', "The image vulnerability scan must block CI."),
        (r"^\s+ignore-unfixed:\s+false\s*$", "High/critical unfixed findings must not be hidden."),
        (r"^\s+vuln-type:\s+os,library\s*$", "Both OS and library vulnerabilities must be scanned."),
        (r"^\s+severity:\s+CRITICAL,HIGH\s*$", "The image gate must include high and critical severity."),
    ):
        _require(trivy, pattern, message)

    required_provenance = (
        "--artifact /tmp/taximobile-api.spdx.json",
        "--output /tmp/taximobile-backend-evidence.json",
    )
    for snippet in required_provenance:
        if snippet not in workflow:
            raise CiSecurityError(
                f"Backend image evidence is not bound to its SBOM: missing {snippet}."
            )

    contract_inventory_requirements = (
        "python ../infra/scripts/generate_source_contract_inventory.py",
        "--output /tmp/taximobile-source-contract-inventory.json",
        "--artifact /tmp/taximobile-source-contract-inventory.json",
        "cat /tmp/taximobile-source-contract-inventory.json",
    )
    missing_contract_inventory = [
        snippet for snippet in contract_inventory_requirements if snippet not in workflow
    ]
    if missing_contract_inventory:
        raise CiSecurityError(
            "Generated API/migration/permission inventory is not retained in the "
            f"candidate evidence: missing {missing_contract_inventory[0]}."
        )

    simulated_persona_requirements = (
        "python ../infra/scripts/run_simulated_persona_suite.py",
        "--output /tmp/taximobile-t2-simulated-personas.json",
        "--junit-output /tmp/taximobile-t2-simulated-personas.junit.xml",
        "--artifact /tmp/taximobile-t2-simulated-personas.json",
        "--artifact /tmp/taximobile-t2-simulated-personas.junit.xml",
        "cat /tmp/taximobile-t2-simulated-personas.json",
        "cat /tmp/taximobile-t2-simulated-personas.junit.xml",
        "This result does not accept T2 or any deployment phase.",
    )
    missing_simulated_persona = [
        snippet for snippet in simulated_persona_requirements if snippet not in workflow
    ]
    if missing_simulated_persona:
        raise CiSecurityError(
            "The bounded T2 simulated-persona report is not executed, limitation-"
            f"marked, retained, and source-bound: missing {missing_simulated_persona[0]}."
        )

    t3_system_requirements = (
        "python -m pytest --junitxml=/tmp/taximobile-t3-full-backend.junit.xml",
        "python ../infra/scripts/collect_t3_database_metadata.py",
        "--authority-mode EPHEMERAL_CI_SERVICE_ROLE",
        "--database-lifecycle EPHEMERAL_SERVICE_DATABASE",
        "--output /tmp/taximobile-t3-database-metadata.json",
        "python ../infra/scripts/run_t3_backup_restore_rehearsal.py",
        "--maintenance-user taximobile",
        "--output /tmp/taximobile-t3-backup-restore.json",
        "python ../infra/scripts/generate_t3_system_report.py",
        "--junit /tmp/taximobile-t3-full-backend.junit.xml",
        "--database-metadata /tmp/taximobile-t3-database-metadata.json",
        "--backup-restore /tmp/taximobile-t3-backup-restore.json",
        "--output /tmp/taximobile-t3-system-evidence.json",
        "--artifact /tmp/taximobile-t3-full-backend.junit.xml",
        "--artifact /tmp/taximobile-t3-database-metadata.json",
        "--artifact /tmp/taximobile-t3-backup-restore.json",
        "--artifact /tmp/taximobile-t3-system-evidence.json",
        "cat /tmp/taximobile-t3-system-evidence.json",
        "cat /tmp/taximobile-t3-database-metadata.json",
        "cat /tmp/taximobile-t3-backup-restore.json",
        "This complete evidence set does not accept T3 or deployment; formal engineering sign-off remains required.",
    )
    missing_t3_system = [snippet for snippet in t3_system_requirements if snippet not in workflow]
    if missing_t3_system:
        raise CiSecurityError(
            "The bounded T3 full-system report is not executed, limitation-marked, "
            f"retained, and source-bound: missing {missing_t3_system[0]}."
        )

    web_candidate_requirements = (
        "python ../infra/scripts/package_web_release.py",
        "python ../infra/scripts/run_t4_browser_smoke.py",
        "--browser chrome",
        '--output "${RUNNER_TEMP}/taximobile-t4-browser-smoke.json"',
        '--artifact "${RUNNER_TEMP}/taximobile-web-release/release-manifest.json"',
        '--artifact "${RUNNER_TEMP}/taximobile-t4-browser-smoke.json"',
        '--output "${RUNNER_TEMP}/taximobile-web-evidence.json"',
        'cat "${RUNNER_TEMP}/taximobile-web-release/release-manifest.json"',
        'cat "${RUNNER_TEMP}/taximobile-t4-browser-smoke.json"',
        'cat "${RUNNER_TEMP}/taximobile-web-evidence.json"',
        "does not complete any T4 browser case or accept deployment",
        "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
        "taximobile-t4-browser-smoke-artifacts",
    )
    missing_web_candidate = [
        snippet for snippet in web_candidate_requirements if snippet not in workflow
    ]
    if missing_web_candidate:
        raise CiSecurityError(
            "The packaged web manifest is not bound to source and retained in the "
            f"CI run summary: missing {missing_web_candidate[0]}."
        )

    android_candidate_requirements = (
        "-ManifestPath \"$env:RUNNER_TEMP/taximobile-android-verification-manifest.json\"",
        '--artifact "${RUNNER_TEMP}/taximobile-android-verification-manifest.json"',
        '--output "${RUNNER_TEMP}/taximobile-android-evidence.json"',
        'cat "${RUNNER_TEMP}/taximobile-android-verification-manifest.json"',
        'cat "${RUNNER_TEMP}/taximobile-android-evidence.json"',
        "unsigned/providerless verification outputs, not distributable releases",
    )
    missing_android_candidate = [
        snippet for snippet in android_candidate_requirements if snippet not in workflow
    ]
    if missing_android_candidate:
        raise CiSecurityError(
            "Android verification artifacts are not limitation-marked, bound to "
            f"source, and retained in the CI run summary: missing "
            f"{missing_android_candidate[0]}."
        )

    mobile_diagnostic_requirements = (
        "Run Android shared tests with bounded failure capture",
        "./gradlew --no-daemon :shared:jvmTest :shared:testAndroidHostTest --stacktrace",
        'tee "${RUNNER_TEMP}/taximobile-mobile-shared-tests.log"',
        "Publish redacted Android shared-test failure annotation",
        "python ../infra/scripts/emit_ci_failure_annotation.py",
        '--input "${RUNNER_TEMP}/taximobile-mobile-shared-tests.log"',
        '--title "TaxiMobile Android shared-test failure"',
    )
    missing_mobile_diagnostic = [
        snippet for snippet in mobile_diagnostic_requirements if snippet not in workflow
    ]
    if missing_mobile_diagnostic:
        raise CiSecurityError(
            "Android shared-test failures must publish a bounded redacted diagnostic: "
            f"missing {missing_mobile_diagnostic[0]}."
        )

    ios_candidate_requirements = (
        "ios-shared:\n    runs-on: macos-15\n    timeout-minutes: 45",
        "Compile shared iOS simulator production and test sources with bounded failure capture",
        "./gradlew --no-daemon :shared:compileTestKotlinIosSimulatorArm64 --stacktrace",
        'tee "${RUNNER_TEMP}/taximobile-ios-shared.log"',
        "python ../infra/scripts/emit_ci_failure_annotation.py",
        '--input "${RUNNER_TEMP}/taximobile-ios-shared.log"',
        '--title "TaxiMobile iOS shared Gradle failure"',
        "Record upstream iOS test-link limitation",
        "MapLibre Compose 0.14.0 publishes an invalid absolute framework path (upstream issue #824)",
        "this run does not claim iOS test execution",
        "python scripts/generate_ios_verification_manifest.py",
        '--products-dir "${RUNNER_TEMP}/taximobile-ios-derived/Build/Products/Release-iphonesimulator"',
        '--artifact "${RUNNER_TEMP}/taximobile-ios-verification-manifest.json"',
        '--output "${RUNNER_TEMP}/taximobile-ios-evidence.json"',
        'cat "${RUNNER_TEMP}/taximobile-ios-verification-manifest.json"',
        'cat "${RUNNER_TEMP}/taximobile-ios-evidence.json"',
        "unsigned simulator/providerless verification outputs, not App Store releases",
    )
    missing_ios_candidate = [
        snippet for snippet in ios_candidate_requirements if snippet not in workflow
    ]
    if missing_ios_candidate:
        raise CiSecurityError(
            "iOS simulator artifacts are not limitation-marked, bound to source, "
            f"and retained in the CI run summary: missing {missing_ios_candidate[0]}."
        )
    if workflow.count(
        '-clonedSourcePackagesDirPath "${RUNNER_TEMP}/taximobile-ios-swift-packages"'
    ) != 2:
        raise CiSecurityError(
            "Both iOS role builds must use the cache-isolated Swift package directory."
        )
    if workflow.count("-disableAutomaticPackageResolution") != 2:
        raise CiSecurityError(
            "Both iOS role builds must reject automatic Swift package resolution."
        )

    monitoring_diagnostic_requirements = (
        "Parse monitoring configuration with pinned official tools",
        'exec > >(tee "${RUNNER_TEMP}/taximobile-monitoring-validation.log") 2>&1',
        "Publish redacted monitoring-tool failure annotation",
        '--input "${RUNNER_TEMP}/taximobile-monitoring-validation.log"',
        '--title "TaxiMobile monitoring validation failure"',
    )
    missing_monitoring_diagnostic = [
        snippet for snippet in monitoring_diagnostic_requirements if snippet not in workflow
    ]
    if missing_monitoring_diagnostic:
        raise CiSecurityError(
            "Monitoring CI failures must publish a bounded redacted diagnostic: "
            f"missing {missing_monitoring_diagnostic[0]}."
        )
    monitoring_annotation_block = (
        "      - name: Publish redacted monitoring-tool failure annotation\n"
        "        if: failure()\n"
        "        run: >-\n"
        "          python ../infra/scripts/emit_ci_failure_annotation.py\n"
        "          --input \"${RUNNER_TEMP}/taximobile-monitoring-validation.log\"\n"
        "          --title \"TaxiMobile monitoring validation failure\""
    )
    if monitoring_annotation_block not in workflow:
        raise CiSecurityError(
            "Monitoring CI failures must publish a bounded redacted diagnostic "
            "from the backend working directory."
        )

    if 'assert len(dashboard["panels"]) == 26' not in workflow:
        raise CiSecurityError(
            "The Grafana runtime smoke must verify all 26 reviewed operations panels."
        )

    if workflow.count("python infra/scripts/validate_test_phase_evidence.py") != 1:
        raise CiSecurityError(
            "The T0-T10 phase catalog and evidence template must be validated once "
            "in the source job."
        )

    if workflow.count("python infra/scripts/run_simulated_persona_suite.py --validate-only") != 1:
        raise CiSecurityError(
            "The T2 simulated-persona catalog must be validated once in the "
            "dependency-free source job."
        )

    if workflow.count("python infra/scripts/validate_t4_lab_evidence.py") != 1:
        raise CiSecurityError(
            "The T4 device/browser laboratory catalog and no-claim template must "
            "be validated once in the dependency-free source job."
        )

    if workflow.count("python infra/scripts/validate_production_environment_inventory.py") != 1:
        raise CiSecurityError(
            "The GAP-002 production environment inventory and no-acceptance template "
            "must be validated once in the dependency-free source job."
        )

    if workflow.count("python infra/scripts/validate_managed_postgis_evidence.py") != 1:
        raise CiSecurityError(
            "The GAP-003 managed PostGIS evidence and no-acceptance template must "
            "be validated once in the dependency-free source job."
        )

    if workflow.count("python infra/scripts/validate_pilot_city_launch_approval.py") != 1:
        raise CiSecurityError(
            "The GAP-004 pilot-city approval and no-acceptance template must "
            "be validated once in the dependency-free source job."
        )

    if workflow.count("python infra/scripts/validate_operations_identity_governance.py") != 1:
        raise CiSecurityError(
            "The GAP-005 operations identity governance and no-acceptance template "
            "must be validated once in the dependency-free source job."
        )

    if workflow.count("python infra/scripts/validate_maps_routing_navigation.py") != 1:
        raise CiSecurityError(
            "The GAP-006 maps/routing/navigation evidence and no-acceptance template "
            "must be validated once in the dependency-free source job."
        )

    if workflow.count("node scripts/test-web-compatibility-loader.mjs") != 1:
        raise CiSecurityError(
            "The fail-closed web compatibility loader runtime scenarios must run "
            "once in the web job."
        )

    legacy_admin_gates = (
        "python infra/scripts/validate_legacy_admin_retirement.py",
        "python ../infra/scripts/validate_legacy_admin_retirement.py",
    )
    missing_legacy_admin_gates = [
        command for command in legacy_admin_gates if workflow.count(command) != 1
    ]
    if missing_legacy_admin_gates:
        raise CiSecurityError(
            "Legacy-administration caller validation must run once in both the "
            "source and backend jobs."
        )


def main() -> int:
    try:
        validate_ci_security(WORKFLOW_PATH.read_text(encoding="utf-8"))
    except (OSError, CiSecurityError) as error:
        print(f"CI security validation failed: {error}", file=sys.stderr)
        return 1
    print(
        "CI security validation passed: immutable actions, dependency review, "
        "image SBOM/provenance, web/mobile candidate binding, source-contract inventory, "
        "test-phase/T2 persona/T3 system/T4 lab evidence controls, GAP-002 environment "
        "inventory, GAP-003 managed PostGIS evidence, GAP-004 pilot-city approval, "
        "GAP-005 operations identity governance, GAP-006 maps/routing/navigation "
        "evidence, web compatibility runtime "
        "coverage, and blocking scan are present."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
