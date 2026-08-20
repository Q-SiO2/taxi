import pytest
from pydantic import ValidationError

from taximobile_api.domains.drivers.schemas import VehicleUpdateRequest


def test_vehicle_update_requires_an_actual_field_and_preserves_required_identity() -> None:
    with pytest.raises(ValidationError):
        VehicleUpdateRequest()
    with pytest.raises(ValidationError):
        VehicleUpdateRequest(registration_number=None)


def test_vehicle_update_allows_clearing_optional_taxi_identifier() -> None:
    update = VehicleUpdateRequest(color="Blue", taxi_identifier=None)

    assert update.model_dump(exclude_unset=True) == {"color": "Blue", "taxi_identifier": None}
