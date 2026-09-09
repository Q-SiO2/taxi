"""Real CLI/socket/PostGIS cash journeys, including errors after durable commit."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import json
from os import environ
import socket
import sys

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.responses import JSONResponse
import uvicorn

from taximobile_api.core.rate_limit import PostgresRateLimiter
from taximobile_api.domains.drivers.models import DriverProfile, AvailabilityStatus
from taximobile_api.domains.markets.constants import LEGACY_CITY_ID, LEGACY_OPERATOR_ID
from taximobile_api.domains.payments.models import Payment, PaymentStatus, DriverEarning
from taximobile_api.domains.pricing.models import PricingModel, PricingRule, PricingRuleStatus, FareRecord, RideFinancialSnapshot
from taximobile_api.domains.pricing.models import OperatorFeePolicy, BookingType, OperatorFeeCalculationMode, OperatorFeeFundingMode
from taximobile_api.domains.pricing.service import calculate_financial_quote
from taximobile_api.domains.rides.router import fare_economics_response, quote_economics_response
from taximobile_api.domains.rides.models import Ride, RideStatus, RideOffer, RideOfferStatus
from taximobile_api.main import create_app

from test_mvp_lifecycle import require_integration_settings
from workload_fixtures import seed_workload_supply


pytestmark = pytest.mark.integration


@pytest.mark.parametrize("fault,fee_mode", [(None, "zero"), (None, "flat_driver"), (None, "percentage_passenger"), ("complete", "zero"), ("settle", "zero")])
def test_cash_cli_durable_money_and_post_commit_failure(fault, fee_mode):
    settings = replace(require_integration_settings(), process_role="api", log_level="ERROR")
    users, journeys = (2, 2) if fault is None else (1, 1)
    expected_total = Decimal("38.50") if fee_mode == "percentage_passenger" else Decimal("35.00")

    async def scenario():
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        credentials = await seed_workload_supply(sessions, users, loginable=True)
        async with sessions.begin() as session:
            # Synthetic fee variants exercise existing policy modes; no deployed
            # tariff or production policy is changed by this fixture.
            policy = await session.scalar(select(OperatorFeePolicy))
            if fee_mode == "flat_driver":
                policy.calculation_mode = OperatorFeeCalculationMode.FLAT_PER_COMPLETED_BOOKING
                policy.funding_mode = OperatorFeeFundingMode.DRIVER_SETTLEMENT_DEDUCTION
                policy.flat_amount, policy.percentage_rate = Decimal("5.00"), None
            elif fee_mode == "percentage_passenger":
                policy.calculation_mode = OperatorFeeCalculationMode.PERCENTAGE_OF_TRANSPORT_FARE
                policy.funding_mode = OperatorFeeFundingMode.PASSENGER_SURCHARGE
                policy.percentage_rate, policy.flat_amount = Decimal("10.00"), None
            session.add(PricingRule(
                city_id=LEGACY_CITY_ID, operator_id=LEGACY_OPERATOR_ID,
                name="Synthetic cash tariff", version="cash-workload-fixture-v1",
                model=PricingModel.FIXED, fixed_amount=Decimal("35.00"), currency="MAD",
                status=PricingRuleStatus.ACTIVE, effective_from=datetime.now(UTC) - timedelta(minutes=1),
            ))
        app = create_app(settings=settings, session_factory=sessions, rate_limiter=PostgresRateLimiter(sessions))
        injected = []
        if fault:
            @app.middleware("http")
            async def fail_after_commit(request, call_next):
                response = await call_next(request)
                if request.url.path.endswith(f"/{fault}") and response.status_code == 200 and not injected:
                    # The handler's transaction has already committed. This models
                    # a non-2xx proxy response, not a TCP reset or an aborted write.
                    injected.append(True)
                    return JSONResponse({"detail": "private synthetic gateway detail"}, status_code=503)
                return response
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        origin = f"http://127.0.0.1:{listener.getsockname()[1]}"
        server = uvicorn.Server(uvicorn.Config(app, access_log=False, log_level="critical"))
        server_task = asyncio.create_task(server.serve(sockets=[listener]))
        process = None
        try:
            async with asyncio.timeout(10):
                while not server.started:
                    if server_task.done():
                        await server_task
                        pytest.fail("Cash workload HTTP server stopped before readiness")
                    await asyncio.sleep(.01)
            driver_secrets = []
            async with httpx.AsyncClient(base_url=origin, trust_env=False) as client:
                for account in credentials:
                    response = await client.post("/api/v1/auth/login", json={
                        "identifier": account["identifier"], "password": account["password"],
                        "device_label": "synthetic-cash-driver",
                    })
                    assert response.status_code == 200
                    driver_secrets.append({"user_id": account["user_id"], "access_token": response.json()["access_token"]})
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "taximobile_api.operations.cash_workload",
                "--base-url", origin, "--city-id", str(LEGACY_CITY_ID),
                "--pickup", "33.5731", "-7.5898", "--destination", "33.58", "-7.61",
                "--confirm-synthetic-target", "--confirm-synthetic-cash",
                "--users", str(users), "--journeys-per-user", str(journeys),
                "--interval-seconds", "0", "--duration-seconds", "40", "--p95-budget-ms", "60000",
                env={**environ, "TAXIMOBILE_WORKLOAD_DRIVERS_JSON": json.dumps(driver_secrets)},
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            output, diagnostics = await asyncio.wait_for(process.communicate(), timeout=50)
            if fault is None:
                async with sessions() as observer:
                    fare = await observer.scalar(select(FareRecord))
                    if fare is not None:
                        rule = await observer.get(PricingRule, fare.pricing_rule_id)
                        policy = await observer.scalar(select(OperatorFeePolicy))
                        quote = calculate_financial_quote(rule, policy, booking_type=BookingType.IMMEDIATE)
                        assert fare_economics_response(fare) == quote_economics_response(quote)
            assert process.returncode == (0 if fault is None else 1), output.decode()
            assert not diagnostics, "Unexpected CLI diagnostics"
            report = json.loads(output)
            assert report["passed"] is (fault is None)
            assert report["completed_journeys"] == (4 if fault is None else 0)
            assert report["unresolved_ride_commands"] == (0 if fault is None else 1)
            assert report["drivers_not_confirmed_offline"] == 0
            assert "private synthetic gateway detail" not in output.decode()
            for account, secret in zip(credentials, driver_secrets):
                assert account["password"].encode() not in output
                assert account["identifier"].encode() not in output
                assert secret["access_token"].encode() not in output
            async with sessions() as session:
                rides = list(await session.scalars(select(Ride)))
                offers = list(await session.scalars(select(RideOffer)))
                payments = list(await session.scalars(select(Payment)))
                fares = list(await session.scalars(select(FareRecord)))
                earnings = list(await session.scalars(select(DriverEarning)))
                snapshots = list(await session.scalars(select(RideFinancialSnapshot)))
                expected = 4 if fault is None else 1
                assert len(rides) == len(offers) == len(payments) == len(fares) == len(snapshots) == expected
                assert all(ride.status == RideStatus.COMPLETED for ride in rides)
                assert all(offer.status == RideOfferStatus.ACCEPTED for offer in offers)
                assert all(payment.status == (PaymentStatus.PENDING if fault == "complete" else PaymentStatus.COMPLETED)
                           and payment.amount == expected_total for payment in payments)
                assert len(earnings) == (0 if fault == "complete" else expected)
                assert sum(earning.net_amount + earning.operator_allocation_amount for earning in earnings) == expected_total * len(earnings)
                if fee_mode == "flat_driver":
                    assert all(e.net_amount == Decimal("30.00") and e.operator_allocation_amount == Decimal("5.00") for e in earnings)
                elif fee_mode == "percentage_passenger":
                    assert all(e.net_amount == Decimal("35.00") and e.operator_allocation_amount == Decimal("3.50") for e in earnings)
                assert len({earning.payment_id for earning in earnings}) == len(earnings)
                assert all(driver.availability_status == AvailabilityStatus.OFFLINE
                           for driver in await session.scalars(select(DriverProfile)))
                assert bool(injected) is (fault is not None)
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
