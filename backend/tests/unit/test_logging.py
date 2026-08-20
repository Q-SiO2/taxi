import json
import logging
from starlette.requests import Request

from taximobile_api.core.logging import JsonFormatter, correlation_id, request_route_template


def test_json_logs_include_only_allowlisted_request_metadata() -> None:
    record = logging.LogRecord("taximobile_api", logging.INFO, "", 0, "request_completed", (), None)
    record.request_id = "request-id"
    record.path = "/api/v1/rides"
    record.status_code = 201
    record.error_type = "RuntimeError"
    record.worker = "outbox"
    record.password = "must-not-appear"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["request_id"] == "request-id"
    assert payload["path"] == "/api/v1/rides"
    assert payload["error_type"] == "RuntimeError"
    assert payload["worker"] == "outbox"
    assert "password" not in payload


def test_request_logging_uses_route_templates_and_hides_unmatched_paths() -> None:
    class Route:
        path = "/api/v1/rides/{ride_id}"

    matched = Request({"type": "http", "method": "GET", "path": "/api/v1/rides/private-id", "headers": [], "route": Route()})
    unmatched = Request({"type": "http", "method": "GET", "path": "/private/passenger@example.com", "headers": []})

    assert request_route_template(matched) == "/api/v1/rides/{ride_id}"
    assert request_route_template(unmatched) == "_unmatched"


def test_correlation_id_accepts_only_canonical_uuids() -> None:
    trusted = "11111111-1111-4111-8111-111111111111"

    assert correlation_id(trusted) == trusted
    assert correlation_id("passenger@example.com") != "passenger@example.com"
    assert correlation_id(None)
