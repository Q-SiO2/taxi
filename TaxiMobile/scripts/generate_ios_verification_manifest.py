"""Validate and inventory TaxiMobile's two unsigned iOS simulator products.

This manifest is deliberately evidence for CI verification products only. It
does not claim signing, App Store eligibility, provider configuration, physical-
device behavior, or deployment acceptance. A separate clean-source evidence
record binds the resulting manifest to a commit and migration head.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import plistlib
import re
from typing import Sequence


VERSION = re.compile(
    r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
    r"(?:\.(?:0|[1-9][0-9]*))?"
)
PRODUCTS = (
    ("passenger", "TaxiMobile Passenger.app", "ma.taximobile.passenger"),
    ("driver", "TaxiMobile Driver.app", "ma.taximobile.driver"),
)


class IosVerificationError(RuntimeError):
    """Raised when a simulator product cannot support the claimed evidence."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bundle_record(
    products_dir: Path,
    *,
    role: str,
    app_name: str,
    expected_bundle_id: str,
    expected_version_name: str,
    expected_version_code: str,
) -> dict[str, object]:
    app = products_dir / app_name
    if not app.is_dir():
        raise IosVerificationError(f"Missing {role} simulator product: {app_name}")
    info_path = app / "Info.plist"
    try:
        with info_path.open("rb") as source:
            info = plistlib.load(source)
    except (OSError, plistlib.InvalidFileException) as error:
        raise IosVerificationError(f"Invalid {role} Info.plist: {error}") from error

    expected = {
        "CFBundleIdentifier": expected_bundle_id,
        "CFBundleShortVersionString": expected_version_name,
        "CFBundleVersion": expected_version_code,
    }
    for key, value in expected.items():
        if str(info.get(key, "")) != value:
            raise IosVerificationError(
                f"Unexpected {key} for {role}: expected {value!r}."
            )
    executable_name = str(info.get("CFBundleExecutable", "")).strip()
    if not executable_name or "/" in executable_name or "\\" in executable_name:
        raise IosVerificationError(f"Invalid CFBundleExecutable for {role}.")
    executable = app / executable_name
    if not executable.is_file() or executable.stat().st_size == 0:
        raise IosVerificationError(f"Missing or empty {role} executable.")

    root = app.resolve()
    files: list[tuple[str, Path]] = []
    for path in app.rglob("*"):
        if not path.is_file():
            continue
        try:
            path.resolve().relative_to(root)
        except ValueError as error:
            raise IosVerificationError(
                f"{role} product contains a file link outside its bundle: {path}"
            ) from error
        files.append((path.relative_to(app).as_posix(), path))
    files.sort(key=lambda item: item[0])
    if not files:
        raise IosVerificationError(f"The {role} simulator product is empty.")

    bundle_digest = hashlib.sha256()
    total_bytes = 0
    for relative, path in files:
        size = path.stat().st_size
        total_bytes += size
        bundle_digest.update(relative.encode("utf-8"))
        bundle_digest.update(b"\0")
        bundle_digest.update(str(size).encode("ascii"))
        bundle_digest.update(b"\0")
        bundle_digest.update(bytes.fromhex(_sha256(path)))

    return {
        "role": role,
        "product": app_name,
        "bundle_id": expected_bundle_id,
        "version_code": expected_version_code,
        "version_name": expected_version_name,
        "executable": executable_name,
        "file_count": len(files),
        "bytes": total_bytes,
        "bundle_sha256": bundle_digest.hexdigest(),
        "executable_sha256": _sha256(executable),
        "info_plist_sha256": _sha256(info_path),
        "contains_code_signature": (app / "_CodeSignature" / "CodeResources").is_file(),
    }


def generate_manifest(
    products_dir: Path,
    *,
    expected_version_name: str,
    expected_version_code: int,
) -> dict[str, object]:
    if not products_dir.is_dir():
        raise IosVerificationError(f"iOS products directory does not exist: {products_dir}")
    if VERSION.fullmatch(expected_version_name) is None:
        raise IosVerificationError("Expected version name must have three or four numeric components.")
    if not 1 <= expected_version_code <= 2_147_483_647:
        raise IosVerificationError("Expected version code must be a positive 32-bit integer.")
    version_code = str(expected_version_code)
    artifacts = [
        _bundle_record(
            products_dir,
            role=role,
            app_name=app_name,
            expected_bundle_id=bundle_id,
            expected_version_name=expected_version_name,
            expected_version_code=version_code,
        )
        for role, app_name, bundle_id in PRODUCTS
    ]
    if artifacts[0]["bundle_sha256"] == artifacts[1]["bundle_sha256"]:
        raise IosVerificationError("Passenger and driver products must be distinct bundles.")
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_level": "IOS_SIMULATOR_VERIFICATION_ARTIFACTS",
        "deployment_accepted": False,
        "distribution_eligible": False,
        "expected_version_code": expected_version_code,
        "expected_version_name": expected_version_name,
        "limitations": [
            "SIGNING_NOT_ACCEPTED",
            "PUSH_CRASH_PROVIDER_NOT_ACCEPTED",
            "PHYSICAL_DEVICE_NOT_ACCEPTED",
            "APP_STORE_NOT_ACCEPTED",
        ],
        "artifacts": artifacts,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--products-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-version-name", required=True)
    parser.add_argument("--expected-version-code", required=True, type=int)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        manifest = generate_manifest(
            arguments.products_dir,
            expected_version_name=arguments.expected_version_name,
            expected_version_code=arguments.expected_version_code,
        )
        if arguments.output.exists():
            raise IosVerificationError(
                f"Refusing to overwrite existing iOS verification manifest: {arguments.output}"
            )
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    except (OSError, IosVerificationError) as error:
        print(f"iOS verification manifest failed: {error}")
        return 1
    print(
        f"Wrote {len(manifest['artifacts'])} non-distributable iOS simulator "
        f"artifact records to {arguments.output}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
