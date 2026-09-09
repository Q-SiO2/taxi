"""Migrated city restrictions, reviewed reinstatement and assignment races."""

import asyncio
from datetime import timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from assignment_concurrency import contended_commands
from scheduled_handoff_fixtures import prepare_handoff_fixture
from test_mvp_lifecycle import require_integration_settings
from taximobile_api.domains.administration.models import AuditLog
from taximobile_api.domains.auth.models import User, UserStatus
from taximobile_api.domains.driver_applications.authorization_lifecycle import (
    AuthorizationDecisionRequest, decide_authorization,
)
from taximobile_api.domains.driver_applications.models import (
    CityAuthorizationStatus, DriverCityApplication, DriverCityAuthorization,
)
from taximobile_api.domains.driver_applications.service import RecruitmentConflict
from taximobile_api.domains.drivers.models import DriverProfile, Vehicle, VehicleVerificationStatus
from taximobile_api.domains.notifications.models import Notification
from taximobile_api.domains.outbox.models import OutboxEvent
from taximobile_api.domains.rides.models import Ride
from taximobile_api.domains.scheduled_bookings.models import ScheduledBooking
from taximobile_api.domains.scheduled_bookings.service import handoff_booking


pytestmark = pytest.mark.integration
REASONS = {"SUSPEND": "ELIGIBILITY_REVIEW", "REVOKE": "OPERATING_PERMISSION_WITHDRAWN",
           "REINSTATE": "ELIGIBILITY_REVIEW_PASSED"}


async def authorization_for(session, ready):
    return await session.scalar(select(DriverCityAuthorization).where(
        DriverCityAuthorization.driver_id == ready.driver_id,
    ))


async def command(session, ready, action, *, version=None):
    authorization = await authorization_for(session, ready)
    application = await session.get(DriverCityApplication, authorization.application_id)
    return await decide_authorization(
        session, application_id=application.id, reviewer_user_id=ready.user_id,
        payload=AuthorizationDecisionRequest(
            expected_application_version=version if version is not None else application.optimistic_version,
            action=action, reason_code=REASONS[action],
        ), now=ready.now,
    )


def test_suspend_reinstate_revoke_keeps_history_expiry_and_other_driver_authorization():
    async def prove():
        engine = create_async_engine(require_integration_settings().database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            ready = await prepare_handoff_fixture(sessions)
            async with sessions.begin() as session:
                original = await authorization_for(session, ready)
                original.valid_until = ready.now + timedelta(days=1)
                other = await session.scalar(select(DriverCityAuthorization).where(
                    DriverCityAuthorization.driver_id != ready.driver_id,
                ))
                other_id = other.id
            for action, status in [("SUSPEND", "SUSPENDED"), ("REINSTATE", "ACTIVE"), ("REVOKE", "REVOKED")]:
                async with sessions.begin() as session:
                    application = await command(session, ready, action)
                    assert application.status.value == "APPROVED"
                async with sessions() as session:
                    authorization = await authorization_for(session, ready)
                    assert authorization.status.value == status
                    assert authorization.valid_until == ready.now + timedelta(days=1)
                    assert (await session.get(DriverCityAuthorization, other_id)).status.value == "ACTIVE"
                    assert (await session.get(ScheduledBooking, ready.booking_id)).status.value == "DRIVER_COMMITTED"
            async with sessions.begin() as session:
                with pytest.raises(RecruitmentConflict):
                    await command(session, ready, "REINSTATE")
            async with sessions() as session:
                assert await session.scalar(select(func.count(AuditLog.id)).where(
                    AuditLog.resource_id == authorization.id,
                    AuditLog.resource_type == "driver_city_authorization",
                )) == 3
                assert await session.scalar(select(func.count(Notification.id)).where(
                    Notification.user_id == ready.user_id,
                    Notification.type == "DRIVER_CITY_AUTHORIZATION_CHANGED",
                    Notification.data["authorization_id"].astext == str(authorization.id),
                )) == 3
                assert await session.scalar(select(func.count(OutboxEvent.id)).where(
                    OutboxEvent.topic == "driver.city_authorization.changed",
                    OutboxEvent.payload["authorization_id"].astext == str(authorization.id),
                )) == 3
        finally:
            await engine.dispose()
    asyncio.run(prove())


@pytest.mark.parametrize("failure", ["expired", "global-suspension", "vehicle", "stale-version"])
def test_reinstatement_rechecks_eligibility_without_extending_or_partially_restoring(failure):
    async def prove():
        engine = create_async_engine(require_integration_settings().database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            ready = await prepare_handoff_fixture(sessions)
            async with sessions.begin() as session:
                await command(session, ready, "SUSPEND")
                authorization = await authorization_for(session, ready)
                if failure == "expired":
                    authorization.valid_until = ready.now
                elif failure == "global-suspension":
                    (await session.get(User, ready.user_id)).status = UserStatus.SUSPENDED
                elif failure == "vehicle":
                    profile = await session.get(DriverProfile, ready.driver_id)
                    (await session.get(Vehicle, profile.active_vehicle_id)).verification_status = VehicleVerificationStatus.PENDING
            async with sessions.begin() as session:
                with pytest.raises(RecruitmentConflict):
                    await command(session, ready, "REINSTATE", version=1 if failure == "stale-version" else None)
            async with sessions() as session:
                authorization = await authorization_for(session, ready)
                assert authorization.status == CityAuthorizationStatus.SUSPENDED
                assert await session.scalar(select(func.count(AuditLog.id)).where(
                    AuditLog.resource_id == authorization.id,
                    AuditLog.resource_type == "driver_city_authorization",
                )) == 1
        finally:
            await engine.dispose()
    asyncio.run(prove())


@pytest.mark.parametrize("action", ["SUSPEND", "REVOKE"])
@pytest.mark.parametrize("winner", ["restriction", "handoff"])
def test_city_restriction_and_handoff_wait_for_driver_authority(action, winner):
    async def prove():
        settings = require_integration_settings()
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            ready = await prepare_handoff_fixture(sessions)
            async def handoff(session, booking=None):
                return await handoff_booking(
                    session, booking or await session.get(ScheduledBooking, ready.booking_id),
                    now=ready.now, matching_settings=settings,
                )
            async def acquire(session):
                if winner == "restriction":
                    await command(session, ready, action)
                else:
                    assert isinstance(await handoff(session), Ride)
            async def prepare(session):
                authorization = await authorization_for(session, ready)
                assert authorization.status == CityAuthorizationStatus.ACTIVE
                return await session.get(ScheduledBooking, ready.booking_id), authorization
            async def first(_session):
                return winner
            async def second(session, cached):
                if winner == "restriction":
                    result = await handoff(session, cached[0])
                    assert isinstance(result, ScheduledBooking)
                    assert result.status.value == "UNFULFILLED"
                else:
                    await command(session, ready, action)
                return "finished"
            assert await contended_commands(sessions, acquire_first=acquire, prepare_second=prepare,
                first_command=first, second_command=second) == [winner, "finished"]
            async with sessions() as session:
                authorization = await authorization_for(session, ready)
                assert authorization.status.value == ("SUSPENDED" if action == "SUSPEND" else "REVOKED")
                rides = list(await session.scalars(select(Ride).where(Ride.scheduled_booking_id == ready.booking_id)))
                assert len(rides) == (0 if winner == "restriction" else 1)
                if rides:
                    assert rides[0].driver_id == ready.driver_id
                    assert rides[0].status.value == "ACCEPTED"
                assert (await session.get(User, ready.user_id)).status == UserStatus.ACTIVE
        finally:
            await engine.dispose()
    asyncio.run(prove())
