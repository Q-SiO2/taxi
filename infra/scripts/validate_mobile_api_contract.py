"""Verify that handwritten Kotlin gateway calls still exist in FastAPI.

The mobile client intentionally remains handwritten while the v1 API is still
evolving. This gate extracts the actual Ktor call sites rather than trusting a
separate route manifest that could drift independently. It compares HTTP
method/path pairs with FastAPI's generated OpenAPI document and verifies the
best-effort live-event WebSocket against the registered application routes.
"""

from __future__ import annotations

from itertools import product
from pathlib import Path
import re
import sys
from typing import Iterable, NamedTuple


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
MOBILE_GATEWAY_ROOT = (
    WORKSPACE_ROOT
    / "TaxiMobile"
    / "shared"
    / "src"
    / "commonMain"
    / "kotlin"
    / "org"
    / "example"
    / "taximobile"
    / "data"
)
ANDROID_MOBILE_GATEWAY_ROOT = (
    WORKSPACE_ROOT
    / "TaxiMobile"
    / "shared"
    / "src"
    / "androidMain"
    / "kotlin"
    / "org"
    / "example"
    / "taximobile"
    / "data"
)
IOS_MOBILE_GATEWAY_ROOT = (
    WORKSPACE_ROOT
    / "TaxiMobile"
    / "shared"
    / "src"
    / "iosMain"
    / "kotlin"
    / "org"
    / "example"
    / "taximobile"
    / "data"
)
API_PREFIX = "/api/v1"
HTTP_METHODS = ("get", "post", "put", "patch", "delete")

# The only non-identifier interpolation in a gateway route is deliberately
# finite. Adding another dynamic route segment must be reviewed here instead
# of silently accepting an arbitrary runtime path.
DYNAMIC_SEGMENT_VALUES = {
    "action": ("en-route", "arrived", "start"),
}

_METHOD_GROUP = "|".join(HTTP_METHODS)
_HTTP_CALL = re.compile(
    rf"\bclient\s*\.\s*(?P<method>{_METHOD_GROUP})\s*\(\s*"
    r"api\s*\.\s*endpoint\s*\(\s*\"(?P<path>[^\"\r\n]+)\"\s*\)",
    re.MULTILINE,
)
_ANY_HTTP_CALL = re.compile(rf"\bclient\s*\.\s*(?:{_METHOD_GROUP})\s*\(")
_WEBSOCKET_CALL = re.compile(
    r"\bclient\s*\.\s*webSocket\s*\(\s*"
    r"urlString\s*=\s*api\s*\.\s*websocketEndpoint\s*\(\s*\"(?P<path>[^\"\r\n]+)\"\s*\)",
    re.MULTILINE,
)
_ANY_WEBSOCKET_CALL = re.compile(r"\bclient\s*\.\s*webSocket\s*\(")
_INTERPOLATION = re.compile(r"\$(?:\{)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?:\})?")
_PLACEHOLDER_SEGMENT = re.compile(r"\{[^{}\/]+\}")
_STATIC_SEGMENT = re.compile(r"[A-Za-z0-9._-]+")


class MobileOperation(NamedTuple):
    source: Path
    line: int
    protocol: str
    method: str
    path: str


class ContractIssue(NamedTuple):
    source: Path
    line: int
    reason: str


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _relative(path: Path, root: Path) -> Path:
    try:
        return path.resolve().relative_to(root.resolve())
    except ValueError:
        return path


def _expand_mobile_path(fragment: str) -> tuple[list[str], str | None]:
    """Expand reviewed finite segments and normalize resource IDs."""

    if fragment.startswith("/") or "?" in fragment or "#" in fragment or "//" in fragment:
        return [], "endpoint fragments must be clean relative paths without query or fragment text"

    choices: list[tuple[str, ...]] = []
    for segment in fragment.split("/"):
        match = _INTERPOLATION.fullmatch(segment)
        if match:
            name = match.group("name")
            if name in DYNAMIC_SEGMENT_VALUES:
                choices.append(DYNAMIC_SEGMENT_VALUES[name])
            elif name.lower().endswith("id"):
                choices.append(("{mobile_parameter}",))
            else:
                return [], f"unreviewed dynamic endpoint segment: {name}"
        elif _STATIC_SEGMENT.fullmatch(segment):
            choices.append((segment,))
        else:
            return [], "endpoint contains an unsupported or embedded interpolation"

    return [f"{API_PREFIX}/{'/'.join(parts)}" for parts in product(*choices)], None


def _covered_offsets(matches: Iterable[re.Match[str]]) -> set[int]:
    return {match.start() for match in matches}


def extract_mobile_operations(
    gateway_root: Path = MOBILE_GATEWAY_ROOT,
    workspace_root: Path = WORKSPACE_ROOT,
) -> tuple[list[MobileOperation], list[ContractIssue]]:
    operations: list[MobileOperation] = []
    issues: list[ContractIssue] = []
    gateway_roots = [gateway_root]
    if gateway_root.resolve() == MOBILE_GATEWAY_ROOT.resolve():
        gateway_roots.append(ANDROID_MOBILE_GATEWAY_ROOT)
        android_adapter = ANDROID_MOBILE_GATEWAY_ROOT / "network" / "KtorClientCompatibilityGateway.kt"
        ios_adapter = IOS_MOBILE_GATEWAY_ROOT / "network" / "KtorClientCompatibilityGateway.kt"
        if not android_adapter.is_file() or not ios_adapter.is_file():
            issues.append(
                ContractIssue(
                    _relative(android_adapter, workspace_root),
                    1,
                    "Android and iOS compatibility adapters must both exist",
                )
            )
        elif android_adapter.read_bytes() != ios_adapter.read_bytes():
            issues.append(
                ContractIssue(
                    _relative(ios_adapter, workspace_root),
                    1,
                    "Android and iOS compatibility adapters must remain byte-identical",
                )
            )

    sources = sorted(
        source
        for root in gateway_roots
        for source in root.rglob("*Gateway.kt")
    )
    for source in sources:
        text = source.read_text(encoding="utf-8")
        relative = _relative(source, workspace_root)
        http_matches = list(_HTTP_CALL.finditer(text))
        websocket_matches = list(_WEBSOCKET_CALL.finditer(text))

        parsed_http_offsets = _covered_offsets(http_matches)
        for match in _ANY_HTTP_CALL.finditer(text):
            if match.start() not in parsed_http_offsets:
                issues.append(
                    ContractIssue(
                        relative,
                        _line_number(text, match.start()),
                        "HTTP call must use client.<method>(api.endpoint(\"literal/path\"))",
                    )
                )

        parsed_websocket_offsets = _covered_offsets(websocket_matches)
        for match in _ANY_WEBSOCKET_CALL.finditer(text):
            if match.start() not in parsed_websocket_offsets:
                issues.append(
                    ContractIssue(
                        relative,
                        _line_number(text, match.start()),
                        "WebSocket call must use api.websocketEndpoint(\"literal/path\")",
                    )
                )

        for match in http_matches:
            paths, error = _expand_mobile_path(match.group("path"))
            line = _line_number(text, match.start())
            if error is not None:
                issues.append(ContractIssue(relative, line, error))
                continue
            for path in paths:
                operations.append(
                    MobileOperation(relative, line, "http", match.group("method").upper(), path)
                )

        for match in websocket_matches:
            paths, error = _expand_mobile_path(match.group("path"))
            line = _line_number(text, match.start())
            if error is not None:
                issues.append(ContractIssue(relative, line, error))
                continue
            for path in paths:
                operations.append(MobileOperation(relative, line, "websocket", "WS", path))

    if not operations:
        issues.append(ContractIssue(_relative(gateway_root, workspace_root), 1, "no mobile API calls found"))
    return operations, issues


def path_templates_match(mobile_path: str, backend_path: str) -> bool:
    mobile_segments = mobile_path.strip("/").split("/")
    backend_segments = backend_path.strip("/").split("/")
    if len(mobile_segments) != len(backend_segments):
        return False
    return all(
        mobile == backend
        or (
            _PLACEHOLDER_SEGMENT.fullmatch(mobile) is not None
            and _PLACEHOLDER_SEGMENT.fullmatch(backend) is not None
        )
        for mobile, backend in zip(mobile_segments, backend_segments, strict=True)
    )


def validate_operations(operations: Iterable[MobileOperation], app: object) -> list[ContractIssue]:
    openapi = app.openapi()
    supported_http = {
        (method.upper(), path)
        for path, definition in openapi["paths"].items()
        for method in definition
        if method.lower() in HTTP_METHODS
    }

    from starlette.routing import WebSocketRoute

    supported_websockets = {
        route.path for route in app.routes if isinstance(route, WebSocketRoute)
    }
    issues: list[ContractIssue] = []
    for operation in operations:
        if operation.protocol == "websocket":
            supported = any(
                path_templates_match(operation.path, backend_path)
                for backend_path in supported_websockets
            )
        else:
            supported = any(
                operation.method == backend_method
                and path_templates_match(operation.path, backend_path)
                for backend_method, backend_path in supported_http
            )
        if not supported:
            issues.append(
                ContractIssue(
                    operation.source,
                    operation.line,
                    f"{operation.method} {operation.path} is absent from the backend contract",
                )
            )
    return issues


def validate_workspace(app: object) -> tuple[list[MobileOperation], list[ContractIssue]]:
    operations, issues = extract_mobile_operations()
    if not issues:
        issues.extend(validate_operations(operations, app))
    return operations, issues


def main() -> int:
    backend_source = WORKSPACE_ROOT / "backend" / "src"
    if str(backend_source) not in sys.path:
        sys.path.insert(0, str(backend_source))

    from taximobile_api.main import create_app

    operations, issues = validate_workspace(create_app())
    if issues:
        print("Mobile/backend API contract validation failed:", file=sys.stderr)
        for issue in issues:
            print(f"- {issue.source}:{issue.line}: {issue.reason}", file=sys.stderr)
        return 1

    http_count = sum(operation.protocol == "http" for operation in operations)
    websocket_count = sum(operation.protocol == "websocket" for operation in operations)
    print(
        "Mobile/backend API contract validation passed "
        f"({http_count} expanded HTTP operations, {websocket_count} WebSocket operation)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
