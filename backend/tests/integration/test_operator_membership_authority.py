"""Closed-shop SQL admission, real assignment and observed membership races.

All organizations/accounts are synthetic and isolated by the existing per-test
PostGIS fixture. No union roster or deployed staging data is used.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.exc import IntegrityError

from assignment_concurrency import contended_commands
from scheduled_acceptance_fixtures import seed_acceptance
from scheduled_handoff_fixtures import prepare_handoff_fixture
from test_dispatch_candidate_contention import seed_ride
from test_mvp_lifecycle import require_integration_settings, register_and_login
from test_scheduled_acceptance_concurrency import accept as accept_scheduled
from test_scheduled_live_protection import assert_no_live_acceptance
from workload_fixtures import seed_workload_supply
from taximobile_api.domains.cooperatives.authority import (
    driver_membership_is_active, operator_membership_allows,
)
from taximobile_api.domains.cooperatives.models import (
    Cooperative, CooperativeMembership, CooperativeMembershipStatus, CooperativeStatus,
)
from taximobile_api.domains.driver_applications.models import (
    DriverCityAuthorization, DriverCityAuthorizationService,
)
from taximobile_api.domains.drivers.models import AvailabilityStatus, DriverProfile
from taximobile_api.domains.fixed_routes.models import (
    FixedRoute, FixedRouteDirection, FixedRouteDirectionCode, FixedRouteVersion,
)
from taximobile_api.domains.markets.constants import LEGACY_CITY_ID, LEGACY_OPERATOR_ID
from taximobile_api.domains.markets.models import Operator, OperatorType, ServiceType
from taximobile_api.domains.matching.service import dispatch_ride
from taximobile_api.domains.payments.models import Payment
from taximobile_api.domains.pricing.models import (
    BookingType, PricingModel, PricingRule, PricingRuleStatus,
)
from taximobile_api.domains.pricing.service import quote_immediate_ride
from taximobile_api.domains.rides.models import Ride, RideStatus
from taximobile_api.domains.rides.service import (
    RideOfferUnavailable, accept_offer_atomically, complete_assigned_ride,
    transition_assigned_ride,
)
from taximobile_api.domains.scheduled_bookings import service as scheduling
from taximobile_api.domains.scheduled_bookings.models import (
    ScheduledBooking, ScheduledBookingCommitment, ScheduledBookingOffer, ScheduledBookingStatus,
)
from taximobile_api.domains.scheduled_bookings.schemas import ScheduledBookingCreateRequest
from taximobile_api.main import create_app

pytestmark = pytest.mark.integration


def database(scenario):
    async def run():
        engine = create_async_engine(require_integration_settings().database_url)
        try:
            return await scenario(async_sessionmaker(engine, expire_on_commit=False))
        finally:
            await engine.dispose()
    return asyncio.run(run())


async def closed_shop(session, *, active_driver_ids=()):
    organization = Cooperative(name="Synthetic union register")
    session.add(organization)
    await session.flush()
    operator = await session.get(Operator, LEGACY_OPERATOR_ID)
    operator.operator_type = OperatorType.COOPERATIVE
    operator.cooperative_id = organization.id
    operator.requires_active_membership = True
    members = {}
    for driver_id in active_driver_ids:
        profile = await session.get(DriverProfile, driver_id)
        member = CooperativeMembership(
            cooperative_id=organization.id, user_id=profile.user_id,
            membership_status=CooperativeMembershipStatus.ACTIVE,
            joined_at=datetime.now(UTC) - timedelta(days=1),
        )
        session.add(member)
        await session.flush()
        members[driver_id] = member.id
    await session.flush()
    return organization.id, members


def test_database_constraint_requires_an_organization_for_closed_shop_policy():
    async def prove(sessions):
        with pytest.raises(IntegrityError):
            async with sessions.begin() as session:
                operator = await session.get(Operator, LEGACY_OPERATOR_ID)
                operator.cooperative_id = None
                operator.requires_active_membership = True
                await session.flush()
        async with sessions() as session:
            assert not (await session.get(Operator, LEGACY_OPERATOR_ID)).requires_active_membership
    database(prove)


@pytest.mark.parametrize("state", [
    "active", "pending", "suspended", "ended", "future", "expired",
    "organization-inactive", "foreign-register", "missing", "legacy-null-date",
])
def test_policy_sql_is_correlated_to_the_driver_and_exact_operator_register(state):
    async def prove(sessions):
        await seed_workload_supply(sessions, 2)
        async with sessions.begin() as session:
            drivers = list(await session.scalars(select(DriverProfile).order_by(DriverProfile.id)))
            organization_id, members = await closed_shop(session, active_driver_ids=[drivers[0].id])
            member = await session.get(CooperativeMembership, members[drivers[0].id])
            at = datetime.now(UTC)
            allowed = state in {"active", "legacy-null-date"}
            if state in {"pending", "suspended", "ended"}:
                member.membership_status = CooperativeMembershipStatus(state.upper())
            elif state == "future":
                member.joined_at = at + timedelta(seconds=1)
            elif state == "expired":
                member.ended_at = at
            elif state == "organization-inactive":
                (await session.get(Cooperative, organization_id)).status = CooperativeStatus.INACTIVE
            elif state == "foreign-register":
                other = Cooperative(name="Unrelated member register")
                session.add(other)
                await session.flush()
                member.cooperative_id = other.id
            elif state == "missing":
                await session.delete(member)
            elif state == "legacy-null-date":
                member.joined_at = None
            await session.flush()
            ids = set(await session.scalars(select(DriverProfile.id).where(
                operator_membership_allows(DriverProfile.user_id, LEGACY_OPERATOR_ID, at)
            )))
            assert ids == ({drivers[0].id} if allowed else set())
            assert await driver_membership_is_active(
                session, drivers[0].user_id, LEGACY_OPERATOR_ID, now=at
            ) is allowed
            assert not await driver_membership_is_active(session, drivers[0].user_id, uuid4())
            # Membership never becomes a global account restriction for open operators.
            (await session.get(Operator, LEGACY_OPERATOR_ID)).requires_active_membership = False
            await session.flush()
            assert set(await session.scalars(select(DriverProfile.id).where(
                operator_membership_allows(DriverProfile.user_id, LEGACY_OPERATOR_ID, at)
            ))) == {driver.id for driver in drivers}
    database(prove)


@pytest.mark.parametrize("service_type", [ServiceType.ON_DEMAND, ServiceType.FIXED_ROUTE])
def test_matching_excludes_nonmembers_for_both_immediate_service_types(service_type):
    async def prove(sessions):
        await seed_workload_supply(sessions, 2)
        ride_id = await seed_ride(sessions)
        async with sessions.begin() as session:
            profiles = list(await session.scalars(select(DriverProfile).order_by(DriverProfile.id)))
            member_driver = profiles[1].id
            await closed_shop(session, active_driver_ids=[member_driver])
            if service_type == ServiceType.FIXED_ROUTE:
                route = FixedRoute(city_id=LEGACY_CITY_ID, operator_id=LEGACY_OPERATOR_ID,
                    code='synthetic-member-route', created_by_user_id=profiles[0].user_id)
                session.add(route)
                await session.flush()
                version = FixedRouteVersion(fixed_route_id=route.id, version='membership-v1',
                    localized_name={'en':'Synthetic route'}, effective_from=datetime.now(UTC)-timedelta(days=1),
                    created_by_user_id=profiles[0].user_id)
                session.add(version)
                await session.flush()
                direction = FixedRouteDirection(route_version_id=version.id,
                    direction_code=FixedRouteDirectionCode.OUTBOUND,
                    start_location_name={'en':'Start'}, finish_location_name={'en':'Finish'},
                    start_point=WKTElement('POINT(-7.5898 33.5731)',srid=4326),
                    finish_point=WKTElement('POINT(-7.61 33.58)',srid=4326),
                    static_geometry=WKTElement('LINESTRING(-7.5898 33.5731,-7.61 33.58)',srid=4326))
                session.add(direction)
                await session.flush()
                ride = await session.get(Ride,ride_id)
                ride.fixed_route_direction_id=direction.id
                ride.service_type=service_type
                for profile in profiles:
                    profile.online_service_type = service_type
                    authorization = await session.scalar(select(DriverCityAuthorization).where(
                        DriverCityAuthorization.driver_id == profile.id))
                    session.add(DriverCityAuthorizationService(
                        authorization_id=authorization.id, service_type=service_type))
        async with sessions.begin() as session:
            offer = await dispatch_ride(session, ride_id, require_integration_settings())
            assert offer is not None and offer.driver_id == member_driver
    database(prove)


def test_online_rejects_nonmember_then_accepts_verified_member_and_passengers_stay_open():
    async def seed(sessions):
        credentials = await seed_workload_supply(sessions, 1, loginable=True)
        async with sessions.begin() as session:
            profile = await session.scalar(select(DriverProfile))
            organization_id, _ = await closed_shop(session)
            return credentials[0], profile.id, profile.user_id, organization_id
    credentials, driver_id, user_id, organization_id = database(seed)
    with TestClient(create_app(settings=require_integration_settings())) as client:
        response = client.post('/api/v1/auth/login', json={
            'identifier': credentials['identifier'], 'password': credentials['password']})
        assert response.status_code == 200
        headers = {'Authorization': 'Bearer '+response.json()['access_token']}
        payload = {'city_id': str(LEGACY_CITY_ID), 'service_type': 'ON_DEMAND'}
        response = client.post('/api/v1/drivers/me/availability/online', headers=headers, json=payload)
        assert response.status_code == 409 and 'membership' in response.json()['error']['message']
        async def enroll(sessions):
            async with sessions.begin() as session:
                session.add(CooperativeMembership(
                    cooperative_id=organization_id, user_id=user_id,
                    membership_status=CooperativeMembershipStatus.ACTIVE,
                    joined_at=datetime.now(UTC)-timedelta(days=1)))
        database(enroll)
        assert client.post('/api/v1/drivers/me/availability/online', headers=headers, json=payload).status_code == 200
        token = register_and_login(client, email=f'passenger-{uuid4().hex}@taximobile.invalid',
                                   password='Synthetic-only-password-2026', display_name='Passenger')
        assert token


def test_revocation_after_offering_rejects_acceptance_without_partial_assignment():
    async def prove(sessions):
        await seed_workload_supply(sessions, 1)
        ride_id = await seed_ride(sessions)
        async with sessions.begin() as session:
            driver = await session.scalar(select(DriverProfile))
            driver_id = driver.id
            _, members = await closed_shop(session, active_driver_ids=[driver_id])
            member_id = members[driver_id]
        async with sessions.begin() as session:
            offer = await dispatch_ride(session, ride_id, require_integration_settings())
            offer_id = offer.id
        async with sessions.begin() as session:
            (await session.get(CooperativeMembership, member_id)).membership_status = CooperativeMembershipStatus.SUSPENDED
        async with sessions.begin() as session:
            with pytest.raises(RideOfferUnavailable, match='membership'):
                await accept_offer_atomically(session, offer_id, driver_id)
        async with sessions() as session:
            await assert_no_live_acceptance(session, ride_id, offer_id)
    database(prove)


def test_policy_enabled_after_offer_revalidates_nonmember_before_assignment():
    async def prove(sessions):
        await seed_workload_supply(sessions, 1)
        ride_id = await seed_ride(sessions)
        async with sessions.begin() as session:
            offer = await dispatch_ride(session, ride_id, require_integration_settings())
            offer_id, driver_id = offer.id, offer.driver_id
        async with sessions.begin() as session:
            await closed_shop(session)
        async with sessions.begin() as session:
            with pytest.raises(RideOfferUnavailable, match='membership'):
                await accept_offer_atomically(session, offer_id, driver_id)
        async with sessions() as session:
            await assert_no_live_acceptance(session, ride_id, offer_id)
    database(prove)


@pytest.mark.parametrize('withdrawal_first', [True, False])
def test_membership_withdrawal_serializes_with_actual_acceptance(withdrawal_first):
    async def prove(sessions):
        await seed_workload_supply(sessions, 1)
        ride_id = await seed_ride(sessions)
        async with sessions.begin() as session:
            profile = await session.scalar(select(DriverProfile))
            driver_id = profile.id
            _, members = await closed_shop(session, active_driver_ids=[driver_id])
            member_id = members[driver_id]
        async with sessions.begin() as session:
            offer = await dispatch_ride(session, ride_id, require_integration_settings())
            offer_id = offer.id
        async def acquire(session):
            if withdrawal_first:
                await session.scalar(select(CooperativeMembership).where(
                    CooperativeMembership.id == member_id).with_for_update())
            else:
                await accept_offer_atomically(session, offer_id, driver_id)
        async def prepare(session):
            return await session.get(CooperativeMembership, member_id)  # retain stale ACTIVE projection
        async def first(session):
            if withdrawal_first:
                (await session.get(CooperativeMembership, member_id)).membership_status = CooperativeMembershipStatus.SUSPENDED
        async def second(session, stale):
            if withdrawal_first:
                with pytest.raises(RideOfferUnavailable, match='membership'):
                    await accept_offer_atomically(session, offer_id, driver_id)
            else:
                stale.membership_status = CooperativeMembershipStatus.SUSPENDED
                await session.flush()
        await contended_commands(sessions, acquire_first=acquire, prepare_second=prepare,
                                 first_command=first, second_command=second)
        async with sessions() as session:
            ride = await session.get(Ride, ride_id)
            assert ride.status == (RideStatus.MATCHING if withdrawal_first else RideStatus.ACCEPTED)
            assert (ride.driver_id is None) is withdrawal_first
            assert (await session.get(CooperativeMembership, member_id)).membership_status == CooperativeMembershipStatus.SUSPENDED
    database(prove)


def test_membership_withdrawal_preserves_accepted_trip_completion_and_payment():
    async def prove(sessions):
        await seed_workload_supply(sessions, 1)
        ride_id = await seed_ride(sessions)
        async with sessions.begin() as session:
            profile = await session.scalar(select(DriverProfile)); driver_id = profile.id
            _, members = await closed_shop(session, active_driver_ids=[driver_id])
            member_id = members[driver_id]
            rule = PricingRule(city_id=LEGACY_CITY_ID, operator_id=LEGACY_OPERATOR_ID,
                service_type=ServiceType.ON_DEMAND, booking_type=BookingType.IMMEDIATE,
                name='Synthetic member completion', version='membership-completion',
                model=PricingModel.FIXED, fixed_amount=Decimal('35.00'), currency='MAD',
                status=PricingRuleStatus.ACTIVE, effective_from=datetime.now(UTC)-timedelta(days=1))
            session.add(rule); await session.flush()
            quote = await quote_immediate_ride(session, city_id=LEGACY_CITY_ID,
                operator_id=LEGACY_OPERATOR_ID, tariff_version_id=rule.id,
                operator_fee_policy_version_id=None, at=datetime.now(UTC))
            ride = await session.get(Ride, ride_id)
            ride.quoted_pricing_rule_id=rule.id; ride.quoted_amount=quote.passenger_total_amount
            ride.quoted_currency=quote.currency; session.add(quote.ride_snapshot(ride_id))
        async with sessions.begin() as session:
            offer = await dispatch_ride(session, ride_id, require_integration_settings())
        async with sessions.begin() as session:
            await accept_offer_atomically(session, offer.id, driver_id)
        async with sessions.begin() as session:
            (await session.get(CooperativeMembership, member_id)).membership_status=CooperativeMembershipStatus.ENDED
        for target in [RideStatus.DRIVER_EN_ROUTE,RideStatus.DRIVER_ARRIVED,RideStatus.IN_PROGRESS]:
            async with sessions.begin() as session:
                await transition_assigned_ride(session, await session.get(Ride,ride_id),
                    await session.get(DriverProfile,driver_id),target,
                    (await session.get(DriverProfile,driver_id)).user_id)
        async with sessions.begin() as session:
            profile=await session.get(DriverProfile,driver_id)
            await complete_assigned_ride(session,await session.get(Ride,ride_id),profile,
                profile.user_id,33.58,-7.61)
        async with sessions() as session:
            assert (await session.get(Ride,ride_id)).status==RideStatus.COMPLETED
            payment=await session.scalar(select(Payment).where(Payment.ride_id==ride_id))
            assert payment is not None and payment.amount==Decimal('35.00')
    database(prove)


def test_scheduled_offer_discovery_excludes_nonmembers_and_withdrawn_members():
    async def prove(sessions):
        fixture = await seed_acceptance(sessions, offsets=(0,))
        async with sessions.begin() as session:
            _, members = await closed_shop(session, active_driver_ids=[fixture.driver_ids[0]])
        for withdraw in (False, True):
            async with sessions.begin() as session:
                if withdraw:
                    member = await session.get(CooperativeMembership, members[fixture.driver_ids[0]])
                    member.membership_status = CooperativeMembershipStatus.ENDED
                booking = await scheduling.create_scheduled_booking(
                    session, passenger_id=fixture.passenger_ids[0], now=fixture.now,
                    payload=ScheduledBookingCreateRequest(
                        city_id=LEGACY_CITY_ID,
                        scheduled_for=fixture.now + timedelta(hours=4, minutes=10 if withdraw else 5),
                        pickup={"latitude": 33.5731, "longitude": -7.5898},
                        destination={"latitude": 33.58, "longitude": -7.61},
                        payment_method="CASH",
                    ),
                )
                booking_id = booking.id
            async with sessions() as session:
                offered = list(await session.scalars(select(ScheduledBookingOffer.driver_id).where(
                    ScheduledBookingOffer.booking_id == booking_id)))
                assert offered == ([] if withdraw else [fixture.driver_ids[0]])
    database(prove)


def test_scheduled_commitment_rechecks_membership():
    async def prove(sessions):
        fixture=await seed_acceptance(sessions,offsets=(0,))
        async with sessions.begin() as session:
            _,members=await closed_shop(session,active_driver_ids=[fixture.driver_ids[0]])
        async with sessions.begin() as session:
            with pytest.raises(scheduling.ScheduledOfferUnavailable,match='membership'):
                await accept_scheduled(session,fixture,fixture.booking_ids[0],fixture.driver_ids[1])
        async with sessions.begin() as session:
            (await session.get(CooperativeMembership,members[fixture.driver_ids[0]])).membership_status=CooperativeMembershipStatus.ENDED
        async with sessions.begin() as session:
            with pytest.raises(scheduling.ScheduledOfferUnavailable,match='membership'):
                await accept_scheduled(session,fixture,fixture.booking_ids[0],fixture.driver_ids[0])
        async with sessions() as session:
            assert await session.scalar(select(ScheduledBookingCommitment.id)) is None
    database(prove)


def test_scheduled_handoff_does_not_assign_a_member_withdrawn_after_commitment():
    async def prove(sessions):
        ready=await prepare_handoff_fixture(sessions)
        async with sessions.begin() as session:
            _,members=await closed_shop(session,active_driver_ids=[ready.driver_id])
            (await session.get(CooperativeMembership,members[ready.driver_id])).membership_status=CooperativeMembershipStatus.SUSPENDED
        async with sessions.begin() as session:
            booking=await session.get(ScheduledBooking,ready.booking_id)
            await scheduling.handoff_booking(session,booking,now=ready.now,
                matching_settings=require_integration_settings())
        async with sessions() as session:
            commitment=await session.scalar(select(ScheduledBookingCommitment).where(
                ScheduledBookingCommitment.booking_id==ready.booking_id))
            assert commitment.status.value=='RELEASED'
            assigned=list(await session.scalars(select(Ride).where(Ride.driver_id==ready.driver_id)))
            assert assigned==[]
            assert (await session.get(ScheduledBooking,ready.booking_id)).status!=ScheduledBookingStatus.LIVE_RIDE_CREATED
    database(prove)
