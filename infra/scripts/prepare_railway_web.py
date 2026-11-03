"""Package the existing Compose compatibility release for bounded alpha hosting."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from package_web_release import DEFAULT_INPUT, WebPackageError, package_distribution


def prepare(source: Path, output: Path) -> dict:
    if output.exists():
        raise WebPackageError("Railway web upload must be a new directory.")
    manifest = package_distribution(source, output / "public")
    template = Path(__file__).resolve().parents[1] / "deploy" / "railway-web"
    aliases = manifest["hosting_requirements"]["asset_aliases"]
    directives = []
    for alias, destination in aliases.items():
        if alias != "skiko.wasm" or not re.fullmatch(r"[a-f0-9]{20}\.wasm", destination):
            raise WebPackageError("Unexpected binary alias; nginx configuration was not generated.")
        directives.append(f"location = /{alias} {{ rewrite ^ /{destination} last; }}")
    config = (template / "nginx.conf").read_text()
    marker = "# WASM_ALIASES: filled from the validated release manifest at packaging."
    if config.count(marker) != 1:
        raise WebPackageError("Railway web alias marker is missing or ambiguous.")
    (output / "nginx.conf").write_text(config.replace(marker, "\n        ".join(directives)), newline="\n")
    (output / "Dockerfile").write_text((template / "Dockerfile").read_text(), newline="\n")
    (output / "start.sh").write_text((template / "start.sh").read_text(), newline="\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.input, args.output)
    print(f"Prepared {len(result['files'])} source-map-free web assets; "
          f"{result['summary']['source_bytes_excluding_maps']} bytes; "
          f"{len(result['hosting_requirements']['asset_aliases'])} verified binary alias.")
