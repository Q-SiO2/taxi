"""Normalize approved transparent vehicle masters into deterministic UI exports.

This is a design-time tool, not an application dependency. Install Pillow in the
Python environment used to run it: ``python -m pip install Pillow``.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image


ASSET_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ASSET_ROOT / "vehicles" / "renders" / "source"
EXPORT_DIR = ASSET_ROOT / "vehicles" / "renders" / "exports"
CANVAS_SIZE = 1024
MAX_ART_WIDTH = 960
MAX_ART_HEIGHT = 880
ART_BOTTOM = 940

RENDERS = {
    "standard": SOURCE_DIR / "vehicle_render_standard_generated_master.png",
    "large": SOURCE_DIR / "vehicle_render_large_generated_master.png",
}


def normalized_canvas(source: Path) -> Image.Image:
    image = Image.open(source).convert("RGBA")
    alpha_box = image.getchannel("A").getbbox()
    if alpha_box is None:
        raise ValueError(f"{source} contains no visible pixels")

    artwork = image.crop(alpha_box)
    scale = min(MAX_ART_WIDTH / artwork.width, MAX_ART_HEIGHT / artwork.height)
    target_size = (
        max(1, round(artwork.width * scale)),
        max(1, round(artwork.height * scale)),
    )
    artwork = artwork.resize(target_size, Image.Resampling.LANCZOS)

    x = (CANVAS_SIZE - artwork.width) // 2
    y = ART_BOTTOM - artwork.height
    if x < 0 or y < 0:
        raise ValueError(f"{source} does not fit the normalized export canvas")

    canvas = Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (0, 0, 0, 0))
    canvas.alpha_composite(artwork, (x, y))
    return canvas


def export_render(name: str, source: Path) -> None:
    canvas = normalized_canvas(source)
    for size in (1024, 512, 256):
        output = canvas if size == CANVAS_SIZE else canvas.resize(
            (size, size), Image.Resampling.LANCZOS
        )
        destination = EXPORT_DIR / f"vehicle_render_{name}_{size}.png"
        output.save(destination, format="PNG", optimize=True)
        print(f"wrote {destination.relative_to(ASSET_ROOT.parent)}")


def main() -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    for name, source in RENDERS.items():
        if not source.is_file():
            raise FileNotFoundError(source)
        export_render(name, source)


if __name__ == "__main__":
    main()
