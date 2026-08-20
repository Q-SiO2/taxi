import asyncio

import pytest

from taximobile_api.integrations.routing.factory import create_routing_provider
from taximobile_api.integrations.routing.graphhopper import GraphHopperRoutingProvider
from taximobile_api.integrations.routing.valhalla import ValhallaRoutingProvider


@pytest.mark.parametrize(
    ("provider_name", "expected_type"),
    [
        ("valhalla", ValhallaRoutingProvider),
        ("graphhopper", GraphHopperRoutingProvider),
    ],
)
def test_routing_factory_selects_the_configured_adapter(
    provider_name: str,
    expected_type: type,
) -> None:
    provider = create_routing_provider(
        provider_name,
        "https://routing.example.test",
        timeout_seconds=2.5,
    )

    assert isinstance(provider, expected_type)
    asyncio_close(provider)


def test_routing_factory_refuses_an_unknown_adapter() -> None:
    with pytest.raises(ValueError, match="Unsupported routing provider"):
        create_routing_provider("osrm", "https://routing.example.test", timeout_seconds=2.5)


def asyncio_close(provider: ValhallaRoutingProvider | GraphHopperRoutingProvider) -> None:
    asyncio.run(provider.aclose())
