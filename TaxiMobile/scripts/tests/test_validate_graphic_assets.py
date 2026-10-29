from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = WORKSPACE_ROOT / "TaxiMobile" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from validate_graphic_assets import read_png_header, validate_assets, validate_runtime_artwork, validate_svg, validate_png, sha256  # noqa: E402


class GraphicAssetValidationTest(unittest.TestCase):
    def test_welcome_export_is_bound_to_selected_portrait_not_rejected_vectors(self) -> None:
        manifest = json.loads((WORKSPACE_ROOT / "assets/manifest.json").read_text(encoding="utf-8"))
        landing = next(item for item in manifest["assets"] if item["id"] == "B01")
        self.assertEqual("explicit_exports", landing["runtime"])
        self.assertIn("assets/illustrations/onboarding/source/illustration_landing_undraw.svg", landing["sources"])
        self.assertEqual("assets/illustrations/onboarding/source/illustration_landing_navy_outline_master.png", landing["selected_source"])
        self.assertTrue((WORKSPACE_ROOT / landing["provenance_record"]).is_file())
        svg_exporter = (WORKSPACE_ROOT / "assets/tools/export_svg_rasters.cjs").read_text(encoding="utf-8")
        self.assertNotIn('source: "illustrations/onboarding/illustration_landing.svg"', svg_exporter)
        self.assertNotIn('source: "illustrations/onboarding/source/illustration_landing_undraw.svg"', svg_exporter)
        self.assertNotIn('source: "illustrations/onboarding/source/illustration_landing_qarawiyyin.svg"', svg_exporter)
        self.assertIn('source: "illustrations/onboarding/source/illustration_landing_navy_outline_master.png"', svg_exporter)
        self.assertEqual(sha256(WORKSPACE_ROOT / landing["selected_source"]), sha256(WORKSPACE_ROOT / landing["exports"][0]))

    def test_opaque_welcome_is_explicit_and_does_not_weaken_cutout_validation(self) -> None:
        manifest = json.loads((WORKSPACE_ROOT / "assets/manifest.json").read_text(encoding="utf-8"))
        landing = next(item for item in manifest["assets"] if item["id"] == "B01")
        self.assertFalse(landing["require_alpha"])
        source = WORKSPACE_ROOT / landing["selected_source"]
        errors: list[str] = []
        validate_png(source, errors, WORKSPACE_ROOT)
        self.assertTrue(any("real alpha channel" in error for error in errors))
        errors.clear()
        validate_png(source, errors, WORKSPACE_ROOT, require_alpha=False)
        self.assertEqual([], errors)
        self.assertLessEqual(source.stat().st_size, landing["max_runtime_bytes"])

    def test_stock_palette_does_not_extend_the_ui_brand_palette(self) -> None:
        manifest = json.loads((WORKSPACE_ROOT / "assets/manifest.json").read_text(encoding="utf-8"))
        brand = set(manifest["palette"])
        source = WORKSPACE_ROOT / "assets/illustrations/onboarding/source/illustration_landing_undraw.svg"
        errors: list[str] = []
        validate_svg(source, brand, errors, WORKSPACE_ROOT)
        self.assertTrue(any("outside the approved palette" in error for error in errors))
        landing = next(item for item in manifest["assets"] if item["id"] == "B01")
        scoped = brand | set(landing["source_palettes"][source.relative_to(WORKSPACE_ROOT).as_posix()])
        errors.clear()
        validate_svg(source, scoped, errors, WORKSPACE_ROOT)
        self.assertEqual([], errors)

    def test_short_hex_colours_are_validated_not_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "test.svg"
            source.write_text('<svg viewBox="0 0 10 10"><path fill="#abc"/></svg>', encoding="utf-8")
            errors: list[str] = []
            validate_svg(source, {"#FFFFFF"}, errors, root)
            self.assertIn("#AABBCC", " ".join(errors))

    def test_live_decorative_exports_keep_master_dimensions_and_alpha(self) -> None:
        for name, dimensions in (
            ("illustration_landing_runtime", (941, 1672)),
            ("brand_logo_mark_runtime", (256, 256)),
            ("vehicle_silhouette_standard_runtime", (640, 360)),
        ):
            path = WORKSPACE_ROOT / "TaxiMobile/shared/src/commonMain/composeResources/drawable" / f"{name}.png"
            width, height, bits, color, _ = read_png_header(path)
            self.assertEqual(dimensions, (width, height))
            self.assertEqual(8, bits)
            self.assertIn(color, (2, 4, 6) if name == "illustration_landing_runtime" else (4, 6))

    def test_shared_ui_cannot_load_an_svg_even_when_the_master_is_mirrored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shared = root / "TaxiMobile/shared/src/commonMain"
            (shared / "kotlin").mkdir(parents=True)
            (shared / "composeResources/drawable").mkdir(parents=True)
            (shared / "kotlin/Unsafe.kt").write_text("painterResource(Res.drawable.logo)", encoding="utf-8")
            (shared / "composeResources/drawable/logo.svg").write_text("<svg/>", encoding="utf-8")
            errors = validate_runtime_artwork(root)
            self.assertEqual(1, len(errors))
            self.assertIn("Android requires a PNG or XML-vector", errors[0])

    def test_missing_and_corrupt_runtime_png_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shared = root / "TaxiMobile/shared/src/commonMain"
            (shared / "kotlin").mkdir(parents=True)
            (shared / "composeResources/drawable").mkdir(parents=True)
            (shared / "kotlin/Art.kt").write_text('val path = "drawable/logo_runtime.png"', encoding="utf-8")
            self.assertIn("missing runtime PNG", " ".join(validate_runtime_artwork(root)))
            (shared / "composeResources/drawable/logo_runtime.png").write_bytes(b"not a PNG")
            self.assertIn("invalid PNG", " ".join(validate_runtime_artwork(root)))

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
