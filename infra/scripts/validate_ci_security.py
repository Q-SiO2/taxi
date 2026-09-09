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

    if workflow.count("python infra/scripts/validate_test_phase_evidence.py") != 1:
        raise CiSecurityError(
            "The T0-T10 phase catalog and evidence template must be validated once "
            "in the source job."
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
        "image SBOM/provenance, source-contract inventory, test-phase evidence "
        "control, and blocking scan are present."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
