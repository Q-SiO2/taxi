"""Verify browser operations gateways and preflight against FastAPI OpenAPI.

The operations console uses handwritten Ktor gateways. This gate extracts the
actual method/path pairs from direct calls and a deliberately small set of
reviewed route helpers, expands only finite fail-closed action selectors, and
compares every result with OpenAPI. Any call that bypasses the central versioned
URL builder or any route expression the extractor cannot prove is rejected.
"""

from __future__ import annotations

from itertools import product
from pathlib import Path
import re
import sys
from typing import Iterable, NamedTuple


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from validate_mobile_api_contract import (  # noqa: E402
    API_PREFIX,
    ContractIssue,
    HTTP_METHODS,
    MobileOperation,
    validate_operations,
)


WEB_GATEWAY_ROOT = (
    WORKSPACE_ROOT
    / "TaxiMobile"
    / "webApp"
    / "src"
    / "webMain"
    / "kotlin"
    / "org"
    / "example"
    / "taximobile"
    / "operations"
    / "data"
)
WEB_COMPATIBILITY_LOADER = (
    WORKSPACE_ROOT
    / "TaxiMobile"
    / "webApp"
    / "src"
    / "webMain"
    / "resources"
    / "compatibility.js"
)
ACCOUNT_SECURITY_MODEL = WEB_GATEWAY_ROOT.parent / "model" / "AccountSecurityModels.kt"

# Helpers remain private to one gateway and only forward a reviewed literal
# path to the listed method. Adding or renaming one is an explicit contract-gate
# change; arbitrary runtime paths are never accepted.
ROUTE_HELPERS: dict[str, dict[str, str]] = {
    "PricingEconomicsGateway.kt": {
        "list": "GET",
        "post": "POST",
        "patch": "PATCH",
        "command": "POST",
    },
    "FixedRoutesGateway.kt": {"post": "POST"},
    "PaymentOperationsGateway.kt": {"getPage": "GET"},
}

_METHOD_GROUP = "|".join(HTTP_METHODS)
_DIRECT_HTTP_CALL = re.compile(
    rf"\bclient\s*\.\s*(?P<method>{_METHOD_GROUP})\s*\(\s*"
    r"endpoints\s*\.\s*url\s*\(\s*\"(?P<path>[^\"\r\n]+)\"\s*\)",
    re.MULTILINE,
)
_DYNAMIC_HTTP_CALL = re.compile(
    rf"\bclient\s*\.\s*(?P<method>{_METHOD_GROUP})\s*\(\s*"
    r"endpoints\s*\.\s*url\s*\(\s*path\s*\)",
    re.MULTILINE,
)
_ANY_HTTP_CALL = re.compile(rf"\bclient\s*\.\s*(?:{_METHOD_GROUP})\s*\(")
_ROUTE_LITERAL = re.compile(r'\"(?P<path>operations/[^\"\r\n]+)\"')
_INTERPOLATION = re.compile(
    r"\$(?:\{(?P<braced>[^{}]+)\}|(?P<simple>[A-Za-z_][A-Za-z0-9_]*))"
)
_PLACEHOLDER_SEGMENT = re.compile(r"\{[^{}\/]+\}")
_STATIC_SEGMENT = re.compile(r"[A-Za-z0-9._-]+")
_ENDPOINT_BUILDER = re.compile(
    r"private\s+val\s+endpoints\s*=\s*OperationsApiEndpoints\s*\(\s*apiBaseUrl\s*\)"
)
_FUNCTION_DEFINITION = re.compile(
    r"\bfun\s*(?:<[^>{}]+>\s*)?"
    r"(?:[A-Za-z_][A-Za-z0-9_.<>?]*\.)?"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\("
)


class FunctionDefinition(NamedTuple):
    offset: int
    name_offset: int
    name: str


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _relative(path: Path, root: Path) -> Path:
    try:
        return path.resolve().relative_to(root.resolve())
    except ValueError:
        return path


def _mask_kotlin_comments(text: str) -> str:
    """Blank comments while preserving strings, offsets, and newlines."""

    chars = list(text)
    index = 0
    in_string = False
    escaped = False
    block_depth = 0
    while index < len(chars):
        current = chars[index]
        following = chars[index + 1] if index + 1 < len(chars) else ""
        if block_depth:
            if current == "/" and following == "*":
                chars[index] = chars[index + 1] = " "
                block_depth += 1
                index += 2
            elif current == "*" and following == "/":
                chars[index] = chars[index + 1] = " "
                block_depth -= 1
                index += 2
            else:
                if current != "\n":
                    chars[index] = " "
                index += 1
            continue
        if in_string:
            if escaped:
                escaped = False
            elif current == "\\":
                escaped = True
            elif current == '"':
                in_string = False
            index += 1
            continue
        if current == '"':
            in_string = True
            index += 1
        elif current == "/" and following == "/":
            chars[index] = chars[index + 1] = " "
            index += 2
            while index < len(chars) and chars[index] != "\n":
                chars[index] = " "
                index += 1
        elif current == "/" and following == "*":
            chars[index] = chars[index + 1] = " "
            block_depth = 1
            index += 2
        else:
            index += 1
    return "".join(chars)


def _function_definitions(text: str) -> list[FunctionDefinition]:
    return [
        FunctionDefinition(match.start(), match.start("name"), match.group("name"))
        for match in _FUNCTION_DEFINITION.finditer(text)
    ]


def _enclosing_function(
    definitions: list[FunctionDefinition],
    offset: int,
) -> FunctionDefinition | None:
    previous = [definition for definition in definitions if definition.offset < offset]
    return previous[-1] if previous else None


def _account_security_paths(model_path: Path) -> tuple[str, ...]:
    if not model_path.is_file():
        return ()
    text = _mask_kotlin_comments(model_path.read_text(encoding="utf-8"))
    enum_match = re.search(
        r"enum\s+class\s+AccountSecurityAction\s*\([^)]*\)\s*\{(?P<body>.*?)\n\s*\}",
        text,
        re.DOTALL,
    )
    if enum_match is None:
        return ()
    return tuple(
        match.group("path")
        for match in re.finditer(
            r'^\s*[A-Z][A-Z0-9_]*\s*\(\s*\"(?P<path>[^\"]+)\"',
            enum_match.group("body"),
            re.MULTILINE,
        )
    )


def _when_outputs(text: str, expression: str) -> tuple[str, ...]:
    if expression == "action.pathSegment":
        return ()

    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", expression):
        name = re.escape(expression)
        pattern = re.compile(
            rf"\bval\s+{name}\s*=\s*when\s*\([^)]*\)\s*\{{(?P<body>.*?)\n\s*\}}",
            re.DOTALL,
        )
    else:
        call_names = re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*\(", expression)
        if not call_names:
            return ()
        name = re.escape(call_names[-1])
        pattern = re.compile(
            rf"\bfun\s+(?:[A-Za-z_][A-Za-z0-9_.<>?]*\.)?{name}\s*"
            r"\([^)]*\)\s*:\s*String\s*=\s*when\s*\([^)]*\)\s*\{"
            r"(?P<body>.*?)\n\s*\}",
            re.DOTALL,
        )

    match = pattern.search(text)
    if match is None:
        return ()
    body = match.group("body")
    if re.search(r"\belse\s*->\s*(?:throw\b|error\s*\()", body) is None:
        return ()
    return tuple(dict.fromkeys(re.findall(r'->\s*\"([A-Za-z0-9._/-]+)\"', body)))


def _finite_values(
    text: str,
    expression: str,
    account_security_paths: tuple[str, ...],
) -> tuple[str, ...]:
    if expression == "action.pathSegment":
        return account_security_paths
    return _when_outputs(text, expression)


def _is_identifier_expression(expression: str) -> bool:
    tail = expression.rsplit(".", 1)[-1]
    return re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", tail) is not None and tail.lower().endswith("id")


def _expand_web_path(
    fragment: str,
    source_text: str,
    account_security_paths: tuple[str, ...],
) -> tuple[list[str], str | None]:
    if fragment.startswith("/") or "?" in fragment or "#" in fragment or "//" in fragment:
        return [], "endpoint fragments must be clean relative paths without query or fragment text"

    choices: list[tuple[str, ...]] = []
    for segment in fragment.split("/"):
        interpolation = _INTERPOLATION.fullmatch(segment)
        if interpolation is not None:
            expression = interpolation.group("braced") or interpolation.group("simple")
            if _is_identifier_expression(expression):
                choices.append(("{web_parameter}",))
                continue
            values = _finite_values(source_text, expression, account_security_paths)
            if not values:
                return [], f"unreviewed or non-fail-closed dynamic endpoint segment: {expression}"
            if any(
                not value
                or "?" in value
                or "#" in value
                or "//" in value
                or any(_STATIC_SEGMENT.fullmatch(part) is None for part in value.split("/"))
                for value in values
            ):
                return [], f"dynamic endpoint segment has an unsafe value: {expression}"
            choices.append(values)
        elif _STATIC_SEGMENT.fullmatch(segment):
            choices.append((segment,))
        elif "$" in segment:
            return [], "endpoint contains an unsupported embedded interpolation"
        else:
            return [], "endpoint contains an unsupported segment"

    return [f"{API_PREFIX}/{'/'.join(parts)}" for parts in product(*choices)], None


def _helper_patterns(helper_names: Iterable[str]) -> tuple[re.Pattern[str], re.Pattern[str]]:
    group = "|".join(re.escape(name) for name in sorted(helper_names, key=len, reverse=True))
    any_call = re.compile(
        rf"(?<![.A-Za-z0-9_])(?P<helper>{group})(?:\s*<[^>()]+>)?\s*\("
    )
    literal_call = re.compile(
        rf"(?<![.A-Za-z0-9_])(?P<helper>{group})(?:\s*<[^>()]+>)?\s*\(\s*"
        r"accessToken\s*,\s*\"(?P<path>[^\"\r\n]+)\"",
        re.MULTILINE,
    )
    return any_call, literal_call


def extract_web_operations(
    gateway_root: Path = WEB_GATEWAY_ROOT,
    workspace_root: Path = WORKSPACE_ROOT,
    account_security_model: Path = ACCOUNT_SECURITY_MODEL,
) -> tuple[list[MobileOperation], list[ContractIssue]]:
    operations: list[MobileOperation] = []
    issues: list[ContractIssue] = []
    account_paths = _account_security_paths(account_security_model)

    for source in sorted(gateway_root.glob("*Gateway.kt")):
        original_text = source.read_text(encoding="utf-8")
        text = _mask_kotlin_comments(original_text)
        relative = _relative(source, workspace_root)
        definitions = _function_definitions(text)
        definition_name_offsets = {definition.name_offset for definition in definitions}
        helper_methods = ROUTE_HELPERS.get(source.name, {})

        direct_matches = list(_DIRECT_HTTP_CALL.finditer(text))
        dynamic_matches = list(_DYNAMIC_HTTP_CALL.finditer(text))
        covered_http_offsets = {match.start() for match in direct_matches}
        covered_literal_offsets = {match.start("path") for match in direct_matches}

        if list(_ANY_HTTP_CALL.finditer(text)) and _ENDPOINT_BUILDER.search(text) is None:
            issues.append(
                ContractIssue(
                    relative,
                    1,
                    "gateway must construct OperationsApiEndpoints(apiBaseUrl)",
                )
            )

        for match in dynamic_matches:
            function = _enclosing_function(definitions, match.start())
            expected_method = helper_methods.get(function.name if function else "")
            actual_method = match.group("method").upper()
            if expected_method != actual_method:
                issues.append(
                    ContractIssue(
                        relative,
                        _line_number(text, match.start()),
                        "dynamic route forwarding is not inside a reviewed method-matched helper",
                    )
                )
            else:
                covered_http_offsets.add(match.start())

        helper_literal_matches: list[re.Match[str]] = []
        helper_any_pattern: re.Pattern[str] | None = None
        if helper_methods:
            helper_any_pattern, helper_literal_pattern = _helper_patterns(helper_methods)
            helper_literal_matches = list(helper_literal_pattern.finditer(text))
            covered_literal_offsets.update(match.start("path") for match in helper_literal_matches)

            literal_call_offsets = {match.start("helper") for match in helper_literal_matches}
            for match in helper_any_pattern.finditer(text):
                helper_offset = match.start("helper")
                if (
                    helper_offset in definition_name_offsets
                    or helper_offset in literal_call_offsets
                ):
                    continue
                remainder = text[match.end() : match.end() + 160]
                forwards_path = re.match(r"\s*accessToken\s*,\s*path\s*[,)]", remainder) is not None
                enclosing = _enclosing_function(definitions, helper_offset)
                if forwards_path and enclosing is not None and enclosing.name in helper_methods:
                    continue
                issues.append(
                    ContractIssue(
                        relative,
                        _line_number(text, helper_offset),
                        "reviewed route helper must receive accessToken and a literal route",
                    )
                )

        for match in _ANY_HTTP_CALL.finditer(text):
            if match.start() not in covered_http_offsets:
                issues.append(
                    ContractIssue(
                        relative,
                        _line_number(text, match.start()),
                        "HTTP call must use client.<method>(endpoints.url(\"literal/path\")) "
                        "or a reviewed literal-route helper",
                    )
                )

        for match in _ROUTE_LITERAL.finditer(text):
            if match.start("path") not in covered_literal_offsets:
                issues.append(
                    ContractIssue(
                        relative,
                        _line_number(text, match.start()),
                        "operations route literal is not bound to a reviewed HTTP call",
                    )
                )

        route_matches: list[tuple[str, str, int]] = [
            (match.group("method").upper(), match.group("path"), match.start())
            for match in direct_matches
        ]
        route_matches.extend(
            (
                helper_methods[match.group("helper")],
                match.group("path"),
                match.start(),
            )
            for match in helper_literal_matches
        )
        for method, fragment, offset in route_matches:
            paths, error = _expand_web_path(fragment, text, account_paths)
            line = _line_number(text, offset)
            if error is not None:
                issues.append(ContractIssue(relative, line, error))
                continue
            operations.extend(
                MobileOperation(relative, line, "http", method, path)
                for path in paths
            )

    if not operations:
        issues.append(
            ContractIssue(
                _relative(gateway_root, workspace_root),
                1,
                "no web API calls found",
            )
        )
    return operations, issues


def extract_web_compatibility_operation(
    loader_path: Path = WEB_COMPATIBILITY_LOADER,
    workspace_root: Path = WORKSPACE_ROOT,
) -> tuple[list[MobileOperation], list[ContractIssue]]:
    relative = _relative(loader_path, workspace_root)
    if not loader_path.is_file():
        return [], [ContractIssue(relative, 1, "web compatibility boot loader is missing")]

    text = loader_path.read_text(encoding="utf-8")
    required = (
        'nativeFetch(`${apiBase}/client-compatibility`',
        'method: "GET"',
        '"X-TaxiMobile-Client"',
        '"X-TaxiMobile-Version"',
        '"X-TaxiMobile-Build"',
        'policy.status === "UPGRADE_REQUIRED"',
        'policy.status === "SUPPORTED"',
        'policy.status === "UPDATE_AVAILABLE"',
        "target.origin !== apiUrl.origin",
        "!target.pathname.startsWith(apiPathPrefix)",
        "window.fetch =",
        "return nativeFetch(input, init);",
        "return nativeFetch(input, { ...init, headers });",
        'script.src = "webApp.js"',
    )
    issues = [
        ContractIssue(relative, 1, "web compatibility boot contract is incomplete")
        for fragment in required
        if fragment not in text
    ]
    if text.count("nativeFetch(") != 3:
        issues.append(
            ContractIssue(
                relative,
                1,
                "web compatibility loader must retain two transport branches and one preflight call",
            )
        )
    if "Authorization" in text or "localStorage" in text or "sessionStorage" in text:
        issues.append(
            ContractIssue(relative, 1, "web compatibility loader crosses the pre-auth storage boundary")
        )
    if issues:
        return [], issues

    endpoint_offset = text.index("/client-compatibility")
    return [
        MobileOperation(
            relative,
            _line_number(text, endpoint_offset),
            "http",
            "GET",
            f"{API_PREFIX}/client-compatibility",
        )
    ], []


def validate_web_workspace(app: object) -> tuple[list[MobileOperation], list[ContractIssue]]:
    operations, issues = extract_web_operations()
    compatibility_operations, compatibility_issues = extract_web_compatibility_operation()
    operations.extend(compatibility_operations)
    issues.extend(compatibility_issues)
    if not issues:
        issues.extend(validate_operations(operations, app))
    return operations, issues


def main() -> int:
    backend_source = WORKSPACE_ROOT / "backend" / "src"
    if str(backend_source) not in sys.path:
        sys.path.insert(0, str(backend_source))

    from taximobile_api.main import create_app

    operations, issues = validate_web_workspace(create_app())
    if issues:
        print("Web/backend API contract validation failed:", file=sys.stderr)
        for issue in issues:
            print(f"- {issue.source}:{issue.line}: {issue.reason}", file=sys.stderr)
        return 1

    print(
        "Web/backend API contract validation passed "
        f"({len(operations)} expanded HTTP operations)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
