"""Real database/API error mapping and atomic scheduled-acceptance rollback."""

import asyncio
from dataclasses import replace
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from taximobile_api.core.rate_limit import PostgresRateLimiter
from taximobile_api.domains.drivers.models import DriverProfile
from taximobile_api.domains.scheduled_bookings import service as scheduling_service
from taximobile_api.domains.scheduled_bookings.models import ScheduledBookingCommitment
from taximobile_api.main import create_app

from scheduled_acceptance_fixtures import seed_acceptance
from test_mvp_lifecycle import require_integration_settings
from test_scheduled_acceptance_concurrency import accept, assert_durable


pytestmark = pytest.mark.integration


@pytest.mark.parametrize("fault", ["overlap", "foreign-key", "after-outbox", "adjacent"])
def test_acceptance_distinguishes_expected_conflict_from_internal_integrity_error(monkeypatch, fault):
    async def prove():
        settings = replace(require_integration_settings(), process_role="api", log_level="ERROR")
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            fixture = await seed_acceptance(sessions, offsets=(0, 90 if fault == "overlap" else 150))
            booking_a, booking_b = fixture.booking_ids
            driver_id = fixture.driver_ids[0]
            async with sessions.begin() as session:
                await accept(session, fixture, booking_a, driver_id)
                user_id = str((await session.get(DriverProfile, driver_id)).user_id)
            account = next(c for c in fixture.credentials if c["user_id"] == user_id)
            app = create_app(settings=settings, session_factory=sessions, rate_limiter=PostgresRateLimiter(sessions))
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app, raise_app_exceptions=False),
                                         base_url="http://testserver", trust_env=False) as client:
                login = await client.post("/api/v1/auth/login", json={
                    "identifier": account["identifier"], "password": account["password"],
                })
                assert login.status_code == 200
                original_flush = AsyncSession.flush
                original_enqueue = scheduling_service.enqueue
                failures = []
                flushed_delivery = []

                async def inject(session, *args, **kwargs):
                    pending = [row for row in session.new if isinstance(row, ScheduledBookingCommitment)]
                    if pending and fault == "foreign-key":
                        # Deliberately corrupt only a new synthetic row. A FK
                        # failure must not be presented as the driver's overlap.
                        pending[0].vehicle_id = uuid4()
                    try:
                        return await original_flush(session, *args, **kwargs)
                    except IntegrityError as error:
                        failures.append(getattr(error.orig, "sqlstate", None))
                        raise

                async def fail_after_outbox(session, *args, **kwargs):
                    await original_enqueue(session, *args, **kwargs)
                    await session.flush()  # Prove rollback after all side effects reached SQL.
                    flushed_delivery.append(True)
                    raise RuntimeError("private synthetic post-flush failure")

                with monkeypatch.context() as patch:
                    patch.setattr(AsyncSession, "flush", inject)
                    if fault == "after-outbox":
                        patch.setattr(scheduling_service, "enqueue", fail_after_outbox)
                    response = await client.post(
                        f"/api/v1/scheduled-offers/{fixture.offer_ids[booking_b, driver_id]}/accept",
                        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
                    )
                assert failures == ({"overlap": ["23P01"], "foreign-key": ["23503"]}.get(fault, []))
                assert flushed_delivery == ([True] if fault == "after-outbox" else [])
                if fault == "overlap":
                    assert response.status_code == 409
                    assert response.json()["error"]["message"] == "This trip overlaps another accepted scheduled commitment."
                elif fault != "adjacent":
                    assert response.status_code == 500
                    assert response.json()["error"] == {
                        "code": "INTERNAL_ERROR", "message": "An unexpected error occurred.", "details": {},
                    }
                else:
                    assert response.status_code == 200
                    assert response.json()["booking_id"] == str(booking_b)
                    # Acceptance is not a replay-success contract. A duplicate
                    # must conflict and leave the original durable facts intact.
                    duplicate = await client.post(
                        f"/api/v1/scheduled-offers/{fixture.offer_ids[booking_b, driver_id]}/accept",
                        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
                    )
                    assert duplicate.status_code == 409
                for private in ("INSERT", "private synthetic", account["password"], account["identifier"], login.json()["access_token"]):
                    assert private not in response.text
            winners = [(booking_a, driver_id)]
            if fault == "adjacent":
                winners.append((booking_b, driver_id))
            await assert_durable(sessions, fixture, winners)
        finally:
            await engine.dispose()
    asyncio.run(prove())
