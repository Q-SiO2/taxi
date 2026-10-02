"""Inspect signatures without signing APKs or accepting release promotion.

Expected certificate fingerprints are public operator input, not approval proof.
Use the SDK verifier's default manifest-declared platform range; never narrow it
to conceal unsupported devices. Java invokes the jar directly on every host,
avoiding platform shell/batch interpretation of APK paths.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess


class AndroidSignatureError(RuntimeError):
    pass


def certificate_sha256(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(
        r"(?:[0-9a-fA-F]{64}|(?:[0-9a-fA-F]{2}:){31}[0-9a-fA-F]{2})", value
    ):
        raise AndroidSignatureError("Expected signer must be a complete SHA-256 certificate fingerprint.")
    return value.replace(":", "").lower()


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_verified_signature(text: str, expected: str) -> dict:
    expected = certificate_sha256(expected)
    if len(text.encode("utf-8")) > 64 * 1024:
        raise AndroidSignatureError("SDK signature report exceeds the bounded inspection size.")
    lines = text.splitlines()
    signer_counts = [line for line in lines if line.startswith("Number of signers:")]
    identities = [line for line in lines if re.match(r"Signer #\d+ certificate SHA-256 digest:", line)]
    schemes = [line for line in lines if line.startswith("Verified using v2 scheme")]
    if (lines.count("Verifies") != 1 or signer_counts != ["Number of signers: 1"]
            or len(identities) != 1
            or schemes != ["Verified using v2 scheme (APK Signature Scheme v2): true"]):
        raise AndroidSignatureError("SDK must verify one signer with APK Signature Scheme v2.")
    match = re.fullmatch(r"Signer #1 certificate SHA-256 digest: ([0-9a-fA-F]{64})", identities[0])
    if match is None or match[1].lower() != expected:
        raise AndroidSignatureError("APK signer does not match the expected certificate fingerprint.")
    # Certificate subjects, PEM, public keys and tool diagnostics are not retained.
    return {"signature_verification": "SDK_APKSIGNER", "certificate_sha256": expected,
            "signature_scheme_v2_verified": True, "signer_count": 1,
            "platform_range": "APK_MANIFEST_DEFAULT", "signer_approval_accepted": False}


def _java() -> str:
    home = os.environ.get("JAVA_HOME")
    if home:
        executable = Path(home) / "bin" / ("java.exe" if os.name == "nt" else "java")
        if not executable.is_file():
            raise AndroidSignatureError("JAVA_HOME must identify a usable Java installation.")
        return str(executable)
    executable = shutil.which("java")
    if not executable:
        raise AndroidSignatureError("Install Java or configure JAVA_HOME for SDK signature verification.")
    return executable


def verify_apk_signature(apk: Path, verifier_jar: Path, expected: str, apk_sha256: str) -> dict:
    expected = certificate_sha256(expected)
    if (not verifier_jar.is_file() or not 1 <= verifier_jar.stat().st_size <= 16 * 1024 * 1024
            or not apk.is_file() or not 1 <= apk.stat().st_size <= 512 * 1024 * 1024
            or not isinstance(apk_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", apk_sha256)):
        raise AndroidSignatureError("Missing or invalid SDK signature-verification inputs.")
    if _hash(apk) != apk_sha256:
        raise AndroidSignatureError("APK changed between packaged identity and signature verification.")
    tool_hash = _hash(verifier_jar)
    tool_bytes = verifier_jar.stat().st_size
    try:
        result = subprocess.run(
            [_java(), "-jar", str(verifier_jar), "verify", "--verbose", "--print-certs",
             "-Werr", "--in", str(apk)],
            capture_output=True, text=True, encoding="utf-8", timeout=45, check=False,
        )
    except (OSError, subprocess.SubprocessError, UnicodeError):
        raise AndroidSignatureError("SDK signature verification could not complete; check Java, SDK and APK inputs.") from None
    if result.returncode:
        raise AndroidSignatureError("SDK rejected the APK signature or reported signing warnings.")
    evidence = parse_verified_signature(result.stdout, expected)
    if _hash(apk) != apk_sha256 or _hash(verifier_jar) != tool_hash:
        raise AndroidSignatureError("APK or SDK verifier changed during signature inspection.")
    return {**evidence, "verifier_artifact_sha256": tool_hash, "verifier_artifact_bytes": tool_bytes}
