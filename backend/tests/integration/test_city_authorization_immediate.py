"""Real PostGIS city restrictions against immediate offers and assignment.

Independent sessions retain stale identity-map records. Blocking races use the
observed-wait harness; SKIP LOCKED races explicitly require bounded nonblocking
completion. Synthetic supply never establishes a city's operating permission.
"""

import asyncio
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from assignment_concurrency import contended_commands
from test_account_assignment_authority import suspend_account
from test_dispatch_candidate_contention import seed_ride
from test_mvp_lifecycle import require_integration_settings
from test_scheduled_live_protection import assert_no_live_acceptance
from workload_fixtures import seed_workload_supply
from taximobile_api.domains.auth.models import User, UserStatus
from taximobile_api.domains.driver_applications.authorization_lifecycle import (
    AuthorizationDecisionRequest, decide_authorization,
)
from taximobile_api.domains.driver_applications.models import (
    DriverCityApplication, DriverCityAuthorization,
)
from taximobile_api.domains.drivers.models import AvailabilityStatus, DriverProfile
from taximobile_api.domains.matching.service import dispatch_ride
from taximobile_api.domains.notifications.models import Notification
from taximobile_api.domains.outbox.models import OutboxEvent
from taximobile_api.domains.rides.models import Ride, RideOffer, RideOfferStatus, RideStatus
from taximobile_api.domains.rides.service import RideOfferUnavailable, accept_offer_atomically
from taximobile_api.workers.matching import MatchingProcessor


pytestmark = pytest.mark.integration


@pytest.mark.parametrize("alternative", [False, True])
def test_dispatch_loses_global_authority_after_discovery_and_retries_or_uses_other_supply(alternative):
    async def prove():
        settings = require_integration_settings()
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            ride_id, _, driver_id, _ = await seed(sessions, settings)
            if alternative:
                # Identical location; the original driver has the longer idle
                # time and must be tried first (the observed user-lock wait
                # below proves this rather than assuming the scoring order).
                await seed_workload_supply(sessions, 1)
                async with sessions.begin() as session:
                    other = await session.scalar(select(DriverProfile).where(DriverProfile.id != driver_id))
                    other.available_since = datetime.now(UTC)
            async with sessions() as session:
                user_id = (await session.get(DriverProfile, driver_id)).user_id

            async def acquire(session):
                await suspend_account(session, user_id)

            async def prepare(session):
                return await session.get(User, user_id)

            async def first(_session):
                return "suspended"

            async def second(session, cached):
                assert cached.status == UserStatus.ACTIVE
                offer = await dispatch_ride(session, ride_id, settings)
                if alternative:
                    assert offer is not None and offer.driver_id != driver_id
                else:
                    assert offer is None
                return "other-supply" if alternative else "retry"

            # Discovery sees ACTIVE while suspension is uncommitted; selection
            # owns the driver then waits for the user's shared authority lock.
            assert await contended_commands(sessions, acquire_first=acquire,
                prepare_second=prepare, first_command=first, second_command=second) == [
                    "suspended", "other-supply" if alternative else "retry",
                ]
            async with sessions() as session:
                assert (await session.get(Ride, ride_id)).status == RideStatus.MATCHING
                offers = list(await session.scalars(select(RideOffer)))
                assert len(offers) == int(alternative)
                assert all(offer.driver_id != driver_id for offer in offers)
                assert await session.scalar(select(func.count(Notification.id))) == int(alternative)
            assert await MatchingProcessor(sessions, settings).process_once() == (0 if alternative else 1)
            async with sessions() as session:
                assert (await session.get(Ride, ride_id)).status == (
                    RideStatus.MATCHING if alternative else RideStatus.UNMATCHED
                )
                assert await session.scalar(select(RideOffer.id).where(RideOffer.driver_id == driver_id)) is None
        finally:
            await engine.dispose()
    asyncio.run(prove())


async def restrict(session, authorization_id, action):
    authorization = await session.get(DriverCityAuthorization, authorization_id)
    application = await session.get(DriverCityApplication, authorization.application_id)
    profile = await session.get(DriverProfile, authorization.driver_id)
    return await decide_authorization(
        session, application_id=application.id, reviewer_user_id=profile.user_id,
        payload=AuthorizationDecisionRequest(
            expected_application_version=application.optimistic_version,
            action=action,
            reason_code="ELIGIBILITY_REVIEW" if action == "SUSPEND" else "OPERATING_PERMISSION_WITHDRAWN",
        ),
    )


async def seed(sessions, settings, *, offered=False):
    await seed_workload_supply(sessions, 1, loginable=True)
    ride_id = await seed_ride(sessions)
    async with sessions.begin() as session:
        authorization = await session.scalar(select(DriverCityAuthorization))
        (await session.get(DriverProfile, authorization.driver_id)).availability_status = AvailabilityStatus.AVAILABLE
        await session.flush()
        offer = await dispatch_ride(session, ride_id, settings) if offered else None
        if offered:
            assert offer is not None
        return ride_id, authorization.id, authorization.driver_id, offer.id if offer else None


async def assert_restricted(session, authorization_id, action):
    authorization = await session.get(DriverCityAuthorization, authorization_id)
    assert authorization.status.value == ("SUSPENDED" if action == "SUSPEND" else "REVOKED")
    profile = await session.get(DriverProfile, authorization.driver_id)
    assert (await session.get(User, profile.user_id)).status == UserStatus.ACTIVE


@pytest.mark.parametrize("action", ["SUSPEND", "REVOKE"])
@pytest.mark.parametrize("winner", ["restriction", "acceptance"])
def test_immediate_acceptance_and_city_restriction_serialize(action, winner):
    async def prove():
        settings = require_integration_settings()
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            ride_id, authorization_id, driver_id, offer_id = await seed(sessions, settings, offered=True)

            async def acquire(session):
                if winner == "restriction":
                    await restrict(session, authorization_id, action)
                else:
                    await accept_offer_atomically(session, offer_id, driver_id)

            async def prepare(session):
                authorization = await session.get(DriverCityAuthorization, authorization_id)
                assert authorization.status.value == "ACTIVE"
                return authorization, await session.get(DriverProfile, driver_id)

            async def first(_session):
                return winner

            async def second(session, cached):
                assert cached[0].status.value == "ACTIVE"
                if winner == "restriction":
                    with pytest.raises(RideOfferUnavailable, match="no longer authorized"):
                        await accept_offer_atomically(session, offer_id, driver_id)
                else:
                    await restrict(session, authorization_id, action)
                return "finished"

            assert await contended_commands(sessions, acquire_first=acquire,
                prepare_second=prepare, first_command=first, second_command=second) == [winner, "finished"]
            async with sessions() as session:
                await assert_restricted(session, authorization_id, action)
                if winner == "restriction":
                    await assert_no_live_acceptance(session, ride_id, offer_id)
                else:
                    ride = await session.get(Ride, ride_id)
                    assert ride.status == RideStatus.ACCEPTED and ride.driver_id == driver_id
                    assert (await session.get(RideOffer, offer_id)).status == RideOfferStatus.ACCEPTED
                    assert (await session.get(DriverProfile, driver_id)).availability_status == AvailabilityStatus.EN_ROUTE
                    assert await session.scalar(select(func.count(Notification.id)).where(
                        Notification.user_id == ride.passenger_id, Notification.type == "DRIVER_ASSIGNED",
                    )) == 1
                    assert await session.scalar(select(func.count(OutboxEvent.id)).where(
                        OutboxEvent.topic == "ride.accepted",
                        OutboxEvent.payload["ride_id"].astext == str(ride_id),
                    )) == 1
        finally:
            await engine.dispose()
    asyncio.run(prove())


@pytest.mark.parametrize("action", ["SUSPEND", "REVOKE"])
@pytest.mark.parametrize("committed", [False, True])
def test_dispatch_skips_locked_city_restriction_and_excludes_committed_restriction(action, committed):
    async def prove():
        settings = require_integration_settings()
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            ride_id, authorization_id, driver_id, _ = await seed(sessions, settings)
            async with sessions.begin() as holder:
                await restrict(holder, authorization_id, action)
                if not committed:
                    # Discovery sees the still-committed ACTIVE row, but its
                    # driver is locked. This is retryable contention, not proof
                    # of no supply; no offer or passenger failure may be emitted.
                    async with sessions.begin() as requester:
                        assert await asyncio.wait_for(dispatch_ride(requester, ride_id, settings), 3) is None
                        assert (await requester.get(Ride, ride_id)).status == RideStatus.MATCHING
                        assert await requester.scalar(select(RideOffer.id)) is None
                        assert await requester.scalar(select(Notification.id)) is None
            if committed:
                async with sessions.begin() as requester:
                    assert await dispatch_ride(requester, ride_id, settings) is None
            else:
                assert await MatchingProcessor(sessions, settings).process_once() == 1
            async with sessions() as session:
                await assert_restricted(session, authorization_id, action)
                ride = await session.get(Ride, ride_id)
                assert ride.status == RideStatus.UNMATCHED and ride.driver_id is None
                assert await session.scalar(select(RideOffer.id)) is None
                assert (await session.get(DriverProfile, driver_id)).availability_status == AvailabilityStatus.AVAILABLE
        finally:
            await engine.dispose()
    asyncio.run(prove())


@pytest.mark.parametrize("action", ["SUSPEND", "REVOKE"])
def test_offer_commits_before_restriction_but_cannot_be_accepted_after_it(action):
    async def prove():
        settings = require_integration_settings()
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            ride_id, authorization_id, driver_id, _ = await seed(sessions, settings)
            offer_ids = []

            async def acquire(session):
                offer = await dispatch_ride(session, ride_id, settings)
                assert offer is not None
                offer_ids.append(offer.id)

            async def prepare(session):
                return await session.get(DriverCityAuthorization, authorization_id)

            async def first(_session):
                return "offered"

            async def second(session, cached):
                assert cached.status.value == "ACTIVE"
                await restrict(session, authorization_id, action)
                return "restricted"

            assert await contended_commands(sessions, acquire_first=acquire,
                prepare_second=prepare, first_command=first, second_command=second) == ["offered", "restricted"]
            async with sessions.begin() as session:
                with pytest.raises(RideOfferUnavailable, match="no longer authorized"):
                    await accept_offer_atomically(session, offer_ids[0], driver_id)
            async with sessions() as session:
                await assert_restricted(session, authorization_id, action)
                await assert_no_live_acceptance(session, ride_id, offer_ids[0])
                assert await session.scalar(select(func.count(RideOffer.id))) == 1
        finally:
            await engine.dispose()
    asyncio.run(prove())
