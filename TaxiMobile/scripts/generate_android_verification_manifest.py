"""Verify both actual APK identities with SDK aapt2, not just AGP sidecar JSON.

Signing, provider configuration, device behavior and distribution remain
unaccepted. CI's separate source record binds the resulting full manifest.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*))?")
PRODUCTS = (("passenger", "passengerRelease", "ma.taximobile.passenger"),
            ("driver", "driverRelease", "ma.taximobile.driver"))
BUILD_TOOLS_VERSION = "36.1.0"


class AndroidVerificationError(RuntimeError):
    pass


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AndroidVerificationError("Duplicate release metadata key.")
        result[key] = value
    return result


def metadata(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise AndroidVerificationError("Missing, linked or oversized release metadata.")
    try:
        result = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs)
    except (UnicodeError, ValueError):
        raise AndroidVerificationError("Invalid release metadata JSON.") from None
    if not isinstance(result, dict):
        raise AndroidVerificationError("Release metadata must be an object.")
    return result


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_badging(text: str) -> dict:
    packages = [line for line in text.splitlines() if line.startswith("package:")]
    if len(packages) != 1:
        raise AndroidVerificationError("APK must have exactly one readable packaged identity.")
    if re.search(r"(?<!\S)split=", packages[0]):
        raise AndroidVerificationError("Expected a standalone role APK, not an Android split.")
    result = {}
    for output_key, key in (("application_id", "name"), ("version_code", "versionCode"),
                            ("version_name", "versionName")):
        values = re.findall(rf"(?<!\S){key}='([^']*)'(?=\s|$)", packages[0])
        if len(values) != 1:
            raise AndroidVerificationError("APK packaged identity is missing or ambiguous.")
        result[output_key] = values[0]
    if not re.fullmatch(r"[1-9][0-9]{0,9}", result["version_code"]):
        raise AndroidVerificationError("APK has an invalid packaged version code.")
    result["version_code"] = int(result["version_code"])
    if not VERSION.fullmatch(result["version_name"]):
        raise AndroidVerificationError("APK has an invalid packaged numeric release version.")
    return result


def packaged_identity(apk: Path, aapt2: Path) -> dict:
    try:
        result = subprocess.run([str(aapt2), "dump", "badging", str(apk)],
            capture_output=True, text=True, timeout=45, check=False)
    except (OSError, subprocess.SubprocessError):
        raise AndroidVerificationError("SDK aapt2 could not inspect the APK; check the installed tool.") from None
    if result.returncode:
        raise AndroidVerificationError("SDK aapt2 rejected the APK's packaged manifest.")
    return parse_badging(result.stdout)


def find_aapt2(project: Path) -> Path:
    sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if not sdk:
        local = project / "local.properties"
        if local.is_file():
            # Only the SDK property, never Firebase/signing configuration.
            for line in local.read_text(encoding="utf-8").splitlines():
                if line.startswith("sdk.dir="):
                    sdk = line.split("=", 1)[1].replace("\\:", ":").replace("\\\\", "\\")
                    break
    if not sdk:
        raise AndroidVerificationError("Set ANDROID_HOME or supply --aapt2 for SDK build-tools 36.1.0.")
    tool = Path(sdk) / "build-tools" / BUILD_TOOLS_VERSION / ("aapt2.exe" if os.name == "nt" else "aapt2")
    if not tool.is_file():
        raise AndroidVerificationError("Install SDK build-tools 36.1.0 or supply --aapt2 explicitly.")
    return tool


def generate_manifest(project: Path, *, version_code: int, version_name: str, aapt2: Path) -> dict:
    if type(version_code) is not int or not 1 <= version_code <= 2_147_483_647:
        raise AndroidVerificationError("Expected version code must be a positive bounded integer.")
    if not isinstance(version_name, str) or not VERSION.fullmatch(version_name):
        raise AndroidVerificationError("Expected version name must be a three/four-component numeric release.")
    root = project.resolve(strict=True)
    artifacts, seen_files, seen_hashes = [], set(), set()
    for role, variant, application_id in PRODUCTS:
        directory = root / "androidApp" / "build" / "outputs" / "apk" / role / "release"
        if any(parent.is_symlink() or (hasattr(parent, "is_junction") and parent.is_junction())
               or not parent.resolve().is_relative_to(root)
               for parent in (directory, *directory.parents)
               if parent != root and root in parent.parents):
            raise AndroidVerificationError("Release output directories must not be linked.")
        document = metadata(directory / "output-metadata.json")
        artifact_type = document.get("artifactType")
        if (document.get("applicationId") != application_id or document.get("variantName") != variant
                or not isinstance(artifact_type, dict) or artifact_type.get("type") != "APK"):
            raise AndroidVerificationError(f"Unexpected {role} metadata package, variant or artifact type.")
        elements = document.get("elements")
        if not isinstance(elements, list) or len(elements) != 1 or not isinstance(elements[0], dict):
            raise AndroidVerificationError(f"Expected one {role} release APK.")
        element = elements[0]
        if (type(element.get("versionCode")) is not int or element["versionCode"] != version_code
                or element.get("versionName") != version_name or element.get("filters") != []
                or element.get("type") != "SINGLE"):
            raise AndroidVerificationError(f"Unexpected {role} version metadata or split APK filters.")
        name = element.get("outputFile")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.apk", name):
            raise AndroidVerificationError(f"The {role} APK reference must be one safe filename.")
        apk = directory / name
        if apk.is_symlink() or not apk.is_file() or apk.resolve().parent != directory.resolve():
            raise AndroidVerificationError(f"Missing, linked or escaped {role} APK.")
        if apk.stat().st_size < 1024 * 1024:
            raise AndroidVerificationError(f"The {role} APK is unexpectedly small.")
        before = sha256(apk)
        identity = packaged_identity(apk, aapt2)
        expected = {"application_id": application_id, "version_code": version_code, "version_name": version_name}
        if identity != expected:
            raise AndroidVerificationError(f"The actual {role} APK package/version disagrees with the candidate.")
        after = sha256(apk)
        if before != after:
            raise AndroidVerificationError(f"The {role} APK changed during inspection.")
        if apk.resolve() in seen_files or after in seen_hashes:
            raise AndroidVerificationError("Passenger and driver must have distinct APK files and bytes.")
        seen_files.add(apk.resolve())
        seen_hashes.add(after)
        artifacts.append({"role": role, "variant": variant, **identity,
            "path": apk.relative_to(root).as_posix(), "bytes": apk.stat().st_size, "sha256": after,
            "identity_verification": "AAPT2_PACKAGED_MANIFEST"})
    return {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_level": "ANDROID_VERIFICATION_ARTIFACTS", "deployment_accepted": False,
        "distribution_eligible": False, "expected_version_code": version_code,
        "expected_version_name": version_name, "artifacts": artifacts,
        "limitations": ["SIGNING_NOT_ACCEPTED", "PUSH_CRASH_PROVIDER_NOT_ACCEPTED", "PHYSICAL_DEVICE_NOT_ACCEPTED"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--expected-version-code", type=int, default=1)
    parser.add_argument("--expected-version-name", default="1.0.0")
    parser.add_argument("--aapt2", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.output is not None and args.output.exists():
            raise AndroidVerificationError("Refusing to overwrite existing Android evidence.")
        tool = args.aapt2 if args.aapt2 is not None else find_aapt2(args.project_dir)
        manifest = generate_manifest(args.project_dir, version_code=args.expected_version_code,
                                     version_name=args.expected_version_name, aapt2=tool)
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8", newline="\n") as output:
                output.write(json.dumps(manifest, sort_keys=True, indent=2, allow_nan=False) + "\n")
    except AndroidVerificationError as error:
        print(f"Android artifact verification failed: {error}", file=sys.stderr)
        return 1
    except OSError:
        print("Android artifact verification failed: check installed SDK, APK inputs and exclusive output permissions.", file=sys.stderr)
        return 1
    print("Verified actual passenger/driver APK identities and hashes; signing and deployment remain unaccepted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
