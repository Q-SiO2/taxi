"""Provider-neutral routing contracts and adapters."""

from taximobile_api.integrations.routing.models import Route, RouteCoordinate, RouteManeuver
from taximobile_api.integrations.routing.provider import RoutingProvider
from taximobile_api.integrations.routing.factory import create_routing_provider
from taximobile_api.integrations.routing.graphhopper import GraphHopperRoutingProvider
from taximobile_api.integrations.routing.valhalla import ValhallaRoutingProvider

__all__ = [
    "Route",
    "RouteCoordinate",
    "RouteManeuver",
    "RoutingProvider",
    "create_routing_provider",
    "GraphHopperRoutingProvider",
    "ValhallaRoutingProvider",
]
