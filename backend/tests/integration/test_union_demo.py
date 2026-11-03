"""Real seed + migrated PostGIS + HTTP/worker proof, not native UX acceptance.

Use the normal guarded CI database runner. Login material stays in memory;
assertions never include login bodies, database URLs, or access tokens.
Routing, OS GPS, map rendering and push delivery are separate device tests.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from os import getenv
from time import monotonic, sleep
from uuid import uuid4
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from taximobile_api.core.config import Settings
from taximobile_api.domains.markets.constants import LEGACY_CITY_ID
from taximobile_api.domains.markets.constants import LEGACY_OPERATOR_ID
from taximobile_api.domains.markets.models import City, CityConfigurationService, ServiceType
from taximobile_api.domains.pricing.models import (
    BookingType, PricingModel, PricingRule, PricingRuleStatus,
)
from taximobile_api.main import create_app
from taximobile_api.operations.ux_demo_seed import DEMO_CONFIRMATION, DemoProfile, seed_demo


pytestmark = pytest.mark.integration


def settings_for_demo_test() -> Settings:
    if getenv("TAXIMOBILE_RUN_INTEGRATION") != "1":
        pytest.skip("Union demo requires the guarded isolated PostGIS integration runner.")
    settings = Settings.from_environment()
    database = make_url(settings.database_url).database or ""
    assert settings.environment == "test"
    assert database.startswith("taximobile_ci_test_")
    return replace(
        settings, process_role="all", firebase_project_id=None,
        case_pager_url=None, case_pager_token=None,
        manual_transfer_enabled=False, manual_transfer_recipient_name=None,
        manual_transfer_bank_account=None, manual_transfer_wallet_id=None,
        matching_poll_seconds=0.05, scheduling_poll_seconds=0.1,
    )


def body(response, expected=200):
    assert response.status_code == expected, f"HTTP {response.status_code}, expected {expected}"
    return response.json()


def login(client, seed, persona):
    response = client.post("/api/v1/auth/login", json={
        "identifier": seed["accounts"][persona]["email"],
        "password": seed["password"],
        "device_label": "Union demo integration",
    })
    result = body(response)
    return {"Authorization": f"Bearer {result['access_token']}"}


def command(headers):
    return {**headers, "Idempotency-Key": str(uuid4())}


def seed_local_clone(settings, profile):
    # The clone is independently guarded above and by the autouse fixture.
    # Only the seeder gets development mode; the application remains in test.
    return asyncio.run(seed_demo(
        replace(settings, environment="development"),
        confirmation=DEMO_CONFIRMATION,
        profile=profile,
    ))


async def pin_prior_tariff(settings):
    """Reproduce the configured-ID path, not merely legacy active-tariff lookup."""
    engine = create_async_engine(settings.database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session, session.begin():
            city = await session.get(City, LEGACY_CITY_ID)
            service = await session.scalar(select(CityConfigurationService).where(
                CityConfigurationService.configuration_version_id == city.active_configuration_version_id,
                CityConfigurationService.service_type == ServiceType.ON_DEMAND,
            ))
            prior = PricingRule(
                city_id=LEGACY_CITY_ID, operator_id=LEGACY_OPERATOR_ID,
                service_type=ServiceType.ON_DEMAND, booking_type=BookingType.IMMEDIATE,
                name="Synthetic prior pinned fare", version=f"prior-demo-{uuid4().hex}",
                model=PricingModel.FIXED, fixed_amount=Decimal("17.00"), currency="MAD",
                status=PricingRuleStatus.ACTIVE, effective_from=datetime.now(UTC),
            )
            session.add(prior)
            await session.flush()
            service.tariff_version_id = prior.id
    finally:
        await engine.dispose()


TRIP = {
    "city_id": str(LEGACY_CITY_ID),
    "pickup": {"latitude": 33.5731, "longitude": -7.5898, "address": "United Nations Square"},
    "destination": {"latitude": 33.5899, "longitude": -7.6039, "address": "Casa-Port"},
}


@pytest.mark.parametrize("profile", list(DemoProfile))
def test_demo_profiles_keep_quotes_catalog_and_history_coherent(profile):
    settings = settings_for_demo_test()
    asyncio.run(pin_prior_tariff(settings))
    seed = seed_local_clone(settings, profile)
    assert seed["profile"] == profile.value
    with TestClient(create_app(settings=settings)) as client:
        passenger = login(client, seed, "passenger_rich")
        driver = login(client, seed, "driver_rich")
        estimate = body(client.post("/api/v1/rides/estimate", headers=passenger, json=TRIP))
        assert estimate["estimate"]["amount"] == "35.00"
        assert estimate["estimate"]["economics"]["operator_service_fee"] == "0.00"
        assert estimate["payment_methods"] == ["CASH"]
        routes = body(client.get(f"/api/v1/cities/{LEGACY_CITY_ID}/fixed-routes"))
        assert routes["routes"]
        # Public service publication must not disclose live taxi supply.
        assert not ({"drivers", "driver_locations", "online_taxis"} & routes.keys())
        rides = body(client.get("/api/v1/rides", headers=passenger))["items"]
        active = [ride for ride in rides if ride["status"] != "COMPLETED"]
        assert len(active) == (0 if profile == DemoProfile.UNION_LIVE else 1)
        availability = body(client.get("/api/v1/drivers/me/availability", headers=driver))
        assert availability["status"] == (
            "OFFLINE" if profile == DemoProfile.UNION_LIVE else "EN_ROUTE"
        )
        for ride in rides:
            if ride["status"] != "COMPLETED":
                continue
            receipt = body(client.get(f"/api/v1/rides/{ride['id']}/receipt", headers=passenger))
            assert receipt["fare"]["economics"]["expected_driver_net"] == "35.00"
            assert receipt["fare"]["economics"]["operator_allocation"] == "0.00"
        notifications = body(client.get("/api/v1/notifications", headers=passenger))["items"]
        completed_notifications = 0
        assigned_notifications = 0
        for notification in notifications:
            if notification["type"] not in {"RIDE_COMPLETED", "DRIVER_ASSIGNED"}:
                continue  # scheduled-booking worker events do not carry ride_id
            ride = body(client.get(
                f"/api/v1/rides/{notification['data']['ride_id']}", headers=passenger,
            ))
            if notification["type"] == "RIDE_COMPLETED":
                completed_notifications += 1
                assert ride["status"] == "COMPLETED"
            elif notification["type"] == "DRIVER_ASSIGNED":
                assigned_notifications += 1
                assert profile == DemoProfile.UX_REVIEW
                assert ride["status"] == "DRIVER_EN_ROUTE"
        assert completed_notifications == 1
        assert assigned_notifications == (0 if profile == DemoProfile.UNION_LIVE else 1)


def test_additive_union_seed_keeps_existing_accounts_and_latest_quote_usable():
    settings = settings_for_demo_test()
    first = seed_local_clone(settings, DemoProfile.UNION_LIVE)
    second = seed_local_clone(settings, DemoProfile.UNION_LIVE)
    assert first["accounts"]["passenger_rich"]["email"] != second["accounts"]["passenger_rich"]["email"]
    with TestClient(create_app(settings=settings)) as client:
        for seed in (first, second):
            passenger = login(client, seed, "passenger_rich")
            estimate = body(client.post("/api/v1/rides/estimate", headers=passenger, json=TRIP))
            assert estimate["estimate"]["amount"] == "35.00"
            assert body(client.get("/api/v1/rides", headers=passenger))["total"] == 2


def test_union_demo_new_cash_ride_uses_real_matching_and_payment_authority():
    settings = settings_for_demo_test()
    seed = seed_local_clone(settings, DemoProfile.UNION_LIVE)
    with TestClient(create_app(settings=settings)) as client:
        passenger = login(client, seed, "passenger_rich")
        driver = login(client, seed, "driver_rich")
        pending = login(client, seed, "driver_pending")
        body(client.post(
            "/api/v1/drivers/me/availability/online", headers=pending,
        ), 409)
        body(client.post(
            "/api/v1/drivers/me/availability/online", headers=driver,
        ), 409)  # no seeded GPS for a live demo
        body(client.post("/api/v1/drivers/me/location", headers=driver, json={
            "latitude": 33.5731, "longitude": -7.5898,
            "observed_at": datetime.now(UTC).isoformat(), "accuracy": 8,
        }))
        online = body(client.post(
            "/api/v1/drivers/me/availability/online", headers=driver,
            json={"city_id": str(LEGACY_CITY_ID), "service_type": "ON_DEMAND"},
        ))
        assert online["status"] == "AVAILABLE"
        request_headers = command(passenger)
        ride = body(client.post(
            "/api/v1/rides", headers=request_headers, json={**TRIP, "payment_method": "CASH"},
        ), 201)
        replay = body(client.post(
            "/api/v1/rides", headers=request_headers, json={**TRIP, "payment_method": "CASH"},
        ), 201)
        assert replay["id"] == ride["id"]
        assert ride["driver"] is None
        deadline = monotonic() + 10
        offers = []
        while monotonic() < deadline:
            offers = body(client.get("/api/v1/drivers/me/ride-offers", headers=driver))["offers"]
            if offers:
                break
            sleep(0.05)
        assert len(offers) == 1
        accepted = body(client.post(
            f"/api/v1/ride-offers/{offers[0]['id']}/accept", headers=driver,
        ))
        assert accepted["status"] == "ACCEPTED"
        for action, expected in (
            ("en-route", "DRIVER_EN_ROUTE"), ("arrived", "DRIVER_ARRIVED"),
            ("start", "IN_PROGRESS"),
        ):
            assert body(client.post(
                f"/api/v1/rides/{ride['id']}/{action}", headers=driver,
            ))["status"] == expected
        completed = body(client.post(
            f"/api/v1/rides/{ride['id']}/complete", headers=command(driver),
            json={"latitude": 33.5899, "longitude": -7.6039},
        ))
        assert completed["status"] == "COMPLETED"
        receipt_url = f"/api/v1/rides/{ride['id']}/receipt"
        assert body(client.get(receipt_url, headers=passenger))["payment"]["status"] == "PENDING"
        body(client.post(
            f"/api/v1/rides/{ride['id']}/payments/cash/settle", headers=command(passenger),
        ), 404)  # passenger has no driver profile; existing API conceals it
        settle_headers = command(driver)
        payment_url = f"/api/v1/rides/{ride['id']}/payments/cash/settle"
        settled = body(client.post(payment_url, headers=settle_headers))
        assert settled["status"] == "COMPLETED"
        assert body(client.post(payment_url, headers=settle_headers))["id"] == settled["id"]
        receipt = body(client.get(receipt_url, headers=passenger))
        assert receipt["payment"] == {"method": "CASH", "status": "COMPLETED"}
        assert receipt["fare"]["amount"] == "35.00"
        rating = body(client.post(
            f"/api/v1/rides/{ride['id']}/rating", headers=passenger,
            json={"score": 5, "comment": "Synthetic union rehearsal"},
        ), 201)
        assert rating["score"] == 5
        assert body(client.get(
            "/api/v1/rides?status=COMPLETED", headers=passenger,
        ))["total"] == 3


def test_union_demo_recruitment_uses_scoped_reviewer_and_keeps_rejection_ineligible():
    """The seeded console persona reviews an actual applicant-owned submission.

    This proves API authority in the same fixture used by browser rehearsal;
    it does not substitute for rendered/mobile document or eligibility checks.
    """
    settings = replace(settings_for_demo_test(), operations_password_login_enabled=True)
    seed = seed_local_clone(settings, DemoProfile.UNION_LIVE)
    with TestClient(create_app(settings=settings)) as client:
        applicant = login(client, seed, "passenger_empty")
        other = login(client, seed, "passenger_rich")
        catalog = body(client.get("/api/v1/drivers/recruiting-cities"))
        assert any(city["id"] == str(LEGACY_CITY_ID) for city in catalog["items"])
        application = body(client.post(
            "/api/v1/drivers/me/city-applications", headers=applicant,
            json={"city_id": str(LEGACY_CITY_ID), "display_name": "Synthetic union applicant"},
        ), 201)
        applicant_url = f"/api/v1/drivers/me/city-applications/{application['id']}"
        assert application["status"] == "NOT_STARTED"
        assert application["authorization"] is None
        assert application["document_upload_available"] is False
        body(client.get(applicant_url, headers=other), 404)
        body(client.post(
            "/api/v1/drivers/me/city-applications", headers=other,
            json={"city_id": str(LEGACY_CITY_ID), "status": "APPROVED"},
        ), 422)
        submitted = body(client.post(f"{applicant_url}/submit", headers=applicant))
        assert submitted["status"] == "SUBMITTED"
        assert body(client.post(f"{applicant_url}/submit", headers=applicant)) == submitted
        body(client.post("/api/v1/drivers/me/location", headers=applicant, json={
            "latitude": 33.5731, "longitude": -7.5898,
            "observed_at": datetime.now(UTC).isoformat(), "accuracy": 8,
        }), 422)  # an unverified applicant must not seed live supply GPS
        online_url = "/api/v1/drivers/me/availability/online"
        online_payload = {"city_id": str(LEGACY_CITY_ID), "service_type": "ON_DEMAND"}
        denied = body(client.post(online_url, headers=applicant, json=online_payload), 409)
        assert denied["error"]["message"] == "Driver account is not active."
        operations = body(client.post("/api/v1/operations/auth/login", json={
            "identifier": seed["accounts"]["operations_recruitment"]["email"],
            "password": seed["password"], "device_label": "Synthetic recruitment rehearsal",
        }))
        reviewer = {"Authorization": f"Bearer {operations['access_token']}"}
        queue = body(client.get(
            f"/api/v1/operations/driver-applications?city_id={LEGACY_CITY_ID}", headers=reviewer,
        ))
        assert any(item["id"] == application["id"] for item in queue["items"])
        body(client.get(
            f"/api/v1/operations/cities/{uuid4()}/driver-requirement-versions", headers=reviewer,
        ), 404)
        detail_url = f"/api/v1/operations/driver-applications/{application['id']}"
        body(client.get(detail_url, headers=applicant), 401)
        assert body(client.get(detail_url, headers=reviewer))["application"]["status"] == "SUBMITTED"
        version = submitted["optimistic_version"]
        for decision, reason, expected in (
            ("START_REVIEW", "MANUAL_REVIEW_STARTED", "UNDER_REVIEW"),
            ("REJECT", "JURISDICTION_REQUIREMENT_NOT_MET", "REJECTED"),
        ):
            payload = {
                "expected_version": version, "decision": decision, "reason_code": reason,
                "applicant_safe_message": "Synthetic union rehearsal decision; no real eligibility review.",
            }
            headers = command(reviewer)
            result = body(client.post(f"{detail_url}/decisions", headers=headers, json=payload))
            assert result["application"]["status"] == expected
            assert body(client.post(f"{detail_url}/decisions", headers=headers, json=payload)) == result
            version = result["application"]["optimistic_version"]
            owned = body(client.get(applicant_url, headers=applicant))
            assert owned["status"] == expected
            assert owned["optimistic_version"] == version
            assert owned["authorization"] is None
            assert "reviewer_user_id" not in owned["latest_decision"]
            denied = body(client.post(online_url, headers=applicant, json=online_payload), 409)
            assert denied["error"]["message"] == "Driver account is not active."
        assert len(body(client.get(detail_url, headers=reviewer))["decisions"]) == 2
        body(client.post(f"{applicant_url}/submit", headers=applicant), 409)
        assert body(client.get("/api/v1/drivers/me", headers=applicant))["availability_status"] == "OFFLINE"
