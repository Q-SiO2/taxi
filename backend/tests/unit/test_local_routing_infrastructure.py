from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
VALIDATOR_PATH = WORKSPACE_ROOT / "infra" / "scripts" / "validate_local_routing.py"

spec = importlib.util.spec_from_file_location("validate_local_routing", VALIDATOR_PATH)
assert spec is not None and spec.loader is not None
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def test_committed_local_routing_infrastructure_preserves_contract() -> None:
    validator.validate_repository()


def test_graphhopper_cannot_bind_publicly() -> None:
    document = deepcopy(validator.load_manifest())
    document["services"]["graphhopper"]["ports"] = ["0.0.0.0:8002:8989"]

    with pytest.raises(ValueError, match="exclusive loopback"):
        validator.validate_manifest(document)


def test_both_engines_cannot_share_one_compose_profile() -> None:
    document = deepcopy(validator.load_manifest())
    document["services"]["graphhopper"]["profiles"] = ["routing-valhalla"]

    with pytest.raises(ValueError, match="routing-graphhopper"):
        validator.validate_manifest(document)


def test_graphhopper_cannot_lose_container_hardening() -> None:
    document = deepcopy(validator.load_manifest())
    document["services"]["graphhopper"]["read_only"] = False

    with pytest.raises(ValueError, match="read-only"):
        validator.validate_manifest(document)


def test_mutable_extract_example_is_rejected() -> None:
    example = validator.ENVIRONMENT_EXAMPLE_PATH.read_text(encoding="utf-8").replace(
        "morocco-260819.osm.pbf", "morocco-latest.osm.pbf"
    )

    with pytest.raises(ValueError, match="dated HTTPS extract"):
        validator.validate_files(
            dockerfile=(validator.GRAPHOPPER_ROOT / "Dockerfile").read_text(encoding="utf-8"),
            entrypoint=(validator.GRAPHOPPER_ROOT / "entrypoint.sh").read_text(encoding="utf-8"),
            config=(validator.GRAPHOPPER_ROOT / "config.yml").read_text(encoding="utf-8"),
            start_script=validator.START_SCRIPT_PATH.read_text(encoding="utf-8"),
            environment_example=example,
        )
