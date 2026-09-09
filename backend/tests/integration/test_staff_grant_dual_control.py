"""PostGIS-backed proof for staff-grant maker-checker and continuity controls."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from os import getenv
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from taximobile_api.core.config import Settings
from taximobile_api.domains.administration.bootstrap import (
    PlatformGrantBootstrapConflict,
    bootstrap_initial_platform_grant,
    bootstrap_platform_admin_quorum_member,
)
from taximobile_api.domains.administration.models import (
    AdministrativeGrant,
    AdministrativeGrantChangeRequest,
    AdministrativeGrantRequestStatus,
    AdministrativeRoleTemplate,
)
from taximobile_api.domains.auth.bootstrap import bootstrap_initial_administrator
from taximobile_api.domains.auth.models import User, UserStatus
from taximobile_api.domains.markets.constants import LEGACY_CITY_ID, LEGACY_MARKET_ID
from taximobile_api.main import create_app


pytestmark = pytest.mark.integration

ADMIN_PASSWORD = "Staff-grant-integration-password-2026"


def integration_settings() -> Settings:
    if getenv("TAXIMOBILE_RUN_INTEGRATION") != "1":
        pytest.skip(
            "Set TAXIMOBILE_RUN_INTEGRATION=1 with an isolated migrated PostGIS database."
        )
    settings = Settings.from_environment()
    if settings.environment != "test" or "taximobile_ci" not in settings.database_url:
        pytest.fail(
            "Integration tests require TAXIMOBILE_ENV=test and an isolated taximobile_ci database."
        )
    assert settings.operations_password_login_enabled
    return settings


def expect(response, status_code: int):
    assert response.status_code == status_code, response.text
    return response.json()


def error_message(response) -> str:
    return response.json()["error"]["message"]


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login_operations(client: TestClient, email: str) -> dict[str, str]:
    payload = expect(
        client.post(
            "/api/v1/operations/auth/login",
            json={"identifier": email, "password": ADMIN_PASSWORD},
        ),
        200,
    )
    return bearer(payload["access_token"])


def register_user(client: TestClient, email: str, display_name: str) -> UUID:
    expect(
        client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": ADMIN_PASSWORD,
                "display_name": display_name,
            },
        ),
        201,
    )
    mobile = expect(
        client.post(
            "/api/v1/auth/login",
            json={"identifier": email, "password": ADMIN_PASSWORD},
        ),
        200,
    )
    return UUID(
        expect(
            client.get(
                "/api/v1/me",
                headers=bearer(mobile["access_token"]),
            ),
            200,
        )["id"]
    )


async def seed_first_administrator(settings: Settings, email: str) -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            async with session.begin():
                await bootstrap_initial_administrator(
                    session,
                    email=email,
                    password=ADMIN_PASSWORD,
                )
        async with sessions() as session:
            async with session.begin():
                await bootstrap_initial_platform_grant(
                    session,
                    admin_email=email,
                    market_code="MA",
                )
    finally:
        await engine.dispose()


async def seed_platform_grants(
    settings: Settings,
    *,
    actor_email: str,
    target_user_ids: list[UUID],
    expires_at: datetime | None = None,
) -> list[UUID]:
    """Test-only authority fixture; the production API cannot call this path."""

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    grant_ids: list[UUID] = []
    try:
        async with sessions() as session:
            async with session.begin():
                actor_id = await session.scalar(
                    select(User.id).where(User.email == actor_email)
                )
                assert actor_id is not None
                for user_id in target_user_ids:
                    grant = AdministrativeGrant(
                        user_id=user_id,
                        role_template=AdministrativeRoleTemplate.PLATFORM_ADMIN,
                        market_id=LEGACY_MARKET_ID,
                        granted_by_user_id=actor_id,
                        grant_reason="Isolated dual-control integration fixture.",
                        expires_at=expires_at,
                    )
                    session.add(grant)
                    await session.flush()
                    grant_ids.append(grant.id)
        return grant_ids
    finally:
        await engine.dispose()


async def bootstrap_quorum_members(
    settings: Settings,
    *,
    emails: list[str],
    change_reference: str,
) -> list[UUID]:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    grant_ids: list[UUID] = []
    try:
        for email in emails:
            async with sessions() as session:
                async with session.begin():
                    result = await bootstrap_platform_admin_quorum_member(
                        session,
                        user_email=email,
                        market_code="MA",
                        change_reference=change_reference,
                    )
                    grant_ids.append(result.grant_id)
        return grant_ids
    finally:
        await engine.dispose()


async def set_user_status(
    settings: Settings,
    *,
    user_id: UUID,
    status: UserStatus,
) -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            async with session.begin():
                user = await session.get(User, user_id)
                assert user is not None
                user.status = status
                user.updated_at = datetime.now(UTC)
    finally:
        await engine.dispose()


async def load_change_request(
    settings: Settings,
    request_id: UUID,
) -> AdministrativeGrantChangeRequest:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            request = await session.get(AdministrativeGrantChangeRequest, request_id)
            assert request is not None
            session.expunge(request)
            return request
    finally:
        await engine.dispose()


def test_staff_grant_changes_require_independent_decisions_and_are_replay_safe() -> None:
    settings = integration_settings()
    suffix = uuid4().hex[:10]
    maker_email = f"grant-maker-{suffix}@example.test"
    checker_email = f"grant-checker-{suffix}@example.test"
    reserve_email = f"grant-reserve-{suffix}@example.test"
    target_email = f"grant-target-{suffix}@example.test"
    asyncio.run(seed_first_administrator(settings, maker_email))

    with TestClient(create_app(settings=settings)) as client:
        _checker_id = register_user(client, checker_email, "Grant checker")
        _reserve_id = register_user(client, reserve_email, "Reserve administrator")
        target_id = register_user(client, target_email, "Scoped staff target")
        asyncio.run(
            bootstrap_quorum_members(
                settings,
                emails=[checker_email, reserve_email],
                change_reference=f"CHG-{suffix}",
            )
        )
        with pytest.raises(
            PlatformGrantBootstrapConflict,
            match="three-person.*already exists",
        ):
            asyncio.run(
                bootstrap_quorum_members(
                    settings,
                    emails=[target_email],
                    change_reference=f"CHG-CLOSED-{suffix}",
                )
            )
        maker_headers = login_operations(client, maker_email)
        checker_headers = login_operations(client, checker_email)

        create_key = f"grant-create-{suffix}"
        create_payload = {
            "user_id": str(target_id),
            "role_template": "CITY_MANAGER",
            "city_id": str(LEGACY_CITY_ID),
            "reason": "Reviewed city operations duty assignment.",
        }
        requested = expect(
            client.post(
                "/api/v1/operations/administrative-grant-requests/create",
                headers={**maker_headers, "Idempotency-Key": create_key},
                json=create_payload,
            ),
            201,
        )
        assert requested["status"] == "PENDING"
        assert requested["resulting_grant_id"] is None
        assert expect(
            client.post(
                "/api/v1/operations/administrative-grant-requests/create",
                headers={**maker_headers, "Idempotency-Key": create_key},
                json=create_payload,
            ),
            201,
        ) == requested

        decision_payload = {
            "expected_version": requested["optimistic_version"],
            "reason": "Independent scope and duty review completed.",
        }
        assert client.post(
            f"/api/v1/operations/administrative-grant-requests/{requested['id']}/approve",
            headers={**maker_headers, "Idempotency-Key": f"self-approve-{suffix}"},
            json=decision_payload,
        ).status_code == 409

        approve_key = f"grant-approve-{suffix}"
        approved = expect(
            client.post(
                f"/api/v1/operations/administrative-grant-requests/{requested['id']}/approve",
                headers={**checker_headers, "Idempotency-Key": approve_key},
                json=decision_payload,
            ),
            200,
        )
        assert approved["status"] == "APPROVED"
        assert approved["resulting_grant_id"] is not None
        assert approved["optimistic_version"] == 2
        assert expect(
            client.post(
                f"/api/v1/operations/administrative-grant-requests/{requested['id']}/approve",
                headers={**checker_headers, "Idempotency-Key": approve_key},
                json=decision_payload,
            ),
            200,
        ) == approved
        assert client.post(
            f"/api/v1/operations/administrative-grant-requests/{requested['id']}/approve",
            headers={
                **checker_headers,
                "Idempotency-Key": f"stale-approve-{suffix}",
            },
            json=decision_payload,
        ).status_code == 409

        queue = expect(
            client.get(
                "/api/v1/operations/administrative-grant-requests?status=APPROVED",
                headers=checker_headers,
            ),
            200,
        )
        assert any(item["id"] == requested["id"] for item in queue["items"])

        revoke_requested = expect(
            client.post(
                "/api/v1/operations/administrative-grant-requests/revoke",
                headers={
                    **maker_headers,
                    "Idempotency-Key": f"grant-revoke-request-{suffix}",
                },
                json={
                    "grant_id": approved["resulting_grant_id"],
                    "reason": "The temporary city operations duty ended.",
                },
            ),
            201,
        )
        revoked = expect(
            client.post(
                "/api/v1/operations/administrative-grant-requests/"
                f"{revoke_requested['id']}/approve",
                headers={
                    **checker_headers,
                    "Idempotency-Key": f"grant-revoke-approve-{suffix}",
                },
                json={
                    "expected_version": revoke_requested["optimistic_version"],
                    "reason": "Independent offboarding evidence was verified.",
                },
            ),
            200,
        )
        assert revoked["status"] == "APPROVED"
        grant = expect(
            client.get(
                "/api/v1/operations/administrative-grants"
                f"?user_id={target_id}&include_revoked=true",
                headers=maker_headers,
            ),
            200,
        )["items"][0]
        assert grant["revoked_at"] is not None


def test_pending_requests_can_be_rejected_cancelled_and_fail_when_target_changes() -> None:
    settings = integration_settings()
    suffix = uuid4().hex[:10]
    maker_email = f"grant-maker-{suffix}@example.test"
    checker_email = f"grant-checker-{suffix}@example.test"
    reserve_email = f"grant-reserve-{suffix}@example.test"
    target_email = f"grant-target-{suffix}@example.test"
    asyncio.run(seed_first_administrator(settings, maker_email))

    with TestClient(create_app(settings=settings)) as client:
        _checker_id = register_user(client, checker_email, "Grant checker")
        _reserve_id = register_user(client, reserve_email, "Reserve administrator")
        target_id = register_user(client, target_email, "Mutable target")
        asyncio.run(
            bootstrap_quorum_members(
                settings,
                emails=[checker_email, reserve_email],
                change_reference=f"CHG-{suffix}",
            )
        )
        maker_headers = login_operations(client, maker_email)
        checker_headers = login_operations(client, checker_email)

        def create(role: str, key: str):
            return expect(
                client.post(
                    "/api/v1/operations/administrative-grant-requests/create",
                    headers={**maker_headers, "Idempotency-Key": key},
                    json={
                        "user_id": str(target_id),
                        "role_template": role,
                        "city_id": str(LEGACY_CITY_ID),
                        "reason": f"Review the {role.lower()} duty assignment.",
                    },
                ),
                201,
            )

        rejected_request = create("SUPPORT_AGENT", f"reject-create-{suffix}")
        rejected = expect(
            client.post(
                "/api/v1/operations/administrative-grant-requests/"
                f"{rejected_request['id']}/reject",
                headers={
                    **checker_headers,
                    "Idempotency-Key": f"reject-decision-{suffix}",
                },
                json={
                    "expected_version": 1,
                    "reason": "Required support training evidence is incomplete.",
                },
            ),
            200,
        )
        assert rejected["status"] == "REJECTED"

        cancelled_request = create("ANALYST", f"cancel-create-{suffix}")
        assert client.post(
            f"/api/v1/operations/administrative-grant-requests/{cancelled_request['id']}/cancel",
            headers={
                **checker_headers,
                "Idempotency-Key": f"wrong-cancel-{suffix}",
            },
            json={"expected_version": 1, "reason": "Checker cannot cancel it."},
        ).status_code == 403
        cancelled = expect(
            client.post(
                "/api/v1/operations/administrative-grant-requests/"
                f"{cancelled_request['id']}/cancel",
                headers={
                    **maker_headers,
                    "Idempotency-Key": f"maker-cancel-{suffix}",
                },
                json={
                    "expected_version": 1,
                    "reason": "Duty request was withdrawn before approval.",
                },
            ),
            200,
        )
        assert cancelled["status"] == "CANCELLED"

        stale_target_request = create(
            "DRIVER_REVIEWER",
            f"stale-target-create-{suffix}",
        )
        asyncio.run(
            set_user_status(
                settings,
                user_id=target_id,
                status=UserStatus.SUSPENDED,
            )
        )
        response = client.post(
            "/api/v1/operations/administrative-grant-requests/"
            f"{stale_target_request['id']}/approve",
            headers={
                **checker_headers,
                "Idempotency-Key": f"stale-target-approve-{suffix}",
            },
            json={
                "expected_version": 1,
                "reason": "Attempt to approve after target suspension.",
            },
        )
        assert response.status_code == 409
        assert "no longer active" in error_message(response)
        durable = asyncio.run(
            load_change_request(settings, UUID(stale_target_request["id"]))
        )
        assert durable.status == AdministrativeGrantRequestStatus.PENDING
        assert durable.decided_at is None


def test_platform_admin_continuity_blocks_direct_reduction_below_two() -> None:
    settings = integration_settings()
    suffix = uuid4().hex[:10]
    maker_email = f"grant-maker-{suffix}@example.test"
    second_email = f"grant-second-{suffix}@example.test"
    asyncio.run(seed_first_administrator(settings, maker_email))

    with TestClient(create_app(settings=settings)) as client:
        second_id = register_user(client, second_email, "Second administrator")
        second_grant_id = asyncio.run(
            bootstrap_quorum_members(
                settings,
                emails=[second_email],
                change_reference=f"CHG-{suffix}",
            )
        )[0]
        maker_headers = login_operations(client, maker_email)
        response = client.delete(
            f"/api/v1/operations/administrative-grants/{second_grant_id}",
            params={"reason": "Continuity invariant integration attempt."},
            headers=maker_headers,
        )
        assert response.status_code == 409
        assert "fewer than two" in error_message(response)


def test_expiring_platform_admin_requires_two_longer_lived_successors() -> None:
    settings = integration_settings()
    suffix = uuid4().hex[:10]
    maker_email = f"grant-maker-{suffix}@example.test"
    checker_email = f"grant-checker-{suffix}@example.test"
    target_email = f"grant-target-{suffix}@example.test"
    asyncio.run(seed_first_administrator(settings, maker_email))

    with TestClient(create_app(settings=settings)) as client:
        checker_id = register_user(client, checker_email, "Expiring checker")
        target_id = register_user(client, target_email, "Future administrator")
        asyncio.run(
            seed_platform_grants(
                settings,
                actor_email=maker_email,
                target_user_ids=[checker_id],
                expires_at=datetime.now(UTC) + timedelta(days=1),
            )
        )
        maker_headers = login_operations(client, maker_email)
        checker_headers = login_operations(client, checker_email)
        requested = expect(
            client.post(
                "/api/v1/operations/administrative-grant-requests/create",
                headers={
                    **maker_headers,
                    "Idempotency-Key": f"expiring-admin-create-{suffix}",
                },
                json={
                    "user_id": str(target_id),
                    "role_template": "PLATFORM_ADMIN",
                    "market_id": str(LEGACY_MARKET_ID),
                    "expires_at": (
                        datetime.now(UTC) + timedelta(days=2)
                    ).isoformat(),
                    "reason": "Time-bounded platform duty continuity exercise.",
                },
            ),
            201,
        )
        response = client.post(
            f"/api/v1/operations/administrative-grant-requests/{requested['id']}/approve",
            headers={
                **checker_headers,
                "Idempotency-Key": f"expiring-admin-approve-{suffix}",
            },
            json={
                "expected_version": 1,
                "reason": "Approval must still satisfy expiry continuity.",
            },
        )
        assert response.status_code == 409
        assert "outlasts" in error_message(response)
