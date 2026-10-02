"""Actual mounted contracts; source evidence only, no lifespan or DB requests."""

import hashlib
import json
from pathlib import Path
import socket
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "infra" / "scripts"))
from generate_openapi_evidence import (
    OpenApiEvidenceError, _load_documents_in_worker, contract_bundle,
    load_documents, write_bundle,
)


def test_actual_contract_export_is_stable_and_ignores_operational_environment(monkeypatch, tmp_path):
    first = load_documents()
    # Even import-time configuration must not use these hostile parent values.
    for key, value in {
        "TAXIMOBILE_ENV": "production", "TAXIMOBILE_PROCESS_ROLE": "worker",
        "TAXIMOBILE_DATABASE_URL": "invalid", "TAXIMOBILE_JWT_SECRET": "do-not-export",
        "TAXIMOBILE_LOG_FILE": str(tmp_path / "must-not-be-created.log"),
        "TAXIMOBILE_API_PREFIX": "/unreviewed", "TAXIMOBILE_LEGACY_ADMIN_API_ENABLED": "true",
        "PYTHONPATH": str(tmp_path / "untrusted-source"),
    }.items():
        monkeypatch.setenv(key, value)
    second = load_documents()
    assert first == second
    assert not (tmp_path / "must-not-be-created.log").exists()
    manifest, files = contract_bundle(first)
    assert manifest["deployment_accepted"] is False
    assert manifest["authorization_accepted"] is False
    write_bundle(tmp_path / "evidence", manifest, files)
    for record in manifest["contracts"]:
        encoded = (tmp_path / "evidence" / record["path"]).read_bytes()
        assert hashlib.sha256(encoded).hexdigest() == record["sha256"]
        assert json.loads(encoded) == first[record["profile"]]
        assert b"do-not-export" not in encoded
    launch = first["launch-api"]
    compatibility = first["local-compatibility-api"]
    assert not any(path.startswith("/api/v1/admin/") for path in launch["paths"])
    assert any(path.startswith("/api/v1/admin/") for path in compatibility["paths"])
    assert "/api/v1/auth/login" in launch["paths"]
    assert launch["components"]["schemas"]


def test_actual_factory_schema_generation_does_not_connect_to_network(monkeypatch):
    import os
    for key in tuple(os.environ):
        if key.upper().startswith("TAXIMOBILE_"):
            monkeypatch.delenv(key)
    monkeypatch.setenv("TAXIMOBILE_ENV", "test")
    monkeypatch.setenv("TAXIMOBILE_PROCESS_ROLE", "api")

    def deny_connection(*args, **kwargs):
        raise AssertionError("Source export must not connect to a database or provider")

    monkeypatch.setattr(socket.socket, "connect", deny_connection)
    monkeypatch.setattr(socket.socket, "connect_ex", deny_connection)
    manifest, _ = contract_bundle(_load_documents_in_worker(Path(__file__).resolve().parents[3]))
    assert len(manifest["contracts"]) == 2


def test_direct_worker_refuses_operational_configuration(monkeypatch):
    monkeypatch.setenv("TAXIMOBILE_JWT_SECRET", "do-not-use")
    with pytest.raises(OpenApiEvidenceError, match="isolated test environment"):
        _load_documents_in_worker(Path(__file__).resolve().parents[3])
