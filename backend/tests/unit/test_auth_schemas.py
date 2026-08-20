import pytest
from pydantic import ValidationError

from taximobile_api.domains.auth.schemas import RegisterRequest


def test_registration_requires_an_identifier_and_does_not_accept_roles() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(password="a-secure-enough-password", display_name="Passenger")

    with pytest.raises(ValidationError):
        RegisterRequest(
            email="passenger@example.test",
            password="a-secure-enough-password",
            display_name="Passenger",
            role="ADMIN",
        )

    request = RegisterRequest(
        email="  Passenger@Example.Test ",
        password="a-secure-enough-password",
        display_name="Passenger",
    )
    assert request.email == "passenger@example.test"


def test_registration_normalizes_moroccan_phone_numbers() -> None:
    request = RegisterRequest(
        phone_number=" +212 600000000 ",
        password="a-secure-enough-password",
        display_name="Passenger",
    )

    assert request.phone_number == "+212600000000"


@pytest.mark.parametrize("input_number", ["0600000000", "00212600000000", "+212-600-000-000"])
def test_registration_accepts_common_moroccan_phone_spellings(input_number: str) -> None:
    request = RegisterRequest(
        phone_number=input_number,
        password="a-secure-enough-password",
        display_name="Passenger",
    )

    assert request.phone_number == "+212600000000"


def test_registration_rejects_non_moroccan_phone_format() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(
            phone_number="+33123456789",
            password="a-secure-enough-password",
            display_name="Passenger",
        )
