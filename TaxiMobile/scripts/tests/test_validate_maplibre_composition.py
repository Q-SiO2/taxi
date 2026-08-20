from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "validate_maplibre_composition.py"
SPEC = importlib.util.spec_from_file_location("validate_maplibre_composition", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class MapLibreCompositionValidationTest(unittest.TestCase):
    def copy_implementations(self, root: Path) -> None:
        for relative in MODULE.MAP_IMPLEMENTATIONS:
            source = MODULE.ROOT / relative
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
        for relative in (
            "androidApp/build.gradle.kts",
            "scripts/run-android-device.ps1",
            "shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt",
            "shared/src/commonMain/kotlin/org/example/taximobile/feature/maps/MapLibreTripMap.kt",
        ):
            source = MODULE.ROOT / relative
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())

    def test_repository_composition_is_valid(self) -> None:
        MODULE.validate_maplibre_composition()

    def test_source_outside_map_style_scope_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.copy_implementations(root)
            android = root / MODULE.MAP_IMPLEMENTATIONS[0]
            source = android.read_text(encoding="utf-8")
            declaration = (
                "        val pickupSource = rememberGeoJsonSource("
                "GeoJsonData.JsonString(pointGeoJson(pickup)))\n"
            )
            source = source.replace(declaration, "", 1)
            source = source.replace(
                "    val focusPoints =",
                declaration.removeprefix("        ") + "    val focusPoints =",
                1,
            )
            android.write_text(source, encoding="utf-8")

            with self.assertRaises(MODULE.MapLibreCompositionError):
                MODULE.validate_maplibre_composition(root)

    def test_remote_dependency_in_neutral_fallback_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.copy_implementations(root)
            common = root / "shared/src/commonMain/kotlin/org/example/taximobile/feature/maps/MapLibreTripMap.kt"
            source = common.read_text(encoding="utf-8").replace(
                '"sources": {},',
                '"sources": {"unsafe": "https://assets.example.test"},',
            )
            common.write_text(source, encoding="utf-8")

            with self.assertRaises(MODULE.MapLibreCompositionError):
                MODULE.validate_maplibre_composition(root)


if __name__ == "__main__":
    unittest.main()
