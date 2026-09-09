from pathlib import Path
import sys
import unittest


SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from validate_legacy_admin_retirement import (
    CLIENT_SOURCE_ROOTS,
    LegacyAdminCallerError,
    WORKSPACE_ROOT,
    validate_legacy_admin_callers,
)


class LegacyAdminRetirementValidationTests(unittest.TestCase):
    def _workspace(self, root: Path) -> None:
        for source_root in CLIENT_SOURCE_ROOTS:
            (root / source_root).mkdir(parents=True, exist_ok=True)

    def test_current_client_source_has_no_legacy_admin_callers(self) -> None:
        validate_legacy_admin_callers(WORKSPACE_ROOT)

    def test_direct_legacy_endpoint_literal_is_rejected_without_echoing_source(
        self,
    ) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._workspace(root)
            source = root / CLIENT_SOURCE_ROOTS[0] / "LegacyGateway.kt"
            source.write_text(
                'client.post(endpoints.url("admin/users/private-value/suspend"))',
                encoding="utf-8",
            )

            with self.assertRaises(LegacyAdminCallerError) as caught:
                validate_legacy_admin_callers(root)

            message = str(caught.exception)
            self.assertIn("LegacyGateway.kt", message)
            self.assertNotIn("private-value", message)

    def test_absolute_legacy_url_is_rejected(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._workspace(root)
            source = root / CLIENT_SOURCE_ROOTS[3] / "LegacyAbsoluteUrl.ts"
            source.write_text(
                'fetch("https://api.example.test/api/v1/admin/audit-logs")',
                encoding="utf-8",
            )

            with self.assertRaises(LegacyAdminCallerError):
                validate_legacy_admin_callers(root)

    def test_scoped_administrative_grant_name_is_not_a_false_positive(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._workspace(root)
            source = root / CLIENT_SOURCE_ROOTS[3] / "StaffGateway.kt"
            source.write_text(
                'client.get(endpoints.url("operations/administrative-grants"))',
                encoding="utf-8",
            )

            validate_legacy_admin_callers(root)


if __name__ == "__main__":
    unittest.main()
