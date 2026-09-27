"""Validate release-critical GitHub Actions supply-chain controls.

The validator intentionally uses only the Python standard library so it can run
before project dependencies are installed. It is not a general YAML parser; it
checks the committed workflow's immutable action references and the exact
security settings whose weakening would otherwise look like an ordinary CI edit.
"""

from __future__ import annotations

import re
from pathlib import Path
import sys


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = WORKSPACE_ROOT / ".github" / "workflows" / "ci.yml"

USES_PATTERN = re.compile(r"^\s+(?:-\s+)?uses:\s+([^\s#]+)", re.MULTILINE)
PINNED_ACTION_PATTERN = re.compile(r"^[^/@\s]+/[^@\s]+@[0-9a-f]{40}$")


class CiSecurityError(RuntimeError):
    """Raised when a release-critical CI invariant is absent or weakened."""


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

    ios_candidate_requirements = (
        "Run shared iOS simulator tests with bounded failure capture",
        "./gradlew --no-daemon :shared:iosSimulatorArm64Test --stacktrace",
        'tee "${RUNNER_TEMP}/taximobile-ios-shared.log"',
        "python ../infra/scripts/emit_ci_failure_annotation.py",
        '--input "${RUNNER_TEMP}/taximobile-ios-shared.log"',
        '--title "TaxiMobile iOS shared Gradle failure"',
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

    monitoring_diagnostic_requirements = (
        "Parse monitoring configuration with pinned official tools",
        'exec > >(tee "${RUNNER_TEMP}/taximobile-monitoring-validation.log") 2>&1',
        "Publish redacted monitoring-tool failure annotation",
        "python infra/scripts/emit_ci_failure_annotation.py",
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
        "test-phase/T2 persona/T3 system/T4 lab evidence controls, web compatibility runtime coverage, and "
        "blocking scan are present."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
