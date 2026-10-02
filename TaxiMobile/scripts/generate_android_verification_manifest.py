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
import zipfile
from validate_android_release_log import AndroidReleaseLogError, validate_release_log
from verify_android_apk_signatures import AndroidSignatureError, certificate_sha256, verify_apk_signature

VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*))?")
PRODUCTS = (("passenger", "passengerRelease", "ma.taximobile.passenger"),
            ("driver", "driverRelease", "ma.taximobile.driver"))
BUILD_TOOLS_VERSION = "36.1.0"
R8_VERSION = "9.1.56"


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
    if any(line.strip().startswith("application-debuggable") for line in text.splitlines()):
        raise AndroidVerificationError("Expected a non-debuggable release APK.")
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


def confined_file(root: Path, path: Path) -> None:
    """Generated compiler evidence must not escape through links or junctions."""
    if not path.is_file() or not path.resolve().is_relative_to(root):
        raise AndroidVerificationError("Missing or escaped Android compiler evidence.")
    for item in (path, *path.parents):
        if item == root:
            break
        if item.is_symlink() or (hasattr(item, "is_junction") and item.is_junction()):
            raise AndroidVerificationError("Android compiler evidence must not be linked.")


def shrinker_record(root: Path) -> dict:
    path = root / "build/reports/android-shrinker/resolved-shrinker.json"
    confined_file(root, path)
    before = sha256(path)
    document = metadata(path)
    if (document.get("schema_version") != 1
            or document.get("evidence_level") != "ANDROID_RESOLVED_SHRINKER"
            or document.get("deployment_accepted") is not False
            or document.get("distribution_eligible") is not False
            or document.get("r8_version") != R8_VERSION
            or document.get("resolution_scope") != "AGP_PLUGIN_CLASSLOADER"
            or not isinstance(document.get("kotlin_version"), str)
            or not re.fullmatch(r"2\.4\.[0-9]+", document["kotlin_version"])
            or type(document.get("compiler_artifact_bytes")) is not int
            or document["compiler_artifact_bytes"] <= 0
            or not isinstance(document.get("compiler_artifact_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", document["compiler_artifact_sha256"])):
        raise AndroidVerificationError("Android plugin shrinker report does not match the reviewed Kotlin/R8 contract.")
    if sha256(path) != before:
        raise AndroidVerificationError("Android plugin shrinker report changed during inspection.")
    return {**document, "report_sha256": before}


def mapping_record(root: Path, variant: str) -> dict:
    path = root / "androidApp/build/outputs/mapping" / variant / "mapping.txt"
    confined_file(root, path)
    before = sha256(path)
    header = []
    # Read only a bounded compiler header; never export class/member mappings.
    with path.open(encoding="utf-8") as source:
        for _ in range(16):
            line = source.readline(4097)
            if len(line) > 4096:
                raise AndroidVerificationError("R8 mapping compiler header is oversized.")
            if not line.startswith("#"):
                break
            header.append(line.rstrip("\r\n"))
    compilers = [line[len("# compiler: "):] for line in header if line.startswith("# compiler: ")]
    versions = [line[len("# compiler_version: "):] for line in header if line.startswith("# compiler_version: ")]
    map_ids = [line[len("# pg_map_id: "):] for line in header if line.startswith("# pg_map_id: ")]
    if (compilers != ["R8"] or versions != [R8_VERSION] or len(map_ids) != 1
            or not re.fullmatch(r"[0-9a-f]{1,64}", map_ids[0])):
        raise AndroidVerificationError("Role mapping was not produced by the reviewed R8 compiler.")
    if sha256(path) != before:
        raise AndroidVerificationError("R8 mapping changed during inspection.")
    return {"r8_version": R8_VERSION, "mapping_bytes": path.stat().st_size,
            "mapping_sha256": before, "pg_map_id": map_ids[0]}


def verify_dex_compiler(apk: Path, mapping: dict) -> None:
    """Cross-check embedded R8 markers: a fresh sidecar cannot bless an old APK.

This is build provenance under the trusted CI producer, not signature checking
or a general DEX verifier. Never export bytecode/marker text to the report.
"""
    if apk.stat().st_size > 512 * 1024 * 1024:
        raise AndroidVerificationError("APK exceeds the bounded compiler-inspection size.")
    try:
        with zipfile.ZipFile(apk) as archive:
            all_entries = archive.infolist()
            entries = [item for item in all_entries
                       if re.fullmatch(r"classes(?:[2-9]|[1-9][0-9]+)?\.dex", item.filename)]
            names = [item.filename for item in entries]
            if (len(all_entries) > 10_000 or not 1 <= len(entries) <= 32 or "classes.dex" not in names
                    or len(names) != len(set(names)) or sum(item.file_size for item in entries) > 256 * 1024 * 1024
                    or any(item.flag_bits & 1 or not 8 <= item.file_size <= 64 * 1024 * 1024 for item in entries)):
                raise AndroidVerificationError("Invalid, duplicate or oversized APK DEX entries.")
            markers = []
            for item in entries:
                payload = archive.read(item)
                if not re.match(rb"dex\n0[0-9]{2}\x00", payload):
                    raise AndroidVerificationError("APK has an unreadable DEX header.")
                for match in re.finditer(rb"~~R8(\{[^\x00]{1,4096}\})\x00", payload):
                    markers.append(json.loads(match[1], object_pairs_hook=_pairs))
    except AndroidVerificationError:
        raise
    except (zipfile.BadZipFile, RuntimeError, UnicodeError, ValueError):
        raise AndroidVerificationError("APK compiler marker inspection failed.") from None
    if not markers or any(not isinstance(marker, dict)
            or marker.get("version") != R8_VERSION or marker.get("backend") != "dex"
            or marker.get("compilation-mode") != "release" or marker.get("r8-mode") != "full"
            or marker.get("pg-map-id") != mapping["pg_map_id"] for marker in markers):
        raise AndroidVerificationError("APK embedded compiler identity does not match the reviewed R8 mapping.")


def generate_manifest(project: Path, *, version_code: int, version_name: str, aapt2: Path) -> dict:
    if type(version_code) is not int or not 1 <= version_code <= 2_147_483_647:
        raise AndroidVerificationError("Expected version code must be a positive bounded integer.")
    if not isinstance(version_name, str) or not VERSION.fullmatch(version_name):
        raise AndroidVerificationError("Expected version name must be a three/four-component numeric release.")
    root = project.resolve(strict=True)
    shrinker = shrinker_record(root)
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
        mapping = mapping_record(root, variant)
        verify_dex_compiler(apk, mapping)
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
            "identity_verification": "AAPT2_PACKAGED_MANIFEST", **mapping,
            "compiler_verification": "R8_EMBEDDED_DEX_MARKER_AND_MAPPING"})
    return {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_level": "ANDROID_VERIFICATION_ARTIFACTS", "deployment_accepted": False,
        "distribution_eligible": False, "expected_version_code": version_code,
        "expected_version_name": version_name, "artifacts": artifacts, "resolved_shrinker": shrinker,
        "limitations": ["SIGNING_NOT_ACCEPTED", "PUSH_CRASH_PROVIDER_NOT_ACCEPTED", "PHYSICAL_DEVICE_NOT_ACCEPTED"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--expected-version-code", type=int, default=1)
    parser.add_argument("--expected-version-name", default="1.0.0")
    parser.add_argument("--aapt2", type=Path)
    parser.add_argument("--build-log", type=Path)
    parser.add_argument("--expected-passenger-certificate-sha256")
    parser.add_argument("--expected-driver-certificate-sha256")
    parser.add_argument("--apksigner-jar", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.output is not None and args.output.exists():
            raise AndroidVerificationError("Refusing to overwrite existing Android evidence.")
        fingerprints = {"passenger": args.expected_passenger_certificate_sha256,
                        "driver": args.expected_driver_certificate_sha256}
        check_signatures = any(value is not None for value in fingerprints.values()) or args.apksigner_jar is not None
        if check_signatures and any(value is None for value in fingerprints.values()):
            raise AndroidSignatureError("Signature inspection requires expected certificate fingerprints for both roles.")
        if check_signatures:
            fingerprints = {role: certificate_sha256(value) for role, value in fingerprints.items()}
        tool = args.aapt2 if args.aapt2 is not None else find_aapt2(args.project_dir)
        manifest = generate_manifest(args.project_dir, version_code=args.expected_version_code,
                                     version_name=args.expected_version_name, aapt2=tool)
        if check_signatures:
            verifier = args.apksigner_jar if args.apksigner_jar is not None else tool.parent / "lib/apksigner.jar"
            for artifact in manifest["artifacts"]:
                artifact.update(verify_apk_signature(args.project_dir / artifact["path"], verifier,
                                                    fingerprints[artifact["role"]], artifact["sha256"]))
            manifest["signature_inspection"] = "BOTH_ROLES_CRYPTOGRAPHICALLY_VERIFIED_EXPECTED_SIGNERS"
            manifest["signer_approval_accepted"] = False
            # Neither an operator-supplied digest nor SDK success proves approval.
            manifest["limitations"][0] = "SIGNER_APPROVAL_NOT_ACCEPTED"
        if args.build_log is not None:
            manifest["release_build_log"] = validate_release_log(args.build_log, R8_VERSION)
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8", newline="\n") as output:
                output.write(json.dumps(manifest, sort_keys=True, indent=2, allow_nan=False) + "\n")
    except (AndroidVerificationError, AndroidReleaseLogError, AndroidSignatureError) as error:
        print(f"Android artifact verification failed: {error}", file=sys.stderr)
        return 1
    except OSError:
        print("Android artifact verification failed: check installed SDK, APK inputs and exclusive output permissions.", file=sys.stderr)
        return 1
    print("Verified actual passenger/driver APK identities and hashes; signing and deployment remain unaccepted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
