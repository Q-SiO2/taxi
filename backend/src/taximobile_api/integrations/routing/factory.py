"""Select exactly one server-side routing adapter from validated settings."""

from taximobile_api.integrations.routing.graphhopper import GraphHopperRoutingProvider
from taximobile_api.integrations.routing.provider import RoutingProvider
from taximobile_api.integrations.routing.valhalla import ValhallaRoutingProvider


def create_routing_provider(
    provider_name: str,
    base_url: str,
    *,
    timeout_seconds: float,
) -> RoutingProvider:
    if provider_name == "valhalla":
        return ValhallaRoutingProvider(base_url, timeout_seconds=timeout_seconds)
    if provider_name == "graphhopper":
        return GraphHopperRoutingProvider(base_url, timeout_seconds=timeout_seconds)
    raise ValueError("Unsupported routing provider")
