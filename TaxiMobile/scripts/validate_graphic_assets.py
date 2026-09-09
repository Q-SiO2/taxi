#!/usr/bin/env python3
"""Validate TaxiMobile's editable graphic assets and Compose resource mirrors."""

from __future__ import annotations

import hashlib
import json
import re
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = WORKSPACE_ROOT / "assets" / "manifest.json"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
SAFE_NAME = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
HEX_COLOR = re.compile(r"#[0-9A-Fa-f]{6}\b")
SIZED_PNG = re.compile(r"_(128|256|512|1024)\.png$")
FORBIDDEN_STEMS = ("final2", "copy", "fixed_final", "newcar", "taxi3")
REQUIRED_PRODUCTION_IDS = {
    "A01",
    "A02",
    "A03",
    "A04",
    "B01",
    "B02",
    "B04",
    "B06",
    "C01-C07",
    "D01-D02",
    "E01-E02",
    "E04",
    "P01",
}


def relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_png_header(path: Path) -> tuple[int, int, int, int, int]:
    with path.open("rb") as source:
        signature = source.read(8)
        if signature != PNG_SIGNATURE:
            raise ValueError("invalid PNG signature")
        length_data = source.read(4)
        chunk_type = source.read(4)
        if len(length_data) != 4 or chunk_type != b"IHDR":
            raise ValueError("missing PNG IHDR")
        length = struct.unpack(">I", length_data)[0]
        payload = source.read(length)
        if length != 13 or len(payload) != 13:
            raise ValueError("invalid PNG IHDR length")
        width, height, bit_depth, color_type, _, _, interlace = struct.unpack(
            ">IIBBBBB", payload
        )
        return width, height, bit_depth, color_type, interlace


def validate_svg(path: Path, allowed_palette: set[str], errors: list[str], root: Path) -> None:
    label = relative(path, root)
    try:
        document = ET.parse(path)
    except ET.ParseError as error:
        errors.append(f"{label}: invalid SVG XML: {error}")
        return

    svg = document.getroot()
    if not svg.tag.endswith("svg"):
        errors.append(f"{label}: root element is not svg")
    if not svg.attrib.get("viewBox"):
        errors.append(f"{label}: missing viewBox")

    for node in svg.iter():
        local_name = node.tag.rsplit("}", 1)[-1]
        if local_name == "text" and not path.stem.startswith("brand_wordmark_"):
            errors.append(f"{label}: visible text must not be baked into artwork")
        for key, value in node.attrib.items():
            if key.rsplit("}", 1)[-1] == "href" and not value.startswith("#"):
                errors.append(f"{label}: external SVG reference is not allowed: {value}")

    contents = path.read_text(encoding="utf-8")
    colors = {match.upper() for match in HEX_COLOR.findall(contents)}
    unexpected = sorted(colors - allowed_palette)
    if unexpected:
        errors.append(f"{label}: colors outside the approved palette: {', '.join(unexpected)}")


def validate_png(path: Path, errors: list[str], root: Path) -> None:
    label = relative(path, root)
    try:
        width, height, bit_depth, color_type, interlace = read_png_header(path)
    except (OSError, ValueError, struct.error) as error:
        errors.append(f"{label}: invalid PNG: {error}")
        return

    if bit_depth != 8:
        errors.append(f"{label}: expected 8-bit channels, found {bit_depth}")
    if color_type not in (4, 6):
        errors.append(f"{label}: expected a real alpha channel, PNG color type is {color_type}")
    if interlace not in (0, 1):
        errors.append(f"{label}: invalid interlace method {interlace}")

    size_match = SIZED_PNG.search(path.name)
    if size_match:
        expected = int(size_match.group(1))
        if (width, height) != (expected, expected):
            errors.append(
                f"{label}: filename declares {expected}px but image is {width}x{height}"
            )


def validate_assets(root: Path = WORKSPACE_ROOT) -> list[str]:
    errors: list[str] = []
    manifest_path = root / "assets" / "manifest.json"
    try:
        manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"assets/manifest.json: cannot read manifest: {error}"]

    if manifest.get("schema_version") != 1:
        errors.append("assets/manifest.json: unsupported schema_version")

    palette = {str(color).upper() for color in manifest.get("palette", [])}
    required_palette = {"#FFFFFF", "#0B1F3A", "#163A63", "#D6A800", "#F3D76A", "#071426"}
    missing_palette = sorted(required_palette - palette)
    if missing_palette:
        errors.append(f"assets/manifest.json: missing brand colors: {', '.join(missing_palette)}")

    marker_contract = manifest.get("marker_contract", {})
    if marker_contract.get("forward_axis") != "up_at_zero_degrees":
        errors.append("assets/manifest.json: vehicle forward axis must be up_at_zero_degrees")
    if marker_contract.get("vehicle_anchor") != [0.5, 0.5]:
        errors.append("assets/manifest.json: vehicle marker anchor must be [0.5, 0.5]")
    if marker_contract.get("pin_anchor") != [0.5, 1.0]:
        errors.append("assets/manifest.json: pin anchor must be [0.5, 1.0]")

    assets = manifest.get("assets")
    if not isinstance(assets, list):
        return errors + ["assets/manifest.json: assets must be a list"]

    ids = [item.get("id") for item in assets if isinstance(item, dict)]
    duplicate_ids = sorted({item for item in ids if item and ids.count(item) > 1})
    if duplicate_ids:
        errors.append(f"assets/manifest.json: duplicate IDs: {', '.join(duplicate_ids)}")

    ready_ids = {
        str(item.get("id"))
        for item in assets
        if isinstance(item, dict) and item.get("status") == "ready"
    }
    missing_required = sorted(REQUIRED_PRODUCTION_IDS - ready_ids)
    if missing_required:
        errors.append(
            "assets/manifest.json: high-priority assets not ready: "
            + ", ".join(missing_required)
        )

    runtime_root_value = manifest.get("runtime_root")
    runtime_root = root / str(runtime_root_value)
    listed_sources: set[Path] = set()

    for item in assets:
        if not isinstance(item, dict):
            errors.append("assets/manifest.json: every asset entry must be an object")
            continue
        asset_id = str(item.get("id", "<missing>"))
        status = item.get("status")
        sources = item.get("sources", [])
        exports = item.get("exports", [])

        if status == "ready" and not sources:
            errors.append(f"{asset_id}: ready asset has no source")

        resolved_sources: list[Path] = []
        for value in sources:
            source = root / str(value)
            listed_sources.add(source.resolve())
            resolved_sources.append(source)
            if not source.is_file():
                errors.append(f"{asset_id}: missing source {relative(source, root)}")
                continue
            if not SAFE_NAME.fullmatch(source.stem):
                errors.append(f"{asset_id}: source name is not snake_case: {source.name}")
            if any(fragment in source.stem.lower() for fragment in FORBIDDEN_STEMS):
                errors.append(f"{asset_id}: source uses a forbidden provisional name: {source.name}")
            if source.suffix.lower() == ".svg":
                validate_svg(source, palette, errors, root)
            elif source.suffix.lower() == ".png":
                validate_png(source, errors, root)
            else:
                errors.append(f"{asset_id}: unsupported source type: {source.name}")

        for value in exports:
            export = root / str(value)
            if not export.is_file():
                errors.append(f"{asset_id}: missing export {relative(export, root)}")
            elif export.suffix.lower() == ".png":
                validate_png(export, errors, root)

        if item.get("runtime") == "mirrored_by_basename":
            for source in resolved_sources:
                destination = runtime_root / source.name
                if not destination.is_file():
                    errors.append(f"{asset_id}: missing runtime mirror {relative(destination, root)}")
                elif source.is_file() and sha256(source) != sha256(destination):
                    errors.append(f"{asset_id}: runtime mirror differs from {relative(source, root)}")

        for mapping in item.get("runtime_files", []):
            source = root / str(mapping.get("source", ""))
            destination = root / str(mapping.get("destination", ""))
            if not source.is_file():
                errors.append(f"{asset_id}: missing runtime source {relative(source, root)}")
            if not destination.is_file():
                errors.append(f"{asset_id}: missing runtime destination {relative(destination, root)}")
            if source.is_file() and destination.is_file() and sha256(source) != sha256(destination):
                errors.append(f"{asset_id}: runtime file differs from {relative(source, root)}")

        generation_record = item.get("generation_record")
        if generation_record and not (root / str(generation_record)).is_file():
            errors.append(f"{asset_id}: missing generation record {generation_record}")

    source_svgs = {
        path.resolve()
        for path in (root / "assets").rglob("*.svg")
        if path.is_file()
    }
    unlisted = sorted(relative(path, root) for path in source_svgs - listed_sources)
    if unlisted:
        errors.append("assets/manifest.json: unlisted SVG sources: " + ", ".join(unlisted))

    return errors


def main() -> int:
    errors = validate_assets()
    if errors:
        print("Graphic asset validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Graphic asset validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
