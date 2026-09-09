"""Actual CLI -> loopback Uvicorn -> PostGIS proof, not an ASGI transport fake."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import json
import socket
import sys

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
import uvicorn

from taximobile_api.core.rate_limit import PostgresRateLimiter
from taximobile_api.domains.auth.models import User
from taximobile_api.domains.idempotency.models import IdempotencyRecord
from taximobile_api.domains.markets.constants import LEGACY_CITY_ID, LEGACY_OPERATOR_ID
from taximobile_api.domains.outbox.models import OutboxEvent
from taximobile_api.domains.pricing.models import PricingModel, PricingRule, PricingRuleStatus
from taximobile_api.domains.rides.models import Ride, RideEvent, RideEventType, RideStatus, RideOffer, RideOfferStatus
from taximobile_api.domains.drivers.models import DriverProfile, AvailabilityStatus
from taximobile_api.main import create_app

from test_mvp_lifecycle import require_integration_settings
from workload_fixtures import seed_workload_supply


pytestmark = pytest.mark.integration


@pytest.mark.parametrize("users,journeys,expected_exit", [(2, 2, 0), (6, 1, 1)])
def test_cli_passenger_workload_on_real_http_and_postgis(users, journeys, expected_exit):
    settings = replace(require_integration_settings(), process_role="api", log_level="ERROR")

    async def scenario():
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        # The migrated legacy fixture has geography and zero-fee policy, but no
        # tariff. Provision only synthetic city configuration before HTTP load;
        # the workload itself never reads or writes SQL or administrative APIs.
        async with sessions.begin() as session:
            session.add(PricingRule(
                city_id=LEGACY_CITY_ID, operator_id=LEGACY_OPERATOR_ID,
                name="Synthetic workload tariff", version="workload-fixture-v1",
                model=PricingModel.FIXED, fixed_amount=Decimal("35.00"), currency="MAD",
                status=PricingRuleStatus.ACTIVE,
                effective_from=datetime.now(UTC) - timedelta(minutes=1),
            ))
        if expected_exit == 0:
            await seed_workload_supply(sessions, users)
        app = create_app(settings=settings, session_factory=sessions,
                         rate_limiter=PostgresRateLimiter(sessions))
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, access_log=False, log_level="critical"))
        server_task = asyncio.create_task(server.serve(sockets=[listener]))
        process = None
        try:
            async with asyncio.timeout(10):
                while not server.started:
                    if server_task.done():
                        await server_task
                        pytest.fail("Synthetic HTTP server stopped before readiness")
                    await asyncio.sleep(.01)
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "taximobile_api.operations.passenger_workload",
                "--base-url", f"http://127.0.0.1:{port}",
                "--city-id", str(LEGACY_CITY_ID),
                "--pickup", "33.5731", "-7.5898", "--destination", "33.58", "-7.61",
                "--confirm-synthetic-target", "--users", str(users),
                "--journeys-per-user", str(journeys), "--interval-seconds", "0",
                "--p95-budget-ms", "60000", "--duration-seconds", "40",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            output, diagnostics = await asyncio.wait_for(process.communicate(), timeout=50)
            assert process.returncode == expected_exit, output.decode()
            assert not diagnostics, "CLI emitted unexpected diagnostics"
            report = json.loads(output)
            assert report["passed"] is (expected_exit == 0)
            assert report["unresolved_ride_commands"] == 0
            async with sessions() as session:
                if expected_exit == 0:
                    assert report["completed_journeys"] == users * journeys
                    assert report["failures"] == {}
                    rides = list(await session.scalars(select(Ride)))
                    assert len(rides) == 4
                    assert all(ride.status == RideStatus.CANCELLED and ride.driver_id is None for ride in rides)
                    assert await session.scalar(select(func.count()).select_from(IdempotencyRecord)) == 8
                    assert await session.scalar(select(func.count()).select_from(RideEvent).where(
                        RideEvent.event_type == RideEventType.CANCELLED)) == 4
                    assert await session.scalar(select(func.count()).select_from(OutboxEvent).where(
                        OutboxEvent.topic == "ride.cancelled")) == 4
                    offers = list(await session.scalars(select(RideOffer)))
                    assert len(offers) == 4 and all(offer.status == RideOfferStatus.CANCELLED for offer in offers)
                    assert all(driver.availability_status == AvailabilityStatus.AVAILABLE
                               for driver in await session.scalars(select(DriverProfile)))
                else:
                    assert report["started_journeys"] == 0
                    assert report["failures"] == {"register:http_429": 1}
                    assert await session.scalar(select(func.count()).select_from(Ride)) == 0
                accounts = list(await session.scalars(select(User)))
                assert len(accounts) == (4 if expected_exit == 0 else 5)
                assert all(user.email.endswith("@taximobile.invalid") and user.phone_number is None
                           for user in accounts)
                assert all(user.email.encode() not in output for user in accounts)
        finally:
            if process is not None and process.returncode is None:
                process.kill()
                await process.wait()
            server.should_exit = True
            try:
                await asyncio.wait_for(server_task, timeout=10)
            finally:
                listener.close()
                await engine.dispose()

    asyncio.run(scenario())
