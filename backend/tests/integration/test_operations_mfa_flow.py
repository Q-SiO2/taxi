"""Migrated-database proof for the production operations MFA boundary."""

from __future__ import annotations

import asyncio
from base64 import urlsafe_b64encode
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from os import getenv
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from taximobile_api.cli.enroll_operations_mfa import EnrollmentTarget, persist_enrollment
from taximobile_api.core.config import Settings
from taximobile_api.domains.administration.bootstrap import bootstrap_initial_platform_grant
from taximobile_api.domains.administration.models import (
    AuditLog,
    OperationsMfaChallenge,
    OperationsMfaCredential,
    OperationsMfaRecoveryCode,
    OperationsSession,
)
from taximobile_api.domains.administration.operations_mfa import (
    encrypt_totp_secret,
    recovery_code_hash,
    totp_code,
)
from taximobile_api.domains.auth.bootstrap import bootstrap_initial_administrator
from taximobile_api.main import create_app


pytestmark = pytest.mark.integration

ADMIN_EMAIL = "integration-admin@example.test"
ADMIN_PASSWORD = "Integration-admin-password-2026"
TOTP_SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
RECOVERY_CODE = "23456-789AB-CDEFG-HJKLM"
MFA_KEY = bytes(range(32))
MFA_KEY_TEXT = urlsafe_b64encode(MFA_KEY).decode("ascii").rstrip("=")


def integration_settings() -> Settings:
    if getenv("TAXIMOBILE_RUN_INTEGRATION") != "1":
        pytest.skip("Set TAXIMOBILE_RUN_INTEGRATION=1 with an isolated migrated PostGIS database.")
    settings = Settings.from_environment()
    if settings.environment != "test" or "taximobile_ci" not in settings.database_url:
        pytest.fail("Integration tests require TAXIMOBILE_ENV=test and an isolated taximobile_ci database.")
    return replace(
        settings,
        operations_password_login_enabled=False,
        operations_mfa_encryption_key=MFA_KEY_TEXT,
        operations_secure_cookie_enabled=True,
        allowed_hosts=(*settings.allowed_hosts, "testserver"),
    )


async def seed_operations_factor(settings: Settings) -> UUID:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            async with session.begin():
                administrator = await bootstrap_initial_administrator(
                    session,
                    email=ADMIN_EMAIL,
                    password=ADMIN_PASSWORD,
                )
        async with sessions() as session:
            async with session.begin():
                await bootstrap_initial_platform_grant(
                    session,
                    admin_email=ADMIN_EMAIL,
                    market_code="MA",
                )
                existing = await session.scalar(
                    select(OperationsMfaCredential).where(
                        OperationsMfaCredential.user_id == administrator.user_id
                    )
                )
                if existing is None:
                    now = datetime.now(UTC)
                    ciphertext, nonce = encrypt_totp_secret(
                        TOTP_SECRET,
                        MFA_KEY,
                        administrator.user_id,
                    )
                    existing = OperationsMfaCredential(
                        user_id=administrator.user_id,
                        encrypted_secret=ciphertext,
                        secret_nonce=nonce,
                        enabled_at=now,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(existing)
                    await session.flush()
                    session.add(
                        OperationsMfaRecoveryCode(
                            credential_id=existing.id,
                            code_hash=recovery_code_hash(RECOVERY_CODE),
                            created_at=now,
                        )
                    )
        return administrator.user_id
    finally:
        await engine.dispose()


async def age_session_mfa(settings: Settings, session_id: UUID) -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            async with session.begin():
                await session.execute(
                    update(OperationsSession)
                    .where(OperationsSession.id == session_id)
                    .values(mfa_verified_at=datetime.now(UTC) - timedelta(minutes=11))
                )
    finally:
        await engine.dispose()


async def challenge_state(settings: Settings, challenge_id: UUID) -> tuple[int, bool]:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            challenge = await session.get(OperationsMfaChallenge, challenge_id)
            assert challenge is not None
            return challenge.attempt_count, challenge.consumed_at is not None
    finally:
        await engine.dispose()


async def completed_mfa_login_audit_exists(settings: Settings, user_id: UUID) -> bool:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            return (
                await session.scalar(
                    select(AuditLog.id).where(
                        AuditLog.actor_user_id == user_id,
                        AuditLog.action == "OPERATIONS_MFA_LOGIN_COMPLETED",
                    )
                )
                is not None
            )
    finally:
        await engine.dispose()


async def factor_replacement_state(
    settings: Settings,
    user_id: UUID,
) -> tuple[UUID, int, int]:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            credential_id = await session.scalar(
                select(OperationsMfaCredential.id).where(
                    OperationsMfaCredential.user_id == user_id
                )
            )
            assert credential_id is not None
            active_sessions = await session.scalar(
                select(func.count()).select_from(OperationsSession).where(
                    OperationsSession.user_id == user_id,
                    OperationsSession.revoked_at.is_(None),
                )
            )
            recovery_codes = await session.scalar(
                select(func.count()).select_from(OperationsMfaRecoveryCode).where(
                    OperationsMfaRecoveryCode.credential_id == credential_id
                )
            )
            return credential_id, active_sessions or 0, recovery_codes or 0
    finally:
        await engine.dispose()


def expect(response, status_code: int):
    assert response.status_code == status_code, response.text
    return response.json()


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def begin_login(client: TestClient) -> dict:
    result = expect(
        client.post(
            "/api/v1/operations/auth/login",
            json={
                "identifier": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
                "device_label": "MFA integration",
            },
        ),
        200,
    )
    assert "access_token" not in result
    assert result["authentication_methods"] == ["TOTP", "RECOVERY_CODE"]
    return result


def test_operations_mfa_login_replay_recovery_refresh_and_step_up() -> None:
    settings = integration_settings()
    user_id = asyncio.run(seed_operations_factor(settings))

    with TestClient(create_app(settings=settings), base_url="https://testserver") as client:
        challenge = begin_login(client)
        assert client.post(
            "/api/v1/operations/auth/mfa/verify",
            json={"challenge_id": challenge["challenge_id"], "code": "000000"},
        ).status_code == 401

        counter = int(datetime.now(UTC).timestamp() // 30)
        code = totp_code(TOTP_SECRET, counter)
        verification = client.post(
            "/api/v1/operations/auth/mfa/verify",
            json={"challenge_id": challenge["challenge_id"], "code": code},
        )
        tokens = expect(verification, 200)
        assert tokens["authentication_strength"] == "PASSWORD_TOTP_MFA"
        assert "refresh_token" not in tokens
        assert tokens["csrf_token"]
        set_cookie = verification.headers["set-cookie"]
        assert "Secure" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "SameSite=strict" in set_cookie
        assert "Path=/api/v1/operations/auth" in set_cookie
        cookie = client.cookies.get("__Secure-taximobile-operations-refresh")
        assert cookie is not None
        headers = bearer(tokens["access_token"])

        # One RFC 6238 counter can authenticate only once for this account.
        assert client.post(
            "/api/v1/operations/auth/mfa/step-up",
            headers=headers,
            json={"code": code},
        ).status_code == 401

        current_session = expect(
            client.get("/api/v1/operations/auth/session", headers=headers),
            200,
        )
        assert current_session["authentication_strength"] == "PASSWORD_TOTP_MFA"
        assert current_session["mfa_verified_at"] is not None

        assert client.post("/api/v1/operations/auth/refresh").status_code == 401
        refreshed = expect(
            client.post(
                "/api/v1/operations/auth/refresh",
                headers={"X-CSRF-Token": tokens["csrf_token"]},
            ),
            200,
        )
        assert refreshed["authentication_strength"] == "PASSWORD_TOTP_MFA"
        assert "refresh_token" not in refreshed
        assert refreshed["csrf_token"] != tokens["csrf_token"]
        headers = bearer(refreshed["access_token"])
        refreshed_session = expect(
            client.get("/api/v1/operations/auth/session", headers=headers),
            200,
        )
        assert refreshed_session["mfa_verified_at"] == current_session["mfa_verified_at"]

        asyncio.run(age_session_mfa(settings, UUID(refreshed_session["session_id"])))
        protected_payload = {
            "case_kind": "SUPPORT",
            "case_id": str(uuid4()),
            "reason_code": "REGULATORY_REQUEST",
            "authority_reference": "MFA-INTEGRATION-1",
            "review_due_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        }
        protected_headers = {**headers, "Idempotency-Key": str(uuid4())}
        blocked = client.post(
            "/api/v1/operations/case-retention/holds",
            headers=protected_headers,
            json=protected_payload,
        )
        assert blocked.status_code == 403
        assert blocked.json()["error"]["message"] == (
            "Recent operations MFA verification is required."
        )

        recovery_step_up = expect(
            client.post(
                "/api/v1/operations/auth/mfa/step-up",
                headers=headers,
                json={"code": RECOVERY_CODE.lower()},
            ),
            200,
        )
        assert recovery_step_up["authentication_strength"] == "PASSWORD_RECOVERY_CODE_MFA"

        # The command now crosses the MFA gate and fails only because the test
        # intentionally names a nonexistent case.
        assert client.post(
            "/api/v1/operations/case-retention/holds",
            headers=protected_headers,
            json=protected_payload,
        ).status_code == 404
        assert client.post(
            "/api/v1/operations/auth/mfa/step-up",
            headers=headers,
            json={"code": RECOVERY_CODE},
        ).status_code == 401

        exhausted = begin_login(client)
        for _ in range(5):
            assert client.post(
                "/api/v1/operations/auth/mfa/verify",
                json={"challenge_id": exhausted["challenge_id"], "code": "000000"},
            ).status_code == 401

    assert asyncio.run(challenge_state(settings, UUID(exhausted["challenge_id"]))) == (5, True)
    assert asyncio.run(completed_mfa_login_audit_exists(settings, user_id))

    old_credential_id, active_sessions, _ = asyncio.run(
        factor_replacement_state(settings, user_id)
    )
    assert active_sessions == 1
    replacement_secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    replacement_counter = int(datetime.now(UTC).timestamp() // 30)
    asyncio.run(
        persist_enrollment(
            settings,
            EnrollmentTarget(
                user_id=user_id,
                email=ADMIN_EMAIL,
                existing_credential_id=old_credential_id,
            ),
            replacement_secret,
            totp_code(replacement_secret, replacement_counter),
            ["NPQRS-TUVWX-YZ234-56789"],
        )
    )
    new_credential_id, active_sessions, recovery_code_count = asyncio.run(
        factor_replacement_state(settings, user_id)
    )
    assert new_credential_id != old_credential_id
    assert active_sessions == 0
    assert recovery_code_count == 1
