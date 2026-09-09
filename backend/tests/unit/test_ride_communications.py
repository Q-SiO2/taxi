from pydantic import ValidationError
import pytest

from taximobile_api.domains.ride_communications.models import RideCoordinationCode
from taximobile_api.domains.ride_communications.policy import (
    DRIVER_CODES,
    PASSENGER_CODES,
    compatibility_copy,
    sender_role_for_code,
)
from taximobile_api.domains.ride_communications.schemas import (
    RideCoordinationCreateRequest,
    RideCoordinationSenderRole,
)


def test_launch_coordination_vocabulary_is_closed_and_role_partitioned() -> None:
    assert PASSENGER_CODES.isdisjoint(DRIVER_CODES)
    assert PASSENGER_CODES | DRIVER_CODES == set(RideCoordinationCode)
    assert all(
        sender_role_for_code(code) == RideCoordinationSenderRole.PASSENGER
        for code in PASSENGER_CODES
    )
    assert all(
        sender_role_for_code(code) == RideCoordinationSenderRole.DRIVER
        for code in DRIVER_CODES
    )


def test_coordination_request_rejects_free_text_and_unknown_codes() -> None:
    with pytest.raises(ValidationError):
        RideCoordinationCreateRequest.model_validate(
            {"code": "PASSENGER_AT_PICKUP", "message": "Call my private number"}
        )
    with pytest.raises(ValidationError):
        RideCoordinationCreateRequest.model_validate({"code": "CUSTOM_MESSAGE"})


def test_every_coordination_code_has_bounded_compatibility_copy() -> None:
    for code in RideCoordinationCode:
        title, body = compatibility_copy(code)
        assert title == "Ride update"
        assert 1 <= len(body) <= 160
