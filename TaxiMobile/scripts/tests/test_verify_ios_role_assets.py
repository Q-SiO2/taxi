from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "verify_ios_role_assets.py"
SPEC = importlib.util.spec_from_file_location("verify_ios_role_assets", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class VerifyIosRoleAssetsTest(unittest.TestCase):
    def test_checked_in_role_assets_are_valid(self) -> None:
        MODULE.verify_role_assets(MODULE_PATH.parents[1])

    def test_identical_role_icons_are_rejected(self) -> None:
        source = MODULE_PATH.parents[1]
        with tempfile.TemporaryDirectory() as temporary_directory:
            mobile_root = Path(temporary_directory) / "TaxiMobile"
            shutil.copytree(source / "iosApp", mobile_root / "iosApp")
            passenger = mobile_root / "iosApp/iosApp/Assets.xcassets/AppIcon.appiconset/app-icon-1024.png"
            driver = mobile_root / "iosApp/iosApp/Assets.xcassets/DriverAppIcon.appiconset/driver-app-icon-1024.png"
            shutil.copyfile(passenger, driver)

            with self.assertRaisesRegex(MODULE.RoleAssetError, "must remain distinct"):
                MODULE.verify_role_assets(mobile_root)


if __name__ == "__main__":
    unittest.main()
