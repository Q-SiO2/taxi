from __future__ import annotations

from pathlib import Path
import unittest


PROJECT = Path(__file__).resolve().parents[2]


class DriverDocumentClientContractTest(unittest.TestCase):
    def test_ios_picker_is_bounded_scoped_and_connected_to_authoritative_upload(self) -> None:
        kotlin = (PROJECT / "shared/src/iosMain/kotlin/org/example/taximobile/MainViewController.kt").read_text(
            encoding="utf-8"
        )
        swift = (PROJECT / "iosApp/iosApp/ContentView.swift").read_text(encoding="utf-8")

        for required in (
            "requestDriverDocument",
            "driverDocumentPickerAvailable = requestDriverDocument != null",
            "IOS_DRIVER_DOCUMENT_MAX_BYTES = 10 * 1024 * 1024",
            'setOf("application/pdf", "image/jpeg", "image/png")',
            "uploadDriverCityApplicationDocument",
            "mediaType == null ||",
            "mediaType !in IOS_DRIVER_DOCUMENT_MEDIA_TYPES ||",
        ):
            self.assertIn(required, kotlin)
        for required in (
            "UIDocumentPickerViewController",
            "forOpeningContentTypes: [.pdf, .jpeg, .png]",
            "startAccessingSecurityScopedResource()",
            "stopAccessingSecurityScopedResource()",
            "fileSize <= 10 * 1024 * 1024",
            "data.count <= 10 * 1024 * 1024",
            "data.base64EncodedString()",
        ):
            self.assertIn(required, swift)
        self.assertNotIn("UIImagePickerController", swift)

    def test_android_and_browser_pickers_keep_the_same_closed_media_set(self) -> None:
        android = (PROJECT / "androidApp/src/main/kotlin/org/example/taximobile/MainActivity.kt").read_text(
            encoding="utf-8"
        )
        browser = (
            PROJECT
            / "webApp/src/jsMain/kotlin/org/example/taximobile/applicant/state/BrowserDriverDocumentPicker.js.kt"
        ).read_text(encoding="utf-8")

        self.assertIn("ActivityResultContracts.OpenDocument()", android)
        for media_type in ("application/pdf", "image/jpeg", "image/png"):
            self.assertIn(media_type, android)
            self.assertIn(media_type, browser)
        self.assertIn("MAX_BYTES = 10 * 1024 * 1024", browser)


if __name__ == "__main__":
    unittest.main()
