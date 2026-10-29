from dataclasses import FrozenInstanceError, replace

import pytest

from taximobile_api.integrations.document_storage_config import (
    DocumentStorageConfigurationError,
    S3DocumentStorageSettings,
)


def valid():
    return S3DocumentStorageSettings("https://s3.example.test", "document-fixture-bucket",
                                   "document-fixture-access", "document-fixture-secret-only")


def test_s3_configuration_is_explicit_immutable_and_redacts_credentials():
    settings = valid()
    settings.validate()
    assert settings.access_key_id not in repr(settings)
    assert settings.secret_access_key not in repr(settings)
    with pytest.raises(FrozenInstanceError):
        settings.bucket = "changed-fixture-bucket"
    with pytest.raises(DocumentStorageConfigurationError, match="explicit valid bucket credentials"):
        S3DocumentStorageSettings.from_environment({
            "TAXIMOBILE_DRIVER_DOCUMENT_S3_ENDPOINT": settings.endpoint,
            "TAXIMOBILE_DRIVER_DOCUMENT_S3_BUCKET": settings.bucket,
            "AWS_ACCESS_KEY_ID": settings.access_key_id,
            "AWS_SECRET_ACCESS_KEY": settings.secret_access_key,
        })


@pytest.mark.parametrize("endpoint", [
    "http://s3.example.test", "https://username:private-input@s3.example.test",
    "https://s3.example.test/private-path", "https://s3.example.test?signature=private-input",
    "https://s3.example.test#private-input", "https://s3.example.test:444", "https://127.0.0.1",
    "https://localhost", "https://s3.localhost", "https://s3.local", "https://[::1]",
    "https://s3.example.test\n", "https://s3.example.test.", "https://s3.example.test:bad",
    "https://*.example.test", "https://s3..example.test",
])
def test_s3_endpoint_must_be_a_verified_reviewable_https_origin(endpoint):
    with pytest.raises(DocumentStorageConfigurationError) as error:
        replace(valid(), endpoint=endpoint).validate()
    assert endpoint not in str(error.value) and "private-input" not in str(error.value)


@pytest.mark.parametrize("field,value", [
    ("bucket", "ab"), ("bucket", "../outside"), ("bucket", "Not-A-DNS-Bucket"),
    ("bucket", "127.0.0.1"), ("bucket", "invalid..bucket"),
    ("access_key_id", ""), ("secret_access_key", ""), ("secret_access_key", "space containing fixture"),
    ("region", ""), ("region", "region/private-input"), ("addressing_style", "auto"),
    ("timeout_seconds", 0), ("timeout_seconds", 31), ("timeout_seconds", float("inf")),
    ("timeout_seconds", float("nan")), ("max_in_flight", 0), ("max_in_flight", 9),
    ("max_in_flight", True), ("max_in_flight", 1.5),
])
def test_s3_storage_limits_and_credentials_fail_closed(field, value):
    settings = replace(valid(), **{field: value})
    with pytest.raises(DocumentStorageConfigurationError) as error:
        settings.validate()
    assert "private-input" not in str(error.value)
    assert valid().secret_access_key not in str(error.value)


def test_complete_environment_maps_provider_defaults_and_explicit_legacy_addressing():
    settings = valid()
    environment = {"TAXIMOBILE_DRIVER_DOCUMENT_S3_" + key: value for key, value in {
        "ENDPOINT": settings.endpoint, "BUCKET": settings.bucket,
        "ACCESS_KEY_ID": settings.access_key_id, "SECRET_ACCESS_KEY": settings.secret_access_key,
        "ADDRESSING_STYLE": "path", "MAX_IN_FLIGHT": "3", "TIMEOUT_SECONDS": "2.5",
    }.items()}
    actual = S3DocumentStorageSettings.from_environment(environment)
    assert actual.region == "auto" and actual.addressing_style == "path"
    assert actual.max_in_flight == 3 and actual.timeout_seconds == 2.5
    with pytest.raises(DocumentStorageConfigurationError, match="valid numbers"):
        S3DocumentStorageSettings.from_environment(environment | {"TAXIMOBILE_DRIVER_DOCUMENT_S3_TIMEOUT_SECONDS": "private-input"})
