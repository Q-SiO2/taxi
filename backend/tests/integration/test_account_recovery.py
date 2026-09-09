"""Migrated-PostGIS proof for provider-independent account recovery and sessions."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from os import getenv

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from taximobile_api.core.config import Settings
from taximobile_api.domains.auth.bootstrap import bootstrap_initial_administrator
from taximobile_api.domains.auth.models import AccountRecoveryCode
from taximobile_api.domains.auth.security import account_recovery_code_hash
from taximobile_api.domains.notifications.models import DeviceToken, Notification
from taximobile_api.main import create_app


pytestmark = pytest.mark.integration

PASSENGER_EMAIL = "recovery-passenger@example.test"
PASSENGER_PASSWORD = "Recovery-passenger-password-2026"
REPLACEMENT_PASSWORD = "Recovery-replacement-password-2026"
SECOND_REPLACEMENT_PASSWORD = "Recovery-second-password-2026"
ADMIN_EMAIL = "recovery-admin@example.test"
ADMIN_PASSWORD = "Recovery-admin-password-2026"
STAFF_RECOVERY_CODE = "23456-789AB-CDEFG-HJKLM"


def integration_settings() -> Settings:
    if getenv("TAXIMOBILE_RUN_INTEGRATION") != "1":
        pytest.skip("Set TAXIMOBILE_RUN_INTEGRATION=1 with an isolated migrated PostGIS database.")
    settings = Settings.from_environment()
    if settings.environment != "test" or "taximobile_ci" not in settings.database_url:
        pytest.fail(
            "Integration tests require TAXIMOBILE_ENV=test and an isolated "
            "taximobile_ci database."
        )
    return settings


def expect(response, status_code: int) -> dict:
    assert response.status_code == status_code, response.text
    return response.json()


def bearer(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def recovery_test_app(settings: Settings):
    """Keep recovery assertions independent from the separately tested login quota."""
    return create_app(settings=replace(settings, login_rate_limit_per_minute=20))


def register_passenger(client: TestClient) -> None:
    expect(
        client.post(
            "/api/v1/auth/register",
            json={
                "email": PASSENGER_EMAIL,
                "password": PASSENGER_PASSWORD,
                "display_name": "Recovery Passenger",
            },
        ),
        201,
    )


def login(client: TestClient, password: str, device_label: str) -> dict:
    return expect(
        client.post(
            "/api/v1/auth/login",
            json={
                "identifier": PASSENGER_EMAIL,
                "password": password,
                "device_label": device_label,
            },
        ),
        200,
    )


async def recovery_database_state(settings: Settings) -> tuple[int, int, set[str]]:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            code_count = await session.scalar(
                select(func.count()).select_from(AccountRecoveryCode)
            )
            active_devices = await session.scalar(
                select(func.count())
                .select_from(DeviceToken)
                .where(DeviceToken.revoked_at.is_(None))
            )
            notification_types = set(await session.scalars(select(Notification.type)))
            return code_count or 0, active_devices or 0, notification_types
    finally:
        await engine.dispose()


async def expire_recovery_codes(settings: Settings) -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)
    try:
        async with sessions() as session:
            async with session.begin():
                await session.execute(
                    update(AccountRecoveryCode).values(
                        created_at=now - timedelta(days=2),
                        expires_at=now - timedelta(days=1),
                    )
                )
    finally:
        await engine.dispose()


async def seed_staff_recovery_code(settings: Settings) -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)
    try:
        async with sessions() as session:
            async with session.begin():
                administrator = await bootstrap_initial_administrator(
                    session,
                    email=ADMIN_EMAIL,
                    password=ADMIN_PASSWORD,
                )
                session.add(
                    AccountRecoveryCode(
                        user_id=administrator.user_id,
                        code_hash=account_recovery_code_hash(STAFF_RECOVERY_CODE),
                        created_at=now,
                        expires_at=now + timedelta(days=30),
                    )
                )
    finally:
        await engine.dispose()


def test_recovery_consumes_code_revokes_every_session_and_hides_account_existence() -> None:
    settings = integration_settings()
    with TestClient(recovery_test_app(settings)) as client:
        register_passenger(client)
        first = login(client, PASSENGER_PASSWORD, "Passenger phone")
        second = login(client, PASSENGER_PASSWORD, "Passenger tablet")

        for index, tokens in enumerate((first, second), start=1):
            expect(
                client.post(
                    "/api/v1/devices",
                    headers=bearer(tokens["access_token"]),
                    json={
                        "platform": "ANDROID",
                        "registration_kind": "FIREBASE_INSTALLATION_ID",
                        "registration_id": f"recovery-device-{index}",
                    },
                ),
                201,
            )

        session_page = expect(
            client.get(
                "/api/v1/auth/sessions",
                headers=bearer(first["access_token"]),
            ),
            200,
        )
        assert session_page["total"] == 2
        assert sum(item["current"] for item in session_page["items"]) == 1
        second_session_id = next(
            item["id"]
            for item in session_page["items"]
            if item["device_label"] == "Passenger tablet"
        )
        revoked = expect(
            client.delete(
                f"/api/v1/auth/sessions/{second_session_id}",
                headers=bearer(first["access_token"]),
            ),
            200,
        )
        assert revoked == {"revoked": True, "current_session": False}
        assert client.get("/api/v1/me", headers=bearer(second["access_token"])).status_code == 401
        second = login(client, PASSENGER_PASSWORD, "Passenger tablet replacement")

        assert client.post(
            "/api/v1/auth/recovery-codes",
            headers=bearer(first["access_token"]),
            json={"current_password": "wrong-password"},
        ).status_code == 401
        recovery = expect(
            client.post(
                "/api/v1/auth/recovery-codes",
                headers=bearer(first["access_token"]),
                json={"current_password": PASSENGER_PASSWORD},
            ),
            200,
        )
        assert len(recovery["codes"]) == 8
        assert len(set(recovery["codes"])) == 8

        generic_failure = expect(
            client.post(
                "/api/v1/auth/recovery/reset",
                json={
                    "identifier": "absent@example.test",
                    "recovery_code": recovery["codes"][0],
                    "new_password": REPLACEMENT_PASSWORD,
                },
            ),
            202,
        )
        reset = expect(
            client.post(
                "/api/v1/auth/recovery/reset",
                json={
                    "identifier": PASSENGER_EMAIL,
                    "recovery_code": recovery["codes"][0],
                    "new_password": REPLACEMENT_PASSWORD,
                },
            ),
            202,
        )
        assert generic_failure == reset == {"accepted": True}
        assert client.get("/api/v1/me", headers=bearer(first["access_token"])).status_code == 401
        assert client.get("/api/v1/me", headers=bearer(second["access_token"])).status_code == 401
        assert client.post(
            "/api/v1/auth/login",
            json={"identifier": PASSENGER_EMAIL, "password": PASSENGER_PASSWORD},
        ).status_code == 401
        current = login(client, REPLACEMENT_PASSWORD, "Recovered phone")

        replay = expect(
            client.post(
                "/api/v1/auth/recovery/reset",
                json={
                    "identifier": PASSENGER_EMAIL,
                    "recovery_code": recovery["codes"][0],
                    "new_password": SECOND_REPLACEMENT_PASSWORD,
                },
            ),
            202,
        )
        assert replay == {"accepted": True}
        assert client.get("/api/v1/me", headers=bearer(current["access_token"])).status_code == 200
        assert client.post(
            "/api/v1/auth/login",
            json={"identifier": PASSENGER_EMAIL, "password": SECOND_REPLACEMENT_PASSWORD},
        ).status_code == 401

    code_count, active_devices, notification_types = asyncio.run(
        recovery_database_state(settings)
    )
    assert code_count == 0
    assert active_devices == 0
    assert {
        "ACCOUNT_RECOVERY_CODES_REPLACED",
        "ACCOUNT_PASSWORD_RESET",
    }.issubset(notification_types)


def test_expired_code_is_inert_and_password_change_revokes_access() -> None:
    settings = integration_settings()
    with TestClient(recovery_test_app(settings)) as client:
        register_passenger(client)
        tokens = login(client, PASSENGER_PASSWORD, "Password-change phone")
        recovery = expect(
            client.post(
                "/api/v1/auth/recovery-codes",
                headers=bearer(tokens["access_token"]),
                json={"current_password": PASSENGER_PASSWORD},
            ),
            200,
        )
        asyncio.run(expire_recovery_codes(settings))

        assert expect(
            client.post(
                "/api/v1/auth/recovery/reset",
                json={
                    "identifier": PASSENGER_EMAIL,
                    "recovery_code": recovery["codes"][0],
                    "new_password": REPLACEMENT_PASSWORD,
                },
            ),
            202,
        ) == {"accepted": True}
        assert client.post(
            "/api/v1/auth/login",
            json={"identifier": PASSENGER_EMAIL, "password": REPLACEMENT_PASSWORD},
        ).status_code == 401

        assert client.post(
            "/api/v1/auth/password/change",
            headers=bearer(tokens["access_token"]),
            json={
                "current_password": PASSENGER_PASSWORD,
                "new_password": PASSENGER_PASSWORD,
            },
        ).status_code == 409
        changed = expect(
            client.post(
                "/api/v1/auth/password/change",
                headers=bearer(tokens["access_token"]),
                json={
                    "current_password": PASSENGER_PASSWORD,
                    "new_password": REPLACEMENT_PASSWORD,
                },
            ),
            200,
        )
        assert changed["changed"] is True
        assert changed["sessions_revoked"] >= 1
        assert client.get("/api/v1/me", headers=bearer(tokens["access_token"])).status_code == 401
        login(client, REPLACEMENT_PASSWORD, "Password changed")


def test_staff_accounts_cannot_use_mobile_recovery_codes() -> None:
    settings = integration_settings()
    asyncio.run(seed_staff_recovery_code(settings))
    with TestClient(recovery_test_app(settings)) as client:
        tokens = expect(
            client.post(
                "/api/v1/auth/login",
                json={
                    "identifier": ADMIN_EMAIL,
                    "password": ADMIN_PASSWORD,
                    "device_label": "Staff mobile login",
                },
            ),
            200,
        )
        assert client.post(
            "/api/v1/auth/recovery-codes",
            headers=bearer(tokens["access_token"]),
            json={"current_password": ADMIN_PASSWORD},
        ).status_code == 403

        assert expect(
            client.post(
                "/api/v1/auth/recovery/reset",
                json={
                    "identifier": ADMIN_EMAIL,
                    "recovery_code": STAFF_RECOVERY_CODE,
                    "new_password": REPLACEMENT_PASSWORD,
                },
            ),
            202,
        ) == {"accepted": True}
        assert client.post(
            "/api/v1/auth/login",
            json={"identifier": ADMIN_EMAIL, "password": REPLACEMENT_PASSWORD},
        ).status_code == 401
        assert client.post(
            "/api/v1/auth/login",
            json={"identifier": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        ).status_code == 200


def test_recovery_attempts_are_limited_per_client_and_normalized_identifier() -> None:
    settings = replace(
        integration_settings(),
        account_recovery_rate_limit_per_hour=2,
    )
    payload = {
        "identifier": " Rate-Limit@Example.Test ",
        "recovery_code": "23456-789AB-CDEFG-HJKLM",
        "new_password": REPLACEMENT_PASSWORD,
    }
    with TestClient(recovery_test_app(settings)) as client:
        assert client.post("/api/v1/auth/recovery/reset", json=payload).status_code == 202
        payload["identifier"] = "rate-limit@example.test"
        assert client.post("/api/v1/auth/recovery/reset", json=payload).status_code == 202
        assert client.post("/api/v1/auth/recovery/reset", json=payload).status_code == 429

        payload["identifier"] = "separate@example.test"
        assert client.post("/api/v1/auth/recovery/reset", json=payload).status_code == 202
