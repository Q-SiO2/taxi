"""Portable source gate for TaxiMobile's fail-closed crash reporting wiring."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CrashReportingConfigurationError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CrashReportingConfigurationError(message)


def validate_mobile_crash_reporting(root: Path = ROOT) -> None:
    catalog = (root / "gradle/libs.versions.toml").read_text(encoding="utf-8")
    android_build = (root / "androidApp/build.gradle.kts").read_text(encoding="utf-8")
    manifest = (root / "androidApp/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
    project = (root / "iosApp/iosApp.xcodeproj/project.pbxproj").read_text(encoding="utf-8")
    uploader = (root / "scripts/upload-ios-crash-symbols.sh").read_text(encoding="utf-8")

    require('firebase-crashlytics-plugin = "3.0.7"' in catalog, "Android Crashlytics plugin must stay pinned.")
    require("firebase-crashlytics" in catalog, "Android Crashlytics SDK is missing.")
    require("firebase-analytics" not in catalog.lower(), "Crash reporting must not add Firebase Analytics.")
    require('apply(plugin = "com.google.firebase.crashlytics")' in android_build, "Android symbol plugin is missing.")
    require("projectFirebaseConfigurationPresent" in android_build, "Android Firebase plugin must remain config-gated.")
    require('resValue("bool", "firebase_crashlytics_collection_enabled", "false")' in android_build,
            "Android debug crash collection must be disabled.")
    require("taximobileCrashReportingEnabled" in android_build, "Android release collection must be explicit.")
    require("!allowMissingFirebaseVerificationProvider.get()" in android_build,
            "Providerless Android verification must force collection off.")
    require("firebase_crashlytics_collection_enabled" in manifest, "Android collection metadata is missing.")

    require(project.count("productName = FirebaseCrashlytics;") == 1, "iOS must pin one Crashlytics package product.")
    require(project.count("FirebaseCrashlytics in Frameworks") >= 4, "Both iOS roles must link Crashlytics.")
    require(project.count("Upload Crash Symbols */,") == 2, "Both iOS targets need a final symbol phase.")
    require(project.count("INFOPLIST_KEY_FirebaseCrashlyticsCollectionEnabled = NO;") == 2,
            "Both iOS debug roles must disable collection.")
    require(project.count('INFOPLIST_KEY_FirebaseCrashlyticsCollectionEnabled = "$(TAXIMOBILE_CRASH_REPORTING_ENABLED)";') == 2,
            "Both iOS release roles must use the explicit collection switch.")
    require(project.count("Prepare iOS Configuration */,") == 2, "Both iOS targets must prepare provider config.")
    require(
        project.count("Prepare iOS Configuration */,") == project.count("Upload Crash Symbols */,"),
        "Every iOS provider-preparation phase needs a symbol-upload phase.",
    )
    require("Crashlytics/run" in uploader, "iOS must invoke Firebase's pinned symbol uploader.")
    require("TAXIMOBILE_CRASH_REPORTING_ENABLED" in uploader, "iOS symbol upload must be fail-closed.")
    require("TAXIMOBILE_ALLOW_MISSING_FIREBASE_FOR_VERIFICATION" in uploader,
            "Providerless CI must remain an explicit non-distributable path.")

    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for source_root in (root / "androidApp/src", root / "iosApp/iosApp")
        for path in source_root.rglob("*")
        if path.suffix in {".kt", ".swift"}
    )
    forbidden = ("setUserId(", "setUserID(", "setCustomKey(", "Crashlytics.crashlytics().log(")
    require(not any(token in source_text for token in forbidden),
            "Crash reporting must not attach identities, custom business data, or breadcrumbs.")


if __name__ == "__main__":
    validate_mobile_crash_reporting()
    print("Validated fail-closed Android/iOS Crashlytics wiring.")
