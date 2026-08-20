import importlib.util
from pathlib import Path

from taximobile_api.main import create_app


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
VALIDATOR_PATH = WORKSPACE_ROOT / "infra" / "scripts" / "validate_mobile_api_contract.py"

spec = importlib.util.spec_from_file_location("validate_mobile_api_contract", VALIDATOR_PATH)
assert spec is not None and spec.loader is not None
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def kotlin_gateway(root: Path, content: str) -> Path:
    path = root / "data" / "KtorExampleGateway.kt"
    path.parent.mkdir(parents=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_extracts_literal_identifier_and_reviewed_finite_routes(tmp_path: Path) -> None:
    kotlin_gateway(
        tmp_path,
        """
        client.get(api.endpoint("rides/$rideId"))
        client.post(api.endpoint("rides/$rideId/$action"))
        """,
    )

    operations, issues = validator.extract_mobile_operations(tmp_path, tmp_path)

    assert issues == []
    assert {(item.method, item.path) for item in operations} == {
        ("GET", "/api/v1/rides/{mobile_parameter}"),
        ("POST", "/api/v1/rides/{mobile_parameter}/en-route"),
        ("POST", "/api/v1/rides/{mobile_parameter}/arrived"),
        ("POST", "/api/v1/rides/{mobile_parameter}/start"),
    }


def test_rejects_a_call_that_bypasses_the_versioned_endpoint_builder(tmp_path: Path) -> None:
    kotlin_gateway(tmp_path, "client.get(rawUrl)")

    operations, issues = validator.extract_mobile_operations(tmp_path, tmp_path)

    assert operations == []
    assert any("must use client.<method>" in issue.reason for issue in issues)


def test_rejects_an_unreviewed_dynamic_route_segment(tmp_path: Path) -> None:
    kotlin_gateway(tmp_path, 'client.post(api.endpoint("rides/$command"))')

    operations, issues = validator.extract_mobile_operations(tmp_path, tmp_path)

    assert operations == []
    assert any("unreviewed dynamic endpoint segment: command" == issue.reason for issue in issues)


def test_rejects_a_websocket_that_bypasses_the_versioned_endpoint_builder(tmp_path: Path) -> None:
    kotlin_gateway(tmp_path, "client.webSocket(urlString = rawUrl) {}")

    operations, issues = validator.extract_mobile_operations(tmp_path, tmp_path)

    assert operations == []
    assert any("WebSocket call must use" in issue.reason for issue in issues)


def test_template_matching_ignores_parameter_names_but_not_static_segments() -> None:
    assert validator.path_templates_match(
        "/api/v1/rides/{mobile_parameter}/fare",
        "/api/v1/rides/{ride_id}/fare",
    )
    assert not validator.path_templates_match(
        "/api/v1/rides/{mobile_parameter}/fare",
        "/api/v1/rides/{ride_id}/receipt",
    )


def test_reports_a_mobile_method_path_absent_from_openapi() -> None:
    class EmptyApp:
        routes = []

        @staticmethod
        def openapi() -> dict[str, dict]:
            return {"paths": {"/api/v1/rides": {"get": {}}}}

    operation = validator.MobileOperation(
        Path("KtorRideGateway.kt"),
        12,
        "http",
        "POST",
        "/api/v1/rides",
    )

    assert validator.validate_operations([operation], EmptyApp()) == [
        validator.ContractIssue(
            Path("KtorRideGateway.kt"),
            12,
            "POST /api/v1/rides is absent from the backend contract",
        )
    ]


def test_current_handwritten_mobile_calls_exist_in_fastapi_contract() -> None:
    operations, issues = validator.validate_workspace(create_app())

    assert len(operations) >= 40
    assert any(operation.protocol == "websocket" for operation in operations)
    assert issues == []
