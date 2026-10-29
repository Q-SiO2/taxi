"""Both process roles select one complete private storage boundary and own closure."""

from base64 import urlsafe_b64encode
from dataclasses import replace
from os import environ

from fastapi.testclient import TestClient
import pytest

from taximobile_api.core.config import ConfigurationError, Settings
from taximobile_api.integrations.driver_documents import create_driver_document_store
from taximobile_api.integrations.s3_driver_documents import S3DriverDocumentStore
from taximobile_api.main import create_app
from taximobile_api.workers.application import BackgroundWorkerRuntime


def configured(monkeypatch):
    for name in tuple(environ):
        if name.startswith("TAXIMOBILE_DRIVER_DOCUMENT_"):
            monkeypatch.delenv(name)
    values = {
        "STORAGE_BACKEND": "s3", "S3_ENDPOINT": "https://s3.example.test",
        "S3_BUCKET": "document-fixture-bucket", "S3_ACCESS_KEY_ID": "document-fixture-access",
        "S3_SECRET_ACCESS_KEY": "document-fixture-secret-only", "CLAMAV_HOST": "clamav.internal",
        "ENCRYPTION_KEY": urlsafe_b64encode(bytes(range(32))).decode().rstrip("="),
    }
    for name, value in values.items():
        monkeypatch.setenv("TAXIMOBILE_DRIVER_DOCUMENT_" + name, value)
    return values


def test_s3_process_settings_are_complete_and_document_secrets_are_redacted(monkeypatch):
    values = configured(monkeypatch)
    settings = Settings.from_environment()
    assert settings.driver_document_storage_backend == "s3"
    assert settings.driver_document_storage_root is None
    assert settings.driver_document_s3.endpoint == values["S3_ENDPOINT"]
    assert settings.driver_document_encryption_key == bytes(range(32))
    assert values["S3_SECRET_ACCESS_KEY"] not in repr(settings)
    assert repr(bytes(range(32))) not in repr(settings)


@pytest.mark.parametrize("missing", ["S3_ENDPOINT", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY",
                                     "CLAMAV_HOST", "ENCRYPTION_KEY"])
def test_partial_s3_process_configuration_never_uses_ambient_credentials(monkeypatch, missing):
    values = configured(monkeypatch)
    monkeypatch.delenv("TAXIMOBILE_DRIVER_DOCUMENT_" + missing)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", values["S3_ACCESS_KEY_ID"])
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", values["S3_SECRET_ACCESS_KEY"])
    with pytest.raises(ConfigurationError) as error:
        Settings.from_environment()
    assert values["S3_SECRET_ACCESS_KEY"] not in str(error.value)


@pytest.mark.parametrize("backend", ["filesystem", "s3", "unexpected"])
def test_mixed_or_unknown_document_provider_fails_startup(monkeypatch, tmp_path, backend):
    configured(monkeypatch)
    monkeypatch.setenv("TAXIMOBILE_DRIVER_DOCUMENT_STORAGE_BACKEND", backend)
    monkeypatch.setenv("TAXIMOBILE_DRIVER_DOCUMENT_STORAGE_ROOT", str(tmp_path))
    with pytest.raises(ConfigurationError):
        Settings.from_environment()


def test_factory_rejects_s3_without_complete_security_settings():
    with pytest.raises(ValueError, match="configured together"):
        create_driver_document_store(backend="s3")
    with pytest.raises(ValueError, match="settings must be configured together"):
        create_driver_document_store(backend="s3", encryption_key=bytes(range(32)), clamav_host="clamav.internal")


@pytest.mark.asyncio
async def test_api_and_separate_worker_use_matching_s3_config_and_close_only_owned_client(monkeypatch):
    configured(monkeypatch)
    settings = replace(Settings.from_environment(), environment="test", process_role="api")
    clients, observed = [], []

    class Client:
        closed = False
        def close(self):
            self.closed = True

    def client(config):
        observed.append(config)
        result = Client()
        clients.append(result)
        return result
    monkeypatch.setattr("taximobile_api.integrations.s3_driver_documents.create_document_s3_client", client)
    app = create_app(settings=settings)
    assert isinstance(app.state.driver_document_store, S3DriverDocumentStore)
    # No SQL/S3 operations are needed to establish lifecycle ownership.
    with TestClient(app):
        assert not clients[0].closed
    assert clients[0].closed
    worker = BackgroundWorkerRuntime(object(), replace(settings, process_role="worker"), object(), None)
    assert len(clients) == 2 and observed == [settings.driver_document_s3] * 2
    await worker.stop()
    assert clients[1].closed

    shared = S3DriverDocumentStore(settings.driver_document_s3, bytes(range(32)), object())
    shared_worker = BackgroundWorkerRuntime(object(), settings, object(), None, shared)
    await shared_worker.stop()
    assert not clients[2].closed
    await shared.aclose()
    assert clients[2].closed
