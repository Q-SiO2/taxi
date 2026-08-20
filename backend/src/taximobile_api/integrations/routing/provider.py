"""Routing provider boundary used by the application layer."""

from typing import Protocol

from taximobile_api.integrations.routing.models import Route, RouteCoordinate


class RoutingUnavailable(RuntimeError):
    """The configured routing service could not produce a trustworthy route."""


class RoutingProvider(Protocol):
    async def route(
        self,
        origin: RouteCoordinate,
        destination: RouteCoordinate,
        language: str = "en",
    ) -> Route: ...

    async def aclose(self) -> None: ...
