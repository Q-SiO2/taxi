from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from taximobile_api.domains.matching.scoring import CandidateSignals, MatchingPolicy, rank_candidates


NOW = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
DRIVER_A = UUID("00000000-0000-0000-0000-000000000001")
DRIVER_B = UUID("00000000-0000-0000-0000-000000000002")


def policy(**overrides) -> MatchingPolicy:
    values = {
        "radius_meters": 3000,
        "idle_cap_seconds": 1800,
        "assumed_pickup_speed_mps": 5.0,
        "proximity_weight": 0.55,
        "idle_weight": 0.30,
        "fairness_weight": 0.15,
        "algorithm_version": "mvp-v1",
    }
    values.update(overrides)
    return MatchingPolicy(**values)


def test_closer_driver_wins_when_wait_and_assignment_history_are_equal() -> None:
    ranked = rank_candidates(
        [
            CandidateSignals(DRIVER_A, 300, NOW - timedelta(minutes=5), 0),
            CandidateSignals(DRIVER_B, 900, NOW - timedelta(minutes=5), 0),
        ],
        now=NOW,
        policy=policy(),
    )

    assert [candidate.driver_id for candidate in ranked] == [DRIVER_A, DRIVER_B]
    assert ranked[0].estimated_pickup_time_seconds == 60


def test_longer_idle_time_can_outweigh_a_small_distance_difference() -> None:
    ranked = rank_candidates(
        [
            CandidateSignals(DRIVER_A, 300, NOW - timedelta(minutes=2), 0),
            CandidateSignals(DRIVER_B, 500, NOW - timedelta(minutes=18), 0),
        ],
        now=NOW,
        policy=policy(),
    )

    assert ranked[0].driver_id == DRIVER_B
    assert ranked[0].idle_seconds == 18 * 60


def test_recent_assignment_fairness_can_favor_driver_with_fewer_rides() -> None:
    ranked = rank_candidates(
        [
            CandidateSignals(DRIVER_A, 300, NOW - timedelta(minutes=5), 4),
            CandidateSignals(DRIVER_B, 450, NOW - timedelta(minutes=5), 0),
        ],
        now=NOW,
        policy=policy(proximity_weight=0.2, idle_weight=0.1, fairness_weight=0.7),
    )

    assert ranked[0].driver_id == DRIVER_B
    assert ranked[0].fairness_score == 1.0
    assert ranked[1].fairness_score == 0.2


def test_exact_ties_have_stable_driver_id_order() -> None:
    ranked = rank_candidates(
        [
            CandidateSignals(DRIVER_B, 500, NOW - timedelta(minutes=5), 0),
            CandidateSignals(DRIVER_A, 500, NOW - timedelta(minutes=5), 0),
        ],
        now=NOW,
        policy=policy(),
    )

    assert [candidate.driver_id for candidate in ranked] == [DRIVER_A, DRIVER_B]


@pytest.mark.parametrize(
    "overrides",
    [
        {"radius_meters": 0},
        {"idle_cap_seconds": 0},
        {"assumed_pickup_speed_mps": 0},
        {"proximity_weight": -1},
        {"proximity_weight": 0, "idle_weight": 0, "fairness_weight": 0},
        {"algorithm_version": ""},
    ],
)
def test_invalid_matching_policy_is_rejected(overrides) -> None:
    with pytest.raises(ValueError):
        policy(**overrides)
