"""Build a reference-complete Casablanca road extract from pinned real OSM data.

Preparation tool only: requires Pyosmium 4.3.1 in a separate tooling environment.
No application dependency. Output is immutable and carries ODbL provenance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import osmium


SOURCE_SHA256 = "78334b24b7e8913b0153ad866f4806279d41cd11a91f97f17e7102621cc6b1d9"
BBOX = (-7.75, 33.40, -7.40, 33.75)  # west, south, east, north; alpha area only


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def extract(source: Path, output: Path) -> dict:
    if output.exists() or output.with_suffix(".manifest.json").exists():
        raise ValueError("Extract and manifest must be new files; no overwrite.")
    if digest(source) != SOURCE_SHA256:
        raise ValueError("OSM input differs from the verified Geofabrik source.")
    selected_ways = set()
    restrictions = 0
    west, south, east, north = BBOX
    # Preserve full ways and all referenced nodes. Include touching turn
    # restrictions and their referenced roads; do not invent straight geometry.
    with osmium.BackReferenceWriter(output, osmium.io.File(str(source), "pbf"),
                                    remove_tags=False, relation_depth=3) as writer:
        for obj in osmium.FileProcessor(osmium.io.File(str(source), "pbf")).with_locations("flex_mem"):
            if not obj.is_way() or not ("highway" in obj.tags or obj.tags.get("route") == "ferry"):
                continue
            if any(node.location.valid() and west <= node.lon <= east and south <= node.lat <= north
                   for node in obj.nodes):
                selected_ways.add(obj.id)
                writer.add_way(obj)
        for obj in osmium.FileProcessor(osmium.io.File(str(source), "pbf"), osmium.osm.RELATION):
            if obj.tags.get("type") == "restriction" and any(
                    member.type == "w" and member.ref in selected_ways for member in obj.members):
                writer.add_relation(obj)
                restrictions += 1
    # A second actual parse proves every way node is present in the output.
    nodes = ways = relations = 0
    for obj in osmium.FileProcessor(output).with_locations("flex_mem"):
        if obj.is_node():
            nodes += 1
        elif obj.is_way():
            ways += 1
            if any(not node.location.valid() for node in obj.nodes):
                raise ValueError("Extract has incomplete way references; refuse graph import.")
        else:
            relations += 1
    result = {"source_url": "https://download.geofabrik.de/africa/morocco-260901.osm.pbf",
              "source_sha256": SOURCE_SHA256, "bbox_west_south_east_north": BBOX,
              "extract_sha256": digest(output), "extract_bytes": output.stat().st_size,
              "nodes": nodes, "ways": ways, "relations": relations,
              "selected_roads": len(selected_ways), "selected_turn_restrictions": restrictions,
              "license": "OpenStreetMap contributors, ODbL 1.0",
              "license_url": "https://www.openstreetmap.org/copyright",
              "tool": "Pyosmium 4.3.1", "scope": "Casablanca synthetic alpha, not national coverage"}
    output.with_suffix(".manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    print(json.dumps(extract(arguments.source, arguments.output), indent=2))
