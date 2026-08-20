import asyncio
from dataclasses import replace

import pytest

from taximobile_api.integrations.routing.models import Route, RouteCoordinate, RouteManeuver
from taximobile_api.integrations.routing.provider import RoutingUnavailable
from taximobile_api.operations.routing_acceptance import (
    MOROCCO_SCENARIOS,
    RoutingScenario,
    confirm_target,
    is_local_target,
    run_routing_acceptance,
    validate_base_url,
)


class LocalizedRoutingProvider:
    def __init__(
        self,
        *,
        unavailable: bool = False,
        geometry_outside_morocco: bool = False,
        instructions: dict[str, str] | None = None,
    ) -> None:
        self.unavailable = unavailable
        self.geometry_outside_morocco = geometry_outside_morocco
        self.instructions = instructions or {
            "en": "Turn right and continue",
            "fr": "Tournez à droite et continuez",
            "ar": "انعطف يمينًا ثم تابع",
        }
        self.calls: list[tuple[str, str]] = []

    async def route(
        self,
        origin: RouteCoordinate,
        destination: RouteCoordinate,
        language: str = "en",
    ) -> Route:
        self.calls.append((language, f"{origin.latitude:.4f}"))
        if self.unavailable:
            raise RoutingUnavailable("private provider detail")
        midpoint = RouteCoordinate(
            latitude=(origin.latitude + destination.latitude) / 2,
            longitude=(origin.longitude + destination.longitude) / 2,
        )
        geometry = (origin, midpoint, destination)
        if self.geometry_outside_morocco:
            geometry = (origin, RouteCoordinate(48.8566, 2.3522), destination)
        return Route(
            distance_meters=5_000,
            duration_seconds=600,
            geometry=geometry,
            maneuvers=(
                RouteManeuver(
                    instruction=self.instructions[language],
                    distance_meters=5_000,
                    duration_seconds=600,
                    begin_shape_index=0,
                    end_shape_index=2,
                ),
            ),
        )

    async def aclose(self) -> None:
        return None


def test_graphhopper_acceptance_covers_all_fixed_routes_and_languages() -> None:
    provider = LocalizedRoutingProvider()

    report = asyncio.run(
        run_routing_acceptance(provider_name="graphhopper", provider=provider)
    )

    assert report.passed
    assert len(report.checks) == len(MOROCCO_SCENARIOS) * 3
    assert len(provider.calls) == len(report.checks)
    serialized = str(report.as_dict())
    assert "Turn right" not in serialized
    assert "Tournez" not in serialized
    assert "انعطف" not in serialized


def test_valhalla_fails_closed_for_required_arabic_narration_without_calling_fallback() -> None:
    provider = LocalizedRoutingProvider()

    report = asyncio.run(
        run_routing_acceptance(provider_name="valhalla", provider=provider)
    )

    assert not report.passed
    arabic_checks = [check for check in report.checks if check.language == "ar"]
    assert arabic_checks
    assert all(check.failures == ("provider_language_unsupported",) for check in arabic_checks)
    assert all(language != "ar" for language, _ in provider.calls)


def test_route_geometry_outside_morocco_is_rejected() -> None:
    report = asyncio.run(
        run_routing_acceptance(
            provider_name="graphhopper",
            provider=LocalizedRoutingProvider(geometry_outside_morocco=True),
            scenarios=(MOROCCO_SCENARIOS[0],),
        )
    )

    assert not report.passed
    assert all("geometry_outside_morocco" in check.failures for check in report.checks)


def test_provider_failure_is_bounded_to_a_stable_code() -> None:
    report = asyncio.run(
        run_routing_acceptance(
            provider_name="graphhopper",
            provider=LocalizedRoutingProvider(unavailable=True),
            scenarios=(MOROCCO_SCENARIOS[0],),
        )
    )

    assert not report.passed
    assert all(check.failures == ("provider_unavailable",) for check in report.checks)
    assert "private provider detail" not in str(report.as_dict())


def test_untranslated_and_non_arabic_narration_are_rejected() -> None:
    provider = LocalizedRoutingProvider(
        instructions={
            "en": "Turn right and continue",
            "fr": "Turn right and continue",
            "ar": "Right turn then continue",
        }
    )

    report = asyncio.run(
        run_routing_acceptance(
            provider_name="graphhopper",
            provider=provider,
            scenarios=(MOROCCO_SCENARIOS[0],),
        )
    )

    french = next(check for check in report.checks if check.language == "fr")
    arabic = next(check for check in report.checks if check.language == "ar")
    assert "narration_not_localized" in french.failures
    assert "arabic_script_missing" in arabic.failures


def test_duplicate_or_out_of_country_scenarios_are_rejected_before_network_calls() -> None:
    provider = LocalizedRoutingProvider()
    duplicate = replace(MOROCCO_SCENARIOS[0])
    with pytest.raises(ValueError, match="identifiers must be unique"):
        asyncio.run(
            run_routing_acceptance(
                provider_name="graphhopper",
                provider=provider,
                scenarios=(MOROCCO_SCENARIOS[0], duplicate),
            )
        )

    outside = RoutingScenario(
        "outside",
        RouteCoordinate(48.8566, 2.3522),
        MOROCCO_SCENARIOS[0].destination,
    )
    with pytest.raises(ValueError, match="remain inside Morocco"):
        asyncio.run(
            run_routing_acceptance(
                provider_name="graphhopper",
                provider=provider,
                scenarios=(outside,),
            )
        )
    assert provider.calls == []


@pytest.mark.parametrize(
    "base_url",
    ["http://localhost:8002", "http://127.0.0.1:8002/", "http://[::1]:8989"],
)
def test_loopback_routing_targets_need_no_confirmation(base_url: str) -> None:
    assert is_local_target(base_url)
    confirm_target(base_url, None)


@pytest.mark.parametrize(
    "base_url",
    [
        "https://user:secret@routing.example.test",
        "https://routing.example.test/private",
        "https://routing.example.test?token=secret",
        "https://routing.example.test#fragment",
    ],
)
def test_routing_target_rejects_url_data_that_could_leak_or_change_path(base_url: str) -> None:
    with pytest.raises(ValueError):
        validate_base_url(base_url)


def test_nonlocal_target_requires_exact_hostname_confirmation() -> None:
    with pytest.raises(ValueError, match="exact hostname"):
        confirm_target("https://routing.internal.example", None)
    with pytest.raises(ValueError, match="exact hostname"):
        confirm_target("https://routing.internal.example", "another.internal.example")

    confirm_target("https://routing.internal.example", "ROUTING.INTERNAL.EXAMPLE")
