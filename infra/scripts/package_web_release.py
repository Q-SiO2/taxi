"""Create a reviewable TaxiMobile web release directory.

Compose's compatibility distribution contains browser source maps and both the
JavaScript fallback and Wasm path. This packager rejects unexpected structure,
enforces reviewed raw-size ceilings, excludes source maps, and emits hashes plus
recommended cache/security headers for the hosting layer.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
from typing import Sequence


DEFAULT_INPUT = (
    Path(__file__).resolve().parents[2]
    / "TaxiMobile"
    / "webApp"
    / "build"
    / "dist"
    / "composeWebCompatibility"
    / "productionExecutable"
)
WEB_BUDGETS = {
    # Reviewed against the 2026-09-09 production fallback (6,104,171 bytes).
    # The 2.39% margin admits the measured candidate while still turning
    # material dependency or feature growth into a release gate.
    "originJsWebApp.js": 6_250_000,
    "originWasmWebApp.js": 700_000,
}
MAX_WASM_BYTES = 9_000_000
MAX_RELEASE_BYTES = 35_000_000
REQUIRED_FILES = (
    "index.html",
    "favicon.svg",
    "styles.css",
    "compatibility.js",
    "webApp.js",
    "originJsWebApp.js",
    "originWasmWebApp.js",
)
REMOTE_REFERENCE = re.compile(r"(?:src|href)\s*=\s*['\"]https?://", re.IGNORECASE)
INLINE_SCRIPT = re.compile(r"<script(?![^>]+\bsrc=)[^>]*>", re.IGNORECASE)
CLIENT_VERSION_META = re.compile(
    r'<meta\s+name=["\']taximobile-client-version["\']\s+content=["\']'
    r'(?P<value>(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)'
    r'(?:\.(?:0|[1-9][0-9]*))?)["\']\s*/?>',
    re.IGNORECASE,
)
CLIENT_BUILD_META = re.compile(
    r'<meta\s+name=["\']taximobile-client-build["\']\s+content=["\']'
    r'(?P<value>[1-9][0-9]{0,9})["\']\s*/?>',
    re.IGNORECASE,
)


class WebPackageError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_distribution(source: Path) -> dict[str, object]:
    if not source.is_dir():
        raise WebPackageError(f"Web distribution does not exist: {source}")
    for name in REQUIRED_FILES:
        path = source / name
        if not path.is_file():
            raise WebPackageError(f"Required web distribution file is missing: {name}")

    index = (source / "index.html").read_text(encoding="utf-8")
    if 'src="compatibility.js"' not in index and "src='compatibility.js'" not in index:
        raise WebPackageError("index.html must boot through compatibility.js")
    if 'src="webApp.js"' in index or "src='webApp.js'" in index:
        raise WebPackageError("index.html must not bypass the client compatibility preflight")
    if REMOTE_REFERENCE.search(index):
        raise WebPackageError("index.html must not load remote scripts or styles")
    if INLINE_SCRIPT.search(index):
        raise WebPackageError("index.html must not contain inline scripts")
    client_version = CLIENT_VERSION_META.search(index)
    client_build = CLIENT_BUILD_META.search(index)
    if client_version is None or client_build is None:
        raise WebPackageError(
            "index.html must contain numeric TaxiMobile client version and build metadata"
        )
    if int(client_build.group("value")) > 2_147_483_647:
        raise WebPackageError("TaxiMobile web client build exceeds the supported bound")

    compatibility_loader = (source / "compatibility.js").read_text(encoding="utf-8")
    required_loader_contract = (
        "/client-compatibility",
        '"X-TaxiMobile-Client"',
        '"X-TaxiMobile-Version"',
        '"X-TaxiMobile-Build"',
        'policy.status === "UPGRADE_REQUIRED"',
        'policy.status === "SUPPORTED"',
        'policy.status === "UPDATE_AVAILABLE"',
        "target.origin !== apiUrl.origin",
        "!target.pathname.startsWith(apiPathPrefix)",
        "window.fetch =",
        "return nativeFetch(input, init);",
        "return nativeFetch(input, { ...init, headers });",
        'script.src = "webApp.js"',
    )
    if any(fragment not in compatibility_loader for fragment in required_loader_contract):
        raise WebPackageError("compatibility.js does not implement the reviewed fail-closed boot contract")
    if "localStorage" in compatibility_loader or "sessionStorage" in compatibility_loader:
        raise WebPackageError("compatibility.js must not persist client or session state")

    for name, limit in WEB_BUDGETS.items():
        size = (source / name).stat().st_size
        if size > limit:
            raise WebPackageError(f"{name} is {size} bytes, exceeding the {limit}-byte budget")

    wasm_files = sorted(source.glob("*.wasm"))
    if len(wasm_files) < 2:
        raise WebPackageError("Compatibility distribution must contain application and Skiko Wasm")
    for path in wasm_files:
        if path.stat().st_size > MAX_WASM_BYTES:
            raise WebPackageError(
                f"{path.name} is {path.stat().st_size} bytes, exceeding the "
                f"{MAX_WASM_BYTES}-byte Wasm budget"
            )

    included = [path for path in source.rglob("*") if path.is_file() and path.suffix != ".map"]
    total = sum(path.stat().st_size for path in included)
    if total > MAX_RELEASE_BYTES:
        raise WebPackageError(
            f"Web release is {total} bytes excluding maps, exceeding the "
            f"{MAX_RELEASE_BYTES}-byte reviewed ceiling"
        )
    return {
        "source_file_count": len(included),
        "source_bytes_excluding_maps": total,
        "excluded_source_map_count": len(list(source.rglob("*.map"))),
        "client_version": client_version.group("value"),
        "client_build": client_build.group("value"),
    }


def package_distribution(source: Path, output: Path) -> dict[str, object]:
    summary = validate_distribution(source)
    if output.exists():
        raise WebPackageError(f"Output path already exists: {output}")
    output.mkdir(parents=True)

    records: list[dict[str, object]] = []
    for path in sorted(source.rglob("*")):
        if not path.is_file() or path.suffix == ".map":
            continue
        relative = path.relative_to(source)
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        records.append(
            {
                "path": relative.as_posix(),
                "bytes": destination.stat().st_size,
                "sha256": _sha256(destination),
            }
        )

    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "deployment_accepted": False,
        "summary": summary,
        "budgets": {
            "javascript": WEB_BUDGETS,
            "maximum_wasm_bytes": MAX_WASM_BYTES,
            "maximum_release_bytes_excluding_maps": MAX_RELEASE_BYTES,
        },
        "hosting_requirements": {
            "tls_only": True,
            "source_maps_public": False,
            "template_requires_exact_api_and_websocket_hosts": True,
            "content_security_policy": (
                "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                "font-src 'self'; connect-src 'self' https: wss:; "
                "object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
            ),
            "cache_policy": {
                "index.html": "no-cache",
                "compatibility.js": "no-cache",
                "webApp.js": "no-cache",
                "originJsWebApp.js": "no-cache",
                "originWasmWebApp.js": "no-cache",
                "hashed_assets": "public, max-age=31536000, immutable",
            },
        },
        "files": records,
    }
    (output / "release-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        manifest = package_distribution(arguments.input, arguments.output)
    except WebPackageError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(
        f"Packaged {len(manifest['files'])} web files at {arguments.output}; "
        f"excluded {manifest['summary']['excluded_source_map_count']} source maps."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
