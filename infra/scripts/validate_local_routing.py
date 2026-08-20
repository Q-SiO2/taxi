"""Validate the committed local routing build and selection contract."""

from __future__ import annotations

from pathlib import Path
import re

import yaml


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_PATH = WORKSPACE_ROOT / "infra" / "compose.yaml"
GRAPHOPPER_ROOT = WORKSPACE_ROOT / "infra" / "routing" / "graphhopper"
START_SCRIPT_PATH = WORKSPACE_ROOT / "infra" / "scripts" / "start-local-stack.ps1"
ENVIRONMENT_EXAMPLE_PATH = WORKSPACE_ROOT / "infra" / ".env.example"

GRAPHOPPER_JAR_SHA256 = "b59c024afe172ec6ec85b6327006c3138ec58c7d0bcd26253d0e42853f613def"
TEMURIN_IMAGE_DIGEST = "sha256:1e38389ecd9e5c444e40d4385be4a4a5f56a836a38a6e41c099810c32ec1c595"


def load_manifest(path: Path = COMPOSE_PATH) -> dict:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("Local Compose manifest must be an object.")
    return document


def validate_manifest(document: dict) -> None:
    services = document.get("services")
    if not isinstance(services, dict):
        raise ValueError("Local Compose manifest must define services.")
    valhalla = _service(services, "valhalla")
    graphhopper = _service(services, "graphhopper")
    api = _service(services, "api")

    if valhalla.get("profiles") != ["routing-valhalla"]:
        raise ValueError("Valhalla must use only the routing-valhalla profile.")
    if valhalla.get("ports") != ["127.0.0.1:8002:8002"]:
        raise ValueError("Valhalla must bind to the exclusive loopback routing port.")
    valhalla_image = valhalla.get("image")
    if not isinstance(valhalla_image, str) or ":3.8.3@sha256:" not in valhalla_image:
        raise ValueError("Valhalla image must pin version 3.8.3 and an immutable digest.")

    if graphhopper.get("profiles") != ["routing-graphhopper"]:
        raise ValueError("GraphHopper must use only the routing-graphhopper profile.")
    if graphhopper.get("build") != {"context": "routing/graphhopper"} or "image" in graphhopper:
        raise ValueError("GraphHopper must build the reviewed workspace image definition.")
    if graphhopper.get("ports") != ["127.0.0.1:8002:8989"]:
        raise ValueError("GraphHopper must bind to the exclusive loopback routing port.")
    if graphhopper.get("read_only") is not True or graphhopper.get("cap_drop") != ["ALL"]:
        raise ValueError("GraphHopper must remain read-only and drop all Linux capabilities.")
    if "no-new-privileges:true" not in graphhopper.get("security_opt", []):
        raise ValueError("GraphHopper must disable privilege escalation.")
    if graphhopper.get("volumes") != ["taximobile_graphhopper_data:/data"]:
        raise ValueError("GraphHopper must persist only its dedicated graph-data volume.")
    graphhopper_environment = graphhopper.get("environment", {})
    if set(graphhopper_environment) != {"GRAPHHOPPER_OSM_URL", "GRAPHHOPPER_OSM_SHA256"}:
        raise ValueError("GraphHopper must receive only the reviewed graph input variables.")
    health_command = graphhopper.get("healthcheck", {}).get("test", [])
    if health_command != ["CMD", "curl", "--fail", "--silent", "http://127.0.0.1:8989/info"]:
        raise ValueError("GraphHopper health must probe its loopback information endpoint.")

    api_environment = api.get("environment", {})
    if api_environment.get("TAXIMOBILE_ROUTING_PROVIDER") != "${TAXIMOBILE_ROUTING_PROVIDER:-valhalla}":
        raise ValueError("API routing provider must remain environment-selected.")
    if api_environment.get("TAXIMOBILE_ROUTING_BASE_URL") != "${TAXIMOBILE_ROUTING_BASE_URL:-http://valhalla:8002}":
        raise ValueError("API routing URL must remain environment-selected.")

    volumes = document.get("volumes", {})
    if "taximobile_graphhopper_data" not in volumes:
        raise ValueError("Local Compose must declare the GraphHopper data volume.")


def validate_files(
    *,
    dockerfile: str,
    entrypoint: str,
    config: str,
    start_script: str,
    environment_example: str,
) -> None:
    required_dockerfile = (
        f"@{TEMURIN_IMAGE_DIGEST}",
        "GRAPHOPPER_VERSION=11.0",
        "graphhopper-web/11.0/graphhopper-web-11.0.jar",
        GRAPHOPPER_JAR_SHA256,
        "USER 10001:10001",
    )
    if any(marker not in dockerfile for marker in required_dockerfile):
        raise ValueError("GraphHopper image must pin its base, release JAR, checksum, and user.")

    required_entrypoint = (
        "https://*",
        "GRAPHHOPPER_OSM_SHA256",
        "sha256sum --check --strict",
        'graph_directory="/data/graph-v11-${osm_sha256}"',
        "--proto '=https'",
        "--proto-redir '=https'",
        "-Xmx3g",
    )
    if any(marker not in entrypoint for marker in required_entrypoint):
        raise ValueError("GraphHopper entrypoint lost an input, checksum, cache, TLS, or resource guard.")
    if "latest" in entrypoint.casefold():
        raise ValueError("GraphHopper entrypoint must not select mutable latest resources.")

    required_config = (
        "name: car",
        "custom_model_files: [car.json]",
        "routing.timeout_ms: 15000",
        "bind_host: 0.0.0.0",
        "port: 8989",
    )
    if any(marker not in config for marker in required_config):
        raise ValueError("GraphHopper config lost the reviewed car-routing boundary.")

    required_start_markers = (
        '[ValidateSet("none", "valhalla", "graphhopper")]',
        '"routing-valhalla"',
        '"routing-graphhopper"',
        "Assert-ImmutableHttpsDownload",
        "GRAPHHOPPER_OSM_SHA256",
        "RunRoutingAcceptance",
        "taximobile_api.operations.routing_acceptance",
    )
    if any(marker not in start_script for marker in required_start_markers):
        raise ValueError("Local startup lost routing exclusivity, input validation, or acceptance execution.")

    values = _environment_values(environment_example)
    valhalla_url = values.get("VALHALLA_TILE_URL", "")
    graphhopper_url = values.get("GRAPHHOPPER_OSM_URL", "")
    graphhopper_sha = values.get("GRAPHHOPPER_OSM_SHA256", "")
    if not valhalla_url.startswith("https://") or "-latest." in valhalla_url.casefold():
        raise ValueError("Valhalla example must use a dated HTTPS extract.")
    if not graphhopper_url.startswith("https://") or "-latest." in graphhopper_url.casefold():
        raise ValueError("GraphHopper example must use a dated HTTPS extract.")
    if not re.fullmatch(r"[0-9a-f]{64}", graphhopper_sha):
        raise ValueError("GraphHopper example must pin the extract SHA-256 digest.")


def validate_repository() -> None:
    validate_manifest(load_manifest())
    validate_files(
        dockerfile=(GRAPHOPPER_ROOT / "Dockerfile").read_text(encoding="utf-8"),
        entrypoint=(GRAPHOPPER_ROOT / "entrypoint.sh").read_text(encoding="utf-8"),
        config=(GRAPHOPPER_ROOT / "config.yml").read_text(encoding="utf-8"),
        start_script=START_SCRIPT_PATH.read_text(encoding="utf-8"),
        environment_example=ENVIRONMENT_EXAMPLE_PATH.read_text(encoding="utf-8"),
    )


def _service(services: dict, name: str) -> dict:
    service = services.get(name)
    if not isinstance(service, dict):
        raise ValueError(f"Local Compose must define the {name} service.")
    return service


def _environment_values(contents: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in contents.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        values[name.strip()] = value.strip()
    return values


if __name__ == "__main__":
    validate_repository()
    print("Local routing infrastructure contract is valid.")
