"""Scheduling cannot bypass ordinary professional eligibility facts."""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from taximobile_api.domains.drivers.models import (
    AvailabilityStatus, DriverAccountStatus, DriverProfile, Vehicle,
    VehicleStatus, VehicleVerificationStatus, VerificationStatus,
)
from taximobile_api.domains.scheduled_bookings.eligibility import scheduled_driver_eligibility_failure


def eligible_driver():
    profile = DriverProfile(
        id=uuid4(), account_status=DriverAccountStatus.ACTIVE,
        verification_status=VerificationStatus.APPROVED,
        availability_status=AvailabilityStatus.OFFLINE,
    )
    vehicle = Vehicle(
        id=uuid4(), driver_id=profile.id, status=VehicleStatus.ACTIVE,
        verification_status=VehicleVerificationStatus.VERIFIED,
    )
    profile.active_vehicle_id = vehicle.id
    return profile, vehicle


@pytest.mark.parametrize("defect", [
    "pending-account", "suspended-account", "deactivated-account",
    "unapproved", "suspended-verification", "expired-verification",
    "missing-vehicle", "different-selection", "foreign-vehicle",
    "inactive-vehicle", "unverified-vehicle", "expired-vehicle",
])
def test_invalid_profile_or_vehicle_is_rejected_before_credential_lookup(defect):
    profile, vehicle = eligible_driver()
    account_states = {
        "pending-account": DriverAccountStatus.PENDING,
        "suspended-account": DriverAccountStatus.SUSPENDED,
        "deactivated-account": DriverAccountStatus.DEACTIVATED,
    }
    verification_states = {
        "unapproved": VerificationStatus.SUBMITTED,
        "suspended-verification": VerificationStatus.SUSPENDED,
        "expired-verification": VerificationStatus.EXPIRED,
    }
    if defect in account_states:
        profile.account_status = account_states[defect]
    elif defect in verification_states:
        profile.verification_status = verification_states[defect]
    elif defect == "missing-vehicle":
        vehicle = None
    elif defect == "different-selection":
        profile.active_vehicle_id = uuid4()
    elif defect == "foreign-vehicle":
        vehicle.driver_id = uuid4()
    elif defect == "inactive-vehicle":
        vehicle.status = VehicleStatus.INACTIVE
    elif defect == "unverified-vehicle":
        vehicle.verification_status = VehicleVerificationStatus.PENDING
    else:
        vehicle.verification_status = VehicleVerificationStatus.EXPIRED

    class Session:
        async def scalar(self, _statement):
            raise AssertionError("Invalid basic facts must reject before credential lookup.")

    failure = asyncio.run(scheduled_driver_eligibility_failure(
        Session(), profile, vehicle, now=datetime.now(UTC),
    ))
    assert failure is not None


@pytest.mark.parametrize("invalid_credentials", [False, True])
def test_future_commitment_needs_valid_credentials_but_not_immediate_online_state(invalid_credentials):
    profile, vehicle = eligible_driver()
    now = datetime(2026, 9, 3, 12, tzinfo=UTC)
    queries = []

    class Session:
        async def scalar(self, statement):
            queries.append(statement)
            return invalid_credentials

    failure = asyncio.run(scheduled_driver_eligibility_failure(Session(), profile, vehicle, now=now))
    assert (failure is not None) == invalid_credentials
    assert len(queries) == 1
    # Bind the authoritative driver and handoff clock into the real credential predicate.
    parameters = queries[0].compile().params.values()
    assert profile.id in parameters
    assert now in parameters
