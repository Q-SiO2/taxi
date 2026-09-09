"""Open-loop CLI -> Uvicorn -> PostGIS reconciliation on an isolated database."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import json
from pathlib import Path
import socket
import sys

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
import uvicorn

from taximobile_api.core.rate_limit import PostgresRateLimiter
from taximobile_api.domains.auth.models import User
from taximobile_api.domains.drivers.models import AvailabilityStatus, DriverProfile
from taximobile_api.domains.idempotency.models import IdempotencyRecord
from taximobile_api.domains.markets.constants import LEGACY_CITY_ID, LEGACY_OPERATOR_ID
from taximobile_api.domains.outbox.models import OutboxEvent
from taximobile_api.domains.pricing.models import PricingModel, PricingRule, PricingRuleStatus
from taximobile_api.domains.rides.models import (
    Ride,
    RideEvent,
    RideEventType,
    RideOffer,
    RideOfferStatus,
    RideStatus,
)
from taximobile_api.main import create_app

from test_mvp_lifecycle import require_integration_settings
from workload_fixtures import seed_workload_supply


pytestmark = pytest.mark.integration


def test_open_loop_capacity_cli_reconciles_every_released_arrival():
    settings = replace(require_integration_settings(), process_role="api", log_level="ERROR")

    async def scenario():
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions.begin() as session:
            session.add(PricingRule(
                city_id=LEGACY_CITY_ID,
                operator_id=LEGACY_OPERATOR_ID,
                name="Synthetic open-loop tariff",
                version="open-loop-fixture-v1",
                model=PricingModel.FIXED,
                fixed_amount=Decimal("35.00"),
                currency="MAD",
                status=PricingRuleStatus.ACTIVE,
                effective_from=datetime.now(UTC) - timedelta(minutes=1),
            ))
        await seed_workload_supply(sessions, 2)

        app = create_app(
            settings=settings,
            session_factory=sessions,
            rate_limiter=PostgresRateLimiter(sessions),
        )
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
                sys.executable,
                "-m",
                "taximobile_api.operations.capacity_workload",
                "--base-url",
                f"http://127.0.0.1:{port}",
                "--city-id",
                str(LEGACY_CITY_ID),
                "--pickup",
                "33.5731",
                "-7.5898",
                "--destination",
                "33.58",
                "-7.61",
                "--confirm-synthetic-target",
                "--users",
                "2",
                "--journeys-per-user",
                "2",
                "--arrival-rate-per-second",
                "20",
                "--arrival-lag-budget-ms",
                "60000",
                "--p95-budget-ms",
                "60000",
                "--duration-seconds",
                "40",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            output, diagnostics = await asyncio.wait_for(process.communicate(), timeout=50)
            assert process.returncode == 0, (output + diagnostics).decode()
            assert not diagnostics
            report = json.loads(output)
            assert report["passed"] is True
            assert report["scenario"] == "passenger_request_cancel_open_loop_v1"
            assert report["load_shape"]["model"] == "OPEN_LOOP_CONSTANT_ARRIVAL"
            assert report["load_shape"]["released_arrivals"] == 4
            assert report["completed_journeys"] == 4
            assert report["unresolved_ride_commands"] == 0

            async with sessions() as session:
                rides = list(await session.scalars(select(Ride)))
                assert len(rides) == 4
                assert all(
                    ride.status == RideStatus.CANCELLED and ride.driver_id is None
                    for ride in rides
                )
                assert await session.scalar(select(func.count()).select_from(IdempotencyRecord)) == 8
                assert await session.scalar(select(func.count()).select_from(RideEvent).where(
                    RideEvent.event_type == RideEventType.CANCELLED,
                )) == 4
                assert await session.scalar(select(func.count()).select_from(OutboxEvent).where(
                    OutboxEvent.topic == "ride.cancelled",
                )) == 4
                offers = list(await session.scalars(select(RideOffer)))
                assert len(offers) == 4
                assert all(offer.status == RideOfferStatus.CANCELLED for offer in offers)
                assert all(
                    driver.availability_status == AvailabilityStatus.AVAILABLE
                    for driver in await session.scalars(select(DriverProfile))
                )
                accounts = list(await session.scalars(select(User)))
                assert len(accounts) == 4
                assert all(user.email.endswith("@taximobile.invalid") for user in accounts)
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


def test_four_phase_capacity_plan_cli_reconciles_profile_execution(tmp_path: Path):
    settings = replace(require_integration_settings(), process_role="api", log_level="ERROR")
    profile_path = tmp_path / "capacity-profile.json"
    profile_path.write_text(json.dumps({
        "schema_version": 1,
        "profile_id": "casablanca-synthetic-integration-v1",
        "approval_status": "APPROVED",
        "approval_reference": "LOAD-LOCAL-POSTGIS-001",
        "scenario": "passenger_request_cancel_open_loop_v1",
        "city_id": str(LEGACY_CITY_ID),
        "pickup": [33.5731, -7.5898],
        "destination": [33.58, -7.61],
        "request_timeout_seconds": 5,
        "monitoring_sample_interval_seconds": 5,
        "monitoring_query_timeout_seconds": 2,
        "operational_thresholds": {
            "core_targets_up_min": 1,
            "http_5xx_ratio_max": 0.01,
            "http_p95_latency_seconds_max": 1,
            "worker_seconds_since_success_max": 300,
            "worker_errors_increase_max": 0,
            "outbox_pending_events_max": 100,
            "outbox_oldest_pending_age_seconds_max": 300,
            "outbox_dead_letter_events_max": 0,
            "unhandled_errors_increase_max": 0,
            "log_dropped_lines_increase_max": 0,
            "log_delivery_failures_increase_max": 0,
            "database_metrics_up_min": 1,
            "database_connection_utilization_ratio_max": .7,
            "database_active_connections_max": 70,
            "database_waiting_locks_max": 0,
            "database_deadlocks_increase_max": 0,
            "database_pool_metrics_up_min": 1,
            "database_pool_checked_out_max": 4,
            "database_pool_overflow_max": 0,
            "database_pool_checkout_wait_p95_seconds_max": 0.1,
            "database_pool_checkout_timeouts_increase_max": 0,
        },
        "cooldown_seconds": 0,
        "phases": [
            {
                "phase": phase,
                "users": 1,
                "journeys_per_user": 1,
                "arrival_rate_per_second": rate,
                "duration_seconds": 20,
                "p95_budget_ms": 60000,
                "arrival_lag_budget_ms": 60000,
            }
            for phase, rate in zip(
                ("WARMUP", "STEADY", "BURST", "RECOVERY"),
                (5, 10, 20, 5),
                strict=True,
            )
        ],
    }), encoding="utf-8")

    async def scenario():
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions.begin() as session:
            session.add(PricingRule(
                city_id=LEGACY_CITY_ID,
                operator_id=LEGACY_OPERATOR_ID,
                name="Synthetic capacity-plan tariff",
                version="capacity-plan-fixture-v1",
                model=PricingModel.FIXED,
                fixed_amount=Decimal("35.00"),
                currency="MAD",
                status=PricingRuleStatus.ACTIVE,
                effective_from=datetime.now(UTC) - timedelta(minutes=1),
            ))
        await seed_workload_supply(sessions, 1)

        app = create_app(
            settings=settings,
            session_factory=sessions,
            rate_limiter=PostgresRateLimiter(sessions),
        )
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
                sys.executable,
                "-m",
                "taximobile_api.operations.capacity_plan",
                "--profile",
                str(profile_path),
                "--base-url",
                f"http://127.0.0.1:{port}",
                "--confirm-synthetic-target",
                "--confirm-approved-profile",
                "--confirm-harness-without-monitoring",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            output, diagnostics = await asyncio.wait_for(process.communicate(), timeout=100)
            assert process.returncode == 0, (output + diagnostics).decode()
            assert not diagnostics
            report = json.loads(output)
            assert report["passed"] is True
            assert report["scenario"] == "passenger_capacity_plan_v1"
            assert report["planned_phases"] == ["WARMUP", "STEADY", "BURST", "RECOVERY"]
            assert report["executed_phases"] == 4 and report["unexecuted_phases"] == []
            assert report["planned_arrivals"] == report["released_arrivals"] == 4
            assert report["completed_journeys"] == 4
            assert report["unresolved_ride_commands"] == 0
            assert len(report["profile_sha256"]) == 64
            assert str(LEGACY_CITY_ID).encode() not in output
            assert b"33.5731" not in output and b"-7.5898" not in output

            async with sessions() as session:
                rides = list(await session.scalars(select(Ride)))
                assert len(rides) == 4
                assert all(
                    ride.status == RideStatus.CANCELLED and ride.driver_id is None
                    for ride in rides
                )
                assert await session.scalar(select(func.count()).select_from(IdempotencyRecord)) == 8
                assert await session.scalar(select(func.count()).select_from(RideEvent).where(
                    RideEvent.event_type == RideEventType.CANCELLED,
                )) == 4
                assert await session.scalar(select(func.count()).select_from(OutboxEvent).where(
                    OutboxEvent.topic == "ride.cancelled",
                )) == 4
                offers = list(await session.scalars(select(RideOffer)))
                assert len(offers) == 4
                assert all(offer.status == RideOfferStatus.CANCELLED for offer in offers)
                assert all(
                    driver.availability_status == AvailabilityStatus.AVAILABLE
                    for driver in await session.scalars(select(DriverProfile))
                )
                accounts = list(await session.scalars(select(User)))
                assert len(accounts) == 5
                assert all(user.email.endswith("@taximobile.invalid") for user in accounts)
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
