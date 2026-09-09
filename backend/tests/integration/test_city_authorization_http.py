"""Real MFA, scoped HTTP decisions, idempotent replay and rollback evidence."""

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from scheduled_handoff_fixtures import prepare_handoff_fixture
from test_city_driver_recruitment import seed_recruiting_test_city
from test_operations_mfa_flow import (
    TOTP_SECRET, age_session_mfa, begin_login, integration_settings,
    seed_operations_factor, totp_code,
)
from taximobile_api.domains.administration.models import AdministrativeGrant, AdministrativeRoleTemplate, AuditLog
from taximobile_api.domains.driver_applications import authorization_lifecycle as lifecycle
from taximobile_api.domains.driver_applications.models import DriverCityApplication, DriverCityAuthorization
from taximobile_api.domains.notifications.models import Notification
from taximobile_api.domains.outbox.models import OutboxEvent
from taximobile_api.main import create_app


pytestmark = pytest.mark.integration


async def with_database(settings, command):
    engine = create_async_engine(settings.database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        return await command(sessions)
    finally:
        await engine.dispose()


@pytest.mark.parametrize("scenario", ["lifecycle", "rollback", "scope-replay", "stale-mfa"])
def test_city_authorization_http_preserves_scope_mfa_replay_and_transaction(scenario, monkeypatch):
    settings = integration_settings()
    reviewer_id = asyncio.run(seed_operations_factor(settings))
    async def seed(sessions):
        ready = await prepare_handoff_fixture(sessions)
        async with sessions() as session:
            authorization = await session.scalar(select(DriverCityAuthorization).where(
                DriverCityAuthorization.driver_id == ready.driver_id,
            ))
            application = await session.get(DriverCityApplication, authorization.application_id)
            return application.id, application.optimistic_version, authorization.id
    application_id, version, authorization_id = asyncio.run(with_database(settings, seed))
    url = f"/api/v1/operations/driver-applications/{application_id}/authorization/decisions"
    payload = {"expected_application_version": version, "action": "SUSPEND", "reason_code": "SAFETY_REVIEW"}

    with TestClient(create_app(settings=settings), base_url="https://testserver", raise_server_exceptions=False) as client:
        challenge = begin_login(client)
        verification = client.post("/api/v1/operations/auth/mfa/verify", json={
            "challenge_id": challenge["challenge_id"],
            "code": totp_code(TOTP_SECRET, int(datetime.now(UTC).timestamp() // 30)),
        })
        assert verification.status_code == 200, verification.text
        headers = {"Authorization": f"Bearer {verification.json()['access_token']}", "Idempotency-Key": uuid4().hex}
        assert client.post(url, json=payload).status_code == 401
        if scenario == "stale-mfa":
            current = client.get("/api/v1/operations/auth/session", headers=headers)
            assert current.status_code == 200
            asyncio.run(age_session_mfa(settings, UUID(current.json()["session_id"])))
            assert client.post(url, headers=headers, json=payload).status_code == 403
        else:
            if scenario == "rollback":
                original = lifecycle.enqueue
                async def fail_after_outbox(*args, **kwargs):
                    await original(*args, **kwargs)
                    raise RuntimeError("synthetic private outbox fault")
                with monkeypatch.context() as patch:
                    patch.setattr(lifecycle, "enqueue", fail_after_outbox)
                    failed = client.post(url, headers=headers, json=payload)
                assert failed.status_code == 500
                assert "synthetic private" not in failed.text
                detail = client.get(f"/api/v1/operations/driver-applications/{application_id}", headers=headers)
                assert detail.json()["application"]["authorization"]["status"] == "ACTIVE"
                assert detail.json()["application"]["optimistic_version"] == version
            changed = client.post(url, headers=headers, json=payload)
            assert changed.status_code == 200, changed.text
            assert changed.json()["application"]["authorization"]["status"] == "SUSPENDED"
            assert changed.json()["application"]["optimistic_version"] == version + 1
            if scenario == "scope-replay":
                other_city = asyncio.run(seed_recruiting_test_city(settings, uuid4().hex))
                async def restrict(sessions):
                    async with sessions.begin() as session:
                        grant = await session.scalar(select(AdministrativeGrant).where(AdministrativeGrant.user_id == reviewer_id))
                        grant.market_id = None
                        grant.city_id = other_city
                        grant.role_template = AdministrativeRoleTemplate.DRIVER_REVIEWER
                asyncio.run(with_database(settings, restrict))
                replay = client.post(url, headers=headers, json=payload)
                assert replay.status_code == 404
                assert str(authorization_id) not in replay.text
            else:
                replay = client.post(url, headers=headers, json=payload)
                assert replay.status_code == 200 and replay.json() == changed.json()
                assert client.post(url, headers=headers, json=payload | {"reason_code": "ELIGIBILITY_REVIEW"}).status_code == 409
                assert client.post(url, headers=headers | {"Idempotency-Key": uuid4().hex}, json=payload).status_code == 409
                restored = client.post(url, headers=headers | {"Idempotency-Key": uuid4().hex}, json={
                    "expected_application_version": version + 1, "action": "REINSTATE", "reason_code": "ELIGIBILITY_REVIEW_PASSED",
                })
                assert restored.status_code == 200, restored.text
                assert restored.json()["application"]["authorization"]["status"] == "ACTIVE"

    async def assert_durable(sessions):
        async with sessions() as session:
            authorization = await session.get(DriverCityAuthorization, authorization_id)
            expected = "SUSPENDED" if scenario == "scope-replay" else "ACTIVE"
            assert authorization.status.value == expected
            count = await session.scalar(select(func.count(AuditLog.id)).where(
                AuditLog.resource_id == authorization_id, AuditLog.resource_type == "driver_city_authorization",
            ))
            assert count == (0 if scenario == "stale-mfa" else 1 if scenario == "scope-replay" else 2)
            expected_count = 0 if scenario == "stale-mfa" else 1 if scenario == "scope-replay" else 2
            assert await session.scalar(select(func.count(Notification.id)).where(
                Notification.type == "DRIVER_CITY_AUTHORIZATION_CHANGED",
                Notification.data["authorization_id"].astext == str(authorization_id),
            )) == expected_count
            assert await session.scalar(select(func.count(OutboxEvent.id)).where(
                OutboxEvent.topic == "driver.city_authorization.changed",
                OutboxEvent.payload["authorization_id"].astext == str(authorization_id),
            )) == expected_count
    asyncio.run(with_database(settings, assert_durable))
