import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from validate_localization import validate_catalog_data, validate_localization  # noqa: E402


class LocalizationValidationTest(unittest.TestCase):
    def test_committed_localization_contract(self) -> None:
        validate_localization()

    def test_missing_locale_key_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "key mismatch"):
            validate_catalog_data(
                {
                    "en": {"greeting": "Hello %1$s"},
                    "fr": {"greeting": "Bonjour %1$s"},
                    "ar": {},
                }
            )

    def test_placeholder_drift_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "placeholders"):
            validate_catalog_data(
                {
                    "en": {"greeting": "Hello %1$s"},
                    "fr": {"greeting": "Bonjour"},
                    "ar": {"greeting": "مرحباً %1$s"},
                }
            )


if __name__ == "__main__":
    unittest.main()
