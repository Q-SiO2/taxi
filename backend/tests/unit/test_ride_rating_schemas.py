import pytest
from pydantic import ValidationError

from taximobile_api.domains.rides.schemas import RideRatingCreateRequest


def test_rating_score_is_limited_to_the_documented_range() -> None:
    assert RideRatingCreateRequest(score=5, comment="Reliable trip.").score == 5
    with pytest.raises(ValidationError):
        RideRatingCreateRequest(score=0)
    with pytest.raises(ValidationError):
        RideRatingCreateRequest(score=6)


def test_rating_rejects_unexpected_or_oversized_input() -> None:
    with pytest.raises(ValidationError):
        RideRatingCreateRequest(score=4, unrelated="not accepted")
    with pytest.raises(ValidationError):
        RideRatingCreateRequest(score=4, comment="x" * 2001)
