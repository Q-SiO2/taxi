"""Portable source gate for native MapLibre style-composition safety."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAP_IMPLEMENTATIONS = (
    "shared/src/androidMain/kotlin/org/example/taximobile/feature/maps/MapLibreTripMap.android.kt",
    "shared/src/iosMain/kotlin/org/example/taximobile/feature/maps/MapLibreTripMap.ios.kt",
)


class MapLibreCompositionError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise MapLibreCompositionError(message)


def validate_maplibre_composition(root: Path = ROOT) -> None:
    for relative in MAP_IMPLEMENTATIONS:
        source = (root / relative).read_text(encoding="utf-8")
        map_start = source.index("MaplibreMap(")
        map_content_start = source.index("    ) {", map_start)
        first_layer = source.index("LineLayer(", map_content_start)
        source_positions = []
        cursor = 0
        while True:
            position = source.find("rememberGeoJsonSource(", cursor)
            if position == -1:
                break
            source_positions.append(position)
            cursor = position + 1

        require(
            len(source_positions) == 4,
            f"{relative} must declare exactly four TaxiMobile GeoJSON sources.",
        )
        require(
            all(map_content_start < position < first_layer for position in source_positions),
            f"{relative} declares a GeoJSON source outside MaplibreMap's style-composition scope.",
        )
        require(
            "BaseStyle.Json(TaxiMobileFallbackMapStyleJson)" in source,
            f"{relative} has no dependency-free fallback style.",
        )
        require(
            "onMapLoadFailed" in source and "usingFallbackStyle = true" in source,
            f"{relative} does not fail over after a configured style load failure.",
        )

    build = (root / "androidApp/build.gradle.kts").read_text(encoding="utf-8")
    launcher = (root / "scripts/run-android-device.ps1").read_text(encoding="utf-8")
    passenger = (
        root / "shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt"
    ).read_text(encoding="utf-8")
    neutral_style = (
        root / "shared/src/commonMain/kotlin/org/example/taximobile/feature/maps/MapLibreTripMap.kt"
    ).read_text(encoding="utf-8")
    generic_style = "https://tiles.openfreemap.org/styles/positron"
    require(generic_style in build, "Android debug builds do not default to the restrained generic map style.")
    require(generic_style in launcher, "The physical-device launcher overrides the restrained generic map style.")
    require(
        "showManualCoordinateEntry || mapUnavailable" in passenger,
        "Passenger manual location entry is not promoted after map failure.",
    )
    fallback = neutral_style[neutral_style.index("TaxiMobileFallbackMapStyleJson"):]
    require("http://" not in fallback and "https://" not in fallback,
            "The fallback map style must not depend on a remote asset or source.")


if __name__ == "__main__":
    validate_maplibre_composition()
    print("Validated Android/iOS MapLibre sources inside native style-composition scope.")
