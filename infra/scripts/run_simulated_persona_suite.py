"""Run TaxiMobile's bounded T2 simulated-persona contract suite.

The runner executes only explicit unit-test node IDs from the committed catalog.
It has no target URL, provider credential, database setup, real-user input, or
live-money mode. Its report is useful candidate evidence but deliberately cannot
mark T2, deployment, or a city pilot accepted.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Iterable, Sequence
import xml.etree.ElementTree as ET


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = WORKSPACE_ROOT / "backend"
DEFAULT_CATALOG = WORKSPACE_ROOT / "infra" / "testing" / "simulated-persona-catalog.json"
REQUIRED_CATEGORIES = {
    "ACCOUNT_STATUS",
    "AUTHENTICATION",
    "CITY_ROLLOUT",
    "CLIENT_LIFECYCLE",
    "COORDINATION",
    "DRIVER_ELIGIBILITY",
    "DRIVER_RECRUITMENT",
    "FIXED_ROUTE",
    "MATCHING",
    "NOTIFICATION",
    "PAYMENT_CASH",
    "PAYMENT_TRANSFER",
    "REFUND",
    "RIDE_LIFECYCLE",
    "SAFETY",
    "SCHEDULING",
    "SCOPE_ISOLATION",
    "SECURITY_INCIDENT",
    "STAFF_AUTHORITY",
    "SUPPORT",
}
SAFETY_CONTRACT = {
    "external_network_allowed": False,
    "public_users_allowed": False,
    "live_money_allowed": False,
    "provider_credentials_allowed": False,
    "persistent_personal_data_allowed": False,
}
SCENARIO_ID = re.compile(r"SIM-[A-Z]+-[0-9]{3}")
CLOSED_ID = re.compile(r"[A-Z][A-Z0-9_]{2,95}")
PERSONA = re.compile(r"[A-Z][A-Z0-9_]{2,63}")
SELECTOR = re.compile(r"tests/unit/test_[A-Za-z0-9_]+\.py::test_[^\s]{1,220}")
EXPECTED_ROOT_KEYS = {
    "schema_version",
    "catalog_revision",
    "phase",
    "suite_id",
    "data_classification",
    "safety",
    "coverage_boundaries",
    "scenarios",
}
EXPECTED_SCENARIO_KEYS = {
    "id",
    "category",
    "personas",
    "journey",
    "selectors",
    "invariants",
}


class SimulatedPersonaError(RuntimeError):
    """Raised when the T2 catalog or execution cannot support its report."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_and_validate_catalog(path: Path, backend_root: Path = BACKEND_ROOT) -> dict[str, Any]:
    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise SimulatedPersonaError(f"Cannot read persona catalog: {error}") from error
    except json.JSONDecodeError as error:
        raise SimulatedPersonaError(
            f"Persona catalog is invalid JSON at line {error.lineno}, column {error.colno}."
        ) from error
    if not isinstance(catalog, dict) or set(catalog) != EXPECTED_ROOT_KEYS:
        raise SimulatedPersonaError("Persona catalog must use the exact reviewed root fields.")
    if catalog.get("schema_version") != 1 or catalog.get("phase") != "T2":
        raise SimulatedPersonaError("Persona catalog must be schema 1 for phase T2.")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(catalog.get("catalog_revision", ""))):
        raise SimulatedPersonaError("Persona catalog revision must be a date.")
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,63}", str(catalog.get("suite_id", ""))):
        raise SimulatedPersonaError("Persona suite ID must be a controlled lowercase identifier.")
    if catalog.get("data_classification") != "SYNTHETIC":
        raise SimulatedPersonaError("Persona suite data must remain SYNTHETIC.")
    if catalog.get("safety") != SAFETY_CONTRACT:
        raise SimulatedPersonaError("Persona suite safety flags cannot enable external or real activity.")

    boundaries = catalog.get("coverage_boundaries")
    if (
        not isinstance(boundaries, list)
        or not boundaries
        or any(not isinstance(item, str) or CLOSED_ID.fullmatch(item) is None for item in boundaries)
        or len(boundaries) != len(set(boundaries))
        or "NO_PHASE_ACCEPTANCE_CLAIM" not in boundaries
    ):
        raise SimulatedPersonaError("Coverage boundaries must be unique closed identifiers and deny acceptance.")

    scenarios = catalog.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise SimulatedPersonaError("Persona catalog must contain scenarios.")
    scenario_ids: list[str] = []
    categories: list[str] = []
    selectors: list[str] = []
    for index, scenario in enumerate(scenarios):
        if not isinstance(scenario, dict) or set(scenario) != EXPECTED_SCENARIO_KEYS:
            raise SimulatedPersonaError(f"Scenario {index} must use the exact reviewed fields.")
        scenario_id = scenario.get("id")
        category = scenario.get("category")
        if not isinstance(scenario_id, str) or SCENARIO_ID.fullmatch(scenario_id) is None:
            raise SimulatedPersonaError(f"Scenario {index} has an invalid ID.")
        if category not in REQUIRED_CATEGORIES:
            raise SimulatedPersonaError(f"Scenario {scenario_id} has an unsupported category.")
        if not isinstance(scenario.get("journey"), str) or not 10 <= len(scenario["journey"]) <= 240:
            raise SimulatedPersonaError(f"Scenario {scenario_id} needs a bounded journey description.")
        personas = scenario.get("personas")
        invariants = scenario.get("invariants")
        node_ids = scenario.get("selectors")
        if (
            not isinstance(personas, list)
            or not personas
            or any(not isinstance(item, str) or PERSONA.fullmatch(item) is None for item in personas)
            or len(personas) != len(set(personas))
        ):
            raise SimulatedPersonaError(f"Scenario {scenario_id} has invalid personas.")
        if (
            not isinstance(invariants, list)
            or not invariants
            or any(not isinstance(item, str) or CLOSED_ID.fullmatch(item) is None for item in invariants)
            or len(invariants) != len(set(invariants))
        ):
            raise SimulatedPersonaError(f"Scenario {scenario_id} has invalid invariants.")
        if not isinstance(node_ids, list) or not node_ids:
            raise SimulatedPersonaError(f"Scenario {scenario_id} has no test selectors.")
        for selector in node_ids:
            if not isinstance(selector, str) or SELECTOR.fullmatch(selector) is None or ".." in selector:
                raise SimulatedPersonaError(f"Scenario {scenario_id} has an unsafe test selector.")
            relative_file = selector.split("::", 1)[0]
            if not (backend_root / relative_file).is_file():
                raise SimulatedPersonaError(
                    f"Scenario {scenario_id} selector file does not exist: {relative_file}"
                )
            selectors.append(selector)
        scenario_ids.append(scenario_id)
        categories.append(category)

    if len(scenario_ids) != len(set(scenario_ids)):
        raise SimulatedPersonaError("Scenario IDs must be unique.")
    if len(categories) != len(set(categories)) or set(categories) != REQUIRED_CATEGORIES:
        raise SimulatedPersonaError("Catalog must cover every required category exactly once.")
    if len(selectors) != len(set(selectors)):
        raise SimulatedPersonaError("Each test selector may support only one simulated scenario.")
    return catalog


def junit_summary(path: Path) -> dict[str, int]:
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as error:
        raise SimulatedPersonaError(f"Cannot parse generated JUnit report: {error}") from error
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    if not suites:
        raise SimulatedPersonaError("Generated JUnit report contains no test suite.")
    result = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for suite in suites:
        for name in result:
            try:
                result[name] += int(suite.attrib.get(name, "0"))
            except ValueError as error:
                raise SimulatedPersonaError(f"JUnit {name} count is not an integer.") from error
    return result


def run_suite(
    *,
    catalog_path: Path,
    output_path: Path,
    junit_path: Path,
    backend_root: Path = BACKEND_ROOT,
    timeout_seconds: int = 300,
) -> tuple[dict[str, Any], int]:
    catalog_path = catalog_path.resolve()
    output_path = output_path.resolve()
    junit_path = junit_path.resolve()
    backend_root = backend_root.resolve()
    catalog = load_and_validate_catalog(catalog_path, backend_root)
    if output_path.exists() or junit_path.exists():
        raise SimulatedPersonaError("Refusing to overwrite an existing T2 report or JUnit file.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    junit_path.parent.mkdir(parents=True, exist_ok=True)
    selectors = [selector for scenario in catalog["scenarios"] for selector in scenario["selectors"]]
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "t2_no_network",
        f"--junitxml={junit_path}",
        *selectors,
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=backend_root,
            check=False,
            capture_output=True,
            env={
                **os.environ,
                "PYTHONPATH": os.pathsep.join(
                    filter(
                        None,
                        (
                            str(Path(__file__).resolve().parent),
                            os.environ.get("PYTHONPATH"),
                        ),
                    )
                ),
            },
            text=True,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise SimulatedPersonaError(f"T2 pytest execution failed or timed out: {error}") from error
    if not junit_path.is_file():
        detail = (completed.stdout or completed.stderr or "no bounded output")[-2000:]
        raise SimulatedPersonaError(
            f"T2 pytest did not produce JUnit (exit {completed.returncode}): {detail}"
        )
    counts = junit_summary(junit_path)
    passed = (
        completed.returncode == 0
        and counts["tests"] == len(selectors)
        and counts["failures"] == 0
        and counts["errors"] == 0
        and counts["skipped"] == 0
    )
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_level": "T2_SIMULATED_PERSONA_EXECUTION",
        "phase": "T2",
        "suite_id": catalog["suite_id"],
        "catalog_revision": catalog["catalog_revision"],
        "catalog_sha256": _sha256(catalog_path),
        "junit_sha256": _sha256(junit_path),
        "data_classification": "SYNTHETIC",
        "network_guard": "DNS_AND_NON_LOOPBACK_SOCKET_DENIED",
        "deployment_accepted": False,
        "phase_accepted": False,
        "phase_evidence_complete": False,
        "supported_evidence_kinds": [
            "SIMULATED_PERSONA_MATRIX",
            "CRITICAL_JOURNEY_REPORT",
        ],
        "missing_t2_evidence_kinds": [
            "ADVERSARIAL_SECURITY_REPORT",
            "STATE_AND_MONEY_RECONCILIATION",
            "TEST_DATA_MINIMIZATION_REPORT",
        ],
        "result": "PASS" if passed else "FAIL",
        "scenario_count": len(catalog["scenarios"]),
        "selector_count": len(selectors),
        "junit": counts,
        "coverage_boundaries": catalog["coverage_boundaries"],
        "scenario_results": [
            {
                "id": scenario["id"],
                "category": scenario["category"],
                "result": "PASS" if passed else "NOT_PROVEN",
                "selector_count": len(scenario["selectors"]),
                "invariants": scenario["invariants"],
            }
            for scenario in catalog["scenarios"]
        ],
    }
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report, 0 if passed else 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--junit-output", type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=300, choices=range(30, 1801))
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    arguments = _parser().parse_args(list(argv) if argv is not None else None)
    if arguments.validate_only:
        if arguments.output is not None or arguments.junit_output is not None:
            print(
                "T2 simulated-persona suite failed: --validate-only cannot write run evidence.",
                file=sys.stderr,
            )
            return 1
        try:
            catalog = load_and_validate_catalog(arguments.catalog)
        except SimulatedPersonaError as error:
            print(f"T2 simulated-persona catalog failed: {error}", file=sys.stderr)
            return 1
        selector_count = sum(len(item["selectors"]) for item in catalog["scenarios"])
        print(
            f"T2 simulated-persona catalog validation passed: "
            f"{len(catalog['scenarios'])} scenarios, {selector_count} exact unit-test selectors."
        )
        return 0
    if arguments.output is None or arguments.junit_output is None:
        print(
            "T2 simulated-persona suite failed: --output and --junit-output are required for execution.",
            file=sys.stderr,
        )
        return 1
    try:
        report, return_code = run_suite(
            catalog_path=arguments.catalog,
            output_path=arguments.output,
            junit_path=arguments.junit_output,
            timeout_seconds=arguments.timeout_seconds,
        )
    except SimulatedPersonaError as error:
        print(f"T2 simulated-persona suite failed: {error}", file=sys.stderr)
        return 1
    print(
        f"T2 simulated-persona suite {report['result']}: "
        f"{report['scenario_count']} scenarios, {report['junit']['tests']} tests, "
        "zero phase/deployment acceptance claims."
    )
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
