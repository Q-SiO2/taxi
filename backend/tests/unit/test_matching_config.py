from taximobile_api.core.config import Settings


def test_matching_configuration_has_bounded_local_defaults(monkeypatch) -> None:
    monkeypatch.delenv("TAXIMOBILE_MATCHING_RADIUS_METERS", raising=False)
    monkeypatch.delenv("TAXIMOBILE_MATCHING_LOCATION_FRESHNESS_SECONDS", raising=False)
    monkeypatch.delenv("TAXIMOBILE_RIDE_OFFER_SECONDS", raising=False)
    monkeypatch.delenv("TAXIMOBILE_MATCHING_CANDIDATE_LIMIT", raising=False)
    monkeypatch.delenv("TAXIMOBILE_MATCHING_IDLE_CAP_SECONDS", raising=False)
    monkeypatch.delenv("TAXIMOBILE_MATCHING_FAIRNESS_LOOKBACK_HOURS", raising=False)
    monkeypatch.delenv("TAXIMOBILE_MATCHING_ASSUMED_PICKUP_SPEED_MPS", raising=False)
    monkeypatch.delenv("TAXIMOBILE_MATCHING_PROXIMITY_WEIGHT", raising=False)
    monkeypatch.delenv("TAXIMOBILE_MATCHING_IDLE_WEIGHT", raising=False)
    monkeypatch.delenv("TAXIMOBILE_MATCHING_FAIRNESS_WEIGHT", raising=False)
    monkeypatch.delenv("TAXIMOBILE_MATCHING_ALGORITHM_VERSION", raising=False)
    monkeypatch.delenv("TAXIMOBILE_MATCHING_POLL_SECONDS", raising=False)
    monkeypatch.delenv("TAXIMOBILE_MATCHING_TIMEOUT_SECONDS", raising=False)

    settings = Settings.from_environment()

    assert settings.matching_radius_meters == 3000
    assert settings.matching_location_freshness_seconds == 30
    assert settings.ride_offer_seconds == 45
    assert settings.matching_candidate_limit == 10
    assert settings.matching_idle_cap_seconds == 1800
    assert settings.matching_fairness_lookback_hours == 24
    assert settings.matching_assumed_pickup_speed_mps == 6.944
    assert settings.matching_proximity_weight == 0.55
    assert settings.matching_idle_weight == 0.30
    assert settings.matching_fairness_weight == 0.15
    assert settings.matching_algorithm_version == "mvp-v1"
    assert settings.matching_poll_seconds == 1
    assert settings.matching_timeout_seconds == 300
