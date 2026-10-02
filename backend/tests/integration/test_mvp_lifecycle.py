"""PostGIS-backed proof of the complete first-release ride/payment lifecycle.

This test is deliberately opt-in because it mutates the explicitly configured
test database. CI provisions an isolated PostGIS service and applies migrations
before enabling it. It never falls back to an implicit or production database.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from os import getenv
from time import sleep
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from taximobile_api.core.config import Settings
from taximobile_api.core.live_events import PostgresLiveEventListener, PostgresLiveEventPublisher
from taximobile_api.core.notification_policy import LIVE_EVENT_TYPES
from taximobile_api.core.rate_limit import PostgresRateLimiter
from taximobile_api.core.realtime import EventHub
from taximobile_api.domains.auth.bootstrap import bootstrap_initial_administrator
from taximobile_api.domains.administration.bootstrap import bootstrap_initial_platform_grant
from taximobile_api.domains.analytics.service import refresh_operational_analytics
from taximobile_api.domains.case_retention.models import CaseRetentionAction
from taximobile_api.domains.cooperatives.models import (
    Cooperative,
    CooperativeMembership,
    CooperativeMembershipStatus,
)
from taximobile_api.domains.drivers.models import DriverCredential, CredentialVerificationStatus
from taximobile_api.domains.notifications.models import DeviceToken
from taximobile_api.domains.safety.models import SafetyReport, SafetyReportNote
from taximobile_api.domains.outbox.metrics import collect_outbox_metrics
from taximobile_api.domains.outbox.models import OutboxEvent
from taximobile_api.domains.markets.constants import LEGACY_CITY_ID, LEGACY_OPERATOR_ID
from taximobile_api.main import create_app
from taximobile_api.operations.outbox_replay import ReplayRefused, replay_dead_letters, validate_request
from taximobile_api.worker import create_worker_app
from taximobile_api.workers.credentials import CredentialLifecycleProcessor
from taximobile_api.workers.case_retention import CaseRetentionProcessor


pytestmark = pytest.mark.integration

ADMIN_PASSWORD = "Integration-admin-password-2026"
DRIVER_PASSWORD = "Integration-driver-password-2026"
PASSENGER_PASSWORD = "Integration-passenger-password-2026"


def require_integration_settings() -> Settings:
    if getenv("TAXIMOBILE_RUN_INTEGRATION") != "1":
        pytest.skip("Set TAXIMOBILE_RUN_INTEGRATION=1 with an isolated migrated PostGIS database.")
    settings = Settings.from_environment()
    if settings.environment != "test" or "taximobile_ci" not in settings.database_url:
        pytest.fail("Integration tests require TAXIMOBILE_ENV=test and an isolated taximobile_ci database.")
    return settings


async def seed_administrator(settings: Settings, email: str) -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            async with session.begin():
                await bootstrap_initial_administrator(session, email=email, password=ADMIN_PASSWORD)
                await bootstrap_initial_platform_grant(
                    session,
                    admin_email=email,
                    market_code="MA",
                )
    finally:
        await engine.dispose()


async def device_token_state(
    settings: Settings,
    token: str,
) -> list[tuple[UUID, UUID, UUID | None, datetime | None]]:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            devices = list(await session.scalars(select(DeviceToken).where(DeviceToken.token == token)))
            return [
                (device.id, device.user_id, device.session_id, device.revoked_at)
                for device in devices
            ]
    finally:
        await engine.dispose()


async def refresh_and_read_operational_metric_codes(settings: Settings) -> set[str]:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            async with session.begin():
                await refresh_operational_analytics(session)
        async with sessions() as session:
            return set(
                await session.scalars(
                    text(
                        "SELECT DISTINCT metric_code "
                        "FROM operational_metric_facts_hourly_v1"
                    )
                )
            )
    finally:
        await engine.dispose()


async def seed_cooperative_membership(settings: Settings, user_id: str, suffix: str) -> tuple[str, datetime]:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    joined_at = datetime.now(UTC)
    try:
        async with sessions() as session:
            async with session.begin():
                cooperative = Cooperative(
                    name="Integration Taxi Cooperative",
                    legal_identifier=f"integration-cooperative-{suffix}",
                )
                session.add(cooperative)
                await session.flush()
                session.add(
                    CooperativeMembership(
                        cooperative_id=cooperative.id,
                        user_id=UUID(user_id),
                        membership_status=CooperativeMembershipStatus.ACTIVE,
                        joined_at=joined_at,
                        membership_number=f"MEMBER-{suffix[:8].upper()}",
                    )
                )
            return str(cooperative.id), joined_at
    finally:
        await engine.dispose()


async def seed_driver_credential(
    settings: Settings,
    driver_profile_id: str,
    credential_type: str,
) -> tuple[str, datetime, datetime]:
    """Insert a reviewed fact without inventing a public document-upload API."""

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    issued_at = datetime.now(UTC) - timedelta(days=365)
    expires_at = datetime.now(UTC) + timedelta(days=365)
    credential = DriverCredential(
        driver_id=UUID(driver_profile_id),
        credential_type=credential_type,
        verification_status=CredentialVerificationStatus.VERIFIED,
        issued_at=issued_at,
        expires_at=expires_at,
    )
    try:
        async with sessions() as session:
            async with session.begin():
                session.add(credential)
                await session.flush()
            return str(credential.id), issued_at, expires_at
    finally:
        await engine.dispose()


async def set_driver_credential_expiry(
    settings: Settings,
    credential_id: str,
    expires_at: datetime,
) -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            async with session.begin():
                credential = await session.get(DriverCredential, UUID(credential_id))
                assert credential is not None
                credential.expires_at = expires_at
    finally:
        await engine.dispose()


async def process_credential_lifecycle(settings: Settings) -> int:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        return await CredentialLifecycleProcessor(sessions, settings).process_once()
    finally:
        await engine.dispose()


async def expire_and_process_safety_retention(
    settings: Settings,
    report_id: str,
) -> tuple[int, SafetyReport, CaseRetentionAction, int]:
    """Force one closed report due and return its minimized shell and evidence."""

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    report_uuid = UUID(report_id)
    try:
        async with sessions() as session:
            async with session.begin():
                note_count = await session.scalar(
                    select(func.count()).select_from(SafetyReportNote).where(
                        SafetyReportNote.report_id == report_uuid
                    )
                )
                await session.execute(
                    update(SafetyReport)
                    .where(SafetyReport.id == report_uuid)
                    .values(retention_until=datetime.now(UTC) - timedelta(seconds=1))
                )

        processed = await CaseRetentionProcessor(
            sessions,
            batch_size=settings.case_retention_batch_size,
        ).process_once()

        async with sessions() as session:
            report = await session.get(SafetyReport, report_uuid)
            action = await session.scalar(
                select(CaseRetentionAction).where(
                    CaseRetentionAction.safety_report_id == report_uuid
                )
            )
            remaining_notes = await session.scalar(
                select(func.count()).select_from(SafetyReportNote).where(
                    SafetyReportNote.report_id == report_uuid
                )
            )
            assert report is not None
            assert action is not None
            assert remaining_notes == 0
            return processed, report, action, int(note_count or 0)
    finally:
        await engine.dispose()


async def prove_shared_rate_limit(settings: Settings, key: str) -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        first_instance = PostgresRateLimiter(sessions)
        second_instance = PostgresRateLimiter(sessions)
        assert await first_instance.allow(key, limit=2, window_seconds=60)
        assert await second_instance.allow(key, limit=2, window_seconds=60)
        assert not await first_instance.allow(key, limit=2, window_seconds=60)
    finally:
        await engine.dispose()


async def prove_shared_live_event_fanout(settings: Settings) -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    from taximobile_api.domains.auth.security import VerifiedAccessToken

    async def permit_transport_fixture(_):
        # This test proves PostgreSQL fanout, not mobile authentication.
        return True

    hub = EventHub(permit_transport_fixture)
    user_id = uuid4()
    ride_id = uuid4()

    class RecordingSocket:
        def __init__(self) -> None:
            self.message = None
            self.received = asyncio.Event()

        async def accept(self) -> None:
            return None

        async def send_json(self, payload) -> None:
            self.message = payload
            self.received.set()

        async def close(self, *, code) -> None:
            pass

    socket = RecordingSocket()
    listener = PostgresLiveEventListener(settings.database_url, hub, reconnect_seconds=0.1)
    listener_task = asyncio.create_task(listener.run())
    try:
        await hub.connect(VerifiedAccessToken(user_id, uuid4(), datetime.now(UTC) + timedelta(minutes=10)), socket)
        await listener.wait_until_ready(5)
        for event_type in sorted(LIVE_EVENT_TYPES):
            socket.received.clear()
            await PostgresLiveEventPublisher(sessions).publish_ride_refresh(
                user_id, ride_id, event_type
            )
            await asyncio.wait_for(socket.received.wait(), timeout=5)
            assert socket.message == {"type": event_type, "ride_id": str(ride_id)}
    finally:
        listener_task.cancel()
        with suppress(asyncio.CancelledError):
            await listener_task
        await hub.aclose()
        await engine.dispose()


def authorization(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def idempotency(token: str) -> dict[str, str]:
    return {**authorization(token), "Idempotency-Key": str(uuid4())}


def expect(response, status_code: int):
    assert response.status_code == status_code, response.text
    return response.json()


def register_and_login(client: TestClient, *, email: str, password: str, display_name: str) -> str:
    expect(
        client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "display_name": display_name},
        ),
        201,
    )
    return expect(
        client.post(
            "/api/v1/auth/login",
            json={"identifier": email, "password": password, "device_label": "integration test"},
        ),
        200,
    )["access_token"]


def test_complete_passenger_driver_payment_lifecycle() -> None:
    settings = replace(
        require_integration_settings(),
        manual_transfer_enabled=True,
        manual_transfer_recipient_name="TaxiMobile Integration Recipient",
        manual_transfer_bank_account="TEST-BANK-ACCOUNT",
        manual_transfer_wallet_id="TEST-WALLET-001",
    )
    suffix = uuid4().hex
    admin_email = "integration-admin@example.test"
    driver_email = f"driver-{suffix}@example.test"
    passenger_email = f"passenger-{suffix}@example.test"
    asyncio.run(seed_administrator(settings, admin_email))

    with TestClient(create_app(settings=settings)) as client:
        admin_token = expect(
            client.post(
                "/api/v1/auth/login",
                json={"identifier": admin_email, "password": ADMIN_PASSWORD, "device_label": "integration admin"},
            ),
            200,
        )["access_token"]
        operations_token = expect(
            client.post(
                "/api/v1/operations/auth/login",
                json={
                    "identifier": admin_email,
                    "password": ADMIN_PASSWORD,
                    "device_label": "integration operations admin",
                },
            ),
            200,
        )["access_token"]
        admin_id = expect(client.get("/api/v1/me", headers=authorization(admin_token)), 200)["id"]
        driver_token = register_and_login(
            client, email=driver_email, password=DRIVER_PASSWORD, display_name="Integration Driver"
        )
        passenger_token = register_and_login(
            client, email=passenger_email, password=PASSENGER_PASSWORD, display_name="Integration Passenger"
        )

        passenger_id = expect(client.get("/api/v1/me", headers=authorization(passenger_token)), 200)["id"]
        driver_id = expect(client.get("/api/v1/me", headers=authorization(driver_token)), 200)["id"]
        assert client.get(
            "/api/v1/cooperative/membership",
            headers=authorization(passenger_token),
        ).status_code == 404
        cooperative_id, joined_at = asyncio.run(
            seed_cooperative_membership(settings, driver_id, suffix),
        )
        membership = expect(
            client.get("/api/v1/cooperative/membership", headers=authorization(driver_token)),
            200,
        )
        assert membership == {
            "cooperative_id": cooperative_id,
            "cooperative_name": "Integration Taxi Cooperative",
            "status": "ACTIVE",
            "joined_at": joined_at.isoformat().replace("+00:00", "Z"),
            "membership_number": f"MEMBER-{suffix[:8].upper()}",
        }
        provider_token = f"integration-fid-{suffix}"
        registration_payload = {
            "platform": "ANDROID",
            "registration_kind": "FIREBASE_INSTALLATION_ID",
            "registration_id": provider_token,
        }
        passenger_device = expect(
            client.post(
                "/api/v1/devices",
                headers=authorization(passenger_token),
                json=registration_payload,
            ),
            201,
        )
        passenger_registration = asyncio.run(device_token_state(settings, provider_token))
        assert len(passenger_registration) == 1
        assert passenger_registration[0][0] == UUID(passenger_device["id"])
        assert passenger_registration[0][1] == UUID(passenger_id)
        assert passenger_registration[0][2] is not None
        assert passenger_registration[0][3] is None
        driver_device = expect(
            client.post(
                "/api/v1/devices",
                headers=authorization(driver_token),
                json=registration_payload,
            ),
            201,
        )
        assert driver_device["id"] == passenger_device["id"]
        driver_registration = asyncio.run(device_token_state(settings, provider_token))
        assert len(driver_registration) == 1
        assert driver_registration[0][0] == UUID(driver_device["id"])
        assert driver_registration[0][1] == UUID(driver_id)
        original_driver_session_id = driver_registration[0][2]
        assert original_driver_session_id is not None
        assert driver_registration[0][3] is None

        # The former owner cannot revoke a token after its atomic transfer.
        assert client.request(
            "DELETE",
            "/api/v1/devices",
            headers=authorization(passenger_token),
            json=registration_payload,
        ).status_code == 204
        assert asyncio.run(device_token_state(settings, provider_token))[0][3] is None

        # A newer session for the same account claims the registration. The old
        # session remains valid for normal account use but cannot revoke it.
        newer_driver_token = expect(
            client.post(
                "/api/v1/auth/login",
                json={
                    "identifier": driver_email,
                    "password": DRIVER_PASSWORD,
                    "device_label": "integration push replacement",
                },
            ),
            200,
        )["access_token"]
        expect(
            client.post(
                "/api/v1/devices",
                headers=authorization(newer_driver_token),
                json=registration_payload,
            ),
            201,
        )
        transferred_registration = asyncio.run(device_token_state(settings, provider_token))[0]
        assert transferred_registration[2] != original_driver_session_id

        assert client.request(
            "DELETE",
            "/api/v1/devices",
            headers=authorization(driver_token),
            json=registration_payload,
        ).status_code == 204
        assert asyncio.run(device_token_state(settings, provider_token))[0][3] is None

        assert client.request(
            "DELETE",
            "/api/v1/devices",
            headers=authorization(newer_driver_token),
            json=registration_payload,
        ).status_code == 204
        owner_state = asyncio.run(device_token_state(settings, provider_token))
        assert len(owner_state) == 1
        assert str(owner_state[0][1]) == driver_id
        assert owner_state[0][3] is not None

        # Successful auth logout is a second authority-side cleanup path.
        expect(
            client.post(
                "/api/v1/devices",
                headers=authorization(newer_driver_token),
                json=registration_payload,
            ),
            201,
        )
        expect(client.post("/api/v1/auth/logout", headers=authorization(newer_driver_token)), 200)
        assert asyncio.run(device_token_state(settings, provider_token))[0][3] is not None

        driver = expect(
            client.post(
                "/api/v1/drivers/apply",
                headers=authorization(driver_token),
                json={"display_name": "Integration Driver"},
            ),
            201,
        )

        other_driver_token = register_and_login(
            client,
            email=f"other-driver-{suffix}@example.test",
            password=DRIVER_PASSWORD,
            display_name="Other Integration Driver",
        )
        other_driver = expect(
            client.post(
                "/api/v1/drivers/apply",
                headers=authorization(other_driver_token),
                json={"display_name": "Other Integration Driver"},
            ),
            201,
        )
        credential_id, issued_at, expires_at = asyncio.run(
            seed_driver_credential(settings, driver["id"], "DRIVER_LICENSE")
        )
        other_credential_id, _, _ = asyncio.run(
            seed_driver_credential(settings, other_driver["id"], "TAXI_AUTHORIZATION")
        )
        credentials = expect(
            client.get("/api/v1/drivers/me/credentials", headers=authorization(driver_token)),
            200,
        )
        assert credentials == {
            "credentials": [
                {
                    "id": credential_id,
                    "type": "DRIVER_LICENSE",
                    "status": "VERIFIED",
                    "issued_at": issued_at.isoformat().replace("+00:00", "Z"),
                    "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
                }
            ]
        }
        assert "credential_number" not in credentials["credentials"][0]
        assert "document" not in credentials["credentials"][0]
        other_credentials = expect(
            client.get("/api/v1/drivers/me/credentials", headers=authorization(other_driver_token)),
            200,
        )
        assert [item["id"] for item in other_credentials["credentials"]] == [other_credential_id]
        assert credential_id not in {item["id"] for item in other_credentials["credentials"]}
        assert client.get(
            "/api/v1/drivers/me/credentials", headers=authorization(passenger_token)
        ).status_code == 404
        assert client.get(
            "/api/v1/drivers/me/credentials", headers=authorization(admin_token)
        ).status_code == 404

        assert expect(
            client.get("/api/v1/drivers/me/verification", headers=authorization(driver_token)),
            200,
        ) == {"status": "NOT_STARTED", "submitted_at": None}
        verification = expect(
            client.post("/api/v1/drivers/me/verification", headers=authorization(driver_token)),
            200,
        )
        assert verification["status"] == "SUBMITTED"
        assert verification["submitted_at"] is not None
        assert expect(
            client.get("/api/v1/drivers/me/verification", headers=authorization(driver_token)),
            200,
        ) == verification
        expect(
            client.post(
                f"/api/v1/admin/drivers/{driver['id']}/approve", headers=authorization(admin_token)
            ),
            200,
        )

        vehicle = expect(
            client.post(
                "/api/v1/drivers/me/vehicles",
                headers=authorization(driver_token),
                json={
                    "make": "Integration",
                    "model": "Taxi",
                    "year": 2025,
                    "color": "White",
                    "registration_number": f"IT-{suffix[:10]}",
                    "taxi_identifier": f"TX-{suffix[:8]}",
                    "passenger_capacity": 4,
                },
            ),
            201,
        )
        expect(
            client.post(
                f"/api/v1/admin/vehicles/{vehicle['id']}/verify", headers=authorization(admin_token)
            ),
            200,
        )
        expect(
            client.post(
                "/api/v1/drivers/me/active-vehicle",
                headers=authorization(driver_token),
                json={"vehicle_id": vehicle["id"]},
            ),
            200,
        )

        # The backend, not the UI, enforces a fresh location before availability.
        expect(client.post("/api/v1/drivers/me/availability/online", headers=authorization(driver_token)), 409)
        expect(
            client.post(
                "/api/v1/drivers/me/location",
                headers=authorization(driver_token),
                json={
                    "latitude": 33.5731,
                    "longitude": -7.5898,
                    "observed_at": datetime.now(UTC).isoformat(),
                    "accuracy": 8.0,
                },
            ),
            200,
        )
        asyncio.run(
            set_driver_credential_expiry(
                settings,
                credential_id,
                datetime.now(UTC) - timedelta(seconds=1),
            )
        )
        invalid_credential_response = client.post(
            "/api/v1/drivers/me/availability/online",
            headers=authorization(driver_token),
        )
        assert invalid_credential_response.status_code == 409
        assert "credential" in invalid_credential_response.json()["error"]["message"].lower()
        asyncio.run(
            set_driver_credential_expiry(
                settings,
                credential_id,
                datetime.now(UTC) + timedelta(days=365),
            )
        )
        online = expect(
            client.post("/api/v1/drivers/me/availability/online", headers=authorization(driver_token)), 200
        )
        assert online["status"] == "AVAILABLE"

        effective_from = datetime.now(UTC) + timedelta(seconds=1)
        tariff = expect(
            client.post(
                "/api/v1/admin/pricing-rules",
                headers=authorization(admin_token),
                json={
                    "name": "Integration fixed fare",
                    "version": f"integration-{suffix}",
                    "fixed_amount": "35.00",
                    "currency": "MAD",
                    "effective_from": effective_from.isoformat(),
                },
            ),
            201,
        )
        expect(
            client.post(
                f"/api/v1/admin/pricing-rules/{tariff['id']}/activate",
                headers=authorization(admin_token),
            ),
            200,
        )
        sleep(max(0.0, (effective_from - datetime.now(UTC)).total_seconds()) + 0.1)

        trip = {
            "pickup": {"latitude": 33.5731, "longitude": -7.5898, "address": "Integration pickup"},
            "destination": {"latitude": 33.5899, "longitude": -7.6039, "address": "Integration destination"},
        }
        estimate = expect(
            client.post("/api/v1/rides/estimate", headers=authorization(passenger_token), json=trip), 200
        )
        assert estimate["estimate"] == {
            "amount": "35.00",
            "currency": "MAD",
            "pricing_rule_version": tariff["version"],
            "city_id": str(LEGACY_CITY_ID),
            "operator_id": str(LEGACY_OPERATOR_ID),
            "service_type": "ON_DEMAND",
            "fixed_route": None,
            "economics": {
                "transport_fare": "35.00",
                "scheduling_surcharge": "0.00",
                "operator_service_fee": "0.00",
                "passenger_total": "35.00",
                "expected_driver_net": "35.00",
                "operator_allocation": "0.00",
                "operator_fee_policy_version": "legacy-zero-fee-v1",
                "operator_fee_calculation_mode": "FLAT_PER_COMPLETED_BOOKING",
                "operator_fee_funding_mode": "DRIVER_SETTLEMENT_DEDUCTION",
                "scheduling_policy_version": None,
            },
        }
        assert estimate["payment_methods"] == ["CASH", "MANUAL_TRANSFER"]

        # Eligibility is re-evaluated by matching; going online once cannot
        # preserve dispatch access after a credential expires.
        asyncio.run(
            set_driver_credential_expiry(
                settings,
                credential_id,
                datetime.now(UTC) - timedelta(seconds=1),
            )
        )
        credential_blocked_ride = expect(
            client.post("/api/v1/rides", headers=idempotency(passenger_token), json=trip),
            201,
        )
        for _ in range(40):
            credential_blocked_ride = expect(
                client.get(
                    f"/api/v1/rides/{credential_blocked_ride['id']}",
                    headers=authorization(passenger_token),
                ),
                200,
            )
            if credential_blocked_ride["status"] == "UNMATCHED":
                break
            sleep(0.05)
        assert credential_blocked_ride["status"] == "UNMATCHED"
        assert expect(
            client.get("/api/v1/drivers/me/ride-offers", headers=authorization(driver_token)),
            200,
        )["offers"] == []
        asyncio.run(
            set_driver_credential_expiry(
                settings,
                credential_id,
                datetime.now(UTC) + timedelta(days=365),
            )
        )

        # A declined offer does not strand the driver in OFFERED_RIDE. With no
        # other untried candidate, the bounded search ends explicitly instead
        # of leaving the passenger in MATCHING forever.
        declined_ride = expect(
            client.post("/api/v1/rides", headers=idempotency(passenger_token), json=trip), 201
        )
        declined_offer_response = expect(
            client.get("/api/v1/drivers/me/ride-offers", headers=authorization(driver_token)), 200
        )
        declined_offer = declined_offer_response["offers"][0]
        assert declined_offer_response["server_time"]
        assert declined_offer["issued_at"]
        assert declined_offer["expires_at"] > declined_offer["issued_at"]
        assert declined_offer["estimated_pickup_distance_meters"] >= 0
        assert declined_offer["estimated_pickup_time_seconds"] >= 1
        assert declined_offer["estimated_fare"] == {"amount": "35.00", "currency": "MAD"}
        assert declined_offer["economics"] == estimate["estimate"]["economics"]
        assert declined_offer["matching_algorithm_version"] == settings.matching_algorithm_version
        expect(
            client.post(
                f"/api/v1/ride-offers/{declined_offer['id']}/decline",
                headers=authorization(driver_token),
                json={"reason": "Integration decline lifecycle"},
            ),
            200,
        )
        assert expect(
            client.get(f"/api/v1/rides/{declined_ride['id']}", headers=authorization(passenger_token)),
            200,
        )["status"] == "UNMATCHED"
        assert expect(
            client.get("/api/v1/drivers/me/availability", headers=authorization(driver_token)), 200
        )["status"] == "AVAILABLE"

        ride = expect(
            client.post("/api/v1/rides", headers=idempotency(passenger_token), json=trip), 201
        )
        assert ride["status"] == "MATCHING"
        accepted_offer_response = expect(
            client.get("/api/v1/drivers/me/ride-offers", headers=authorization(driver_token)), 200
        )
        offers = accepted_offer_response["offers"]
        assert accepted_offer_response["server_time"]
        assert offers[0]["issued_at"]
        assert len(offers) == 1
        asyncio.run(
            set_driver_credential_expiry(
                settings,
                credential_id,
                datetime.now(UTC) - timedelta(seconds=1),
            )
        )
        assert client.post(
            f"/api/v1/ride-offers/{offers[0]['id']}/accept",
            headers=authorization(driver_token),
        ).status_code == 409
        asyncio.run(
            set_driver_credential_expiry(
                settings,
                credential_id,
                datetime.now(UTC) + timedelta(days=365),
            )
        )
        expect(
            client.post(
                f"/api/v1/ride-offers/{offers[0]['id']}/accept", headers=authorization(driver_token)
            ),
            200,
        )

        passenger_ride = expect(
            client.get(f"/api/v1/rides/{ride['id']}", headers=authorization(passenger_token)), 200
        )
        assert passenger_ride["status"] == "ACCEPTED"
        assert passenger_ride["driver"]["display_name"] == "Integration Driver"
        assert passenger_ride["driver"]["vehicle"]["taxi_identifier"] == f"TX-{suffix[:8]}".upper()
        driver_ride = expect(
            client.get(f"/api/v1/rides/{ride['id']}", headers=authorization(driver_token)), 200
        )
        assert driver_ride["id"] == ride["id"]
        assert client.get(
            f"/api/v1/rides/{ride['id']}",
            headers=authorization(other_driver_token),
        ).status_code == 403
        # The dispatch observation predates assignment and must not become
        # passenger-visible location history.
        assert passenger_ride["last_known_driver_location"] is None
        assert client.get(
            f"/api/v1/rides/{ride['id']}",
            headers=authorization(admin_token),
        ).status_code == 403

        # Coordination is a closed, role-specific vocabulary available only to
        # the two participants while the assigned ride remains active.
        passenger_message_headers = {
            **authorization(passenger_token),
            "Idempotency-Key": str(uuid4()),
        }
        passenger_message = expect(
            client.post(
                f"/api/v1/rides/{ride['id']}/messages",
                headers=passenger_message_headers,
                json={"code": "PASSENGER_AT_PICKUP"},
            ),
            201,
        )
        assert passenger_message["sender_role"] == "PASSENGER"
        assert passenger_message["code"] == "PASSENGER_AT_PICKUP"
        assert expect(
            client.post(
                f"/api/v1/rides/{ride['id']}/messages",
                headers=passenger_message_headers,
                json={"code": "PASSENGER_AT_PICKUP"},
            ),
            201,
        )["id"] == passenger_message["id"]
        assert client.post(
            f"/api/v1/rides/{ride['id']}/messages",
            headers=idempotency(passenger_token),
            json={"code": "DRIVER_ON_MY_WAY"},
        ).status_code == 409
        assert client.post(
            f"/api/v1/rides/{ride['id']}/messages",
            headers=idempotency(other_driver_token),
            json={"code": "DRIVER_ON_MY_WAY"},
        ).status_code == 403
        latest_for_driver = expect(
            client.get(
                f"/api/v1/rides/{ride['id']}",
                headers=authorization(driver_token),
            ),
            200,
        )["latest_coordination_message"]
        assert latest_for_driver["id"] == passenger_message["id"]
        driver_message = expect(
            client.post(
                f"/api/v1/rides/{ride['id']}/messages",
                headers=idempotency(driver_token),
                json={"code": "DRIVER_ON_MY_WAY"},
            ),
            201,
        )
        assert driver_message["sender_role"] == "DRIVER"
        assert expect(
            client.get(
                f"/api/v1/rides/{ride['id']}",
                headers=authorization(passenger_token),
            ),
            200,
        )["latest_coordination_message"]["id"] == driver_message["id"]
        driver_notifications = expect(
            client.get("/api/v1/notifications", headers=authorization(driver_token)),
            200,
        )["items"]
        assert any(item["type"] == "PASSENGER_AT_PICKUP" for item in driver_notifications)
        passenger_notifications = expect(
            client.get("/api/v1/notifications", headers=authorization(passenger_token)),
            200,
        )["items"]
        assert any(item["type"] == "DRIVER_ON_MY_WAY" for item in passenger_notifications)

        active_location_observed_at = datetime.now(UTC)
        expect(
            client.post(
                "/api/v1/drivers/me/location",
                headers=authorization(driver_token),
                json={
                    "latitude": 33.5731,
                    "longitude": -7.5898,
                    "observed_at": active_location_observed_at.isoformat(),
                    "accuracy": 7.5,
                },
            ),
            200,
        )
        tracked_ride = expect(
            client.get(f"/api/v1/rides/{ride['id']}", headers=authorization(passenger_token)),
            200,
        )
        assert tracked_ride["last_known_driver_location"]["latitude"] == 33.5731
        assert tracked_ride["last_known_driver_location"]["longitude"] == -7.5898
        assert tracked_ride["last_known_driver_location"]["accuracy_meters"] == 7.5
        assert datetime.fromisoformat(
            tracked_ride["last_known_driver_location"]["observed_at"].replace("Z", "+00:00")
        ) == active_location_observed_at

        for endpoint, expected_status in (
            ("en-route", "DRIVER_EN_ROUTE"),
            ("arrived", "DRIVER_ARRIVED"),
            ("start", "IN_PROGRESS"),
        ):
            transition = expect(
                client.post(
                    f"/api/v1/rides/{ride['id']}/{endpoint}", headers=authorization(driver_token)
                ),
                200,
            )
            assert transition["status"] == expected_status

        completed = expect(
            client.post(
                f"/api/v1/rides/{ride['id']}/complete",
                headers=idempotency(driver_token),
                json={"latitude": 33.5899, "longitude": -7.6039},
            ),
            200,
        )
        assert completed["status"] == "COMPLETED"
        assert completed["fare"] == {"amount": "35.00", "currency": "MAD"}
        completed_ride = expect(
            client.get(f"/api/v1/rides/{ride['id']}", headers=authorization(passenger_token)),
            200,
        )
        assert completed_ride["last_known_driver_location"] is None
        assert completed_ride["latest_coordination_message"] is None
        assert client.post(
            f"/api/v1/rides/{ride['id']}/messages",
            headers=idempotency(passenger_token),
            json={"code": "PASSENGER_AT_PICKUP"},
        ).status_code == 409
        completed_history = expect(
            client.get(
                "/api/v1/rides?status=COMPLETED&page=1&limit=1",
                headers=authorization(passenger_token),
            ),
            200,
        )
        assert completed_history["page"] == 1
        assert completed_history["limit"] == 1
        assert completed_history["total"] >= 1
        assert completed_history["items"][0]["status"] == "COMPLETED"
        assert completed_history["items"][0]["last_known_driver_location"] is None
        assert client.get(
            "/api/v1/rides?status=NOT_A_RIDE_STATUS",
            headers=authorization(passenger_token),
        ).status_code == 422

        pending_receipt = expect(
            client.get(f"/api/v1/rides/{ride['id']}/receipt", headers=authorization(passenger_token)), 200
        )
        assert pending_receipt["payment"] == {"method": "CASH", "status": "PENDING"}
        assert pending_receipt["fare"]["components"] == [
            {"code": "TRANSPORT_FARE", "label": "Transport fare", "amount": "35.00"}
        ]
        expected_receipt_economics = {
            key: value for key, value in estimate["estimate"]["economics"].items() if value is not None
        }
        assert pending_receipt["fare"]["economics"] == expected_receipt_economics

        payment = expect(
            client.post(
                f"/api/v1/rides/{ride['id']}/payments/cash/settle", headers=idempotency(driver_token)
            ),
            200,
        )
        assert payment["status"] == "COMPLETED"
        settled_receipt = expect(
            client.get(f"/api/v1/rides/{ride['id']}/receipt", headers=authorization(passenger_token)), 200
        )
        assert settled_receipt["payment"] == {"method": "CASH", "status": "COMPLETED"}

        rating = expect(
            client.post(
                f"/api/v1/rides/{ride['id']}/rating",
                headers=authorization(passenger_token),
                json={"score": 5, "comment": "Integration lifecycle passed"},
            ),
            201,
        )
        assert rating["score"] == 5

        driver_ratings = expect(
            client.get(
                f"/api/v1/rides/{ride['id']}/ratings",
                headers=authorization(driver_token),
            ),
            200,
        )
        assert driver_ratings == {
            "items": [
                {
                    "id": rating["id"],
                    "score": 5,
                    "comment": "Integration lifecycle passed",
                    "created_at": rating["created_at"],
                }
            ]
        }
        assert client.get(
            f"/api/v1/rides/{ride['id']}/ratings",
            headers=authorization(other_driver_token),
        ).status_code == 403

        refund_payload = {
            "amount": "5.00",
            "reason": "FARE_CORRECTION",
            "settlement_method": "CASH",
            "settlement_reference": f"CASH-REFUND-{suffix}",
            "operator_note": "Controlled integration fare correction returned in cash.",
        }
        assert client.post(
            f"/api/v1/admin/payments/{payment['id']}/refunds",
            headers=idempotency(passenger_token),
            json=refund_payload,
        ).status_code == 403
        refund_headers = idempotency(admin_token)
        refund = expect(
            client.post(
                f"/api/v1/admin/payments/{payment['id']}/refunds",
                headers=refund_headers,
                json=refund_payload,
            ),
            201,
        )
        assert refund["amount"] == "5.00"
        assert refund["operator_funded_amount"] == "5.00"
        assert refund["driver_recovery_amount"] == "0.00"
        assert refund["remaining_refundable_amount"] == "30.00"
        assert refund["payment_status"] == "COMPLETED"
        assert expect(
            client.post(
                f"/api/v1/admin/payments/{payment['id']}/refunds",
                headers=refund_headers,
                json=refund_payload,
            ),
            201,
        ) == refund
        assert client.post(
            f"/api/v1/admin/payments/{payment['id']}/refunds",
            headers=idempotency(admin_token),
            json={**refund_payload, "amount": "31.00", "settlement_reference": f"EXCESS-{suffix}"},
        ).status_code == 409
        assert client.post(
            f"/api/v1/admin/payments/{payment['id']}/refunds",
            headers=idempotency(admin_token),
            json={**refund_payload, "amount": "1.00"},
        ).status_code == 409
        refund_queue = expect(
            client.get(
                "/api/v1/admin/payments/refunds",
                headers=authorization(admin_token),
                params={"payment_id": payment["id"], "page": 1, "limit": 20},
            ),
            200,
        )
        assert refund_queue["total"] == 1
        assert refund_queue["items"][0]["id"] == refund["id"]
        scoped_refunds = expect(
            client.get(
                "/api/v1/operations/payments/refunds",
                headers=authorization(operations_token),
                params={"city_id": str(LEGACY_CITY_ID), "payment_id": payment["id"], "page": 1, "limit": 20},
            ),
            200,
        )
        assert scoped_refunds["total"] == 1
        assert scoped_refunds["items"][0]["city_id"] == str(LEGACY_CITY_ID)
        refund_audit = expect(
            client.get(
                "/api/v1/admin/audit-logs",
                headers=authorization(admin_token),
                params={
                    "action": "PAYMENT_REFUND_RECORDED",
                    "resource_type": "payment_refund",
                    "resource_id": refund["id"],
                },
            ),
            200,
        )
        assert refund_audit["total"] == 1
        assert refund_audit["items"][0]["changes"]["payment_id"] == payment["id"]
        assert "operator_note" not in refund_audit["items"][0]["changes"]
        assert "settlement_reference" not in refund_audit["items"][0]["changes"]
        assert client.get(
            "/api/v1/admin/payments/refunds",
            headers=authorization(passenger_token),
        ).status_code == 403
        refunded_receipt = expect(
            client.get(
                f"/api/v1/rides/{ride['id']}/receipt",
                headers=authorization(passenger_token),
            ),
            200,
        )
        assert refunded_receipt["fare"]["amount"] == "35.00"
        assert refunded_receipt["payment"]["status"] == "COMPLETED"
        assert refunded_receipt["payment"]["refunds"] == {
            "refunded_amount": "5.00",
            "net_paid_amount": "30.00",
            "currency": "MAD",
            "items": [
                {
                    "id": refund["id"],
                    "amount": "5.00",
                    "currency": "MAD",
                    "reason": "FARE_CORRECTION",
                    "refunded_at": refund["refunded_at"],
                }
            ],
        }
        final_refund = expect(
            client.post(
                f"/api/v1/operations/payments/{payment['id']}/refunds",
                headers=idempotency(operations_token),
                json={
                    "amount": "30.00",
                    "reason": "SERVICE_RECOVERY",
                    "settlement_method": "EXTERNAL_TRANSFER",
                    "settlement_reference": f"FINAL-REFUND-{suffix}",
                    "operator_note": "Controlled final refund transfer confirmed.",
                },
            ),
            201,
        )
        assert final_refund["payment_status"] == "REFUNDED"
        assert final_refund["remaining_refundable_amount"] == "0.00"
        fully_refunded_receipt = expect(
            client.get(
                f"/api/v1/rides/{ride['id']}/receipt",
                headers=authorization(passenger_token),
            ),
            200,
        )
        assert fully_refunded_receipt["fare"]["amount"] == "35.00"
        assert fully_refunded_receipt["payment"]["status"] == "REFUNDED"
        assert fully_refunded_receipt["payment"]["refunds"]["refunded_amount"] == "35.00"
        assert fully_refunded_receipt["payment"]["refunds"]["net_paid_amount"] == "0.00"
        assert len(fully_refunded_receipt["payment"]["refunds"]["items"]) == 2

        earnings = expect(client.get("/api/v1/drivers/me/earnings", headers=authorization(driver_token)), 200)
        assert earnings["gross"] == "35.00"
        assert earnings["fees"] == "0.00"
        assert earnings["net"] == "35.00"
        assert earnings["transport_fare"] == "35.00"
        assert earnings["scheduling_surcharge"] == "0.00"
        assert earnings["operator_service_fee"] == "0.00"
        assert earnings["operator_allocation"] == "0.00"
        assert earnings["count"] == 1
        assert earnings["page"] == 1
        assert earnings["limit"] == 20
        assert earnings["settled_through"] is not None
        assert len(earnings["items"]) == 1
        assert earnings["items"][0]["ride_id"] == ride["id"]
        assert earnings["items"][0]["gross"] == "35.00"
        assert earnings["items"][0]["net"] == "35.00"
        assert earnings["items"][0]["transport_fare"] == "35.00"
        assert earnings["items"][0]["scheduling_surcharge"] == "0.00"
        assert earnings["items"][0]["operator_service_fee"] == "0.00"
        assert earnings["items"][0]["operator_fee_funding_mode"] == "DRIVER_SETTLEMENT_DEDUCTION"
        assert earnings["items"][0]["operator_allocation"] == "0.00"

        # A second completed ride proves the no-gateway transfer path through
        # passenger claim, rejection/retry, administrator reconciliation, and
        # immutable driver earning creation.
        expect(
            client.post(
                "/api/v1/drivers/me/location",
                headers=authorization(driver_token),
                json={
                    "latitude": 33.5731,
                    "longitude": -7.5898,
                    "observed_at": datetime.now(UTC).isoformat(),
                    "accuracy": 7.5,
                },
            ),
            200,
        )
        expect(
            client.post(
                "/api/v1/drivers/me/availability/online",
                headers=authorization(driver_token),
            ),
            200,
        )
        transfer_ride = expect(
            client.post(
                "/api/v1/rides",
                headers=idempotency(passenger_token),
                json={**trip, "payment_method": "MANUAL_TRANSFER"},
            ),
            201,
        )
        assert transfer_ride["payment_method"] == "MANUAL_TRANSFER"
        transfer_offer = expect(
            client.get(
                "/api/v1/drivers/me/ride-offers",
                headers=authorization(driver_token),
            ),
            200,
        )["offers"][0]
        expect(
            client.post(
                f"/api/v1/ride-offers/{transfer_offer['id']}/accept",
                headers=authorization(driver_token),
            ),
            200,
        )
        for endpoint in ("en-route", "arrived", "start"):
            expect(
                client.post(
                    f"/api/v1/rides/{transfer_ride['id']}/{endpoint}",
                    headers=authorization(driver_token),
                ),
                200,
            )
        transfer_completion = expect(
            client.post(
                f"/api/v1/rides/{transfer_ride['id']}/complete",
                headers=idempotency(driver_token),
                json={"latitude": 33.5899, "longitude": -7.6039},
            ),
            200,
        )
        assert transfer_completion["payment_method"] == "MANUAL_TRANSFER"
        transfer_receipt = expect(
            client.get(
                f"/api/v1/rides/{transfer_ride['id']}/receipt",
                headers=authorization(passenger_token),
            ),
            200,
        )
        assert transfer_receipt["payment"]["status"] == "PENDING"
        assert transfer_receipt["payment"]["manual_transfer"] == {
            "recipient_name": "TaxiMobile Integration Recipient",
            "bank_account": "TEST-BANK-ACCOUNT",
            "wallet_id": "TEST-WALLET-001",
            "payment_reference": transfer_receipt["payment"]["manual_transfer"]["payment_reference"],
        }
        assert transfer_receipt["payment"]["manual_transfer"]["payment_reference"].startswith("TM-")
        assert client.post(
            f"/api/v1/rides/{transfer_ride['id']}/payments/cash/settle",
            headers=idempotency(driver_token),
        ).status_code == 404

        first_claim_headers = idempotency(passenger_token)
        first_claim = expect(
            client.post(
                f"/api/v1/rides/{transfer_ride['id']}/payments/manual-transfer/submit",
                headers=first_claim_headers,
                json={"payer_reference": "TEST-PAYER-001"},
            ),
            202,
        )
        assert first_claim["status"] == "SUBMITTED"
        assert expect(
            client.post(
                f"/api/v1/rides/{transfer_ride['id']}/payments/manual-transfer/submit",
                headers=first_claim_headers,
                json={"payer_reference": "TEST-PAYER-001"},
            ),
            202,
        ) == first_claim
        assert expect(
            client.get(
                f"/api/v1/rides/{transfer_ride['id']}/receipt",
                headers=authorization(passenger_token),
            ),
            200,
        )["payment"]["status"] == "PROCESSING"
        assert client.post(
            f"/api/v1/admin/payments/{first_claim['payment_id']}/manual-transfer/verify",
            headers=idempotency(passenger_token),
            json={"settlement_reference": "TEST-SETTLEMENT-FORBIDDEN"},
        ).status_code == 403

        rejected = expect(
            client.post(
                f"/api/v1/operations/payments/{first_claim['payment_id']}/manual-transfer/reject",
                headers=idempotency(operations_token),
                json={"reason": "Controlled rejection before retry."},
            ),
            200,
        )
        assert rejected["status"] == "REJECTED"
        rejected_receipt = expect(
            client.get(
                f"/api/v1/rides/{transfer_ride['id']}/receipt",
                headers=authorization(passenger_token),
            ),
            200,
        )
        assert rejected_receipt["payment"]["status"] == "PENDING"
        assert rejected_receipt["payment"]["manual_transfer"]["latest_claim_status"] == "REJECTED"

        second_claim = expect(
            client.post(
                f"/api/v1/rides/{transfer_ride['id']}/payments/manual-transfer/submit",
                headers=idempotency(passenger_token),
                json={},
            ),
            202,
        )
        queue = expect(
            client.get(
                "/api/v1/admin/payments/manual-transfers",
                headers=authorization(admin_token),
                params={"status": "SUBMITTED", "page": 1, "limit": 100},
            ),
            200,
        )
        assert any(item["claim_id"] == second_claim["id"] for item in queue["items"])
        scoped_queue = expect(
            client.get(
                "/api/v1/operations/payments/manual-transfers",
                headers=authorization(operations_token),
                params={"status": "SUBMITTED", "city_id": str(LEGACY_CITY_ID), "page": 1, "limit": 100},
            ),
            200,
        )
        assert any(item["claim_id"] == second_claim["id"] for item in scoped_queue["items"])
        assert all(item["city_id"] == str(LEGACY_CITY_ID) for item in scoped_queue["items"])
        verified = expect(
            client.post(
                f"/api/v1/operations/payments/{second_claim['payment_id']}/manual-transfer/verify",
                headers=idempotency(operations_token),
                json={"settlement_reference": f"TEST-SETTLEMENT-{suffix}"},
            ),
            200,
        )
        assert verified["status"] == "VERIFIED"
        assert expect(
            client.get(
                f"/api/v1/rides/{transfer_ride['id']}/receipt",
                headers=authorization(passenger_token),
            ),
            200,
        )["payment"]["status"] == "COMPLETED"
        transfer_earnings = expect(
            client.get(
                "/api/v1/drivers/me/earnings",
                headers=authorization(driver_token),
            ),
            200,
        )
        assert transfer_earnings["gross"] == "70.00"
        assert transfer_earnings["net"] == "70.00"
        assert transfer_earnings["count"] == 2

        # Ordinary support and safety are deliberately separate participant
        # surfaces. Only the restricted administration routes expose priority,
        # assignment, deadlines, descriptions of safety events, and case notes.
        support_internal_note = f"internal-support-note-{suffix}"
        support_payload = {
            "category": "RIDE_PROBLEM",
            "subject": "Completed ride follow-up",
            "description": "The pickup discussion needs an operator review.",
            "ride_id": ride["id"],
        }
        support_create_headers = idempotency(passenger_token)
        support_ticket = expect(
            client.post(
                "/api/v1/support/tickets",
                headers=support_create_headers,
                json=support_payload,
            ),
            201,
        )
        assert expect(
            client.post(
                "/api/v1/support/tickets",
                headers=support_create_headers,
                json=support_payload,
            ),
            201,
        ) == support_ticket
        assert client.post(
            "/api/v1/support/tickets",
            headers=authorization(passenger_token),
            json=support_payload,
        ).status_code == 422
        assert client.get(
            f"/api/v1/support/tickets/{support_ticket['id']}",
            headers=authorization(other_driver_token),
        ).status_code == 403
        assert client.get(
            "/api/v1/admin/support/tickets",
            headers=authorization(passenger_token),
        ).status_code == 403

        support_queue = expect(
            client.get(
                "/api/v1/admin/support/tickets",
                headers=authorization(admin_token),
                params={"status": "OPEN", "page": 1, "limit": 100},
            ),
            200,
        )
        assert any(item["id"] == support_ticket["id"] for item in support_queue["items"])
        support_triage_headers = idempotency(operations_token)
        triaged_support = expect(
            client.post(
                f"/api/v1/operations/support/tickets/{support_ticket['id']}/triage",
                headers=support_triage_headers,
                json={
                    "priority": "HIGH",
                    "participant_message": "A support specialist is reviewing this request.",
                    "internal_note": support_internal_note,
                },
            ),
            200,
        )
        assert triaged_support["status"] == "IN_PROGRESS"
        assert triaged_support["assigned_to_user_id"] == admin_id
        triage_notes = {note["visibility"]: note for note in triaged_support["notes"]}
        assert triage_notes["INTERNAL"]["message"] == support_internal_note
        assert triage_notes["PARTICIPANT"]["message"] == (
            "A support specialist is reviewing this request."
        )
        assert expect(
            client.post(
                f"/api/v1/operations/support/tickets/{support_ticket['id']}/triage",
                headers=support_triage_headers,
                json={
                    "priority": "HIGH",
                    "participant_message": "A support specialist is reviewing this request.",
                    "internal_note": support_internal_note,
                },
            ),
            200,
        ) == triaged_support

        participant_support = expect(
            client.get(
                f"/api/v1/support/tickets/{support_ticket['id']}",
                headers=authorization(passenger_token),
            ),
            200,
        )
        assert participant_support["status"] == "IN_PROGRESS"
        assert participant_support["latest_public_message"] == (
            "A support specialist is reviewing this request."
        )
        assert support_internal_note not in repr(participant_support)
        assert {
            "priority",
            "assigned_to_user_id",
            "response_due_at",
            "first_responded_at",
            "retention_until",
            "notes",
        }.isdisjoint(participant_support)

        support_public_resolution = "We reviewed the ride and recorded the operator action."
        resolved_support = expect(
            client.post(
                f"/api/v1/operations/support/tickets/{support_ticket['id']}/transition",
                headers=idempotency(operations_token),
                json={
                    "target_status": "RESOLVED",
                    "resolution_code": "ACTION_TAKEN",
                    "participant_message": support_public_resolution,
                    "internal_note": "Validated against the completed ride timeline.",
                },
            ),
            200,
        )
        assert resolved_support["status"] == "RESOLVED"
        assert expect(
            client.get(
                f"/api/v1/support/tickets/{support_ticket['id']}",
                headers=authorization(passenger_token),
            ),
            200,
        )["latest_public_message"] == support_public_resolution
        closed_support = expect(
            client.post(
                f"/api/v1/operations/support/tickets/{support_ticket['id']}/transition",
                headers=idempotency(operations_token),
                json={
                    "target_status": "CLOSED",
                    "resolution_code": "ACTION_TAKEN",
                    "participant_message": "This support request is now closed.",
                    "internal_note": "Closure review completed.",
                },
            ),
            200,
        )
        assert closed_support["retention_policy_version"] == "support-launch-v1"
        assert closed_support["retention_until"] is not None

        safety_internal_note = f"internal-safety-note-{suffix}"
        safety_payload = {
            "ride_id": ride["id"],
            "category": "UNSAFE_DRIVING",
            "description": "The vehicle crossed the center line repeatedly.",
        }
        safety_create_headers = idempotency(passenger_token)
        safety_report = expect(
            client.post(
                "/api/v1/safety/reports",
                headers=safety_create_headers,
                json=safety_payload,
            ),
            201,
        )
        assert expect(
            client.post(
                "/api/v1/safety/reports",
                headers=safety_create_headers,
                json=safety_payload,
            ),
            201,
        ) == safety_report
        assert safety_report["status"] == "SUBMITTED"
        assert "description" not in safety_report
        assert client.get(
            f"/api/v1/safety/reports/{safety_report['id']}",
            headers=authorization(driver_token),
        ).status_code == 403
        assert client.get(
            f"/api/v1/safety/reports/{safety_report['id']}",
            headers=authorization(other_driver_token),
        ).status_code == 403
        assert client.get(
            "/api/v1/admin/safety/reports",
            headers=authorization(passenger_token),
        ).status_code == 403
        assert client.post(
            f"/api/v1/operations/safety/reports/{safety_report['id']}/transition",
            headers=idempotency(operations_token),
            json={
                "target_status": "ACKNOWLEDGED",
                "internal_note": "A participant-safe acknowledgement is mandatory.",
            },
        ).status_code == 422

        safety_acknowledgement = "A safety specialist has acknowledged your report."
        acknowledged_safety = expect(
            client.post(
                f"/api/v1/operations/safety/reports/{safety_report['id']}/transition",
                headers=idempotency(operations_token),
                json={
                    "target_status": "ACKNOWLEDGED",
                    "participant_message": safety_acknowledgement,
                    "internal_note": safety_internal_note,
                },
            ),
            200,
        )
        assert acknowledged_safety["assigned_to_user_id"] == admin_id
        assert acknowledged_safety["reported_user_id"] == driver_id
        assert acknowledged_safety["description"] == safety_payload["description"]
        acknowledgement_notes = {
            note["visibility"]: note for note in acknowledged_safety["notes"]
        }
        assert acknowledgement_notes["INTERNAL"]["message"] == safety_internal_note
        assert acknowledgement_notes["PARTICIPANT"]["message"] == safety_acknowledgement
        participant_safety = expect(
            client.get(
                f"/api/v1/safety/reports/{safety_report['id']}",
                headers=authorization(passenger_token),
            ),
            200,
        )
        assert participant_safety["latest_public_message"] == safety_acknowledgement
        assert safety_internal_note not in repr(participant_safety)
        assert {
            "reporter_user_id",
            "reported_user_id",
            "description",
            "priority",
            "assigned_to_user_id",
            "response_due_at",
            "retention_until",
            "notes",
        }.isdisjoint(participant_safety)

        for target_status, participant_message, resolution_code in (
            ("ESCALATED", "Your report has been escalated for specialist review.", None),
            ("RESOLVED", "The safety review is complete.", "SAFETY_ACTION_TAKEN"),
            ("CLOSED", "The safety report is now closed.", "SAFETY_ACTION_TAKEN"),
        ):
            payload = {
                "target_status": target_status,
                "participant_message": participant_message,
                "internal_note": f"Controlled {target_status.lower()} transition.",
            }
            if resolution_code is not None:
                payload["resolution_code"] = resolution_code
            transitioned_safety = expect(
                client.post(
                    f"/api/v1/operations/safety/reports/{safety_report['id']}/transition",
                    headers=idempotency(operations_token),
                    json=payload,
                ),
                200,
            )
        assert transitioned_safety["status"] == "CLOSED"
        assert transitioned_safety["retention_policy_version"] == "safety-launch-v1"
        assert transitioned_safety["retention_until"] is not None

        processed, retained_safety, retention_action, erased_note_count = asyncio.run(
            expire_and_process_safety_retention(settings, safety_report["id"])
        )
        assert processed == 1
        assert erased_note_count > 0
        assert retained_safety.ride_id is None
        assert retained_safety.reporter_user_id is None
        assert retained_safety.reported_user_id is None
        assert retained_safety.assigned_to_user_id is None
        assert retained_safety.description == ""
        assert retained_safety.latest_public_message is None
        assert retained_safety.retention_action == "PERSONAL_DATA_ERASED"
        assert retained_safety.retention_processed_at is not None
        assert retention_action.action == "PERSONAL_DATA_ERASED"
        assert retention_action.erased_note_count == erased_note_count
        assert client.get(
            f"/api/v1/safety/reports/{safety_report['id']}",
            headers=authorization(passenger_token),
        ).status_code == 403
        assert client.get(
            f"/api/v1/operations/safety/reports/{safety_report['id']}",
            headers=authorization(operations_token),
        ).status_code == 404

        escalation_internal_note = f"support-escalation-note-{suffix}"
        escalation_ticket = expect(
            client.post(
                "/api/v1/support/tickets",
                headers=idempotency(passenger_token),
                json={
                    "category": "RIDE_PROBLEM",
                    "subject": "Safety review needed",
                    "description": "The passenger reports threatening behavior during the ride.",
                    "ride_id": ride["id"],
                },
            ),
            201,
        )
        escalation_headers = idempotency(operations_token)
        escalated_from_support = expect(
            client.post(
                f"/api/v1/operations/support/tickets/{escalation_ticket['id']}/escalate-safety",
                headers=escalation_headers,
                json={
                    "category": "HARASSMENT",
                    "internal_note": escalation_internal_note,
                },
            ),
            201,
        )
        assert escalated_from_support["source_support_ticket_id"] == escalation_ticket["id"]
        assert escalated_from_support["city_id"] == str(LEGACY_CITY_ID)
        assert {"reported_user_id", "description", "notes"}.isdisjoint(escalated_from_support)
        escalated_safety_detail = expect(
            client.get(
                "/api/v1/operations/safety/reports/"
                f"{escalated_from_support['safety_report_id']}",
                headers=authorization(operations_token),
            ),
            200,
        )
        assert escalated_safety_detail["reported_user_id"] == driver_id
        assert expect(
            client.post(
                f"/api/v1/operations/support/tickets/{escalation_ticket['id']}/escalate-safety",
                headers=escalation_headers,
                json={
                    "category": "HARASSMENT",
                    "internal_note": escalation_internal_note,
                },
            ),
            201,
        ) == escalated_from_support
        assert client.post(
            f"/api/v1/operations/support/tickets/{escalation_ticket['id']}/escalate-safety",
            headers=idempotency(operations_token),
            json={
                "category": "HARASSMENT",
                "internal_note": "A duplicate safety record must not be created.",
            },
        ).status_code == 409
        participant_escalated_ticket = expect(
            client.get(
                f"/api/v1/support/tickets/{escalation_ticket['id']}",
                headers=authorization(passenger_token),
            ),
            200,
        )
        assert participant_escalated_ticket["status"] == "IN_PROGRESS"
        assert escalation_internal_note not in repr(participant_escalated_ticket)
        passenger_safety_ids = {
            item["id"]
            for item in expect(
                client.get("/api/v1/safety/reports", headers=authorization(passenger_token)),
                200,
            )["items"]
        }
        assert safety_report["id"] not in passenger_safety_ids
        assert escalated_from_support["safety_report_id"] in passenger_safety_ids

        support_audit = expect(
            client.get(
                "/api/v1/admin/audit-logs",
                headers=authorization(admin_token),
                params={
                    "resource_type": "support_ticket",
                    "resource_id": support_ticket["id"],
                    "page": 1,
                    "limit": 100,
                },
            ),
            200,
        )
        assert {"SUPPORT_TICKET_TRIAGED", "SUPPORT_TICKET_STATUS_CHANGED"}.issubset(
            {entry["action"] for entry in support_audit["items"]}
        )
        assert support_internal_note not in repr(support_audit)
        safety_audit = expect(
            client.get(
                "/api/v1/admin/audit-logs",
                headers=authorization(admin_token),
                params={
                    "resource_type": "safety_report",
                    "resource_id": safety_report["id"],
                    "page": 1,
                    "limit": 100,
                },
            ),
            200,
        )
        assert "SAFETY_REPORT_STATUS_CHANGED" in {
            entry["action"] for entry in safety_audit["items"]
        }
        assert safety_internal_note not in repr(safety_audit)

        asyncio.run(
            set_driver_credential_expiry(
                settings,
                credential_id,
                datetime.now(UTC) + timedelta(days=10),
            )
        )
        asyncio.run(process_credential_lifecycle(settings))
        asyncio.run(process_credential_lifecycle(settings))
        credential_notifications = expect(
            client.get("/api/v1/notifications", headers=authorization(driver_token)),
            200,
        )["items"]
        assert sum(
            item["type"] == "DRIVER_CREDENTIAL_EXPIRING" for item in credential_notifications
        ) == 1

        asyncio.run(
            set_driver_credential_expiry(
                settings,
                credential_id,
                datetime.now(UTC) - timedelta(seconds=1),
            )
        )
        asyncio.run(process_credential_lifecycle(settings))
        credential_notifications = expect(
            client.get("/api/v1/notifications", headers=authorization(driver_token)),
            200,
        )["items"]
        assert sum(
            item["type"] == "DRIVER_CREDENTIAL_EXPIRED" for item in credential_notifications
        ) == 1
        assert expect(
            client.get("/api/v1/drivers/me/credentials", headers=authorization(driver_token)),
            200,
        )["credentials"][0]["status"] == "EXPIRED"

        assert client.get(
            "/api/v1/admin/audit-logs",
            headers=authorization(passenger_token),
        ).status_code == 403

        revoked = expect(
            client.post(
                f"/api/v1/admin/users/{driver_id}/sessions/revoke",
                headers=authorization(admin_token),
                json={"reason": "Integration compromised-session drill"},
            ),
            200,
        )
        assert revoked["status"] == "ACTIVE"
        assert revoked["sessions_revoked"] >= 1
        assert client.get("/api/v1/me", headers=authorization(driver_token)).status_code == 401

        suspension_registration = f"integration-suspension-fid-{suffix}"
        expect(
            client.post(
                "/api/v1/devices",
                headers=authorization(passenger_token),
                json={
                    "platform": "ANDROID",
                    "registration_kind": "FIREBASE_INSTALLATION_ID",
                    "registration_id": suspension_registration,
                },
            ),
            201,
        )
        suspended = expect(
            client.post(
                f"/api/v1/admin/users/{passenger_id}/suspend",
                headers=authorization(admin_token),
                json={"reason": "Integration account-security drill"},
            ),
            200,
        )
        assert suspended["status"] == "SUSPENDED"
        assert suspended["sessions_revoked"] >= 1
        assert suspended["device_registrations_revoked"] == 1
        assert asyncio.run(device_token_state(settings, suspension_registration))[0][3] is not None
        assert client.get("/api/v1/me", headers=authorization(passenger_token)).status_code == 401
        assert client.post(
            "/api/v1/auth/login",
            json={"identifier": passenger_email, "password": PASSENGER_PASSWORD},
        ).status_code == 401

        assert client.post(
            f"/api/v1/admin/users/{admin_id}/suspend",
            headers=authorization(admin_token),
            json={"reason": "Self-suspension must be refused"},
        ).status_code == 409
        reactivated = expect(
            client.post(
                f"/api/v1/admin/users/{passenger_id}/reactivate",
                headers=authorization(admin_token),
                json={"reason": "Integration review completed"},
            ),
            200,
        )
        assert reactivated["status"] == "ACTIVE"
        replacement_token = expect(
            client.post(
                "/api/v1/auth/login",
                json={"identifier": passenger_email, "password": PASSENGER_PASSWORD},
            ),
            200,
        )["access_token"]
        assert expect(client.get("/api/v1/me", headers=authorization(replacement_token)), 200)["id"] == passenger_id
        assert client.get("/api/v1/me", headers=authorization(passenger_token)).status_code == 401

        security_audit = expect(
            client.get(
                "/api/v1/admin/audit-logs",
                headers=authorization(admin_token),
                params={"resource_id": passenger_id, "page": 1, "limit": 100},
            ),
            200,
        )
        assert security_audit["page"] == 1
        assert security_audit["limit"] == 100
        actions = {entry["action"]: entry for entry in security_audit["items"]}
        assert {"USER_SUSPENDED", "USER_REACTIVATED"}.issubset(actions)
        assert actions["USER_SUSPENDED"]["actor_user_id"] == admin_id
        assert actions["USER_SUSPENDED"]["resource_type"] == "user"
        assert actions["USER_SUSPENDED"]["changes"]["reason"] == "Integration account-security drill"

        metric_codes = asyncio.run(refresh_and_read_operational_metric_codes(settings))
        assert {
            "PAYMENT_COMPLETED",
            "FINANCIAL_PASSENGER_TOTAL",
            "FINANCIAL_TRANSPORT_FARE",
            "FINANCIAL_SCHEDULING_SURCHARGE",
            "FINANCIAL_OPERATOR_FEE",
            "FINANCIAL_OPERATOR_ALLOCATION",
            "FINANCIAL_DRIVER_NET",
            "MATCHING_FAIRNESS_SCORE",
            "DRIVER_WORK_DISTRIBUTION",
        }.issubset(metric_codes)


def test_rate_limit_quota_is_shared_across_api_instances() -> None:
    settings = require_integration_settings()
    asyncio.run(prove_shared_rate_limit(settings, f"integration:{uuid4()}"))


def test_live_event_hint_reaches_another_api_process_through_postgres() -> None:
    settings = require_integration_settings()
    asyncio.run(prove_shared_live_event_fanout(settings))


def test_outbox_operational_metrics_are_read_from_migrated_postgres() -> None:
    settings = require_integration_settings()

    async def collect():
        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            return await collect_outbox_metrics(sessions)
        finally:
            await engine.dispose()

    snapshot = asyncio.run(collect())

    assert snapshot.available is True
    assert snapshot.pending_events >= 0
    assert snapshot.dead_letter_events >= 0
    assert snapshot.locked_events >= 0
    assert snapshot.oldest_pending_age_seconds >= 0


def test_production_process_roles_separate_public_api_from_all_worker_loops() -> None:
    settings = require_integration_settings()
    api_app = create_app(settings=replace(settings, process_role="api"))
    assert api_app.state.worker_runtime is None

    token = "integration-worker-monitoring-token"
    worker_app = create_worker_app(
        settings=replace(settings, process_role="worker", monitoring_token=token),
    )
    with TestClient(worker_app) as worker_client:
        readiness = None
        for _ in range(50):
            readiness = worker_client.get("/ready")
            if readiness.status_code == 200:
                break
            sleep(0.1)

        assert readiness is not None
        assert readiness.status_code == 200
        assert readiness.json() == {"status": "ready", "service": "taximobile-worker"}
        assert worker_client.get("/api/v1/meta").status_code == 404
        metrics = worker_client.get(
            "/internal/metrics",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert metrics.status_code == 200
        for worker in (
            "matching",
            "outbox",
            "credentials",
            "scheduling",
            "analytics",
            "case_alerts",
            "case_retention",
            "driver_document_retention",
        ):
            prefix = (
                f'taximobile_worker_iterations_total{{worker="{worker}",outcome="success"}} '
            )
            line = next(line for line in metrics.text.splitlines() if line.startswith(prefix))
            assert int(line.removeprefix(prefix)) >= 1


def test_dead_letter_replay_is_atomic_explicit_and_selective() -> None:
    settings = require_integration_settings()
    asyncio.run(prove_selective_dead_letter_replay(settings))


async def prove_selective_dead_letter_replay(settings: Settings) -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    selected_id, untouched_id, invalid_id = uuid4(), uuid4(), uuid4()
    now = datetime.now(UTC)
    try:
        async with sessions() as session:
            async with session.begin():
                session.add_all(
                    [
                        OutboxEvent(
                            id=selected_id,
                            topic="integration.replay.selected",
                            payload={"resource_id": str(uuid4())},
                            attempts=8,
                            locked_at=now,
                            locked_by="expired-worker-lease",
                            last_error="DELIVERY_DEAD_LETTERED",
                            dead_lettered_at=now,
                        ),
                        OutboxEvent(
                            id=untouched_id,
                            topic="integration.replay.untouched",
                            payload={"resource_id": str(uuid4())},
                            attempts=8,
                            last_error="DELIVERY_DEAD_LETTERED",
                            dead_lettered_at=now,
                        ),
                        OutboxEvent(
                            id=invalid_id,
                            topic="integration.replay.delivered",
                            payload={"resource_id": str(uuid4())},
                            attempts=8,
                            delivered_at=now,
                            last_error="DELIVERY_DEAD_LETTERED",
                            dead_lettered_at=now,
                        ),
                    ]
                )

        target = make_url(settings.database_url)
        request_values = {
            "database_url": settings.database_url,
            "expected_database_host": target.host or "",
            "expected_database_name": target.database or "",
            "incident_reference": "INTEGRATION-REPLAY-001",
        }
        mixed_request = validate_request(
            event_ids=(selected_id, invalid_id),
            **request_values,
        )
        with pytest.raises(ReplayRefused):
            await replay_dead_letters(settings.database_url, mixed_request)

        selected_request = validate_request(event_ids=(selected_id,), **request_values)
        assert await replay_dead_letters(settings.database_url, selected_request) == 1

        async with sessions() as session:
            rows = {
                row.id: row
                for row in (
                    await session.execute(
                        select(
                            OutboxEvent.id,
                            OutboxEvent.attempts,
                            OutboxEvent.locked_at,
                            OutboxEvent.locked_by,
                            OutboxEvent.last_error,
                            OutboxEvent.delivered_at,
                            OutboxEvent.dead_lettered_at,
                        ).where(OutboxEvent.id.in_((selected_id, untouched_id, invalid_id)))
                    )
                ).all()
            }
        selected = rows[selected_id]
        assert selected.attempts == 0
        assert selected.locked_at is None
        assert selected.locked_by is None
        assert selected.last_error is None
        assert selected.delivered_at is None
        assert selected.dead_lettered_at is None
        assert rows[untouched_id].dead_lettered_at is not None
        assert rows[invalid_id].delivered_at is not None
        assert rows[invalid_id].dead_lettered_at is not None
    finally:
        async with sessions() as session:
            async with session.begin():
                await session.execute(
                    delete(OutboxEvent).where(
                        OutboxEvent.id.in_((selected_id, untouched_id, invalid_id))
                    )
                )
        await engine.dispose()
