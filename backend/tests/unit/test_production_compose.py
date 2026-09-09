from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest
import yaml


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
VALIDATOR_PATH = WORKSPACE_ROOT / "infra" / "scripts" / "validate_production_compose.py"
MANIFEST_PATH = WORKSPACE_ROOT / "infra" / "deploy" / "compose.production.yaml"

spec = importlib.util.spec_from_file_location("validate_production_compose", VALIDATOR_PATH)
assert spec is not None and spec.loader is not None
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def production_manifest() -> dict:
    document = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def test_committed_production_manifest_preserves_security_and_readiness_contract() -> None:
    validator.validate_manifest(MANIFEST_PATH)


@pytest.mark.parametrize("service", ["migrate", "api", "worker"])
def test_application_roles_cannot_regain_root_identity(service: str) -> None:
    document = deepcopy(production_manifest())
    document["services"][service]["user"] = "0:0"

    with pytest.raises(ValueError, match="fixed application UID/GID 2000"):
        validator.validate_document(document)


def test_api_allows_only_the_fixed_internal_metrics_alias_before_public_hosts() -> None:
    allowed_hosts = production_manifest()["services"]["api"]["environment"][
        "TAXIMOBILE_ALLOWED_HOSTS"
    ]

    assert allowed_hosts.startswith("taximobile-api-metrics,")
    assert "${TAXIMOBILE_ALLOWED_HOSTS:?" in allowed_hosts


def test_migration_timeouts_are_configurable_only_on_migration_service() -> None:
    services = production_manifest()["services"]
    for name, default in (("TAXIMOBILE_MIGRATION_LOCK_TIMEOUT_SECONDS", 5),
                          ("TAXIMOBILE_MIGRATION_STATEMENT_TIMEOUT_SECONDS", 300)):
        assert services["migrate"]["environment"][name] == f"${{{name}-{default}}}"
        assert name not in services["api"]["environment"]
        assert name not in services["worker"]["environment"]


def test_database_pool_bounds_are_explicit_for_api_and_worker_only() -> None:
    services = production_manifest()["services"]
    expected = {
        "TAXIMOBILE_DATABASE_POOL_SIZE": "${TAXIMOBILE_DATABASE_POOL_SIZE:-5}",
        "TAXIMOBILE_DATABASE_POOL_MAX_OVERFLOW": (
            "${TAXIMOBILE_DATABASE_POOL_MAX_OVERFLOW:-10}"
        ),
        "TAXIMOBILE_DATABASE_POOL_TIMEOUT_SECONDS": (
            "${TAXIMOBILE_DATABASE_POOL_TIMEOUT_SECONDS:-30}"
        ),
    }
    for name, value in expected.items():
        assert services["api"]["environment"][name] == value
        assert services["worker"]["environment"][name] == value
        assert name not in services["migrate"]["environment"]

    for service_name in ("api", "worker"):
        document = deepcopy(production_manifest())
        del document["services"][service_name]["environment"][
            "TAXIMOBILE_DATABASE_POOL_SIZE"
        ]
        with pytest.raises(ValueError, match="bounded database-pool settings"):
            validator.validate_document(document)


@pytest.mark.parametrize("service", ["api", "worker"])
def test_liveness_probe_cannot_replace_container_readiness(service: str) -> None:
    document = deepcopy(production_manifest())
    command = document["services"][service]["healthcheck"]["test"]
    command[3] = command[3].replace("/ready", "/health")

    with pytest.raises(ValueError, match="must probe"):
        validator.validate_document(document)


def test_worker_cannot_receive_api_signing_authority() -> None:
    document = deepcopy(production_manifest())
    document["services"]["worker"]["environment"]["TAXIMOBILE_JWT_SECRET"] = "forbidden"

    with pytest.raises(ValueError, match="must not receive"):
        validator.validate_document(document)


def test_client_compatibility_policy_is_complete_enforced_and_api_only() -> None:
    manifest = production_manifest()
    api_environment = manifest["services"]["api"]["environment"]
    worker_environment = manifest["services"]["worker"]["environment"]
    assert api_environment["TAXIMOBILE_CLIENT_COMPATIBILITY_ENFORCED"] == "true"
    assert "TAXIMOBILE_CLIENT_POLICY_REVISION" in api_environment
    for surface in (
        "ANDROID_PASSENGER",
        "ANDROID_DRIVER",
        "IOS_PASSENGER",
        "IOS_DRIVER",
        "WEB_APPLICANT",
        "WEB_OPERATIONS",
    ):
        for kind in ("MINIMUM", "RECOMMENDED"):
            key = f"TAXIMOBILE_CLIENT_{surface}_{kind}_VERSION"
            assert key in api_environment
            assert key not in worker_environment

    document = deepcopy(manifest)
    document["services"]["api"]["environment"].pop(
        "TAXIMOBILE_CLIENT_IOS_DRIVER_MINIMUM_VERSION"
    )
    with pytest.raises(ValueError, match="complete client compatibility policy"):
        validator.validate_document(document)

    document = deepcopy(manifest)
    document["services"]["api"]["environment"][
        "TAXIMOBILE_CLIENT_COMPATIBILITY_ENFORCED"
    ] = "false"
    with pytest.raises(ValueError, match="force client compatibility enforcement"):
        validator.validate_document(document)

    document = deepcopy(manifest)
    document["services"]["worker"]["environment"][
        "TAXIMOBILE_CLIENT_WEB_OPERATIONS_MINIMUM_VERSION"
    ] = "1.0.0"
    with pytest.raises(ValueError, match="must not receive client compatibility"):
        validator.validate_document(document)


def test_geocoding_configuration_is_complete_and_api_only() -> None:
    document = deepcopy(production_manifest())
    del document["services"]["api"]["environment"]["TAXIMOBILE_GEOCODING_BASE_URL"]
    with pytest.raises(ValueError, match="complete fail-closed geocoding"):
        validator.validate_document(document)

    document = deepcopy(production_manifest())
    document["services"]["worker"]["environment"][
        "TAXIMOBILE_GEOCODING_PROVIDER"
    ] = "disabled"
    with pytest.raises(ValueError, match="must not receive geocoding"):
        validator.validate_document(document)


def test_legacy_admin_api_is_forced_off_and_api_only() -> None:
    document = deepcopy(production_manifest())
    document["services"]["api"]["environment"][
        "TAXIMOBILE_LEGACY_ADMIN_API_ENABLED"
    ] = "true"
    with pytest.raises(ValueError, match="legacy admin API off"):
        validator.validate_document(document)

    document = deepcopy(production_manifest())
    document["services"]["worker"]["environment"][
        "TAXIMOBILE_LEGACY_ADMIN_API_ENABLED"
    ] = "false"
    with pytest.raises(ValueError, match="must not receive legacy admin"):
        validator.validate_document(document)


def test_operations_mfa_encryption_key_is_required_and_api_only() -> None:
    document = deepcopy(production_manifest())
    del document["services"]["api"]["environment"]["TAXIMOBILE_OPERATIONS_MFA_ENCRYPTION_KEY"]
    with pytest.raises(ValueError, match="MFA encryption key"):
        validator.validate_document(document)

    document = deepcopy(production_manifest())
    document["services"]["worker"]["environment"]["TAXIMOBILE_OPERATIONS_MFA_ENCRYPTION_KEY"] = "forbidden"
    with pytest.raises(ValueError, match="must not receive"):
        validator.validate_document(document)


def test_operations_secure_refresh_cookie_is_forced_on_the_api() -> None:
    document = deepcopy(production_manifest())
    document["services"]["api"]["environment"][
        "TAXIMOBILE_OPERATIONS_SECURE_COOKIE_ENABLED"
    ] = "false"
    with pytest.raises(ValueError, match="secure operations refresh cookies"):
        validator.validate_document(document)

    document = deepcopy(production_manifest())
    document["services"]["worker"]["environment"][
        "TAXIMOBILE_OPERATIONS_SECURE_COOKIE_ENABLED"
    ] = "true"
    with pytest.raises(ValueError, match="must not receive"):
        validator.validate_document(document)


def test_api_requires_complete_manual_transfer_configuration_surface() -> None:
    document = deepcopy(production_manifest())
    del document["services"]["api"]["environment"]["TAXIMOBILE_TRANSFER_WALLET_ID"]

    with pytest.raises(ValueError, match="complete fail-closed"):
        validator.validate_document(document)


def test_worker_cannot_receive_manual_transfer_recipient_configuration() -> None:
    document = deepcopy(production_manifest())
    document["services"]["worker"]["environment"]["TAXIMOBILE_TRANSFER_RECIPIENT_NAME"] = "forbidden"

    with pytest.raises(ValueError, match="must not receive manual-transfer"):
        validator.validate_document(document)


def test_case_pager_configuration_is_complete_and_worker_only() -> None:
    document = deepcopy(production_manifest())
    del document["services"]["worker"]["environment"]["TAXIMOBILE_CASE_PAGER_TOKEN"]

    with pytest.raises(ValueError, match="case-pager configuration"):
        validator.validate_document(document)

    document = deepcopy(production_manifest())
    document["services"]["api"]["environment"]["TAXIMOBILE_CASE_PAGER_URL"] = "forbidden"
    with pytest.raises(ValueError, match="worker-only case-pager"):
        validator.validate_document(document)


def test_driver_document_boundary_is_shared_but_role_limits_are_separated() -> None:
    document = deepcopy(production_manifest())
    del document["services"]["api"]["environment"][
        "TAXIMOBILE_DRIVER_DOCUMENT_ENCRYPTION_KEY"
    ]
    with pytest.raises(ValueError, match="protected driver-document boundary"):
        validator.validate_document(document)

    document = deepcopy(production_manifest())
    document["services"]["worker"]["environment"][
        "TAXIMOBILE_DRIVER_DOCUMENT_UPLOAD_RATE_LIMIT_PER_HOUR"
    ] = "forbidden"
    with pytest.raises(ValueError, match="request limits"):
        validator.validate_document(document)


def test_driver_document_volume_and_scanner_cannot_be_made_public() -> None:
    document = deepcopy(production_manifest())
    document["services"]["api"]["volumes"] = []
    with pytest.raises(ValueError, match="shared document and private role-log volumes"):
        validator.validate_document(document)

    document = deepcopy(production_manifest())
    document["services"]["clamav"]["ports"] = ["0.0.0.0:3310:3310"]
    with pytest.raises(ValueError, match="private Compose network"):
        validator.validate_document(document)


def test_api_and_worker_logs_use_separate_bounded_volumes() -> None:
    document = deepcopy(production_manifest())
    document["services"]["worker"]["volumes"][1] = (
        "taximobile_api_logs:/var/log/taximobile"
    )
    with pytest.raises(ValueError, match="private role-log volumes"):
        validator.validate_document(document)

    document = deepcopy(production_manifest())
    del document["services"]["api"]["environment"][
        "TAXIMOBILE_LOG_FILE_BACKUP_COUNT"
    ]
    with pytest.raises(ValueError, match="bounded file-log rotation"):
        validator.validate_document(document)


@pytest.mark.parametrize("service", ["api", "worker"])
def test_single_host_role_log_volume_cannot_be_scaled_in_manifest(service: str) -> None:
    document = deepcopy(production_manifest())
    document["services"][service]["deploy"] = {"replicas": 2}

    with pytest.raises(ValueError, match="cannot share one rotating role-log volume"):
        validator.validate_document(document)

def test_public_container_port_is_rejected() -> None:
    document = deepcopy(production_manifest())
    document["services"]["api"]["ports"] = ["0.0.0.0:8000:8000"]

    with pytest.raises(ValueError, match="host loopback"):
        validator.validate_document(document)


def test_api_probe_cannot_omit_the_reviewed_allowed_host_header() -> None:
    document = deepcopy(production_manifest())
    command = document["services"]["api"]["healthcheck"]["test"]
    command[3] = (
        "import urllib.request; "
        "urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=5).read()"
    )

    with pytest.raises(ValueError, match="allowed Host"):
        validator.validate_document(document)
