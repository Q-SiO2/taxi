"""PostGIS-backed payment capability lifecycle and scope proof."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from os import getenv
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from taximobile_api.core.config import Settings
from taximobile_api.domains.administration.bootstrap import bootstrap_initial_platform_grant
from taximobile_api.domains.auth.bootstrap import bootstrap_initial_administrator
from taximobile_api.domains.markets.constants import LEGACY_MARKET_ID
from taximobile_api.main import create_app


pytestmark = pytest.mark.integration
ADMIN_EMAIL = "payment-capability-admin@example.test"
ADMIN_PASSWORD = "Payment-capability-admin-password-2026"


def settings() -> Settings:
    if getenv("TAXIMOBILE_RUN_INTEGRATION") != "1":
        pytest.skip("Set TAXIMOBILE_RUN_INTEGRATION=1 with an isolated migrated PostGIS database.")
    result = Settings.from_environment()
    if result.environment != "test" or "taximobile_ci" not in result.database_url:
        pytest.fail("Payment capability integration requires the isolated taximobile_ci database.")
    return replace(result, allowed_hosts=("testserver", "localhost", "127.0.0.1"))


async def seed_admin(configuration: Settings) -> None:
    engine = create_async_engine(configuration.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            async with session.begin():
                await bootstrap_initial_administrator(
                    session, email=ADMIN_EMAIL, password=ADMIN_PASSWORD
                )
        async with sessions() as session:
            async with session.begin():
                await bootstrap_initial_platform_grant(
                    session, admin_email=ADMIN_EMAIL, market_code="MA"
                )
    finally:
        await engine.dispose()


def expect(response, code: int):
    assert response.status_code == code, response.text
    return response.json()


def test_recipient_and_payment_capability_lifecycle_is_scoped_and_versioned() -> None:
    configuration = settings()
    asyncio.run(seed_admin(configuration))
    suffix = uuid4().hex[:10]
    now = datetime.now(UTC) - timedelta(minutes=1)

    with TestClient(create_app(settings=configuration)) as client:
        login = expect(
            client.post(
                "/api/v1/operations/auth/login",
                json={
                    "identifier": ADMIN_EMAIL,
                    "password": ADMIN_PASSWORD,
                    "device_label": "payment capability integration",
                },
            ),
            200,
        )
        headers = {"Authorization": f"Bearer {login['access_token']}"}

        def city_and_operator(label: str, longitude: float):
            city = expect(
                client.post(
                    "/api/v1/operations/cities",
                    headers=headers,
                    json={
                        "market_id": str(LEGACY_MARKET_ID),
                        "code": f"payment-{label}-{suffix}",
                        "localized_name": {"en": label, "fr": label, "ar": "مدينة"},
                        "timezone": "Africa/Casablanca",
                        "presentation_centroid": {"longitude": longitude, "latitude": 33.57},
                    },
                ),
                201,
            )
            operator = expect(
                client.post(
                    "/api/v1/operations/operators",
                    headers=headers,
                    json={
                        "market_id": str(LEGACY_MARKET_ID),
                        "name": f"Payment {label} {suffix}",
                        "operator_type": "LOCAL_ENTITY",
                    },
                ),
                201,
            )
            operator = expect(
                client.patch(
                    f"/api/v1/operations/operators/{operator['id']}",
                    headers=headers,
                    json={"status": "ACTIVE"},
                ),
                200,
            )
            expect(
                client.post(
                    "/api/v1/operations/operator-city-assignments",
                    headers=headers,
                    json={
                        "operator_id": operator["id"],
                        "city_id": city["id"],
                        "service_type": "ON_DEMAND",
                        "effective_from": now.isoformat(),
                    },
                ),
                201,
            )
            return city, operator

        city_a, operator_a = city_and_operator("primary", -7.61)
        city_b, operator_b = city_and_operator("other", -6.84)

        recipient = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/payment-recipient-accounts",
                headers=headers,
                json={
                    "operator_id": operator_a["id"],
                    "label": f"settlement-{suffix}",
                    "recipient_name": "TaxiMobile City A",
                    "wallet_id": f"wallet-{suffix}",
                },
            ),
            201,
        )
        assert recipient["status"] == "DRAFT"
        recipient = expect(
            client.post(
                f"/api/v1/operations/payment-recipient-accounts/{recipient['id']}/verify",
                headers=headers,
                json={
                    "expected_version": recipient["optimistic_version"],
                    "reason": "Verified against the controlled settlement account register.",
                },
            ),
            200,
        )
        assert recipient["status"] == "VERIFIED"

        wrong_scope = client.post(
            f"/api/v1/operations/cities/{city_b['id']}/payment-capability-versions",
            headers=headers,
            json={
                "operator_id": operator_b["id"],
                "service_type": "ON_DEMAND",
                "version": f"wrong-{suffix}",
                "cash_enabled": True,
                "manual_transfer_enabled": True,
                "recipient_account_id": recipient["id"],
                "effective_from": now.isoformat(),
            },
        )
        assert wrong_scope.status_code == 409
        assert "same city and operator" in wrong_scope.text

        capability = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/payment-capability-versions",
                headers=headers,
                json={
                    "operator_id": operator_a["id"],
                    "service_type": "ON_DEMAND",
                    "version": f"payment-v1-{suffix}",
                    "cash_enabled": True,
                    "manual_transfer_enabled": True,
                    "recipient_account_id": recipient["id"],
                    "effective_from": now.isoformat(),
                },
            ),
            201,
        )
        for command, expected_status in (
            ("submit", "IN_REVIEW"),
            ("approve", "APPROVED"),
            ("activate", "ACTIVE"),
        ):
            capability = expect(
                client.post(
                    f"/api/v1/operations/payment-capability-versions/{capability['id']}/{command}",
                    headers=headers,
                    json={
                        "expected_version": capability["optimistic_version"],
                        "reason": f"Reviewed payment capability for {command}.",
                    },
                ),
                200,
            )
            assert capability["status"] == expected_status

        listed = expect(
            client.get(
                f"/api/v1/operations/cities/{city_a['id']}/payment-capability-versions",
                headers=headers,
                params={"operator_id": operator_a["id"]},
            ),
            200,
        )
        assert listed["total"] == 1
        assert listed["items"][0]["recipient_account_id"] == recipient["id"]

        retirement = client.post(
            f"/api/v1/operations/payment-recipient-accounts/{recipient['id']}/retire",
            headers=headers,
            json={
                "expected_version": recipient["optimistic_version"],
                "reason": "Attempt retirement while an active capability still uses it.",
            },
        )
        assert retirement.status_code == 409
        assert "active capability" in retirement.text
