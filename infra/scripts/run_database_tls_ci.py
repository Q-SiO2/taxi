"""Run the full backend suite with real TLS fixtures in disposable CI services.

Only GitHub Actions' loopback taximobile_ci/PostGIS service is eligible. This
does not operate on a deployment, install a provider, or grant T3/T5 acceptance.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
import time
import xml.etree.ElementTree as ET

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from sqlalchemy.engine import make_url


ROOT = Path(__file__).resolve().parents[2]
TLS_FIELDS = ("ssl", "ssl_cert_file", "ssl_key_file", "ssl_min_protocol_version")


def validate_target(environment: dict[str, str], container: str):
    if environment.get("GITHUB_ACTIONS") != "true" or environment.get("TAXIMOBILE_ENV") != "test":
        raise ValueError("Database TLS CI runner requires a disposable GitHub test job")
    if not re.fullmatch(r"[a-f0-9]{12,64}", container):
        raise ValueError("An explicit disposable service container ID is required")
    url = make_url(environment.get("TAXIMOBILE_DATABASE_URL", ""))
    if (url.drivername != "postgresql+asyncpg" or url.host not in {"localhost", "127.0.0.1"}
            or url.port != 5432 or url.database != "taximobile_ci" or not url.username
            or not re.fullmatch(r"[a-z][a-z0-9_]*", url.username)):
        raise ValueError("Database TLS CI target must be the loopback taximobile_ci service")
    return url


def literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def authority(name: str):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=5))
            .not_valid_after(now+timedelta(days=2)).add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
            .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(key.public_key()), critical=False).sign(key, hashes.SHA256()))
    return key, cert


def run(container: str, arguments: list[str], payload: bytes | None = None) -> bytes:
    result = subprocess.run(["docker", "exec", "-i", container, *arguments], input=payload, capture_output=True, timeout=30)
    if result.returncode:
        detail = result.stderr.decode(errors="replace").strip()[-800:]
        detail = re.sub(r"postgres(?:ql)?(?:\+asyncpg)?://\S+", "[database URL redacted]", detail)
        raise RuntimeError("Disposable TLS fixture " + arguments[0] + " failed: " + detail)
    return result.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", required=True)
    parser.add_argument("--junit", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    report = {"recorded_utc": datetime.now(timezone.utc).isoformat(), "passed": False,
              "scope": "Disposable CI PostgreSQL identity/transport probes inside the full backend suite; no hosted or phase acceptance",
              "hosted_accepted": False}
    original = None
    directory = "/tmp/taximobile-tls-ci-" + os.urandom(8).hex()
    prepared = False
    status = 1
    try:
        report["phase"] = "TARGET_GUARD"
        url = validate_target(dict(os.environ), args.container)
        inspection = subprocess.run(["docker", "inspect", args.container], capture_output=True, timeout=15, check=True)
        instance = json.loads(inspection.stdout)[0]
        if instance["Config"]["Image"] != "postgis/postgis:16-3.4" or not instance["State"]["Running"]:
            raise ValueError("Unexpected disposable database service image/state")
        psql = ["psql", "-X", "-A", "-t", "-U", url.username, "-d", url.database, "-v", "ON_ERROR_STOP=1"]
        report["phase"] = "ORIGINAL_TLS_BASELINE"
        def sql(statement: str) -> str:
            return run(args.container, psql, statement.encode()).decode().strip()
        original = json.loads(sql("SELECT json_object_agg(name,setting) FROM pg_settings WHERE name IN ('ssl','ssl_cert_file','ssl_key_file','ssl_min_protocol_version');"))
        if set(original) != set(TLS_FIELDS) or original["ssl"] != "off":
            raise ValueError("TLS fixture requires the disposable service's original non-TLS baseline")
        if sql("SELECT context FROM pg_settings WHERE name='ssl';") != "sighup":
            raise ValueError("Disposable service cannot reload TLS without restart")
        key, ca = authority("TaxiMobile disposable CI CA")
        report["phase"] = "GENERATE_DISPOSABLE_PKI"
        _, wrong = authority("TaxiMobile unrelated CI CA")
        leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        now = datetime.now(timezone.utc)
        leaf = (x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")]))
                .issuer_name(ca.subject).public_key(leaf_key.public_key()).serial_number(x509.random_serial_number())
                .not_valid_before(now-timedelta(minutes=5)).not_valid_after(now+timedelta(days=1))
                .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
                .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
                .add_extension(x509.KeyUsage(True, False, True, False, False, False, False, False, False), critical=True)
                .add_extension(x509.SubjectKeyIdentifier.from_public_key(leaf_key.public_key()), critical=False)
                .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(key.public_key()), critical=False).sign(key, hashes.SHA256()))
        uid = int(run(args.container, ["id", "-u", "postgres"]).strip())
        gid = int(run(args.container, ["id", "-g", "postgres"]).strip())
        run(args.container, ["mkdir", "-m", "700", directory])
        prepared = True
        run(args.container, ["chown", "postgres:postgres", directory])
        files = {"server.crt": leaf.public_bytes(serialization.Encoding.PEM),
                 "server.key": leaf_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption())}
        payload = io.BytesIO()
        with tarfile.open(fileobj=payload, mode="w") as archive:
            for name, data in files.items():
                entry = tarfile.TarInfo(name); entry.size = len(data); entry.mode = 0o600; entry.uid = uid; entry.gid = gid
                archive.addfile(entry, io.BytesIO(data))
        run(args.container, ["tar", "-xf", "-", "-C", directory], payload.getvalue())
        report["phase"] = "ENABLE_DISPOSABLE_SERVER_TLS"
        settings = {"ssl_cert_file": directory+"/server.crt", "ssl_key_file": directory+"/server.key", "ssl_min_protocol_version": "TLSv1.2", "ssl": "on"}
        sql("\n".join(f"ALTER SYSTEM SET {name} = {literal(value)};" for name,value in settings.items())+"\nSELECT pg_reload_conf();")
        deadline = time.monotonic()+10
        while sql("SHOW ssl;") != "on":
            if time.monotonic() >= deadline: raise RuntimeError("Disposable TLS reload did not become active")
            time.sleep(.1)
        with tempfile.TemporaryDirectory(prefix="taximobile-ci-ca-") as temporary:
            ca_path = Path(temporary)/"ca.pem"; wrong_path = Path(temporary)/"wrong-ca.pem"
            ca_path.write_bytes(ca.public_bytes(serialization.Encoding.PEM)); wrong_path.write_bytes(wrong.public_bytes(serialization.Encoding.PEM))
            environment = dict(os.environ)
            verified = url.set(host="localhost").render_as_string(hide_password=False)
            plain = url.set(host="localhost", port=5433, database="postgres").render_as_string(hide_password=False)
            environment.update(TAXIMOBILE_RUN_TLS_INTEGRATION="1", TAXIMOBILE_TLS_TEST_DATABASE_URL=verified,
                TAXIMOBILE_TLS_TEST_MIGRATION_URL=verified, TAXIMOBILE_TLS_TEST_PLAIN_URL=plain,
                TAXIMOBILE_TLS_TEST_CA_FILE=str(ca_path), TAXIMOBILE_TLS_TEST_WRONG_CA_FILE=str(wrong_path))
            # Do not change the ordinary test policy or cloning fixture globally.
            report["phase"] = "FULL_BACKEND_SUITE_WITH_TLS_PROBES"
            completed = subprocess.run([sys.executable, "-m", "pytest", "--junitxml="+str(args.junit)],
                                       cwd=ROOT/"backend", env=environment, timeout=1800)
            status = completed.returncode
        suites = list(ET.parse(args.junit).getroot().iter("testsuite"))
        counts = {name: sum(int(s.attrib.get(name,0)) for s in suites) for name in ("tests","failures","errors","skipped")}
        cases = [case for suite in suites for case in suite.findall("testcase") if "test_postgres_tls_transport" in case.attrib.get("classname", "")]
        tls_passed = len(cases) == 8 and all(case.find("failure") is None and case.find("error") is None and case.find("skipped") is None for case in cases)
        report.update(full_suite=counts, tls_cases=len(cases), tls_passed=tls_passed,
                      junit_sha256=hashlib.sha256(args.junit.read_bytes()).hexdigest(),
                      certificate_sha256=leaf.fingerprint(hashes.SHA256()).hex(),
                      passed=status==0 and tls_passed and not any(counts[name] for name in ("failures","errors","skipped")))
        if not report["passed"]:status=1
        report["phase"] = "SUITE_PASSED" if report["passed"] else "SUITE_FAILED"
    except Exception as error:
        report["error_type"] = type(error).__name__
        if type(error) in {ValueError, RuntimeError}:
            report["diagnostic"] = str(error)
        print("Database TLS CI rehearsal failed ("+type(error).__name__+"); inspect its bounded report.", file=sys.stderr)
        status=1
    finally:
        try:
            if original is not None and prepared:
                restore="\n".join(f"ALTER SYSTEM SET {name} = {literal(original[name])};" for name in TLS_FIELDS)+"\nSELECT pg_reload_conf();"
                run(args.container, psql, restore.encode())
                deadline=time.monotonic()+10
                while run(args.container, psql, b"SHOW ssl;").decode().strip() != original["ssl"]:
                    if time.monotonic()>=deadline:raise RuntimeError("TLS fixture baseline restoration timed out")
                    time.sleep(.1)
                run(args.container, ["rm", "-f", directory+"/server.crt", directory+"/server.key"])
                run(args.container, ["rmdir", directory])
                report["baseline_restored"]=True
        except Exception as error:
            report.update(cleanup_error_type=type(error).__name__,passed=False);status=1
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
