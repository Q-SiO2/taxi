"""Carry the already-scanned CI image to GHCR without rebuilding it.

The GitHub run/artifact service is the trust boundary, not this unsigned JSON.
Hashes reject corruption and source/run mixups before Docker loads an archive.
Publication is not deployment, mobile signing, independent review or acceptance.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from generate_release_evidence import EvidenceError, generate_evidence, sha256_file


BUNDLE_FILES = {"image.tar", "image.json", "image.spdx.json", "source-evidence.json"}
IMAGE = "taximobile-api:ci"
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
COMMIT = re.compile(r"[0-9a-f]{40}")


class RegistryEvidenceError(RuntimeError):
    pass


def docker(*arguments: str) -> str:
    try:
        result = subprocess.run(["docker", *arguments], capture_output=True,
                                text=True, timeout=600, check=False)
    except (OSError, subprocess.SubprocessError):
        raise RegistryEvidenceError("Docker operation could not complete.") from None
    if result.returncode:
        # Docker errors can contain credentials or operational connection values.
        raise RegistryEvidenceError("Docker operation failed; inspect protected runner diagnostics.")
    return result.stdout.strip()


def _pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise RegistryEvidenceError("Duplicate evidence JSON key.")
        result[key] = value
    return result


def read_json(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 16 * 1024 * 1024:
        raise RegistryEvidenceError("Missing, linked or oversized evidence JSON.")
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs)
    except (UnicodeError, ValueError):
        raise RegistryEvidenceError("Invalid evidence JSON.") from None
    if not isinstance(value, dict):
        raise RegistryEvidenceError("Evidence JSON must be an object.")
    return value


def write_json(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as output:
        output.write(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")


def context() -> tuple[str, str, str]:
    values = tuple(os.environ.get(key, "") for key in
                   ("GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"))
    if (os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("GITHUB_EVENT_NAME") != "push"
            or os.environ.get("GITHUB_REF") != "refs/heads/main"
            or not COMMIT.fullmatch(values[0])
            or any(not re.fullmatch(r"[1-9][0-9]*", item) for item in values[1:])):
        raise RegistryEvidenceError("Registry operations require an identified main push run.")
    return values


def inspect(image: str) -> dict:
    try:
        value = json.loads(docker("image", "inspect", "--format", "{{json .}}", image))
    except ValueError:
        raise RegistryEvidenceError("Invalid Docker image identity.") from None
    if (not isinstance(value, dict) or not isinstance(value.get("Id"), str)
            or not DIGEST.fullmatch(value["Id"])
            or value.get("Os") != "linux" or value.get("Architecture") != "amd64"):
        raise RegistryEvidenceError("Expected an identified Linux amd64 image.")
    return value


def prepare(bundle: Path, sbom: Path) -> None:
    sha, run_id, attempt = context()
    sbom_document = read_json(sbom)
    if sbom_document.get("spdxVersion") != "SPDX-2.3":
        raise RegistryEvidenceError("Expected the scanned image's SPDX 2.3 SBOM.")
    identity = inspect(IMAGE)
    # Exclusive creation avoids replacing another run's partial/complete packet.
    bundle.mkdir(parents=True, exist_ok=False)
    docker("image", "save", "--output", str(bundle / "image.tar"), IMAGE)
    shutil.copyfile(sbom, bundle / "image.spdx.json")
    write_json(bundle / "image.json", {"schema_version": 1,
               "image_id": identity["Id"], "os": "linux", "architecture": "amd64"})
    evidence = generate_evidence(label=f"registry-{run_id}-{attempt}",
                artifacts=[bundle / name for name in sorted(BUNDLE_FILES - {"source-evidence.json"})])
    write_json(bundle / "source-evidence.json", evidence)
    verify(bundle, sha, run_id, attempt)


def verify(bundle: Path, sha: str, run_id: str, attempt: str, *, loaded: bool = False) -> dict:
    if (not COMMIT.fullmatch(sha) or any(not re.fullmatch(r"[1-9][0-9]*", x)
                                       for x in (run_id, attempt))):
        raise RegistryEvidenceError("Invalid expected source/run identity.")
    if (bundle.is_symlink() or not bundle.is_dir()
            or {item.name for item in bundle.iterdir()} != BUNDLE_FILES
            or any(item.is_symlink() or not item.is_file() for item in bundle.iterdir())):
        raise RegistryEvidenceError("Image packet must contain exactly the four regular files.")
    evidence = read_json(bundle / "source-evidence.json")
    source, ci = evidence.get("source"), evidence.get("ci")
    if not isinstance(source, dict) or not isinstance(ci, dict):
        raise RegistryEvidenceError("Missing source/run binding.")
    if (evidence.get("schema_version") != 1
            or evidence.get("evidence_level") != "SOURCE_CANDIDATE"
            or evidence.get("deployment_accepted") is not False
            or source.get("clean") is not True or source.get("commit") != sha
            or source.get("tracked_change_count") != 0 or source.get("untracked_file_count") != 0
            or not isinstance(source.get("tree"), str) or not COMMIT.fullmatch(source["tree"])
            or ci.get("provider") != "github-actions" or ci.get("reported_sha") != sha
            or ci.get("ref") != "refs/heads/main"
            or ci.get("run_id") != run_id or ci.get("run_attempt") != attempt):
        raise RegistryEvidenceError("Image packet is not this clean main source/run candidate.")
    artifacts = evidence.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 3:
        raise RegistryEvidenceError("Expected three bound image artifacts.")
    names = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict) or not isinstance(artifact.get("path"), str):
            raise RegistryEvidenceError("Invalid image artifact binding.")
        # Only select a fixed bundle basename. Never open a path supplied by JSON.
        name = artifact["path"].replace("\\", "/").rsplit("/", 1)[-1]
        if name not in BUNDLE_FILES - {"source-evidence.json"} or name in names:
            raise RegistryEvidenceError("Unexpected or duplicate image artifact binding.")
        names.add(name)
        path = bundle / name
        if (type(artifact.get("bytes")) is not int or path.stat().st_size != artifact["bytes"]
                or path.stat().st_size == 0 or sha256_file(path) != artifact.get("sha256")):
            raise RegistryEvidenceError("Image artifact hash/size does not match its binding.")
    identity = read_json(bundle / "image.json")
    if (identity.get("schema_version") != 1 or not isinstance(identity.get("image_id"), str)
            or not DIGEST.fullmatch(identity["image_id"])
            or identity.get("os") != "linux" or identity.get("architecture") != "amd64"
            or read_json(bundle / "image.spdx.json").get("spdxVersion") != "SPDX-2.3"):
        raise RegistryEvidenceError("Invalid image descriptor or SBOM.")
    if loaded and inspect(IMAGE)["Id"] != identity["image_id"]:
        raise RegistryEvidenceError("Loaded Docker image differs from the scanned image.")
    return identity


def record(bundle: Path, repository: str, output: Path) -> None:
    sha, run_id, attempt = context()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9_.-]*", repository):
        raise RegistryEvidenceError("Invalid lowercase GitHub repository identity.")
    if repository != os.environ.get("GITHUB_REPOSITORY", "").lower():
        raise RegistryEvidenceError("Registry repository differs from this workflow repository.")
    identity = verify(bundle, sha, run_id, attempt, loaded=True)
    image_repo = f"ghcr.io/{repository}-api"
    tag = f"{image_repo}:sha-{sha}-{run_id}-{attempt}"
    pushed = inspect(tag)
    digests = pushed.get("RepoDigests")
    matches = [x for x in digests if isinstance(x, str) and
               re.fullmatch(re.escape(image_repo) + r"@sha256:[0-9a-f]{64}", x)] if isinstance(digests, list) else []
    if pushed["Id"] != identity["image_id"] or len(matches) != 1:
        raise RegistryEvidenceError("Pushed registry digest is absent, ambiguous or a different image.")
    # Resolve the immutable remote artifact and compare its config identity too.
    docker("image", "pull", matches[0])
    if inspect(matches[0])["Id"] != identity["image_id"]:
        raise RegistryEvidenceError("Registry pull differs from the scanned image.")
    write_json(output, {"schema_version": 1, "evidence_level": "REGISTRY_IMAGE_PROVENANCE",
        "deployment_accepted": False, "phase_accepted": False,
        "acceptance_note": "Published image identity only; not release, security or real-user acceptance.",
        "source_commit": sha, "source_evidence_sha256": sha256_file(bundle / "source-evidence.json"),
        "image_archive_sha256": sha256_file(bundle / "image.tar"),
        "sbom_sha256": sha256_file(bundle / "image.spdx.json"),
        "image_id": identity["image_id"], "platform": "linux/amd64",
        "registry_reference": matches[0], "tag": tag, "run_id": run_id, "run_attempt": attempt})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "verify", "record"))
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--sbom", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--repository")
    parser.add_argument("--loaded", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            if args.sbom is None:
                parser.error("prepare requires --sbom")
            prepare(args.bundle, args.sbom)
        elif args.command == "verify":
            verify(args.bundle, *context(), loaded=args.loaded)
        else:
            if args.repository is None or args.output is None:
                parser.error("record requires --repository and --output")
            record(args.bundle, args.repository, args.output)
    except RegistryEvidenceError as error:
        print(f"Registry evidence failed: {error} No accepted release record was produced.", file=sys.stderr)
        return 1
    except (EvidenceError, OSError):
        print("Registry evidence failed: cannot create exclusive clean-source evidence. "
              "Check Git status, output-path permissions and protected diagnostics.", file=sys.stderr)
        return 1
    print("Registry image evidence step passed; deployment acceptance remains false.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
