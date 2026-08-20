import pytest
from pydantic import ValidationError

from taximobile_api.domains.auth.schemas import PassengerProfileUpdateRequest


def test_passenger_profile_update_normalizes_a_display_name() -> None:
    update = PassengerProfileUpdateRequest(display_name="  Amina  ")

    assert update.display_name == "Amina"


def test_passenger_profile_update_rejects_a_blank_display_name() -> None:
    with pytest.raises(ValidationError):
        PassengerProfileUpdateRequest(display_name="   ")
