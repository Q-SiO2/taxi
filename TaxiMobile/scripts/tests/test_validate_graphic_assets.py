from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = WORKSPACE_ROOT / "TaxiMobile" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from validate_graphic_assets import read_png_header, validate_assets  # noqa: E402


class GraphicAssetValidationTest(unittest.TestCase):
    def test_repository_asset_contract_is_valid(self) -> None:
        self.assertEqual([], validate_assets(WORKSPACE_ROOT))

    def test_manifest_covers_every_editable_svg(self) -> None:
        manifest = json.loads(
            (WORKSPACE_ROOT / "assets" / "manifest.json").read_text(encoding="utf-8")
        )
        listed = {
            str(source)
            for asset in manifest["assets"]
            for source in asset.get("sources", [])
            if str(source).endswith(".svg")
        }
        actual = {
            path.relative_to(WORKSPACE_ROOT).as_posix()
            for path in (WORKSPACE_ROOT / "assets").rglob("*.svg")
        }
        self.assertEqual(actual, listed)

    def test_service_card_exports_have_real_alpha_and_declared_size(self) -> None:
        export_dir = WORKSPACE_ROOT / "assets" / "vehicles" / "renders" / "exports"
        for service in ("standard", "large"):
            for size in (256, 512, 1024):
                path = export_dir / f"vehicle_render_{service}_{size}.png"
                width, height, bit_depth, color_type, _ = read_png_header(path)
                self.assertEqual((size, size), (width, height))
                self.assertEqual(8, bit_depth)
                self.assertIn(color_type, (4, 6))


if __name__ == "__main__":
    unittest.main()
