import base64
import io
import json
from pathlib import Path
import sys
import unittest
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from require_complete_dependency_comparison import (
    ComparisonError, WARNING_HEADER, comparison_identity, inspect_comparison, page_has_warning,
)


class Response(io.BytesIO):
    def __init__(self, data, warning=None):
        super().__init__(json.dumps(data).encode())
        self.headers = {WARNING_HEADER: warning} if warning else {}


class DependencyCompletenessTests(unittest.TestCase):
    def test_identity_uses_exact_same_repository_base_and_head(self):
        event = {"pull_request": {side: {"repo": {"full_name": "example/taxi"}, "sha": char * 40}
                                  for side, char in (("base", "a"), ("head", "b"))}}
        self.assertEqual(comparison_identity(event, "example/taxi"), ("a" * 40, "b" * 40))
        event["pull_request"]["head"]["repo"]["full_name"] = "fork/taxi"
        with self.assertRaisesRegex(ComparisonError, "Fork"):
            comparison_identity(event, "example/taxi")
        event["pull_request"]["head"] = {"repo": {"full_name": "example/taxi"}, "sha": "main"}
        with self.assertRaisesRegex(ComparisonError, "immutable"):
            comparison_identity(event, "example/taxi")

    def test_warning_and_malformed_warning_fail_closed(self):
        self.assertFalse(page_has_warning(None))
        self.assertTrue(page_has_warning(base64.b64encode(b"missing head snapshot").decode()))
        for value in ("not base64!", base64.b64encode(b"\xff").decode()):
            with self.subTest(value=value), self.assertRaises(ComparisonError):
                page_has_warning(value)

    def test_every_page_checked_and_token_not_in_url(self):
        pages = iter([Response([{}] * 100), Response([{}] * 2)])
        requests = []
        def opener(request, **kwargs):
            requests.append(request)
            return next(pages)
        result = inspect_comparison("example/taxi", "a" * 40, "b" * 40, "private-test-token", opener=opener)
        self.assertEqual((result["pages"], result["changes"]), (2, 102))
        self.assertIn("page=2", requests[-1].full_url)
        self.assertNotIn("private-test-token", requests[-1].full_url)
        self.assertTrue(result["snapshots_complete"])

    def test_later_page_warning_cannot_be_hidden(self):
        pages = iter([Response([{}] * 100), Response([], base64.b64encode(b"missing snapshot").decode())])
        with self.assertRaisesRegex(ComparisonError, "incomplete"):
            inspect_comparison("example/taxi", "a" * 40, "b" * 40, "token", opener=lambda *a, **k: next(pages))

    def test_api_errors_do_not_echo_body_or_token(self):
        for error in (HTTPError("https://api.github.com", 403, "private body", {}, None), URLError("private body")):
            def opener(*args, **kwargs):
                raise error
            with self.subTest(error=type(error).__name__), self.assertRaises(ComparisonError) as caught:
                inspect_comparison("example/taxi", "a" * 40, "b" * 40, "secret-token", opener=opener)
            self.assertNotIn("private body", str(caught.exception))
            self.assertNotIn("secret-token", str(caught.exception))

    def test_response_shape_and_page_bounds(self):
        for body in ({"message": "unexpected"}, ["unexpected"]):
            with self.subTest(body=body), self.assertRaisesRegex(ComparisonError, "shape"):
                inspect_comparison("example/taxi", "a" * 40, "b" * 40, "token", opener=lambda *a, **k: Response(body))
        with self.assertRaisesRegex(ComparisonError, "page count"):
            inspect_comparison("example/taxi", "a" * 40, "b" * 40, "token", opener=lambda *a, **k: Response([{}] * 100))
