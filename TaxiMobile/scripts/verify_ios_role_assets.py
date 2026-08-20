"""Portable structural verification for TaxiMobile iOS role branding."""

from __future__ import annotations

import argparse
import hashlib
import json
import plistlib
import struct
from pathlib import Path


class RoleAssetError(ValueError):
    pass


def png_metadata(path: Path) -> tuple[int, int, int, int]:
    data = path.read_bytes()
    if len(data) < 29 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise RoleAssetError(f"{path} is not a valid PNG with an IHDR header.")
    width, height = struct.unpack(">II", data[16:24])
    bit_depth = data[24]
    color_type = data[25]
    return width, height, bit_depth, color_type


def catalog_image(asset_root: Path, catalog: str, expected_filename: str) -> Path:
    catalog_root = asset_root / f"{catalog}.appiconset"
    try:
        contents = json.loads((catalog_root / "Contents.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RoleAssetError(f"{catalog} must have a valid Contents.json.") from error
    universal = [
        image
        for image in contents.get("images", [])
        if image.get("idiom") == "universal"
        and image.get("platform") == "ios"
        and image.get("size") == "1024x1024"
        and "appearances" not in image
    ]
    if len(universal) != 1 or universal[0].get("filename") != expected_filename:
        raise RoleAssetError(f"{catalog} must declare exactly one base 1024x1024 iOS image.")
    image_path = catalog_root / expected_filename
    if not image_path.is_file():
        raise RoleAssetError(f"{catalog} is missing {expected_filename}.")
    width, height, bit_depth, color_type = png_metadata(image_path)
    if (width, height, bit_depth, color_type) != (1024, 1024, 8, 2):
        raise RoleAssetError(f"{catalog} must be an opaque 8-bit RGB 1024x1024 PNG.")
    return image_path


def verify_role_assets(mobile_root: Path) -> None:
    ios_root = mobile_root / "iosApp"
    asset_root = ios_root / "iosApp" / "Assets.xcassets"
    passenger = catalog_image(asset_root, "AppIcon", "app-icon-1024.png")
    driver = catalog_image(asset_root, "DriverAppIcon", "driver-app-icon-1024.png")
    if hashlib.sha256(passenger.read_bytes()).digest() == hashlib.sha256(driver.read_bytes()).digest():
        raise RoleAssetError("Passenger and driver iOS icons must remain distinct.")

    project = (ios_root / "iosApp.xcodeproj" / "project.pbxproj").read_text(encoding="utf-8")
    if project.count("ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;") != 2:
        raise RoleAssetError("Passenger Debug and Release must use AppIcon.")
    if project.count("ASSETCATALOG_COMPILER_APPICON_NAME = DriverAppIcon;") != 2:
        raise RoleAssetError("Driver Debug and Release must use DriverAppIcon.")

    with (ios_root / "iosApp" / "Info.plist").open("rb") as plist_file:
        info = plistlib.load(plist_file)
    if info.get("UILaunchScreen", {}).get("UIColorName") != "LaunchBackground":
        raise RoleAssetError("UILaunchScreen must use the LaunchBackground asset color.")

    try:
        launch_color = json.loads(
            (asset_root / "LaunchBackground.colorset" / "Contents.json").read_text(encoding="utf-8")
        )["colors"][0]["color"]["components"]
    except (OSError, json.JSONDecodeError, KeyError, IndexError, TypeError) as error:
        raise RoleAssetError("LaunchBackground must be a valid asset color.") from error
    expected = {"red": "0.027451", "green": "0.078431", "blue": "0.149020", "alpha": "1.000"}
    if launch_color != expected:
        raise RoleAssetError("LaunchBackground must remain the approved navy.950 #071426.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mobile-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    arguments = parser.parse_args()
    try:
        verify_role_assets(arguments.mobile_root.resolve())
    except RoleAssetError as error:
        parser.exit(1, f"error: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
