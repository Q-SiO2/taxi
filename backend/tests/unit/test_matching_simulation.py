from taximobile_api.domains.matching.scoring import MatchingPolicy
from taximobile_api.operations.matching_simulation import (
    SimulationConfig,
    gini_coefficient,
    main,
    run_matching_simulation,
)


def policy() -> MatchingPolicy:
    return MatchingPolicy(
        radius_meters=3000,
        idle_cap_seconds=1800,
        assumed_pickup_speed_mps=5,
        proximity_weight=0.55,
        idle_weight=0.30,
        fairness_weight=0.15,
        algorithm_version="test-v1",
    )


def test_simulation_is_reproducible_and_accounts_for_every_ride() -> None:
    config = SimulationConfig(seed=7, driver_count=12, ride_count=80)

    first = run_matching_simulation(config=config, policy=policy())
    second = run_matching_simulation(config=config, policy=policy())

    assert first == second
    outcomes = first["outcomes"]
    assert outcomes["completed"] + outcomes["cancelled"] + outcomes["unmatched"] == 80
    assert outcomes["accepted"] == outcomes["completed"] + outcomes["cancelled"]
    assert first["simulation"]["synthetic_coordinates"] is True
    assert first["policy"]["algorithm_version"] == "test-v1"
    assert 0 <= first["ride_distribution"]["gini"] <= 1
    assert 0 <= first["driver_utilization"]["mean"] <= 1


def test_zero_acceptance_generates_declines_and_no_completions() -> None:
    result = run_matching_simulation(
        config=SimulationConfig(
            seed=3,
            driver_count=20,
            ride_count=20,
            city_radius_meters=1000,
            acceptance_probability=0,
        ),
        policy=policy(),
    )

    assert result["outcomes"]["accepted"] == 0
    assert result["outcomes"]["completed"] == 0
    assert result["outcomes"]["unmatched"] == 20
    assert result["outcomes"]["declined_offers"] > 0


def test_gini_coefficient_has_expected_bounds() -> None:
    assert gini_coefficient([]) == 0
    assert gini_coefficient([0, 0]) == 0
    assert gini_coefficient([2, 2, 2]) == 0
    assert round(gini_coefficient([0, 0, 6]), 6) == 0.666667


def test_cli_rejects_invalid_probability(capsys) -> None:
    exit_code = main(["--acceptance-probability", "1.1"])

    assert exit_code == 2
    assert "between zero and one" in capsys.readouterr().err
