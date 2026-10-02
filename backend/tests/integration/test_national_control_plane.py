"""PostGIS-backed Phase 12 scope, lifecycle, and compatibility proof."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from os import getenv
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from taximobile_api.core.config import Settings
from taximobile_api.domains.administration.models import (
    AdministrativeGrant,
    AdministrativeRoleTemplate,
)
from taximobile_api.domains.administration.bootstrap import bootstrap_initial_platform_grant
from taximobile_api.domains.auth.bootstrap import bootstrap_initial_administrator
from taximobile_api.domains.auth.models import User
from taximobile_api.domains.markets.constants import (
    LEGACY_CITY_ID,
    LEGACY_MARKET_ID,
    PILOT_ENTRY_CITY_READINESS_GATES,
    PUBLIC_ACTIVATION_CITY_READINESS_GATES,
)
from taximobile_api.domains.markets.models import Market, MarketStatus
from taximobile_api.domains.support.models import SupportTicket
from taximobile_api.domains.support.models import SupportTicketNote
from taximobile_api.domains.case_retention.models import CaseRetentionAction
from taximobile_api.integrations.case_pager import CasePagerMessage
from taximobile_api.main import create_app
from taximobile_api.workers.case_alerts import CaseAlertProcessor
from taximobile_api.workers.case_retention import CaseRetentionProcessor


pytestmark = pytest.mark.integration

ADMIN_EMAIL = "integration-admin@example.test"
ADMIN_PASSWORD = "Integration-admin-password-2026"
STAFF_PASSWORD = "Integration-city-manager-password-2026"


def integration_settings() -> Settings:
    if getenv("TAXIMOBILE_RUN_INTEGRATION") != "1":
        pytest.skip("Set TAXIMOBILE_RUN_INTEGRATION=1 with an isolated migrated PostGIS database.")
    settings = Settings.from_environment()
    if settings.environment != "test" or "taximobile_ci" not in settings.database_url:
        pytest.fail("Integration tests require TAXIMOBILE_ENV=test and an isolated taximobile_ci database.")
    assert settings.operations_password_login_enabled
    return settings


async def seed_platform_administrator(settings: Settings) -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            async with session.begin():
                await bootstrap_initial_administrator(
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
    finally:
        await engine.dispose()


async def seed_target_cross_market_history(
    settings: Settings,
    *,
    target_user_id: UUID,
) -> UUID:
    """Associate a target with another market without granting the acting admin access."""
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    market_id = uuid4()
    try:
        async with sessions() as session:
            async with session.begin():
                admin_id = await session.scalar(
                    select(User.id).where(User.email == ADMIN_EMAIL)
                )
                assert admin_id is not None
                session.add(
                    Market(
                        id=market_id,
                        code=f"XT{uuid4().hex[:6].upper()}",
                        name="Cross-market security test",
                        default_currency="MAD",
                        status=MarketStatus.ACTIVE,
                    )
                )
                # The grant only carries the market UUID, not an ORM relationship,
                # so make the parent row durable before SQLAlchemy orders the next
                # insert. This keeps the synthetic cross-market fixture independent
                # of mapper insertion-order heuristics.
                await session.flush()
                session.add(
                    AdministrativeGrant(
                        user_id=target_user_id,
                        role_template=AdministrativeRoleTemplate.PLATFORM_ADMIN,
                        market_id=market_id,
                        granted_by_user_id=admin_id,
                        grant_reason="Cross-market account security integration test.",
                    )
                )
        return market_id
    finally:
        await engine.dispose()


async def trigger_overdue_support_alert(
    settings: Settings,
    ticket_id: UUID,
) -> list[CasePagerMessage]:
    class RecordingPager:
        def __init__(self) -> None:
            self.messages: list[CasePagerMessage] = []

        async def send(self, message: CasePagerMessage) -> bool:
            self.messages.append(message)
            return True

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    pager = RecordingPager()
    try:
        async with sessions() as session:
            async with session.begin():
                await session.execute(
                    update(SupportTicket)
                    .where(SupportTicket.id == ticket_id)
                    .values(response_due_at=datetime.now(UTC) - timedelta(minutes=1))
                )
        processed = await CaseAlertProcessor(sessions, pager).process_once()
        assert processed >= 2  # one durable discovery plus one protected delivery
        return pager.messages
    finally:
        await engine.dispose()


async def expire_and_process_support_retention(
    settings: Settings,
    ticket_id: UUID,
) -> tuple[int, SupportTicket, CaseRetentionAction | None, int]:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            async with session.begin():
                await session.execute(
                    update(SupportTicket)
                    .where(SupportTicket.id == ticket_id)
                    .values(retention_until=datetime.now(UTC) - timedelta(minutes=1))
                )
        processed = await CaseRetentionProcessor(sessions).process_once()
        async with sessions() as session:
            ticket = await session.get(SupportTicket, ticket_id)
            assert ticket is not None
            action = await session.scalar(
                select(CaseRetentionAction).where(
                    CaseRetentionAction.support_ticket_id == ticket_id
                )
            )
            note_count = await session.scalar(
                select(func.count()).select_from(SupportTicketNote).where(
                    SupportTicketNote.ticket_id == ticket_id
                )
            )
            return processed, ticket, action, note_count or 0
    finally:
        await engine.dispose()


def expect(response, status_code: int):
    assert response.status_code == status_code, response.text
    return response.json()


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(client: TestClient, path: str, email: str, password: str):
    return expect(
        client.post(
            path,
            json={
                "identifier": email,
                "password": password,
                "device_label": "national control-plane integration",
            },
        ),
        200,
    )


def account_action_headers(token: str, key: UUID | None = None) -> dict[str, str]:
    return {
        **bearer(token),
        "Idempotency-Key": str(key or uuid4()),
    }


def test_market_scoped_account_containment_requires_complete_market_coverage() -> None:
    settings = integration_settings()
    asyncio.run(seed_platform_administrator(settings))
    suffix = uuid4().hex[:12]
    target_email = f"containment-target-{suffix}@example.test"
    unassociated_email = f"unassociated-target-{suffix}@example.test"

    with TestClient(create_app(settings=settings)) as client:
        operations_token = login(
            client,
            "/api/v1/operations/auth/login",
            ADMIN_EMAIL,
            ADMIN_PASSWORD,
        )["access_token"]
        target = expect(
            client.post(
                "/api/v1/auth/register",
                json={
                    "email": target_email,
                    "password": STAFF_PASSWORD,
                    "display_name": "Containment Target",
                },
            ),
            201,
        )["user"]
        target_tokens = login(
            client,
            "/api/v1/auth/login",
            target_email,
            STAFF_PASSWORD,
        )
        target_headers = bearer(target_tokens["access_token"])
        application = expect(
            client.post(
                "/api/v1/drivers/me/city-applications",
                headers=target_headers,
                json={
                    "city_id": str(LEGACY_CITY_ID),
                    "display_name": "Containment Target",
                },
            ),
            201,
        )
        assert application["city_id"] == str(LEGACY_CITY_ID)

        base = (
            f"/api/v1/operations/markets/{LEGACY_MARKET_ID}"
            f"/users/{target['id']}"
        )
        payload = {
            "reason_code": "ACCOUNT_COMPROMISE",
            "case_reference": f"SEC-{suffix.upper()}",
        }
        revoke_key = uuid4()
        revoked = expect(
            client.post(
                f"{base}/sessions/revoke",
                headers=account_action_headers(operations_token, revoke_key),
                json=payload,
            ),
            200,
        )
        assert revoked["sessions_revoked"] >= 1
        assert revoked["status"] == "ACTIVE"
        assert client.get("/api/v1/me", headers=target_headers).status_code == 401
        replay = expect(
            client.post(
                f"{base}/sessions/revoke",
                headers=account_action_headers(operations_token, revoke_key),
                json=payload,
            ),
            200,
        )
        assert replay == revoked
        assert client.post(
            f"{base}/sessions/revoke",
            headers=account_action_headers(operations_token, revoke_key),
            json={**payload, "reason_code": "SECURITY_INCIDENT"},
        ).status_code == 409

        target_tokens = login(
            client,
            "/api/v1/auth/login",
            target_email,
            STAFF_PASSWORD,
        )
        suspended = expect(
            client.post(
                f"{base}/suspend",
                headers=account_action_headers(operations_token),
                json={
                    "reason_code": "SAFETY_CONTAINMENT",
                    "case_reference": f"SAF-{suffix.upper()}",
                },
            ),
            200,
        )
        assert suspended["status"] == "SUSPENDED"
        assert suspended["sessions_revoked"] >= 1
        assert client.get(
            "/api/v1/me",
            headers=bearer(target_tokens["access_token"]),
        ).status_code == 401
        assert client.post(
            "/api/v1/auth/login",
            json={
                "identifier": target_email,
                "password": STAFF_PASSWORD,
                "device_label": "suspended containment target",
            },
        ).status_code == 401

        reactivated = expect(
            client.post(
                f"{base}/reactivate",
                headers=account_action_headers(operations_token),
                json={
                    "reason_code": "VERIFIED_USER_REQUEST",
                    "case_reference": f"SUP-{suffix.upper()}",
                },
            ),
            200,
        )
        assert reactivated["status"] == "ACTIVE"
        login(client, "/api/v1/auth/login", target_email, STAFF_PASSWORD)

        unassociated = expect(
            client.post(
                "/api/v1/auth/register",
                json={
                    "email": unassociated_email,
                    "password": STAFF_PASSWORD,
                    "display_name": "Unassociated Target",
                },
            ),
            201,
        )["user"]
        assert client.post(
            (
                f"/api/v1/operations/markets/{LEGACY_MARKET_ID}"
                f"/users/{unassociated['id']}/suspend"
            ),
            headers=account_action_headers(operations_token),
            json=payload,
        ).status_code == 404

        asyncio.run(
            seed_target_cross_market_history(
                settings,
                target_user_id=UUID(target["id"]),
            )
        )
        cross_market = client.post(
            f"{base}/sessions/revoke",
            headers=account_action_headers(operations_token),
            json={
                "reason_code": "SECURITY_INCIDENT",
                "case_reference": f"SEC-X-{suffix.upper()}",
            },
        )
        assert cross_market.status_code == 409
        assert "cross-market" in cross_market.json()["error"]["message"].lower()


def test_scoped_operations_and_repeatable_second_city_rollout() -> None:
    settings = integration_settings()
    asyncio.run(seed_platform_administrator(settings))
    suffix = uuid4().hex[:12]
    staff_email = f"city-manager-{suffix}@example.test"

    with TestClient(create_app(settings=settings)) as client:
        mobile_tokens = login(client, "/api/v1/auth/login", ADMIN_EMAIL, ADMIN_PASSWORD)
        operations_tokens = login(
            client,
            "/api/v1/operations/auth/login",
            ADMIN_EMAIL,
            ADMIN_PASSWORD,
        )
        mobile_headers = bearer(mobile_tokens["access_token"])
        operations_headers = bearer(operations_tokens["access_token"])

        # Audiences and refresh stores are isolated in both directions.
        assert client.get("/api/v1/operations/cities", headers=mobile_headers).status_code == 401
        assert client.get("/api/v1/me", headers=operations_headers).status_code == 401
        assert client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": operations_tokens["refresh_token"]},
        ).status_code == 401
        assert client.post(
            "/api/v1/operations/auth/refresh",
            json={"refresh_token": mobile_tokens["refresh_token"]},
        ).status_code == 401

        operations_session = expect(
            client.get("/api/v1/operations/auth/session", headers=operations_headers),
            200,
        )
        assert [grant["role_template"] for grant in operations_session["grants"]] == [
            "PLATFORM_ADMIN"
        ]
        markets = expect(
            client.get("/api/v1/operations/markets", headers=operations_headers),
            200,
        )
        assert any(item["id"] == str(LEGACY_MARKET_ID) for item in markets["items"])
        legacy_city = expect(
            client.get(
                f"/api/v1/operations/cities/{LEGACY_CITY_ID}",
                headers=operations_headers,
            ),
            200,
        )
        assert legacy_city["is_legacy_compatibility"] is True
        assert legacy_city["lifecycle_status"] == "ACTIVE"

        def create_city(code: str, en_name: str, longitude: float, latitude: float):
            return expect(
                client.post(
                    "/api/v1/operations/cities",
                    headers=operations_headers,
                    json={
                        "market_id": str(LEGACY_MARKET_ID),
                        "code": code,
                        "localized_name": {
                            "en": en_name,
                            "fr": en_name,
                            "ar": "مدينة اختبار",
                        },
                        "timezone": "Africa/Casablanca",
                        "presentation_centroid": {
                            "latitude": latitude,
                            "longitude": longitude,
                        },
                    },
                ),
                201,
            )

        city_a = create_city(f"rabat-{suffix}", "Rabat test", -6.8498, 34.0209)
        city_b = create_city(f"tangier-{suffix}", "Tangier test", -5.8339, 35.7595)

        expect(
            client.post(
                "/api/v1/auth/register",
                json={
                    "email": staff_email,
                    "password": STAFF_PASSWORD,
                    "display_name": "Integration City Manager",
                },
            ),
            201,
        )
        staff_mobile = login(client, "/api/v1/auth/login", staff_email, STAFF_PASSWORD)
        staff_id = expect(
            client.get("/api/v1/me", headers=bearer(staff_mobile["access_token"])),
            200,
        )["id"]
        grant = expect(
            client.post(
                "/api/v1/operations/administrative-grants",
                headers=operations_headers,
                json={
                    "user_id": staff_id,
                    "role_template": "CITY_MANAGER",
                    "city_id": city_a["id"],
                    "reason": "Independent city-configuration maker integration proof.",
                },
            ),
            201,
        )
        staff_operations = login(
            client,
            "/api/v1/operations/auth/login",
            staff_email,
            STAFF_PASSWORD,
        )
        staff_headers = bearer(staff_operations["access_token"])

        operator_one = expect(
            client.post(
                "/api/v1/operations/operators",
                headers=operations_headers,
                json={
                    "market_id": str(LEGACY_MARKET_ID),
                    "name": f"Rabat test operator {suffix}",
                    "operator_type": "LOCAL_ENTITY",
                },
            ),
            201,
        )
        operator_one = expect(
            client.patch(
                f"/api/v1/operations/operators/{operator_one['id']}",
                headers=operations_headers,
                json={"status": "ACTIVE"},
            ),
            200,
        )
        operator_two = expect(
            client.post(
                "/api/v1/operations/operators",
                headers=operations_headers,
                json={
                    "market_id": str(LEGACY_MARKET_ID),
                    "name": f"Rabat competing operator {suffix}",
                    "operator_type": "LOCAL_ENTITY",
                },
            ),
            201,
        )
        operator_two = expect(
            client.patch(
                f"/api/v1/operations/operators/{operator_two['id']}",
                headers=operations_headers,
                json={"status": "ACTIVE"},
            ),
            200,
        )

        effective_from = datetime.now(UTC) - timedelta(minutes=1)
        assignment_payload = {
            "city_id": city_a["id"],
            "service_type": "ON_DEMAND",
            "effective_from": effective_from.isoformat(),
        }
        assignment = expect(
            client.post(
                "/api/v1/operations/operator-city-assignments",
                headers=operations_headers,
                json={**assignment_payload, "operator_id": operator_one["id"]},
            ),
            201,
        )
        overlap = client.post(
            "/api/v1/operations/operator-city-assignments",
            headers=operations_headers,
            json={**assignment_payload, "operator_id": operator_two["id"]},
        )
        assert overlap.status_code == 409

        service_area = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/service-area-versions",
                headers=operations_headers,
                json={
                    "version": f"rabat-boundary-{suffix}",
                    "boundary": {
                        "type": "MultiPolygon",
                        "coordinates": [
                            [
                                [
                                    [-7.05, 33.85],
                                    [-6.65, 33.85],
                                    [-6.65, 34.20],
                                    [-7.05, 34.20],
                                    [-7.05, 33.85],
                                ]
                            ]
                        ],
                    },
                    "effective_from": effective_from.isoformat(),
                },
            ),
            201,
        )
        service_area = expect(
            client.post(
                f"/api/v1/operations/service-area-versions/{service_area['id']}/transitions",
                headers=operations_headers,
                json={
                    "target_status": "IN_REVIEW",
                    "expected_version": 1,
                    "reason": "Boundary reviewed for integration testing.",
                },
            ),
            200,
        )
        service_area = expect(
            client.post(
                f"/api/v1/operations/service-area-versions/{service_area['id']}/transitions",
                headers=operations_headers,
                json={
                    "target_status": "APPROVED",
                    "expected_version": 2,
                    "reason": "Boundary approved for integration testing.",
                },
            ),
            200,
        )
        tariff = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/pricing-rules",
                headers=operations_headers,
                json={
                    "operator_id": operator_one["id"],
                    "service_type": "ON_DEMAND",
                    "booking_type": "IMMEDIATE",
                    "name": f"Control-plane test tariff {suffix}",
                    "version": f"control-plane-{suffix}",
                    "model": "FIXED",
                    "fixed_amount": "40.00",
                    "currency": "MAD",
                    "effective_from": effective_from.isoformat(),
                },
            ),
            201,
        )
        for command, expected_version in (("submit", 1), ("activate", 2)):
            tariff = expect(
                client.post(
                    f"/api/v1/operations/pricing-rules/{tariff['id']}/{command}",
                    headers=operations_headers,
                    json={
                        "expected_version": expected_version,
                        "reason": f"Integration tariff {command} review.",
                    },
                ),
                200,
            )
        assert tariff["status"] == "ACTIVE"

        zero_fee_policy = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/operator-fee-policies",
                headers=operations_headers,
                json={
                    "operator_id": operator_one["id"],
                    "service_type": "ON_DEMAND",
                    "version": f"zero-fee-{suffix}",
                    "calculation_mode": "FLAT_PER_COMPLETED_BOOKING",
                    "funding_mode": "DRIVER_SETTLEMENT_DEDUCTION",
                    "flat_amount": "0.00",
                    "currency": "MAD",
                    "minimum_driver_net": "0.00",
                    "effective_from": effective_from.isoformat(),
                },
            ),
            201,
        )
        for command, expected_version in (("submit", 1), ("activate", 2)):
            zero_fee_policy = expect(
                client.post(
                    f"/api/v1/operations/operator-fee-policies/{zero_fee_policy['id']}/{command}",
                    headers=operations_headers,
                    json={
                        "expected_version": expected_version,
                        "reason": f"Integration zero-fee policy {command} review.",
                    },
                ),
                200,
            )
        assert zero_fee_policy["status"] == "ACTIVE"

        scheduling_policy = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/scheduling-policies",
                headers=operations_headers,
                json={
                    "operator_id": operator_one["id"],
                    "service_type": "ON_DEMAND",
                    "version": f"scheduling-{suffix}",
                    "surcharge_amount": "5.00",
                    "currency": "MAD",
                    "beneficiary": "DRIVER",
                    "effective_from": effective_from.isoformat(),
                },
            ),
            201,
        )
        for command, expected_version in (("submit", 1), ("activate", 2)):
            scheduling_policy = expect(
                client.post(
                    f"/api/v1/operations/scheduling-policies/{scheduling_policy['id']}/{command}",
                    headers=operations_headers,
                    json={
                        "expected_version": expected_version,
                        "reason": f"Integration scheduling policy {command} review.",
                    },
                ),
                200,
            )
        assert scheduling_policy["status"] == "ACTIVE"

        city_a = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/lifecycle-transitions",
                headers=operations_headers,
                json={
                    "target_status": "CONFIGURING",
                    "expected_version": city_a["optimistic_version"],
                    "reason": "Begin controlled city configuration.",
                },
            ),
            200,
        )

        driver_requirements = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/driver-requirement-versions",
                headers=operations_headers,
                json={
                    "version": f"rabat-drivers-{suffix}",
                    "effective_from": effective_from.isoformat(),
                    "items": [
                        {
                            "requirement_code": "DRIVER_PROFILE",
                            "evidence_type": "PROFILE",
                            "required": True,
                            "validity_rule_code": "PROFILE_OWNED",
                            "display_order": 0,
                            "localized_copy_key": "driver.requirement.profile",
                            "localized_label": {
                                "en": "Driver profile",
                                "fr": "Profil chauffeur",
                                "ar": "ملف السائق",
                            },
                            "localized_description": {
                                "en": "Confirm the account-owned driver profile.",
                                "fr": "Confirmez le profil chauffeur du compte.",
                                "ar": "أكد ملف السائق المملوك للحساب.",
                            },
                        }
                    ],
                },
            ),
            201,
        )
        for command, expected_version in (("submit", 1), ("activate", 2)):
            driver_requirements = expect(
                client.post(
                    f"/api/v1/operations/driver-requirement-versions/{driver_requirements['id']}/{command}",
                    headers=operations_headers,
                    json={
                        "expected_version": expected_version,
                        "reason": f"Integration driver requirement {command} review.",
                    },
                ),
                200,
            )
        payment_capability = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/payment-capability-versions",
                headers=operations_headers,
                json={
                    "operator_id": operator_one["id"],
                    "service_type": "ON_DEMAND",
                    "version": f"cash-only-{suffix}",
                    "cash_enabled": True,
                    "manual_transfer_enabled": False,
                    "effective_from": effective_from.isoformat(),
                },
            ),
            201,
        )
        for command in ("submit", "approve", "activate"):
            payment_capability = expect(
                client.post(
                    f"/api/v1/operations/payment-capability-versions/{payment_capability['id']}/{command}",
                    headers=operations_headers,
                    json={
                        "expected_version": payment_capability["optimistic_version"],
                        "reason": f"Integration cash capability {command} review.",
                    },
                ),
                200,
            )
        assert payment_capability["status"] == "ACTIVE"
        inactive_tariff = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/pricing-rules",
                headers=operations_headers,
                json={
                    "operator_id": operator_one["id"],
                    "service_type": "ON_DEMAND",
                    "booking_type": "IMMEDIATE",
                    "name": f"Inactive control-plane tariff {suffix}",
                    "version": f"inactive-control-plane-{suffix}",
                    "model": "FIXED",
                    "fixed_amount": "41.00",
                    "currency": "MAD",
                    "effective_from": effective_from.isoformat(),
                },
            ),
            201,
        )
        inactive_configuration = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/configuration-versions",
                headers=operations_headers,
                json={
                    "version": f"rabat-inactive-config-{suffix}",
                    "service_area_version_id": service_area["id"],
                    "driver_requirement_version_id": driver_requirements["id"],
                    "services": [
                        {
                            "service_type": "ON_DEMAND",
                            "operator_city_assignment_id": assignment["id"],
                            "tariff_version_id": inactive_tariff["id"],
                            "operator_fee_policy_version_id": zero_fee_policy["id"],
                            "scheduling_policy_version_id": scheduling_policy["id"],
                            "payment_capability_version_id": payment_capability["id"],
                            "enabled": True,
                        }
                    ],
                },
            ),
            201,
        )
        for command, expected_version in (("submit", 1), ("approve", 2)):
            inactive_configuration = expect(
                client.post(
                    f"/api/v1/operations/city-configuration-versions/{inactive_configuration['id']}/{command}",
                    headers=staff_headers if command == "submit" else operations_headers,
                    json={
                        "expected_version": expected_version,
                        "reason": f"Integration inactive tariff {command} review.",
                    },
                ),
                200,
            )
        inactive_activation = client.post(
            f"/api/v1/operations/city-configuration-versions/{inactive_configuration['id']}/activate",
            headers=operations_headers,
            json={
                "expected_version": inactive_configuration["optimistic_version"],
                "reason": "Inactive tariffs must fail closed at activation.",
            },
        )
        assert inactive_activation.status_code == 409
        assert "tariff must be active and effective" in inactive_activation.text

        configuration = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/configuration-versions",
                headers=operations_headers,
                json={
                    "version": f"rabat-config-{suffix}",
                    "service_area_version_id": service_area["id"],
                    "driver_requirement_version_id": driver_requirements["id"],
                    "services": [
                        {
                            "service_type": "ON_DEMAND",
                            "operator_city_assignment_id": assignment["id"],
                            "tariff_version_id": tariff["id"],
                            "operator_fee_policy_version_id": zero_fee_policy["id"],
                            "scheduling_policy_version_id": scheduling_policy["id"],
                            "payment_capability_version_id": payment_capability["id"],
                            "enabled": True,
                        }
                    ],
                },
            ),
            201,
        )
        for command, expected_version, expected_status in (
            ("submit", 1, "IN_REVIEW"),
            ("approve", 2, "APPROVED"),
            ("activate", 3, "ACTIVE"),
        ):
            configuration = expect(
                client.post(
                    f"/api/v1/operations/city-configuration-versions/{configuration['id']}/{command}",
                    headers=staff_headers if command == "submit" else operations_headers,
                    json={
                        "expected_version": expected_version,
                        "reason": f"Integration {command} review.",
                    },
                ),
                200,
            )
            assert configuration["status"] == expected_status
            if command == "submit":
                self_approval = client.post(
                    f"/api/v1/operations/city-configuration-versions/{configuration['id']}/approve",
                    headers=staff_headers,
                    json={
                        "expected_version": configuration["optimistic_version"],
                        "reason": "The configuration maker must not approve their own bundle.",
                    },
                )
                assert self_approval.status_code == 409
                assert "independent authorized reviewer" in self_approval.text

        premature_pilot_evidence = client.post(
            f"/api/v1/operations/city-configuration-versions/{configuration['id']}/readiness-decisions",
            headers=operations_headers,
            json={
                "gate_code": "PILOT_SERVICE_AND_FAIRNESS",
                "status": "PASSED",
                "non_secret_evidence_reference": f"analytics-review-{suffix}",
                "expected_configuration_version": configuration["optimistic_version"],
            },
        )
        assert premature_pilot_evidence.status_code == 409
        assert "requires a city in PILOT, ACTIVE, or PAUSED" in premature_pilot_evidence.text

        for gate_code in sorted(PILOT_ENTRY_CITY_READINESS_GATES):
            configuration = expect(
                client.post(
                    f"/api/v1/operations/city-configuration-versions/{configuration['id']}/readiness-decisions",
                    headers=operations_headers,
                    json={
                        "gate_code": gate_code,
                        "status": "PASSED",
                        "non_secret_evidence_reference": f"pilot-{gate_code.lower()}-{suffix}",
                        "expected_configuration_version": configuration["optimistic_version"],
                    },
                ),
                200,
            )
        assert configuration["missing_pilot_entry_gates"] == []
        assert configuration["missing_public_activation_gates"] == [
            "PILOT_SERVICE_AND_FAIRNESS"
        ]

        refreshed_city_a = expect(
            client.get(
                f"/api/v1/operations/cities/{city_a['id']}",
                headers=operations_headers,
            ),
            200,
        )
        city_a = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/lifecycle-transitions",
                headers=operations_headers,
                json={
                    "target_status": "PILOT",
                    "expected_version": refreshed_city_a["optimistic_version"],
                    "reason": "Begin the bounded, non-public Rabat pilot.",
                },
            ),
            200,
        )
        assert city_a["lifecycle_status"] == "PILOT"

        public_attempt = client.post(
            f"/api/v1/operations/cities/{city_a['id']}/lifecycle-transitions",
            headers=operations_headers,
            json={
                "target_status": "ACTIVE",
                "expected_version": city_a["optimistic_version"],
                "reason": "Pilot evidence is still incomplete.",
            },
        )
        assert public_attempt.status_code == 409
        assert "PILOT_SERVICE_AND_FAIRNESS" in public_attempt.text

        configuration = expect(
            client.post(
                f"/api/v1/operations/city-configuration-versions/{configuration['id']}/readiness-decisions",
                headers=operations_headers,
                json={
                    "gate_code": "PILOT_SERVICE_AND_FAIRNESS",
                    "status": "PASSED",
                    "non_secret_evidence_reference": f"analytics-review-{suffix}",
                    "expected_configuration_version": configuration["optimistic_version"],
                },
            ),
            200,
        )
        city_a = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/lifecycle-transitions",
                headers=operations_headers,
                json={
                    "target_status": "ACTIVE",
                    "expected_version": city_a["optimistic_version"],
                    "reason": "Publish only after reviewed pilot service and fairness evidence.",
                },
            ),
            200,
        )
        assert city_a["lifecycle_status"] == "ACTIVE"

        city_support_ticket = expect(
            client.post(
                "/api/v1/support/tickets",
                headers={**mobile_headers, "Idempotency-Key": f"support-city-{suffix}"},
                json={
                    "city_id": city_a["id"],
                    "category": "ACCOUNT_ACCESS",
                    "subject": "Rabat account support",
                    "description": "Scoped integration support case.",
                },
            ),
            201,
        )
        legacy_support_ticket = expect(
            client.post(
                "/api/v1/support/tickets",
                headers={**mobile_headers, "Idempotency-Key": f"support-legacy-{suffix}"},
                json={
                    "category": "ACCOUNT_ACCESS",
                    "subject": "Compatibility account support",
                    "description": "Legacy-scope integration support case.",
                },
            ),
            201,
        )
        assert city_support_ticket["city_id"] == city_a["id"]
        assert legacy_support_ticket["city_id"] == str(LEGACY_CITY_ID)
        pager_messages = asyncio.run(
            trigger_overdue_support_alert(settings, UUID(city_support_ticket["id"]))
        )
        assert len(pager_messages) == 1
        assert pager_messages[0].city_id == UUID(city_a["id"])
        assert pager_messages[0].case_type == "SUPPORT"

        replacement_configuration = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/configuration-versions",
                headers=operations_headers,
                json={
                    "version": f"rabat-active-replacement-{suffix}",
                    "service_area_version_id": service_area["id"],
                    "driver_requirement_version_id": driver_requirements["id"],
                    "services": [
                        {
                            "service_type": "ON_DEMAND",
                            "operator_city_assignment_id": assignment["id"],
                            "tariff_version_id": tariff["id"],
                            "operator_fee_policy_version_id": zero_fee_policy["id"],
                            "scheduling_policy_version_id": scheduling_policy["id"],
                            "payment_capability_version_id": payment_capability["id"],
                            "enabled": True,
                        }
                    ],
                },
            ),
            201,
        )
        for command in ("submit", "approve"):
            replacement_configuration = expect(
                client.post(
                    f"/api/v1/operations/city-configuration-versions/{replacement_configuration['id']}/{command}",
                    headers=staff_headers if command == "submit" else operations_headers,
                    json={
                        "expected_version": replacement_configuration["optimistic_version"],
                        "reason": f"Review active-city replacement {command} behavior.",
                    },
                ),
                200,
            )
        unsafe_replacement = client.post(
            f"/api/v1/operations/city-configuration-versions/{replacement_configuration['id']}/activate",
            headers=operations_headers,
            json={
                "expected_version": replacement_configuration["optimistic_version"],
                "reason": "An unreviewed replacement must not bypass active-city readiness.",
            },
        )
        assert unsafe_replacement.status_code == 409
        assert "operating city cannot replace its active configuration" in unsafe_replacement.text

        for gate_code in sorted(PUBLIC_ACTIVATION_CITY_READINESS_GATES):
            replacement_configuration = expect(
                client.post(
                    f"/api/v1/operations/city-configuration-versions/{replacement_configuration['id']}/readiness-decisions",
                    headers=operations_headers,
                    json={
                        "gate_code": gate_code,
                        "status": "PASSED",
                        "non_secret_evidence_reference": f"replacement-{gate_code.lower()}-{suffix}",
                        "expected_configuration_version": replacement_configuration[
                            "optimistic_version"
                        ],
                    },
                ),
                200,
            )
        configuration = expect(
            client.post(
                f"/api/v1/operations/city-configuration-versions/{replacement_configuration['id']}/activate",
                headers=operations_headers,
                json={
                    "expected_version": replacement_configuration["optimistic_version"],
                    "reason": "Activate the independently reviewed replacement bundle.",
                },
            ),
            200,
        )
        city_a = expect(
            client.get(
                f"/api/v1/operations/cities/{city_a['id']}",
                headers=operations_headers,
            ),
            200,
        )

        configuration = expect(
            client.post(
                f"/api/v1/operations/city-configuration-versions/{configuration['id']}/readiness-decisions",
                headers=operations_headers,
                json={
                    "gate_code": "POST_LAUNCH_REVIEW",
                    "status": "PASSED",
                    "non_secret_evidence_reference": f"post-launch-review-{suffix}",
                    "expected_configuration_version": configuration["optimistic_version"],
                },
            ),
            200,
        )
        assert configuration["post_launch_review_status"] == "PASSED"

        rollout = expect(
            client.get("/api/v1/operations/rollout-overview", headers=operations_headers),
            200,
        )
        rabat_rollout = next(item for item in rollout["cities"] if item["city_id"] == city_a["id"])
        assert rabat_rollout["pilot_entry_passed"] == rabat_rollout["pilot_entry_required"]
        assert rabat_rollout["public_activation_passed"] == rabat_rollout["public_activation_required"]
        assert rabat_rollout["post_launch_review_status"] == "PASSED"

        city_a = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/lifecycle-transitions",
                headers=operations_headers,
                json={
                    "target_status": "PAUSED",
                    "expected_version": city_a["optimistic_version"],
                    "reason": "Exercise the emergency city pause path.",
                },
            ),
            200,
        )
        city_a = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/lifecycle-transitions",
                headers=operations_headers,
                json={
                    "target_status": "ACTIVE",
                    "expected_version": city_a["optimistic_version"],
                    "reason": "Resume after controlled pause verification.",
                },
            ),
            200,
        )

        support_grant = expect(
            client.post(
                "/api/v1/operations/administrative-grants",
                headers=operations_headers,
                json={
                    "user_id": staff_id,
                    "role_template": "SUPPORT_AGENT",
                    "city_id": city_a["id"],
                    "reason": "City-scoped support queue integration proof.",
                },
            ),
            201,
        )
        scoped_cities = expect(
            client.get("/api/v1/operations/cities?limit=1", headers=staff_headers),
            200,
        )
        assert scoped_cities["total"] == 1
        assert [item["id"] for item in scoped_cities["items"]] == [city_a["id"]]
        scoped_support = expect(
            client.get("/api/v1/operations/support/tickets", headers=staff_headers),
            200,
        )
        assert scoped_support["total"] == 1
        assert [item["id"] for item in scoped_support["items"]] == [
            city_support_ticket["id"]
        ]
        assert client.get(
            f"/api/v1/operations/support/tickets/{legacy_support_ticket['id']}",
            headers=staff_headers,
        ).status_code == 404
        scoped_alerts = expect(
            client.get("/api/v1/operations/case-alerts", headers=staff_headers),
            200,
        )
        assert scoped_alerts["total"] == 1
        assert scoped_alerts["items"][0]["case_id"] == city_support_ticket["id"]
        acknowledged_alert = expect(
            client.post(
                f"/api/v1/operations/case-alerts/{scoped_alerts['items'][0]['id']}/acknowledge",
                headers={**staff_headers, "Idempotency-Key": f"ack-alert-{suffix}"},
                json={"reason": "City support duty owner accepted the overdue case."},
            ),
            200,
        )
        assert acknowledged_alert["status"] == "ACKNOWLEDGED"
        support_triage_headers = {
            **staff_headers,
            "Idempotency-Key": f"scoped-support-triage-{suffix}",
        }
        scoped_triage_payload = {
            "priority": "URGENT",
            "participant_message": "A city support agent is reviewing this request.",
            "internal_note": "Scoped support ownership accepted for integration proof.",
        }
        triaged_support = expect(
            client.post(
                f"/api/v1/operations/support/tickets/{city_support_ticket['id']}/triage",
                headers=support_triage_headers,
                json=scoped_triage_payload,
            ),
            200,
        )
        assert triaged_support["status"] == "IN_PROGRESS"
        assert triaged_support["assigned_to_user_id"] == staff_id
        assert expect(
            client.post(
                f"/api/v1/operations/support/tickets/{city_support_ticket['id']}/triage",
                headers=support_triage_headers,
                json=scoped_triage_payload,
            ),
            200,
        ) == triaged_support
        assert client.post(
            f"/api/v1/operations/support/tickets/{legacy_support_ticket['id']}/triage",
            headers={
                **staff_headers,
                "Idempotency-Key": f"cross-city-support-triage-{suffix}",
            },
            json=scoped_triage_payload,
        ).status_code == 404
        resolved_support = expect(
            client.post(
                f"/api/v1/operations/support/tickets/{city_support_ticket['id']}/transition",
                headers={
                    **staff_headers,
                    "Idempotency-Key": f"scoped-support-resolve-{suffix}",
                },
                json={
                    "target_status": "RESOLVED",
                    "resolution_code": "INFORMATION_PROVIDED",
                    "participant_message": "The reviewed account guidance is now available.",
                    "internal_note": "Controlled city support resolution completed.",
                },
            ),
            200,
        )
        assert resolved_support["status"] == "RESOLVED"
        closed_support = expect(
            client.post(
                f"/api/v1/operations/support/tickets/{city_support_ticket['id']}/transition",
                headers={
                    **staff_headers,
                    "Idempotency-Key": f"scoped-support-close-{suffix}",
                },
                json={
                    "target_status": "CLOSED",
                    "resolution_code": "INFORMATION_PROVIDED",
                    "participant_message": "This support case is now closed.",
                    "internal_note": "Controlled retention integration case closed.",
                },
            ),
            200,
        )
        assert closed_support["retention_until"] is not None

        hold_payload = {
            "case_kind": "SUPPORT",
            "case_id": city_support_ticket["id"],
            "reason_code": "DISPUTE_PRESERVATION",
            "authority_reference": f"LEGAL-{suffix}",
            "review_due_at": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
        }
        legal_hold_headers = {
            **operations_headers,
            "Idempotency-Key": f"case-hold-{suffix}",
        }
        legal_hold = expect(
            client.post(
                "/api/v1/operations/case-retention/holds",
                headers=legal_hold_headers,
                json=hold_payload,
            ),
            201,
        )
        assert legal_hold["status"] == "ACTIVE"
        assert expect(
            client.post(
                "/api/v1/operations/case-retention/holds",
                headers=legal_hold_headers,
                json=hold_payload,
            ),
            201,
        ) == legal_hold

        processed, held_ticket, held_action, held_note_count = asyncio.run(
            expire_and_process_support_retention(
                settings,
                UUID(city_support_ticket["id"]),
            )
        )
        assert processed == 0
        assert held_ticket.user_id is not None
        assert held_ticket.description == "Scoped integration support case."
        assert held_action is None
        assert held_note_count > 0

        released_hold = expect(
            client.post(
                f"/api/v1/operations/case-retention/holds/{legal_hold['id']}/release",
                headers={
                    **operations_headers,
                    "Idempotency-Key": f"case-hold-release-{suffix}",
                },
                json={"reason_code": "OBLIGATION_ENDED"},
            ),
            200,
        )
        assert released_hold["status"] == "RELEASED"

        processed, erased_ticket, retention_action, remaining_notes = asyncio.run(
            expire_and_process_support_retention(
                settings,
                UUID(city_support_ticket["id"]),
            )
        )
        assert processed == 1
        assert erased_ticket.user_id is None
        assert erased_ticket.ride_id is None
        assert erased_ticket.assigned_to_user_id is None
        assert erased_ticket.subject == ""
        assert erased_ticket.description == ""
        assert erased_ticket.latest_public_message is None
        assert erased_ticket.retention_action == "PERSONAL_DATA_ERASED"
        assert retention_action is not None
        assert retention_action.erased_note_count == held_note_count
        assert remaining_notes == 0
        assert client.get(
            f"/api/v1/support/tickets/{city_support_ticket['id']}",
            headers=mobile_headers,
        ).status_code == 403
        assert client.get(
            f"/api/v1/operations/support/tickets/{city_support_ticket['id']}",
            headers=staff_headers,
        ).status_code == 404
        retention_actions = expect(
            client.get(
                f"/api/v1/operations/case-retention/actions?city_id={city_a['id']}",
                headers=operations_headers,
            ),
            200,
        )
        assert any(
            item["case_id"] == city_support_ticket["id"]
            and item["action"] == "PERSONAL_DATA_ERASED"
            for item in retention_actions["items"]
        )
        assert client.get(
            f"/api/v1/operations/cities/{city_b['id']}",
            headers=staff_headers,
        ).status_code == 404
        assert client.post(
            "/api/v1/operations/cities",
            headers=staff_headers,
            json={
                "market_id": str(LEGACY_MARKET_ID),
                "code": f"forbidden-{suffix}",
                "localized_name": {"en": "Forbidden", "fr": "Interdit", "ar": "ممنوع"},
                "timezone": "Africa/Casablanca",
                "presentation_centroid": {"latitude": 34.0, "longitude": -6.8},
            },
        ).status_code == 403

        scoped_audit = expect(
            client.get("/api/v1/operations/audit-logs?limit=100", headers=staff_headers),
            200,
        )
        assert scoped_audit["total"] > 0
        assert all(item["city_id"] == city_a["id"] for item in scoped_audit["items"])
        cross_city_audit = expect(
            client.get(
                f"/api/v1/operations/audit-logs?city_id={city_b['id']}",
                headers=staff_headers,
            ),
            200,
        )
        assert cross_city_audit["total"] == 0

        expect(
            client.delete(
                f"/api/v1/operations/administrative-grants/{grant['id']}?reason=Integration%20scope%20test%20complete",
                headers=operations_headers,
            ),
            200,
        )
        expect(
            client.delete(
                f"/api/v1/operations/administrative-grants/{support_grant['id']}?reason=Integration%20support%20scope%20test%20complete",
                headers=operations_headers,
            ),
            200,
        )
        assert client.get("/api/v1/operations/cities", headers=staff_headers).status_code == 403

        expect(
            client.post("/api/v1/operations/auth/logout", headers=staff_headers),
            200,
        )
        assert client.get("/api/v1/operations/cities", headers=staff_headers).status_code == 401

        expect(
            client.post("/api/v1/operations/auth/logout", headers=operations_headers),
            200,
        )
        assert client.get("/api/v1/operations/cities", headers=operations_headers).status_code == 401
