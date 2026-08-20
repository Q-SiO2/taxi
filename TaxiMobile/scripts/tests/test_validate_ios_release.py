from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "validate_ios_release.py"
SPEC = importlib.util.spec_from_file_location("validate_ios_release", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ValidateIosReleaseTest(unittest.TestCase):
    def test_explicit_https_release_configuration_is_valid(self) -> None:
        MODULE.validate_release_configuration(
            "https://api.example.ma",
            "https://maps.example.ma/style.json?version=1",
            "42",
            "1.2.0",
            "YES",
        )

    def test_api_must_be_an_https_origin(self) -> None:
        for value in (
            "http://api.example.ma",
            "https://api.taximobile.invalid",
            "https://user:secret@api.example.ma",
            "https://api.example.ma/api/v1",
            "https://api.example.ma?private=value",
        ):
            with self.subTest(value=value), self.assertRaises(MODULE.ReleaseConfigurationError):
                MODULE.validate_release_configuration(
                    value,
                    "https://maps.example.ma/style.json",
                    "1",
                    "1.0.0",
                    "YES",
                )

    def test_map_and_versions_fail_closed(self) -> None:
        invalid_values = (
            ("https://maps.taximobile.invalid/style.json", "1", "1.0.0"),
            ("http://maps.example.ma/style.json", "1", "1.0.0"),
            ("https://maps.example.ma/style.json", "0", "1.0.0"),
            ("https://maps.example.ma/style.json", "1", "1.0.0-ci"),
        )
        for map_url, build_number, version in invalid_values:
            with self.subTest(map_url=map_url, build_number=build_number, version=version):
                with self.assertRaises(MODULE.ReleaseConfigurationError):
                    MODULE.validate_release_configuration(
                        "https://api.example.ma",
                        map_url,
                        build_number,
                        version,
                        "YES",
                    )

    def test_crash_reporting_is_required_for_distributable_releases(self) -> None:
        with self.assertRaises(MODULE.ReleaseConfigurationError):
            MODULE.validate_release_configuration(
                "https://api.example.ma",
                "https://maps.example.ma/style.json",
                "1",
                "1.0.0",
                "NO",
            )

        MODULE.validate_release_configuration(
            "https://api.example.ma",
            "https://maps.example.ma/style.json",
            "1",
            "1.0.0",
            "NO",
            providerless_verification=True,
        )

    def test_crash_reporting_switch_is_closed_to_yes_or_no(self) -> None:
        with self.assertRaises(MODULE.ReleaseConfigurationError):
            MODULE.validate_release_configuration(
                "https://api.example.ma",
                "https://maps.example.ma/style.json",
                "1",
                "1.0.0",
                "true",
            )


if __name__ == "__main__":
    unittest.main()
