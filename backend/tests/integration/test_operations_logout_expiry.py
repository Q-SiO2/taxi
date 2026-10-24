"""An expired access token can refresh once and revoke the actual operations session."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from test_operations_mfa_flow import (
    TOTP_SECRET, begin_login, integration_settings, seed_operations_factor, totp_code,
)
from taximobile_api.domains.administration.models import OperationsSession
from taximobile_api.domains.auth.security import TokenService
from taximobile_api.main import create_app

pytestmark = pytest.mark.integration
COOKIE = "__Secure-taximobile-operations-refresh"


async def family_state(settings, session_id):
    engine = create_async_engine(settings.database_url)
    try:
        async with async_sessionmaker(engine)() as session:
            current = await session.get(OperationsSession, session_id)
            assert current is not None
            family = list(await session.scalars(select(OperationsSession).where(
                OperationsSession.refresh_family_id == current.refresh_family_id,
            )))
            return current.revoked_at is not None, current.refresh_rotated_at is not None, sum(row.revoked_at is None for row in family)
    finally:
        await engine.dispose()


@pytest.mark.parametrize("secure_cookie", [True, False])
def test_expired_operations_logout_refreshes_then_revokes(secure_cookie):
    settings = replace(integration_settings(), operations_secure_cookie_enabled=secure_cookie)
    actor = asyncio.run(seed_operations_factor(settings))
    with TestClient(create_app(settings=settings), base_url="https://testserver") as client:
        challenge = begin_login(client)
        verified = client.post("/api/v1/operations/auth/mfa/verify", json={
            "challenge_id": challenge["challenge_id"],
            "code": totp_code(TOTP_SECRET, int(datetime.now(UTC).timestamp() // 30)),
        })
        assert verified.status_code == 200
        original = verified.json()
        principal = client.get("/api/v1/operations/auth/session", headers={"Authorization": "Bearer " + original["access_token"]})
        assert principal.status_code == 200
        first_id = UUID(principal.json()["session_id"])
        expired = TokenService(settings.jwt_secret).create_operations_access_token(
            user_id=actor, session_id=first_id, now=datetime.now(UTC) - timedelta(minutes=11),
        )
        rejected = client.post("/api/v1/operations/auth/logout", headers={"Authorization": "Bearer " + expired})
        assert rejected.status_code == 401
        assert asyncio.run(family_state(settings, first_id)) == (False, False, 1)

        arguments = {"headers": {"X-CSRF-Token": original["csrf_token"]}} if secure_cookie else {"json": {"refresh_token": original["refresh_token"]}}
        refreshed = client.post("/api/v1/operations/auth/refresh", **arguments)
        assert refreshed.status_code == 200
        replacement = refreshed.json()
        access = {"Authorization": "Bearer " + replacement["access_token"]}
        principal = client.get("/api/v1/operations/auth/session", headers=access)
        assert principal.status_code == 200
        replacement_id = UUID(principal.json()["session_id"])
        assert replacement_id != first_id
        refresh = client.cookies.get(COOKIE) if secure_cookie else replacement["refresh_token"]
        assert refresh
        logged_out = client.post("/api/v1/operations/auth/logout", headers=access)
        assert logged_out.status_code == 200
        if secure_cookie:
            assert client.cookies.get(COOKIE) is None
            assert "Max-Age=0" in logged_out.headers["set-cookie"]
        assert asyncio.run(family_state(settings, replacement_id)) == (True, False, 0)
        assert client.get("/api/v1/operations/auth/session", headers=access).status_code == 401
        if secure_cookie:
            client.cookies.set(COOKIE, refresh, domain="testserver.local", path="/api/v1/operations/auth")
        arguments = {"headers": {"X-CSRF-Token": replacement["csrf_token"]}} if secure_cookie else {"json": {"refresh_token": refresh}}
        assert client.post("/api/v1/operations/auth/refresh", **arguments).status_code == 401
