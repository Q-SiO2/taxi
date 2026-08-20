"""Seeded, synthetic evaluation harness for the production matching score.

The simulator deliberately has no database or provider dependency. Coordinates
are generated in an abstract meter-based city plane and output is aggregate, so
an evaluation cannot accidentally export passenger or driver location data.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import json
from math import cos, hypot, pi, sin
import random
import sys
from uuid import UUID

from taximobile_api.domains.matching.scoring import (
    CandidateSignals,
    MatchingPolicy,
    rank_candidates,
)


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    seed: int = 20260812
    driver_count: int = 100
    ride_count: int = 1000
    city_radius_meters: int = 8_000
    mean_request_interval_seconds: float = 20.0
    acceptance_probability: float = 0.80
    cancellation_probability: float = 0.05
    mean_trip_duration_seconds: float = 900.0
    offer_expiration_seconds: int = 20
    matching_timeout_seconds: int = 300
    candidate_limit: int = 10

    def __post_init__(self) -> None:
        positive = (
            self.driver_count,
            self.ride_count,
            self.city_radius_meters,
            self.mean_request_interval_seconds,
            self.mean_trip_duration_seconds,
            self.offer_expiration_seconds,
            self.matching_timeout_seconds,
            self.candidate_limit,
        )
        if min(positive) <= 0:
            raise ValueError("Simulation counts, durations, radii, and limits must be positive.")
        if not 0 <= self.acceptance_probability <= 1:
            raise ValueError("Acceptance probability must be between zero and one.")
        if not 0 <= self.cancellation_probability <= 1:
            raise ValueError("Cancellation probability must be between zero and one.")


@dataclass(slots=True)
class DriverState:
    driver_id: UUID
    x: float
    y: float
    available_since: datetime
    busy_until: datetime | None = None
    next_x: float | None = None
    next_y: float | None = None
    assignment_times: list[datetime] = field(default_factory=list)
    offers: int = 0
    declines: int = 0
    assignments: int = 0
    completions: int = 0
    cancellations: int = 0
    busy_seconds: float = 0.0
    assignment_idle_seconds: list[int] = field(default_factory=list)

    def release_if_due(self, now: datetime) -> None:
        if self.busy_until is None or self.busy_until > now:
            return
        self.x = self.next_x if self.next_x is not None else self.x
        self.y = self.next_y if self.next_y is not None else self.y
        self.available_since = self.busy_until
        self.busy_until = None
        self.next_x = None
        self.next_y = None


def run_matching_simulation(
    *,
    config: SimulationConfig,
    policy: MatchingPolicy,
) -> dict[str, object]:
    """Run one reproducible synthetic scenario and return aggregate metrics."""
    rng = random.Random(config.seed)
    started_at = datetime(2026, 1, 1, tzinfo=UTC)
    now = started_at
    drivers = [
        DriverState(
            driver_id=UUID(int=index + 1),
            x=(point := _random_point(rng, config.city_radius_meters))[0],
            y=point[1],
            available_since=started_at,
        )
        for index in range(config.driver_count)
    ]
    passenger_waits: list[float] = []
    pickup_times: list[int] = []
    matching_times: list[float] = []
    unmatched = 0
    accepted = 0
    declined = 0
    cancelled = 0
    completed = 0

    for ride_index in range(config.ride_count):
        if ride_index:
            now += timedelta(seconds=rng.expovariate(1 / config.mean_request_interval_seconds))
        for driver in drivers:
            driver.release_if_due(now)

        pickup_x, pickup_y = _random_point(rng, config.city_radius_meters)
        destination_x, destination_y = _random_point(rng, config.city_radius_meters)
        lookback_start = now - timedelta(hours=24)
        available_by_id: dict[UUID, DriverState] = {}
        signals: list[CandidateSignals] = []
        for driver in drivers:
            driver.assignment_times = [time for time in driver.assignment_times if time >= lookback_start]
            if driver.busy_until is not None:
                continue
            distance = hypot(driver.x - pickup_x, driver.y - pickup_y)
            if distance > policy.radius_meters:
                continue
            available_by_id[driver.driver_id] = driver
            signals.append(
                CandidateSignals(
                    driver_id=driver.driver_id,
                    distance_meters=distance,
                    available_since=driver.available_since,
                    recent_assignment_count=len(driver.assignment_times),
                )
            )

        ranked = rank_candidates(signals, now=now, policy=policy)[: config.candidate_limit]
        elapsed = 0.0
        selected = None
        for candidate in ranked:
            if elapsed >= config.matching_timeout_seconds:
                break
            driver = available_by_id[candidate.driver_id]
            driver.offers += 1
            response_seconds = rng.uniform(1, config.offer_expiration_seconds)
            elapsed = min(config.matching_timeout_seconds, elapsed + response_seconds)
            if rng.random() <= config.acceptance_probability:
                selected = (driver, candidate)
                break
            driver.declines += 1
            declined += 1

        if selected is None:
            unmatched += 1
            matching_times.append(elapsed)
            passenger_waits.append(elapsed)
            continue

        driver, candidate = selected
        accepted += 1
        driver.assignments += 1
        driver.assignment_times.append(now)
        driver.assignment_idle_seconds.append(candidate.idle_seconds)
        pickup_times.append(candidate.estimated_pickup_time_seconds)
        passenger_wait = elapsed + candidate.estimated_pickup_time_seconds
        matching_times.append(elapsed)
        passenger_waits.append(passenger_wait)

        if rng.random() <= config.cancellation_probability:
            cancelled += 1
            driver.cancellations += 1
            service_seconds = min(float(candidate.estimated_pickup_time_seconds), 60.0)
            driver.busy_seconds += service_seconds
            driver.busy_until = now + timedelta(seconds=elapsed + service_seconds)
            driver.next_x = driver.x
            driver.next_y = driver.y
            continue

        completed += 1
        driver.completions += 1
        trip_seconds = max(60.0, rng.expovariate(1 / config.mean_trip_duration_seconds))
        service_seconds = candidate.estimated_pickup_time_seconds + trip_seconds
        driver.busy_seconds += service_seconds
        driver.busy_until = now + timedelta(seconds=elapsed + service_seconds)
        driver.next_x = destination_x
        driver.next_y = destination_y

    simulation_end = max((driver.busy_until or now for driver in drivers), default=now)
    horizon_seconds = max(1.0, (simulation_end - started_at).total_seconds())
    rides_per_driver = [driver.completions for driver in drivers]
    idle_samples = [value for driver in drivers for value in driver.assignment_idle_seconds]
    utilization = [min(1.0, driver.busy_seconds / horizon_seconds) for driver in drivers]
    busiest_driver = max(drivers, key=lambda driver: (driver.completions, -driver.driver_id.int))
    least_busy_driver = min(
        drivers,
        key=lambda driver: (driver.completions, driver.driver_id.int),
    )

    return {
        "simulation": {
            "seed": config.seed,
            "drivers": config.driver_count,
            "ride_requests": config.ride_count,
            "synthetic_coordinates": True,
            "duration_seconds": round(horizon_seconds, 3),
        },
        "policy": {
            "algorithm_version": policy.algorithm_version,
            "search_radius_meters": policy.radius_meters,
            "candidate_limit": config.candidate_limit,
            "weights": {
                "proximity": policy.proximity_weight,
                "idle": policy.idle_weight,
                "fairness": policy.fairness_weight,
            },
        },
        "outcomes": {
            "accepted": accepted,
            "declined_offers": declined,
            "cancelled": cancelled,
            "completed": completed,
            "unmatched": unmatched,
            "completion_rate": round(completed / config.ride_count, 6),
            "cancellation_rate": round(cancelled / config.ride_count, 6),
            "unmatched_rate": round(unmatched / config.ride_count, 6),
        },
        "timing_seconds": {
            "passenger_wait": _summary(passenger_waits),
            "driver_pickup": _summary(pickup_times),
            "driver_idle_before_assignment": _summary(idle_samples),
            "matching": _summary(matching_times),
        },
        "ride_distribution": {
            "minimum_completed_per_driver": min(rides_per_driver, default=0),
            "maximum_completed_per_driver": max(rides_per_driver, default=0),
            "mean_completed_per_driver": round(sum(rides_per_driver) / config.driver_count, 3),
            "gini": round(gini_coefficient(rides_per_driver), 6),
        },
        "driver_utilization": {
            "mean": round(sum(utilization) / config.driver_count, 6),
            "minimum": round(min(utilization, default=0.0), 6),
            "maximum": round(max(utilization, default=0.0), 6),
        },
        "extremes": {
            "longest_passenger_wait_seconds": round(max(passenger_waits, default=0.0), 3),
            "longest_pickup_seconds": max(pickup_times, default=0),
            "longest_assignment_idle_seconds": max(idle_samples, default=0),
            "most_completed_by_one_driver": busiest_driver.completions,
            "least_completed_by_one_driver": least_busy_driver.completions,
        },
    }


def gini_coefficient(values: list[int]) -> float:
    if not values or sum(values) == 0:
        return 0.0
    ordered = sorted(max(0, value) for value in values)
    weighted_sum = sum(index * value for index, value in enumerate(ordered, start=1))
    return (2 * weighted_sum) / (len(ordered) * sum(ordered)) - (len(ordered) + 1) / len(ordered)


def _random_point(rng: random.Random, radius: int) -> tuple[float, float]:
    distance = radius * (rng.random() ** 0.5)
    angle = rng.random() * 2 * pi
    return distance * cos(angle), distance * sin(angle)


def _summary(values: list[float] | list[int]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "p50": 0.0, "p95": 0.0, "maximum": 0.0}
    ordered = sorted(float(value) for value in values)
    return {
        "mean": round(sum(ordered) / len(ordered), 3),
        "p50": round(_percentile(ordered, 0.50), 3),
        "p95": round(_percentile(ordered, 0.95), 3),
        "maximum": round(ordered[-1], 3),
    }


def _percentile(ordered: list[float], percentile: float) -> float:
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * percentile)))
    return ordered[index]


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="Simulate TaxiMobile's ranked matching policy.")
    command.add_argument("--seed", type=int, default=20260812)
    command.add_argument("--drivers", type=int, default=100)
    command.add_argument("--rides", type=int, default=1000)
    command.add_argument("--city-radius-meters", type=int, default=8000)
    command.add_argument("--search-radius-meters", type=int, default=3000)
    command.add_argument("--candidate-limit", type=int, default=10)
    command.add_argument("--mean-request-interval-seconds", type=float, default=20.0)
    command.add_argument("--acceptance-probability", type=float, default=0.80)
    command.add_argument("--cancellation-probability", type=float, default=0.05)
    command.add_argument("--mean-trip-duration-seconds", type=float, default=900.0)
    command.add_argument("--offer-expiration-seconds", type=int, default=20)
    command.add_argument("--matching-timeout-seconds", type=int, default=300)
    command.add_argument("--idle-cap-seconds", type=int, default=1800)
    command.add_argument("--assumed-pickup-speed-mps", type=float, default=6.944)
    command.add_argument("--proximity-weight", type=float, default=0.55)
    command.add_argument("--idle-weight", type=float, default=0.30)
    command.add_argument("--fairness-weight", type=float, default=0.15)
    command.add_argument("--algorithm-version", default="mvp-v1")
    return command


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        config = SimulationConfig(
            seed=arguments.seed,
            driver_count=arguments.drivers,
            ride_count=arguments.rides,
            city_radius_meters=arguments.city_radius_meters,
            mean_request_interval_seconds=arguments.mean_request_interval_seconds,
            acceptance_probability=arguments.acceptance_probability,
            cancellation_probability=arguments.cancellation_probability,
            mean_trip_duration_seconds=arguments.mean_trip_duration_seconds,
            offer_expiration_seconds=arguments.offer_expiration_seconds,
            matching_timeout_seconds=arguments.matching_timeout_seconds,
            candidate_limit=arguments.candidate_limit,
        )
        policy = MatchingPolicy(
            radius_meters=arguments.search_radius_meters,
            idle_cap_seconds=arguments.idle_cap_seconds,
            assumed_pickup_speed_mps=arguments.assumed_pickup_speed_mps,
            proximity_weight=arguments.proximity_weight,
            idle_weight=arguments.idle_weight,
            fairness_weight=arguments.fairness_weight,
            algorithm_version=arguments.algorithm_version,
        )
        result = run_matching_simulation(config=config, policy=policy)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
