"""PostGIS-backed proof of the complete first-release cash ride lifecycle.

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
from sqlalchemy import delete, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from taximobile_api.core.config import Settings
from taximobile_api.core.live_events import PostgresLiveEventListener, PostgresLiveEventPublisher
from taximobile_api.core.rate_limit import PostgresRateLimiter
from taximobile_api.core.realtime import EventHub
from taximobile_api.domains.auth.bootstrap import bootstrap_initial_administrator
from taximobile_api.domains.cooperatives.models import (
    Cooperative,
    CooperativeMembership,
    CooperativeMembershipStatus,
)
from taximobile_api.domains.drivers.models import DriverCredential, CredentialVerificationStatus
from taximobile_api.domains.notifications.models import DeviceToken
from taximobile_api.domains.outbox.metrics import collect_outbox_metrics
from taximobile_api.domains.outbox.models import OutboxEvent
from taximobile_api.main import create_app
from taximobile_api.operations.outbox_replay import ReplayRefused, replay_dead_letters, validate_request
from taximobile_api.worker import create_worker_app
from taximobile_api.workers.credentials import CredentialLifecycleProcessor


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
    hub = EventHub()
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

    socket = RecordingSocket()
    listener = PostgresLiveEventListener(settings.database_url, hub, reconnect_seconds=0.1)
    listener_task = asyncio.create_task(listener.run())
    try:
        await hub.connect(user_id, socket)
        await listener.wait_until_ready(5)
        await PostgresLiveEventPublisher(sessions).publish_ride_refresh(
            user_id,
            ride_id,
            "DRIVER_ASSIGNED",
        )
        await asyncio.wait_for(socket.received.wait(), timeout=5)
        assert socket.message == {"type": "DRIVER_ASSIGNED", "ride_id": str(ride_id)}
    finally:
        listener_task.cancel()
        with suppress(asyncio.CancelledError):
            await listener_task
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


def test_complete_passenger_driver_cash_ride_lifecycle() -> None:
    settings = require_integration_settings()
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
        }

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

        earnings = expect(client.get("/api/v1/drivers/me/earnings", headers=authorization(driver_token)), 200)
        assert earnings["gross"] == "35.00"
        assert earnings["fees"] == "0.00"
        assert earnings["net"] == "35.00"
        assert earnings["count"] == 1
        assert earnings["page"] == 1
        assert earnings["limit"] == 20
        assert earnings["settled_through"] is not None
        assert len(earnings["items"]) == 1
        assert earnings["items"][0]["ride_id"] == ride["id"]
        assert earnings["items"][0]["gross"] == "35.00"
        assert earnings["items"][0]["net"] == "35.00"

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
        for worker in ("matching", "outbox", "credentials"):
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
