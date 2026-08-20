from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "validate_mobile_recovery.py"
SPEC = importlib.util.spec_from_file_location("validate_mobile_recovery", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class MobileRecoveryValidationTest(unittest.TestCase):
    def test_repository_wiring_is_valid(self) -> None:
        MODULE.validate_mobile_recovery()

    def test_unvalidated_android_network_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            required = (
                "shared/src/commonMain/kotlin/org/example/taximobile/feature/connectivity/Connectivity.kt",
                "androidApp/src/main/kotlin/org/example/taximobile/MainActivity.kt",
                "androidApp/src/main/kotlin/org/example/taximobile/AndroidConnectivityObserver.kt",
                "androidApp/src/main/AndroidManifest.xml",
                "shared/src/iosMain/kotlin/org/example/taximobile/MainViewController.kt",
                "shared/src/iosMain/kotlin/org/example/taximobile/IosConnectivityObserver.kt",
                "shared/src/commonMain/kotlin/org/example/taximobile/feature/app/AppAction.kt",
                "shared/src/commonMain/kotlin/org/example/taximobile/App.kt",
                "shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt",
                "shared/src/commonMain/kotlin/org/example/taximobile/feature/driver/DriverHome.kt",
                "shared/src/commonMain/kotlin/org/example/taximobile/feature/app/TaxiMobileScreen.kt",
                "shared/src/commonMain/kotlin/org/example/taximobile/feature/app/SharedSections.kt",
                "shared/src/commonMain/kotlin/org/example/taximobile/feature/location/OneShotLocationGate.kt",
                "androidApp/src/main/kotlin/org/example/taximobile/AndroidCurrentLocationRequester.kt",
                "shared/src/iosMain/kotlin/org/example/taximobile/IosCurrentLocationRequester.kt",
                "shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/MapFab.kt",
                "shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/SuccessConfirmation.kt",
            )
            for relative in required:
                source = MODULE.ROOT / relative
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                text = source.read_text(encoding="utf-8")
                if relative.endswith("AndroidConnectivityObserver.kt"):
                    text = text.replace("NetworkCapabilities.NET_CAPABILITY_VALIDATED", "0")
                destination.write_text(text, encoding="utf-8")

            with self.assertRaises(MODULE.MobileRecoveryConfigurationError):
                MODULE.validate_mobile_recovery(root)

    def test_authenticated_action_that_bypasses_recovery_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            required = (
                "shared/src/commonMain/kotlin/org/example/taximobile/feature/connectivity/Connectivity.kt",
                "androidApp/src/main/kotlin/org/example/taximobile/MainActivity.kt",
                "androidApp/src/main/kotlin/org/example/taximobile/AndroidConnectivityObserver.kt",
                "androidApp/src/main/AndroidManifest.xml",
                "shared/src/iosMain/kotlin/org/example/taximobile/MainViewController.kt",
                "shared/src/iosMain/kotlin/org/example/taximobile/IosConnectivityObserver.kt",
                "shared/src/commonMain/kotlin/org/example/taximobile/feature/app/AppAction.kt",
                "shared/src/commonMain/kotlin/org/example/taximobile/App.kt",
                "shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt",
                "shared/src/commonMain/kotlin/org/example/taximobile/feature/driver/DriverHome.kt",
                "shared/src/commonMain/kotlin/org/example/taximobile/feature/app/TaxiMobileScreen.kt",
                "shared/src/commonMain/kotlin/org/example/taximobile/feature/app/SharedSections.kt",
                "shared/src/commonMain/kotlin/org/example/taximobile/feature/location/OneShotLocationGate.kt",
                "androidApp/src/main/kotlin/org/example/taximobile/AndroidCurrentLocationRequester.kt",
                "shared/src/iosMain/kotlin/org/example/taximobile/IosCurrentLocationRequester.kt",
                "shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/MapFab.kt",
                "shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/SuccessConfirmation.kt",
            )
            for relative in required:
                source = MODULE.ROOT / relative
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                text = source.read_text(encoding="utf-8")
                if relative.endswith("MainActivity.kt"):
                    text = text.replace(
                        "submitAction(AppAction(AppActionKind.REQUEST_RIDE))",
                        "scope.launch",
                    )
                destination.write_text(text, encoding="utf-8")

            with self.assertRaises(MODULE.MobileRecoveryConfigurationError):
                MODULE.validate_mobile_recovery(root)


if __name__ == "__main__":
    unittest.main()
