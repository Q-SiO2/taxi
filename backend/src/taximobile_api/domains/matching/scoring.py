"""Pure, deterministic candidate scoring for the MVP ranked-offer policy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from math import ceil
from uuid import UUID


@dataclass(frozen=True, slots=True)
class MatchingPolicy:
    radius_meters: int
    idle_cap_seconds: int
    assumed_pickup_speed_mps: float
    proximity_weight: float
    idle_weight: float
    fairness_weight: float
    algorithm_version: str

    def __post_init__(self) -> None:
        if self.radius_meters < 1 or self.idle_cap_seconds < 1 or self.assumed_pickup_speed_mps <= 0:
            raise ValueError("Matching policy bounds must be positive.")
        if min(self.proximity_weight, self.idle_weight, self.fairness_weight) < 0:
            raise ValueError("Matching weights must not be negative.")
        if self.total_weight <= 0:
            raise ValueError("At least one matching weight must be positive.")
        if not self.algorithm_version:
            raise ValueError("Matching algorithm version is required.")

    @property
    def total_weight(self) -> float:
        return self.proximity_weight + self.idle_weight + self.fairness_weight


@dataclass(frozen=True, slots=True)
class CandidateSignals:
    driver_id: UUID
    distance_meters: float
    available_since: datetime | None
    recent_assignment_count: int


@dataclass(frozen=True, slots=True)
class RankedCandidate:
    driver_id: UUID
    distance_meters: int
    estimated_pickup_time_seconds: int
    idle_seconds: int
    recent_assignment_count: int
    proximity_score: float
    idle_score: float
    fairness_score: float
    ranking_score: float


def rank_candidates(
    candidates: list[CandidateSignals],
    *,
    now: datetime,
    policy: MatchingPolicy,
) -> list[RankedCandidate]:
    """Rank eligible candidates; eligibility itself remains a database concern.

    Fairness is based on accepted assignments in a configured recent window,
    not acceptance rate or declined offers. This avoids penalizing a driver for
    exercising the documented right to decline an individual offer.
    """
    current_time = _as_utc(now)
    ranked: list[RankedCandidate] = []
    for candidate in candidates:
        distance = max(0, int(round(candidate.distance_meters)))
        available_since = _as_utc(candidate.available_since) if candidate.available_since else current_time
        idle_seconds = max(0, int((current_time - available_since).total_seconds()))
        assignments = max(0, candidate.recent_assignment_count)
        proximity_score = max(0.0, 1.0 - min(distance / policy.radius_meters, 1.0))
        idle_score = min(idle_seconds / policy.idle_cap_seconds, 1.0)
        fairness_score = 1.0 / (1.0 + assignments)
        weighted_score = (
            proximity_score * policy.proximity_weight
            + idle_score * policy.idle_weight
            + fairness_score * policy.fairness_weight
        ) / policy.total_weight
        ranked.append(
            RankedCandidate(
                driver_id=candidate.driver_id,
                distance_meters=distance,
                estimated_pickup_time_seconds=max(1, ceil(distance / policy.assumed_pickup_speed_mps)),
                idle_seconds=idle_seconds,
                recent_assignment_count=assignments,
                proximity_score=round(proximity_score, 6),
                idle_score=round(idle_score, 6),
                fairness_score=round(fairness_score, 6),
                ranking_score=round(weighted_score, 6),
            )
        )
    return sorted(
        ranked,
        key=lambda candidate: (
            -candidate.ranking_score,
            -candidate.idle_seconds,
            candidate.distance_meters,
            str(candidate.driver_id),
        ),
    )


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
