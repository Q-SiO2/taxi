"""PostGIS-backed Phase 14 pricing-policy lifecycle and scope proof."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from os import getenv
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from taximobile_api.core.config import Settings
from taximobile_api.domains.administration.bootstrap import (
    bootstrap_initial_platform_grant,
)
from taximobile_api.domains.auth.bootstrap import bootstrap_initial_administrator
from taximobile_api.domains.markets.constants import LEGACY_MARKET_ID
from taximobile_api.main import create_app


pytestmark = pytest.mark.integration

ADMIN_EMAIL = "integration-admin@example.test"
ADMIN_PASSWORD = "Integration-admin-password-2026"
PRICING_PASSWORD = "Pricing-manager-password-2026"


def integration_settings() -> Settings:
    if getenv("TAXIMOBILE_RUN_INTEGRATION") != "1":
        pytest.skip(
            "Set TAXIMOBILE_RUN_INTEGRATION=1 with an isolated migrated PostGIS database."
        )
    settings = Settings.from_environment()
    if settings.environment != "test" or "taximobile_ci" not in settings.database_url:
        pytest.fail(
            "Pricing integration tests require TAXIMOBILE_ENV=test and taximobile_ci."
        )
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


def expect(response, status_code: int):
    assert response.status_code == status_code, response.text
    return response.json()


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(client: TestClient, path: str, email: str, password: str) -> dict:
    return expect(
        client.post(
            path,
            json={
                "identifier": email,
                "password": password,
                "device_label": "city pricing integration",
            },
        ),
        200,
    )


def test_scoped_pricing_policy_lifecycle_replacement_and_audit() -> None:
    settings = integration_settings()
    asyncio.run(seed_platform_administrator(settings))
    suffix = uuid4().hex[:12]
    effective_from = datetime.now(UTC) - timedelta(minutes=1)

    with TestClient(create_app(settings=settings)) as client:
        operations = login(
            client,
            "/api/v1/operations/auth/login",
            ADMIN_EMAIL,
            ADMIN_PASSWORD,
        )
        platform_headers = bearer(operations["access_token"])

        def create_city(code_prefix: str, longitude: float, latitude: float):
            return expect(
                client.post(
                    "/api/v1/operations/cities",
                    headers=platform_headers,
                    json={
                        "market_id": str(LEGACY_MARKET_ID),
                        "code": f"{code_prefix}-{suffix}",
                        "localized_name": {
                            "en": f"{code_prefix} pricing test",
                            "fr": f"{code_prefix} test tarification",
                            "ar": "مدينة اختبار الأسعار",
                        },
                        "timezone": "Africa/Casablanca",
                        "presentation_centroid": {
                            "longitude": longitude,
                            "latitude": latitude,
                        },
                    },
                ),
                201,
            )

        city_a = create_city("pricing-a", -6.84, 34.02)
        city_b = create_city("pricing-b", -5.83, 35.76)

        def create_operator_and_assignment(city: dict, label: str):
            operator = expect(
                client.post(
                    "/api/v1/operations/operators",
                    headers=platform_headers,
                    json={
                        "market_id": str(LEGACY_MARKET_ID),
                        "name": f"{label} operator {suffix}",
                        "operator_type": "LOCAL_ENTITY",
                    },
                ),
                201,
            )
            operator = expect(
                client.patch(
                    f"/api/v1/operations/operators/{operator['id']}",
                    headers=platform_headers,
                    json={"status": "ACTIVE"},
                ),
                200,
            )
            assignment = expect(
                client.post(
                    "/api/v1/operations/operator-city-assignments",
                    headers=platform_headers,
                    json={
                        "operator_id": operator["id"],
                        "city_id": city["id"],
                        "service_type": "ON_DEMAND",
                        "effective_from": effective_from.isoformat(),
                    },
                ),
                201,
            )
            return operator, assignment

        operator_a, _ = create_operator_and_assignment(city_a, "Primary")
        operator_b, _ = create_operator_and_assignment(city_b, "Other city")

        invalid_currency = client.post(
            f"/api/v1/operations/cities/{city_a['id']}/pricing-rules",
            headers=platform_headers,
            json={
                "operator_id": operator_a["id"],
                "name": "Wrong currency",
                "version": f"wrong-currency-{suffix}",
                "fixed_amount": "35.00",
                "currency": "USD",
                "effective_from": effective_from.isoformat(),
            },
        )
        assert invalid_currency.status_code == 409
        assert "market currency" in invalid_currency.text

        tariff = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/pricing-rules",
                headers=platform_headers,
                json={
                    "operator_id": operator_a["id"],
                    "service_type": "ON_DEMAND",
                    "booking_type": "IMMEDIATE",
                    "name": "City A regulated fare",
                    "version": f"tariff-v1-{suffix}",
                    "model": "FIXED",
                    "fixed_amount": "35.00",
                    "currency": "MAD",
                    "effective_from": effective_from.isoformat(),
                },
            ),
            201,
        )
        assert tariff["status"] == "DRAFT"
        assert client.patch(
            f"/api/v1/operations/pricing-rules/{tariff['id']}",
            headers=platform_headers,
            json={"expected_version": 99, "fixed_amount": "35.13"},
        ).status_code == 409
        tariff = expect(
            client.patch(
                f"/api/v1/operations/pricing-rules/{tariff['id']}",
                headers=platform_headers,
                json={"expected_version": 1, "fixed_amount": "35.13"},
            ),
            200,
        )
        assert tariff["optimistic_version"] == 2
        for command, expected_version in (("submit", 2), ("activate", 3)):
            tariff = expect(
                client.post(
                    f"/api/v1/operations/pricing-rules/{tariff['id']}/{command}",
                    headers=platform_headers,
                    json={
                        "expected_version": expected_version,
                        "reason": f"Reviewed tariff {command} for integration proof.",
                    },
                ),
                200,
            )
        assert tariff["status"] == "ACTIVE"
        # A replay after the successful commit is harmless even with the original
        # command version, while an edit remains forbidden.
        replay = expect(
            client.post(
                f"/api/v1/operations/pricing-rules/{tariff['id']}/activate",
                headers=platform_headers,
                json={
                    "expected_version": 3,
                    "reason": "Retry the already committed activation.",
                },
            ),
            200,
        )
        assert replay["optimistic_version"] == tariff["optimistic_version"]
        assert client.patch(
            f"/api/v1/operations/pricing-rules/{tariff['id']}",
            headers=platform_headers,
            json={"expected_version": tariff["optimistic_version"], "fixed_amount": "36.00"},
        ).status_code == 409

        fee = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/operator-fee-policies",
                headers=platform_headers,
                json={
                    "operator_id": operator_a["id"],
                    "service_type": "ON_DEMAND",
                    "version": f"fee-v1-{suffix}",
                    "calculation_mode": "PERCENTAGE_OF_TRANSPORT_FARE",
                    "funding_mode": "DRIVER_SETTLEMENT_DEDUCTION",
                    "percentage_rate": "5.0000",
                    "currency": "MAD",
                    "minimum_driver_net": "0.00",
                    "effective_from": effective_from.isoformat(),
                },
            ),
            201,
        )
        for command, expected_version in (("submit", 1), ("activate", 2)):
            fee = expect(
                client.post(
                    f"/api/v1/operations/operator-fee-policies/{fee['id']}/{command}",
                    headers=platform_headers,
                    json={
                        "expected_version": expected_version,
                        "reason": f"Reviewed fee {command} for integration proof.",
                    },
                ),
                200,
            )
        assert fee["status"] == "ACTIVE"
        assert fee["percentage_rate"] == "5.0000"

        scheduling = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/scheduling-policies",
                headers=platform_headers,
                json={
                    "operator_id": operator_a["id"],
                    "service_type": "ON_DEMAND",
                    "version": f"schedule-v1-{suffix}",
                    "surcharge_amount": "5.00",
                    "currency": "MAD",
                    "beneficiary": "DRIVER",
                    "effective_from": effective_from.isoformat(),
                },
            ),
            201,
        )
        for command, expected_version in (("submit", 1), ("activate", 2)):
            scheduling = expect(
                client.post(
                    f"/api/v1/operations/scheduling-policies/{scheduling['id']}/{command}",
                    headers=platform_headers,
                    json={
                        "expected_version": expected_version,
                        "reason": f"Reviewed scheduling {command} for integration proof.",
                    },
                ),
                200,
            )
        assert scheduling["status"] == "ACTIVE"

        replacement = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/pricing-rules",
                headers=platform_headers,
                json={
                    "operator_id": operator_a["id"],
                    "name": "City A replacement fare",
                    "version": f"tariff-v2-{suffix}",
                    "fixed_amount": "36.00",
                    "currency": "MAD",
                    "effective_from": effective_from.isoformat(),
                },
            ),
            201,
        )
        for command, expected_version in (("submit", 1), ("activate", 2)):
            replacement = expect(
                client.post(
                    f"/api/v1/operations/pricing-rules/{replacement['id']}/{command}",
                    headers=platform_headers,
                    json={
                        "expected_version": expected_version,
                        "reason": f"Reviewed replacement {command} for integration proof.",
                    },
                ),
                200,
            )
        previous = expect(
            client.get(
                f"/api/v1/operations/pricing-rules/{tariff['id']}",
                headers=platform_headers,
            ),
            200,
        )
        assert previous["status"] == "REPLACED"
        assert replacement["status"] == "ACTIVE"

        city_b_tariff = expect(
            client.post(
                f"/api/v1/operations/cities/{city_b['id']}/pricing-rules",
                headers=platform_headers,
                json={
                    "operator_id": operator_b["id"],
                    "name": "Other city draft fare",
                    "version": f"city-b-{suffix}",
                    "fixed_amount": "50.00",
                    "currency": "MAD",
                    "effective_from": effective_from.isoformat(),
                },
            ),
            201,
        )

        pricing_email = f"pricing-manager-{suffix}@example.test"
        expect(
            client.post(
                "/api/v1/auth/register",
                json={
                    "email": pricing_email,
                    "password": PRICING_PASSWORD,
                    "display_name": "Scoped Pricing Manager",
                },
            ),
            201,
        )
        mobile_tokens = login(
            client,
            "/api/v1/auth/login",
            pricing_email,
            PRICING_PASSWORD,
        )
        pricing_user_id = expect(
            client.get(
                "/api/v1/me",
                headers=bearer(mobile_tokens["access_token"]),
            ),
            200,
        )["id"]
        expect(
            client.post(
                "/api/v1/operations/administrative-grants",
                headers=platform_headers,
                json={
                    "user_id": pricing_user_id,
                    "role_template": "PRICING_MANAGER",
                    "city_id": city_a["id"],
                    "reason": "Phase 14 city pricing scope integration proof.",
                },
            ),
            201,
        )
        scoped_tokens = login(
            client,
            "/api/v1/operations/auth/login",
            pricing_email,
            PRICING_PASSWORD,
        )
        scoped_headers = bearer(scoped_tokens["access_token"])
        scoped_list = expect(
            client.get(
                f"/api/v1/operations/cities/{city_a['id']}/pricing-rules",
                headers=scoped_headers,
            ),
            200,
        )
        assert scoped_list["total"] == 2
        assert {item["id"] for item in scoped_list["items"]} == {
            tariff["id"],
            replacement["id"],
        }
        assert client.get(
            f"/api/v1/operations/cities/{city_b['id']}/pricing-rules",
            headers=scoped_headers,
        ).status_code == 404
        assert client.get(
            f"/api/v1/operations/pricing-rules/{city_b_tariff['id']}",
            headers=scoped_headers,
        ).status_code == 404
        assert client.post(
            f"/api/v1/operations/cities/{city_a['id']}/pricing-rules",
            headers=scoped_headers,
            json={
                "operator_id": operator_b["id"],
                "name": "Cross-scope tariff",
                "version": f"cross-scope-{suffix}",
                "fixed_amount": "1.00",
                "currency": "MAD",
                "effective_from": effective_from.isoformat(),
            },
        ).status_code == 404

        activation_audit = expect(
            client.get(
                "/api/v1/operations/audit-logs",
                headers=platform_headers,
                params={
                    "city_id": city_a["id"],
                    "action": "PRICING_RULE_ACTIVE",
                    "limit": 20,
                },
            ),
            200,
        )
        replacement_audit = next(
            item
            for item in activation_audit["items"]
            if item["resource_id"] == replacement["id"]
        )
        assert replacement_audit["operator_id"] == operator_a["id"]
        assert replacement_audit["changes"]["reason"].startswith(
            "Reviewed replacement activate"
        )
        assert replacement_audit["changes"]["replaced_version_ids"] == [tariff["id"]]
