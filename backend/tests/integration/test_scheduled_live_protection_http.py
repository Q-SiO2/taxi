"""Authenticated API boundaries for scheduled/live cross-domain conflicts."""

import asyncio
from dataclasses import replace

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from scheduled_acceptance_fixtures import seed_acceptance
from test_mvp_lifecycle import require_integration_settings
from test_scheduled_acceptance_concurrency import accept
from test_scheduled_live_protection import assert_no_live_acceptance, live_work, make_current
from taximobile_api.core.rate_limit import PostgresRateLimiter
from taximobile_api.domains.drivers.models import DriverProfile
from taximobile_api.domains.rides.models import Ride, RideStatus
from taximobile_api.domains.rides.service import accept_offer_atomically
from taximobile_api.domains.scheduled_bookings.models import ScheduledBooking, ScheduledBookingCommitment
from taximobile_api.main import create_app


pytestmark = pytest.mark.integration


async def driver_headers(client, sessions, fixture, driver_id):
    async with sessions() as session:
        user_id = str((await session.get(DriverProfile, driver_id)).user_id)
    account = next(row for row in fixture.credentials if row["user_id"] == user_id)
    response = await client.post("/api/v1/auth/login", json={
        "identifier": account["identifier"], "password": account["password"],
        "device_label": "synthetic-protection",
    })
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}, account


@pytest.mark.parametrize("winner", ["scheduled", "live"])
def test_authenticated_loser_gets_authoritative_cross_domain_conflict(winner):
    async def prove():
        settings = replace(require_integration_settings(), process_role="api", log_level="ERROR")
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            fixture = await seed_acceptance(sessions, offsets=(0,))
            booking_id, driver_id = fixture.booking_ids[0], fixture.driver_ids[0]
            async with sessions.begin() as session:
                (await session.get(ScheduledBooking, booking_id)).scheduled_for = fixture.now
            ride_id, offer_id = await live_work(sessions, fixture, driver_id=driver_id, offer=True)
            async with sessions.begin() as session:
                if winner == "scheduled":
                    await accept(session, fixture, booking_id, driver_id)
                else:
                    await accept_offer_atomically(session, offer_id, driver_id)

            app = create_app(settings=settings, session_factory=sessions,
                             rate_limiter=PostgresRateLimiter(sessions))
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app, raise_app_exceptions=False),
                                         base_url="http://testserver", trust_env=False) as client:
                headers, account = await driver_headers(client, sessions, fixture, driver_id)
                if winner == "scheduled":
                    response = await client.post(f"/api/v1/ride-offers/{offer_id}/accept", headers=headers)
                    # Live-offer conflicts deliberately share one race-safe
                    # public message; the client restores offers/commitments.
                    expected = "This ride offer is no longer available."
                else:
                    response = await client.post(
                        f"/api/v1/scheduled-offers/{fixture.offer_ids[booking_id, driver_id]}/accept",
                        headers=headers,
                    )
                    expected = "Driver already has an active ride during this protected window."
                assert response.status_code == 409
                assert response.json()["error"] == {
                    "code": "REQUEST_REJECTED", "message": expected, "details": {},
                }
                for private in (account["password"], account["identifier"], headers["Authorization"]):
                    assert private not in response.text

            async with sessions() as session:
                booking = await session.get(ScheduledBooking, booking_id)
                ride = await session.get(Ride, ride_id)
                commitments = (
                    1
                    if booking.current_commitment_id is not None
                    and await session.get(ScheduledBookingCommitment, booking.current_commitment_id) is not None
                    else 0
                )
                if winner == "scheduled":
                    assert booking.status.value == "DRIVER_COMMITTED" and commitments == 1
                    await assert_no_live_acceptance(session, ride_id, offer_id)
                else:
                    assert ride.status == RideStatus.ACCEPTED
                    assert booking.status.value == "OFFERING" and booking.current_commitment_id is None
                    assert commitments == 0
        finally:
            await engine.dispose()
    asyncio.run(prove())


def test_authenticated_immediate_acceptance_remains_allowed_outside_window():
    async def prove():
        settings = replace(require_integration_settings(), process_role="api", log_level="ERROR")
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            fixture = await seed_acceptance(sessions, offsets=(0,))
            booking_id, driver_id = fixture.booking_ids[0], fixture.driver_ids[0]
            async with sessions.begin() as session:
                await accept(session, fixture, booking_id, driver_id)  # Window starts in 3.5 hours.
            ride_id, offer_id = await live_work(sessions, fixture, driver_id=driver_id, offer=True)
            app = create_app(settings=settings, session_factory=sessions,
                             rate_limiter=PostgresRateLimiter(sessions))
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app, raise_app_exceptions=False),
                                         base_url="http://testserver", trust_env=False) as client:
                headers, _ = await driver_headers(client, sessions, fixture, driver_id)
                response = await client.post(f"/api/v1/ride-offers/{offer_id}/accept", headers=headers)
                assert response.status_code == 200
                assert response.json()["ride_id"] == str(ride_id)
            async with sessions() as session:
                assert (await session.get(Ride, ride_id)).status == RideStatus.ACCEPTED
                assert (await session.get(ScheduledBooking, booking_id)).status.value == "DRIVER_COMMITTED"
        finally:
            await engine.dispose()
    asyncio.run(prove())
