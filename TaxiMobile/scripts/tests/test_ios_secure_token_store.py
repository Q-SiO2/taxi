from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "shared" / "src" / "iosMain" / "kotlin" / "org" / "example" / "taximobile" / "data" / "auth" / "IosSecureTokenStore.kt"


class IosSecureTokenStoreSourceTest(unittest.TestCase):
    def test_keychain_bridge_uses_owned_core_foundation_values(self) -> None:
        source = STORE.read_text(encoding="utf-8")

        for required in (
            "CFDictionaryCreateMutable",
            "CFStringCreateWithCString",
            "CFDataCreate",
            "CFGetTypeID(item) != CFDataGetTypeID()",
            "CFRelease(item)",
            "CFRelease(dictionary)",
        ):
            self.assertIn(required, source)

        self.assertNotIn("as CFDictionaryRef", source)
        self.assertNotIn("as? NSData", source)

    def test_keychain_writes_are_atomic_and_status_checked(self) -> None:
        source = STORE.read_text(encoding="utf-8")

        for required in (
            'const val SESSION_ACCOUNT = "session-v1"',
            "encodeStoredTokens",
            "SecItemUpdate",
            "errSecDuplicateItem",
            'keychainFailure("read", status)',
            'keychainFailure("delete", status)',
            "kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly",
        ):
            self.assertIn(required, source)

        self.assertNotIn("write(ACCESS_ACCOUNT", source)
        self.assertNotIn("write(REFRESH_ACCOUNT", source)


if __name__ == "__main__":
    unittest.main()
