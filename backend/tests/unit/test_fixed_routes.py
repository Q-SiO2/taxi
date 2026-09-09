"""Phase 15 fixed-route contract tests that do not require PostGIS."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from taximobile_api.domains.fixed_routes.schemas import (
    FixedRouteCreateRequest,
    FixedRouteVersionCreateRequest,
    LineStringGeometry,
)
from taximobile_api.domains.pricing.schemas import (
    OperatorFeePolicyCreateRequest,
    PricingRuleCreateRequest,
)
from taximobile_api.domains.rides.schemas import RideCreateRequest, RideEstimateRequest


LOCALIZED_NAME = {"en": "Central station", "fr": "Gare centrale", "ar": "المحطة المركزية"}


def direction(code: str = "OUTBOUND") -> dict:
    return {
        "direction_code": code,
        "start_location_name": LOCALIZED_NAME,
        "finish_location_name": {
            "en": "University",
            "fr": "Université",
            "ar": "الجامعة",
        },
        "start": {"longitude": -6.84, "latitude": 34.02},
        "finish": {"longitude": -6.80, "latitude": 34.00},
        "geometry": {
            "type": "LineString",
            "coordinates": [[-6.84, 34.02], [-6.82, 34.01], [-6.80, 34.00]],
        },
        "flat_fare_policy_version_id": uuid4(),
        "stops": [],
    }


def test_route_code_is_normalized_and_unknown_fields_fail_closed() -> None:
    request = FixedRouteCreateRequest(operator_id=uuid4(), code="  rb_01 ")

    assert request.code == "RB_01"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        FixedRouteCreateRequest(operator_id=uuid4(), code="RB_01", fare="8.00")


@pytest.mark.parametrize(
    "coordinates",
    (
        [[-6.84, 34.02], [-6.84, 34.02]],
        [[-6.84, 34.02], [-181.0, 34.00]],
        [[-6.84, 34.02], [-6.80]],
    ),
)
def test_route_geometry_rejects_degenerate_or_invalid_coordinates(coordinates) -> None:
    with pytest.raises(ValidationError):
        LineStringGeometry(coordinates=coordinates)


def test_route_version_requires_distinct_explicit_direction_codes() -> None:
    with pytest.raises(ValidationError, match="cannot duplicate a direction code"):
        FixedRouteVersionCreateRequest(
            version="v1",
            localized_name=LOCALIZED_NAME,
            effective_from=datetime.now(UTC),
            directions=[direction(), direction()],
        )


def test_fixed_route_ride_request_is_mutually_exclusive_with_coordinates() -> None:
    direction_id = uuid4()

    fixed = RideEstimateRequest(fixed_route_direction_version_id=direction_id)
    assert fixed.fixed_route_direction_version_id == direction_id
    with pytest.raises(ValidationError, match="derives pickup and destination"):
        RideCreateRequest(
            fixed_route_direction_version_id=direction_id,
            pickup={"latitude": 34.02, "longitude": -6.84},
        )
    with pytest.raises(ValidationError, match="require pickup and destination"):
        RideEstimateRequest()


def test_immediate_fixed_route_financial_policy_contracts_are_supported() -> None:
    direction_id = uuid4()
    common = {
        "operator_id": uuid4(),
        "service_type": "FIXED_ROUTE",
        "currency": "mad",
        "effective_from": datetime.now(UTC),
    }
    tariff = PricingRuleCreateRequest(
        **common,
        name="Published route fare",
        version="route-v1",
        fixed_amount="8.00",
        fixed_route_direction_id=direction_id,
    )
    fee = OperatorFeePolicyCreateRequest(
        **common,
        version="route-fee-v1",
        calculation_mode="FLAT_PER_COMPLETED_BOOKING",
        funding_mode="DRIVER_SETTLEMENT_DEDUCTION",
        flat_amount="0.00",
    )

    assert tariff.service_type.value == "FIXED_ROUTE"
    assert tariff.fixed_route_direction_id == direction_id
    assert tariff.currency == "MAD"
    assert fee.service_type.value == "FIXED_ROUTE"


def test_only_fixed_route_tariffs_can_reference_immutable_directions() -> None:
    with pytest.raises(ValidationError, match="Only a fixed-route tariff"):
        PricingRuleCreateRequest(
            operator_id=uuid4(),
            service_type="ON_DEMAND",
            fixed_route_direction_id=uuid4(),
            name="Invalid point-to-point direction scope",
            version="invalid-direction-v1",
            fixed_amount="8.00",
            currency="MAD",
            effective_from=datetime.now(UTC),
        )


def test_route_geometry_can_be_drafted_before_its_separately_reviewed_fare() -> None:
    unpriced = direction()
    unpriced.pop("flat_fare_policy_version_id")

    version = FixedRouteVersionCreateRequest(
        version="geometry-first-v1",
        localized_name=LOCALIZED_NAME,
        effective_from=datetime.now(UTC),
        directions=[unpriced],
    )

    assert version.directions[0].flat_fare_policy_version_id is None


def test_standalone_scheduled_financial_policy_remains_fail_closed() -> None:
    with pytest.raises(ValidationError, match="fixed-route service only"):
        PricingRuleCreateRequest(
            operator_id=uuid4(),
            service_type="SCHEDULED",
            name="Premature schedule fare",
            version="future-v1",
            fixed_amount="8.00",
            currency="MAD",
            effective_from=datetime.now(UTC),
        )
