"""Guarded acceptance checks for a promoted Morocco routing graph.

This command deliberately exercises only a fixed set of public landmark routes.
It never accepts user coordinates, prints provider payloads, or includes route
geometry/instructions in its result. It is an operational acceptance gate, not a
substitute for the provider adapters or mobile navigation tests.
"""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from dataclasses import dataclass
import json
from math import asin, cos, isfinite, radians, sin, sqrt
from ipaddress import ip_address
import sys
from typing import Final
from urllib.parse import urlparse

from taximobile_api.integrations.routing.factory import create_routing_provider
from taximobile_api.integrations.routing.models import Route, RouteCoordinate
from taximobile_api.integrations.routing.provider import RoutingProvider, RoutingUnavailable


REQUIRED_LANGUAGES: Final = ("en", "fr", "ar")
PROVIDER_LANGUAGES: Final = {
    # The pinned Valhalla 3.8.3 catalog maps Arabic to English. Keep that gap
    # explicit so a release report cannot mislabel fallback narration as Arabic.
    "valhalla": frozenset({"en", "fr"}),
    "graphhopper": frozenset({"en", "fr", "ar"}),
}

# Broad bounds cover the selected single-country MVP without accepting geometry
# that escaped into another continent because of a coordinate-order/data error.
MOROCCO_LATITUDE_RANGE: Final = (27.0, 36.5)
MOROCCO_LONGITUDE_RANGE: Final = (-13.5, -0.5)
MAX_ENDPOINT_SNAP_METERS: Final = 2_500.0
MAX_ROUTE_DISTANCE_METERS: Final = 250_000
MIN_PLAUSIBLE_SPEED_KPH: Final = 1.0
MAX_PLAUSIBLE_SPEED_KPH: Final = 160.0


@dataclass(frozen=True, slots=True)
class RoutingScenario:
    scenario_id: str
    origin: RouteCoordinate
    destination: RouteCoordinate


# Fixed, public city-centre checks. Identifiers are safe to report; coordinates
# and generated paths are intentionally omitted from command output.
MOROCCO_SCENARIOS: Final = (
    RoutingScenario(
        "casablanca_urban",
        RouteCoordinate(latitude=33.5731, longitude=-7.5898),
        RouteCoordinate(latitude=33.5899, longitude=-7.6039),
    ),
    RoutingScenario(
        "rabat_urban",
        RouteCoordinate(latitude=34.0209, longitude=-6.8416),
        RouteCoordinate(latitude=33.9911, longitude=-6.8498),
    ),
    RoutingScenario(
        "marrakech_urban",
        RouteCoordinate(latitude=31.6295, longitude=-7.9811),
        RouteCoordinate(latitude=31.5987, longitude=-8.0255),
    ),
)


@dataclass(frozen=True, slots=True)
class RoutingAcceptanceCheck:
    scenario_id: str
    language: str
    failures: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.failures

    def as_dict(self) -> dict[str, object]:
        return {
            "scenario": self.scenario_id,
            "language": self.language,
            "passed": self.passed,
            "failures": list(self.failures),
        }


@dataclass(frozen=True, slots=True)
class RoutingAcceptanceReport:
    provider: str
    checks: tuple[RoutingAcceptanceCheck, ...]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    def as_dict(self) -> dict[str, object]:
        failure_counts = Counter(
            failure
            for check in self.checks
            for failure in check.failures
        )
        return {
            "provider": self.provider,
            "passed": self.passed,
            "scenario_count": len({check.scenario_id for check in self.checks}),
            "required_languages": list(REQUIRED_LANGUAGES),
            "checks": [check.as_dict() for check in self.checks],
            "failure_counts": dict(sorted(failure_counts.items())),
        }


@dataclass(slots=True)
class _WorkingCheck:
    scenario_id: str
    language: str
    failures: list[str]
    instructions: tuple[str, ...] = ()


async def run_routing_acceptance(
    *,
    provider_name: str,
    provider: RoutingProvider,
    scenarios: tuple[RoutingScenario, ...] = MOROCCO_SCENARIOS,
) -> RoutingAcceptanceReport:
    """Exercise fixed routes through the real configured adapter.

    Transport/provider failures are reduced to stable codes. Raw exception text,
    instructions, geometry, and target details never enter the report.
    """
    supported_languages = PROVIDER_LANGUAGES.get(provider_name)
    if supported_languages is None:
        raise ValueError("Provider must be valhalla or graphhopper.")
    _validate_scenarios(scenarios)

    working: dict[tuple[str, str], _WorkingCheck] = {}
    for scenario in scenarios:
        for language in REQUIRED_LANGUAGES:
            check = _WorkingCheck(scenario.scenario_id, language, [])
            working[(scenario.scenario_id, language)] = check
            if language not in supported_languages:
                check.failures.append("provider_language_unsupported")
                continue
            try:
                route = await provider.route(
                    scenario.origin,
                    scenario.destination,
                    language=language,
                )
            except RoutingUnavailable:
                check.failures.append("provider_unavailable")
                continue
            except Exception:
                # An adapter defect must fail closed without putting private
                # provider diagnostics or response values in the acceptance log.
                check.failures.append("adapter_failure")
                continue

            check.failures.extend(_route_failures(route, scenario))
            check.instructions = tuple(
                " ".join(maneuver.instruction.split()).casefold()
                for maneuver in route.maneuvers
                if maneuver.instruction.strip()
            )

    _validate_localized_narration(working, scenarios)
    checks = tuple(
        RoutingAcceptanceCheck(
            scenario_id=check.scenario_id,
            language=check.language,
            failures=tuple(dict.fromkeys(check.failures)),
        )
        for check in working.values()
    )
    return RoutingAcceptanceReport(provider=provider_name, checks=checks)


def _validate_scenarios(scenarios: tuple[RoutingScenario, ...]) -> None:
    if not scenarios:
        raise ValueError("At least one fixed routing scenario is required.")
    identifiers = [scenario.scenario_id for scenario in scenarios]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Routing scenario identifiers must be unique.")
    for scenario in scenarios:
        if not scenario.scenario_id or not _inside_morocco(scenario.origin) or not _inside_morocco(
            scenario.destination
        ):
            raise ValueError("Every routing scenario must be named and remain inside Morocco.")


def _route_failures(route: Route, scenario: RoutingScenario) -> list[str]:
    failures: list[str] = []
    direct_distance = _distance_meters(scenario.origin, scenario.destination)
    if (
        isinstance(route.distance_meters, bool)
        or not isinstance(route.distance_meters, int)
        or route.distance_meters <= 0
        or route.distance_meters > MAX_ROUTE_DISTANCE_METERS
        or route.distance_meters < direct_distance * 0.7
        or route.distance_meters > max(direct_distance * 8, direct_distance + 10_000)
    ):
        failures.append("distance_implausible")

    if (
        isinstance(route.duration_seconds, bool)
        or not isinstance(route.duration_seconds, int)
        or route.duration_seconds <= 0
    ):
        failures.append("duration_invalid")
    elif isinstance(route.distance_meters, int) and route.distance_meters > 0:
        speed_kph = route.distance_meters / route.duration_seconds * 3.6
        if not isfinite(speed_kph) or not MIN_PLAUSIBLE_SPEED_KPH <= speed_kph <= MAX_PLAUSIBLE_SPEED_KPH:
            failures.append("speed_implausible")

    if len(route.geometry) < 2:
        failures.append("geometry_too_short")
    else:
        if not all(_inside_morocco(coordinate) for coordinate in route.geometry):
            failures.append("geometry_outside_morocco")
        if _distance_meters(route.geometry[0], scenario.origin) > MAX_ENDPOINT_SNAP_METERS:
            failures.append("origin_snap_too_far")
        if _distance_meters(route.geometry[-1], scenario.destination) > MAX_ENDPOINT_SNAP_METERS:
            failures.append("destination_snap_too_far")

    if not route.maneuvers:
        failures.append("maneuvers_missing")
    elif any(not _valid_maneuver(maneuver, len(route.geometry)) for maneuver in route.maneuvers):
        failures.append("maneuver_invalid")
    return failures


def _valid_maneuver(maneuver: object, geometry_size: int) -> bool:
    try:
        instruction = maneuver.instruction
        distance = maneuver.distance_meters
        duration = maneuver.duration_seconds
        begin = maneuver.begin_shape_index
        end = maneuver.end_shape_index
    except AttributeError:
        return False
    return (
        isinstance(instruction, str)
        and bool(instruction.strip())
        and isinstance(distance, int)
        and not isinstance(distance, bool)
        and distance >= 0
        and isinstance(duration, int)
        and not isinstance(duration, bool)
        and duration >= 0
        and isinstance(begin, int)
        and not isinstance(begin, bool)
        and isinstance(end, int)
        and not isinstance(end, bool)
        and 0 <= begin <= end < geometry_size
    )


def _validate_localized_narration(
    checks: dict[tuple[str, str], _WorkingCheck],
    scenarios: tuple[RoutingScenario, ...],
) -> None:
    for scenario in scenarios:
        english = checks[(scenario.scenario_id, "en")]
        for language in ("fr", "ar"):
            localized = checks[(scenario.scenario_id, language)]
            if english.failures or localized.failures:
                continue
            if not english.instructions or not localized.instructions:
                localized.failures.append("narration_missing")
                continue
            if localized.instructions == english.instructions:
                localized.failures.append("narration_not_localized")
            if language == "ar" and not any(
                _contains_arabic(instruction) for instruction in localized.instructions
            ):
                localized.failures.append("arabic_script_missing")


def _inside_morocco(coordinate: RouteCoordinate) -> bool:
    return (
        isfinite(coordinate.latitude)
        and isfinite(coordinate.longitude)
        and MOROCCO_LATITUDE_RANGE[0] <= coordinate.latitude <= MOROCCO_LATITUDE_RANGE[1]
        and MOROCCO_LONGITUDE_RANGE[0] <= coordinate.longitude <= MOROCCO_LONGITUDE_RANGE[1]
    )


def _distance_meters(first: RouteCoordinate, second: RouteCoordinate) -> float:
    earth_radius_meters = 6_371_000.0
    first_latitude = radians(first.latitude)
    second_latitude = radians(second.latitude)
    latitude_delta = second_latitude - first_latitude
    longitude_delta = radians(second.longitude - first.longitude)
    haversine = (
        sin(latitude_delta / 2) ** 2
        + cos(first_latitude) * cos(second_latitude) * sin(longitude_delta / 2) ** 2
    )
    return 2 * earth_radius_meters * asin(sqrt(min(1.0, max(0.0, haversine))))


def _contains_arabic(value: str) -> bool:
    return any(
        "\u0600" <= character <= "\u06ff"
        or "\u0750" <= character <= "\u077f"
        or "\u08a0" <= character <= "\u08ff"
        for character in value
    )


def validate_base_url(base_url: str) -> str:
    if not base_url or base_url != base_url.strip():
        raise ValueError("Base URL must not be empty or padded with whitespace.")
    parsed = urlparse(base_url)
    try:
        parsed_port = parsed.port
    except ValueError as error:
        raise ValueError("Base URL has an invalid port.") from error
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Base URL must be an absolute HTTP or HTTPS origin.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.params:
        raise ValueError("Base URL must not contain credentials, parameters, a query, or a fragment.")
    if parsed.path not in {"", "/"}:
        raise ValueError("Base URL must be an origin without a path.")
    if parsed_port is not None and not 1 <= parsed_port <= 65535:
        raise ValueError("Base URL has an invalid port.")
    return parsed.hostname.rstrip(".").lower()


def is_local_target(base_url: str) -> bool:
    hostname = validate_base_url(base_url)
    if hostname == "localhost":
        return True
    try:
        return ip_address(hostname).is_loopback
    except ValueError:
        return False


def confirm_target(base_url: str, confirmed_host: str | None) -> None:
    hostname = validate_base_url(base_url)
    if is_local_target(base_url):
        return
    normalized_confirmation = (confirmed_host or "").strip().rstrip(".").lower()
    if not normalized_confirmation or normalized_confirmation != hostname:
        raise ValueError("A non-local target requires --confirm-host with its exact hostname.")


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        description="Validate a selected TaxiMobile Morocco routing graph and narration catalog."
    )
    command.add_argument("--provider", choices=tuple(PROVIDER_LANGUAGES), required=True)
    command.add_argument("--base-url", required=True)
    command.add_argument("--timeout-seconds", type=float, default=15.0)
    command.add_argument(
        "--confirm-host",
        help="Exact hostname confirmation required for an authorized non-local routing service.",
    )
    return command


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if not 0.1 <= arguments.timeout_seconds <= 60:
        print("Timeout must be between 0.1 and 60 seconds.", file=sys.stderr)
        return 2
    try:
        confirm_target(arguments.base_url, arguments.confirm_host)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2

    provider = create_routing_provider(
        arguments.provider,
        arguments.base_url.rstrip("/"),
        timeout_seconds=arguments.timeout_seconds,
    )
    try:
        report = asyncio.run(
            run_routing_acceptance(provider_name=arguments.provider, provider=provider)
        )
    finally:
        asyncio.run(provider.aclose())
    print(json.dumps(report.as_dict(), sort_keys=True))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
