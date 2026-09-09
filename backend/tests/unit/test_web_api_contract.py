import importlib.util
from pathlib import Path

from taximobile_api.main import create_app


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
VALIDATOR_PATH = WORKSPACE_ROOT / "infra" / "scripts" / "validate_web_api_contract.py"

spec = importlib.util.spec_from_file_location("validate_web_api_contract", VALIDATOR_PATH)
assert spec is not None and spec.loader is not None
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def kotlin_gateway(root: Path, name: str, content: str) -> Path:
    path = root / name
    path.write_text(content, encoding="utf-8")
    return path


def test_extracts_direct_reviewed_helper_and_fail_closed_action_routes(tmp_path: Path) -> None:
    kotlin_gateway(
        tmp_path,
        "PricingEconomicsGateway.kt",
        """
        class KtorPricingEconomicsGateway(apiBaseUrl: String) {
            private val endpoints = OperationsApiEndpoints(apiBaseUrl)

            suspend fun load(accessToken: String, policyId: String) =
                list<Policy>(accessToken, "operations/policies/$policyId", null)

            suspend fun transition(accessToken: String, policyId: String, target: String) =
                command(accessToken, "operations/policies/$policyId/${target.action()}", 1, "test")

            private suspend inline fun <reified T> list(
                accessToken: String,
                path: String,
                operatorId: String?,
            ): T = client.get(endpoints.url(path)) { }

            private suspend inline fun <reified T> command(
                accessToken: String,
                path: String,
                version: Int,
                reason: String,
            ): T = client.post(endpoints.url(path)) { }

            private fun String.action(): String = when (this) {
                "IN_REVIEW" -> "submit"
                "ACTIVE" -> "activate"
                else -> error("unsupported")
            }
        }
        """,
    )

    operations, issues = validator.extract_web_operations(
        tmp_path,
        tmp_path,
        tmp_path / "missing-model.kt",
    )

    assert issues == []
    assert {(item.method, item.path) for item in operations} == {
        ("GET", "/api/v1/operations/policies/{web_parameter}"),
        ("POST", "/api/v1/operations/policies/{web_parameter}/submit"),
        ("POST", "/api/v1/operations/policies/{web_parameter}/activate"),
    }


def test_expands_account_security_enum_paths_including_nested_session_route(tmp_path: Path) -> None:
    kotlin_gateway(
        tmp_path,
        "AccountSecurityGateway.kt",
        """
        class KtorAccountSecurityGateway(apiBaseUrl: String) {
            private val endpoints = OperationsApiEndpoints(apiBaseUrl)
            suspend fun apply(marketId: String, userId: String, action: AccountSecurityAction) =
                client.post(endpoints.url(
                    "operations/markets/$marketId/users/$userId/${action.pathSegment}"
                )) { }
        }
        """,
    )
    model = tmp_path / "AccountSecurityModels.kt"
    model.write_text(
        """
        enum class AccountSecurityAction(val pathSegment: String) {
            REVOKE("sessions/revoke"),
            SUSPEND("suspend"),
            REACTIVATE("reactivate"),
        }
        """,
        encoding="utf-8",
    )

    operations, issues = validator.extract_web_operations(tmp_path, tmp_path, model)

    assert issues == []
    assert {item.path for item in operations} == {
        "/api/v1/operations/markets/{web_parameter}/users/{web_parameter}/sessions/revoke",
        "/api/v1/operations/markets/{web_parameter}/users/{web_parameter}/suspend",
        "/api/v1/operations/markets/{web_parameter}/users/{web_parameter}/reactivate",
    }


def test_rejects_gateway_that_bypasses_central_endpoint_builder(tmp_path: Path) -> None:
    kotlin_gateway(
        tmp_path,
        "UnsafeGateway.kt",
        'class UnsafeGateway { suspend fun load() = client.get("/api/v1/operations/cities") }',
    )

    operations, issues = validator.extract_web_operations(
        tmp_path,
        tmp_path,
        tmp_path / "missing-model.kt",
    )

    assert operations == []
    assert any("must construct OperationsApiEndpoints" in issue.reason for issue in issues)
    assert any("HTTP call must use" in issue.reason for issue in issues)


def test_rejects_unreviewed_dynamic_route_segment(tmp_path: Path) -> None:
    kotlin_gateway(
        tmp_path,
        "UnsafeGateway.kt",
        """
        class UnsafeGateway(apiBaseUrl: String) {
            private val endpoints = OperationsApiEndpoints(apiBaseUrl)
            suspend fun mutate(command: String) =
                client.post(endpoints.url("operations/policies/$command")) { }
        }
        """,
    )

    operations, issues = validator.extract_web_operations(
        tmp_path,
        tmp_path,
        tmp_path / "missing-model.kt",
    )

    assert operations == []
    assert any("unreviewed or non-fail-closed" in issue.reason for issue in issues)


def test_rejects_reviewed_helper_called_with_runtime_route(tmp_path: Path) -> None:
    kotlin_gateway(
        tmp_path,
        "FixedRoutesGateway.kt",
        """
        class KtorFixedRoutesGateway(apiBaseUrl: String) {
            private val endpoints = OperationsApiEndpoints(apiBaseUrl)
            suspend fun create(accessToken: String, route: String) = post(accessToken, route, Unit)
            private suspend inline fun <reified Request, reified Response> post(
                accessToken: String,
                path: String,
                request: Request,
            ): Response = client.post(endpoints.url(path)) { }
        }
        """,
    )

    operations, issues = validator.extract_web_operations(
        tmp_path,
        tmp_path,
        tmp_path / "missing-model.kt",
    )

    assert operations == []
    assert any(
        "helper must receive accessToken and a literal route" in issue.reason
        for issue in issues
    )


def test_current_handwritten_web_calls_exist_in_fastapi_contract() -> None:
    operations, issues = validator.validate_web_workspace(create_app())

    assert len(operations) >= 90
    assert issues == []


def test_extracts_fail_closed_static_web_compatibility_preflight(tmp_path: Path) -> None:
    loader = tmp_path / "compatibility.js"
    loader.write_text(
        """
        nativeFetch(`${apiBase}/client-compatibility`, {
            method: "GET",
            headers: {
                "X-TaxiMobile-Client": surface,
                "X-TaxiMobile-Version": version,
                "X-TaxiMobile-Build": build,
            },
        });
        if (policy.status === "UPGRADE_REQUIRED") stop();
        if (policy.status === "SUPPORTED") start();
        if (policy.status === "UPDATE_AVAILABLE") start();
        if (target.origin !== apiUrl.origin || !target.pathname.startsWith(apiPathPrefix)) {
            return nativeFetch(input, init);
        }
        window.fetch = () => { return nativeFetch(input, { ...init, headers }); };
        script.src = "webApp.js";
        """,
        encoding="utf-8",
    )

    operations, issues = validator.extract_web_compatibility_operation(loader, tmp_path)

    assert issues == []
    assert [(item.method, item.path) for item in operations] == [
        ("GET", "/api/v1/client-compatibility")
    ]


def test_rejects_web_preflight_with_extra_call_or_browser_storage(tmp_path: Path) -> None:
    loader = tmp_path / "compatibility.js"
    loader.write_text(
        """
        nativeFetch(`${apiBase}/client-compatibility`, { method: "GET",
          headers: { "X-TaxiMobile-Client": surface, "X-TaxiMobile-Version": version,
                     "X-TaxiMobile-Build": build } });
        nativeFetch(`/unreviewed`);
        localStorage.setItem("policy", "unsafe");
        policy.status === "UPGRADE_REQUIRED";
        policy.status === "SUPPORTED";
        policy.status === "UPDATE_AVAILABLE";
        target.origin !== apiUrl.origin;
        !target.pathname.startsWith(apiPathPrefix);
        return nativeFetch(input, init);
        window.fetch = () => { return nativeFetch(input, { ...init, headers }); };
        script.src = "webApp.js";
        """,
        encoding="utf-8",
    )

    operations, issues = validator.extract_web_compatibility_operation(loader, tmp_path)

    assert operations == []
    assert any("transport branches" in issue.reason for issue in issues)
    assert any("storage boundary" in issue.reason for issue in issues)
