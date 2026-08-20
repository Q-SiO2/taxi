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
