"""PostGIS-backed Phase 13 city recruitment and authorization proof."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from os import getenv
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from taximobile_api.core.config import Settings
from taximobile_api.domains.administration.bootstrap import bootstrap_initial_platform_grant
from taximobile_api.domains.auth.bootstrap import bootstrap_initial_administrator
from taximobile_api.domains.analytics.service import refresh_operational_analytics
from taximobile_api.domains.markets.constants import LEGACY_CITY_ID
from taximobile_api.main import create_app
from taximobile_api.integrations.driver_documents import InMemoryDriverDocumentStore
from taximobile_api.workers.driver_document_retention import (
    DriverDocumentRetentionProcessor,
)


pytestmark = pytest.mark.integration

ADMIN_EMAIL = "integration-admin@example.test"
ADMIN_PASSWORD = "Integration-admin-password-2026"
APPLICANT_PASSWORD = "Driver-applicant-password-2026"
DOCUMENT_PDF = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


class CleanDocumentScanner:
    async def require_clean(self, content: bytes) -> None:
        assert content


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


async def seed_recruiting_test_city(settings: Settings, suffix: str) -> UUID:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    city_id = uuid4()
    try:
        async with sessions() as session:
            async with session.begin():
                await session.execute(
                    text(
                        "INSERT INTO cities "
                        "(id, market_id, code, localized_name, timezone, "
                        "presentation_centroid, lifecycle_status, "
                        "is_legacy_compatibility, optimistic_version) "
                        "SELECT :city_id, market_id, :code, "
                        "CAST(:localized_name AS jsonb), timezone, presentation_centroid, "
                        "'CONFIGURING', false, 1 FROM cities WHERE id = :legacy_city_id"
                    ),
                    {
                        "city_id": city_id,
                        "code": f"DOC-{suffix[:10]}",
                        "localized_name": '{"en":"Document Test","fr":"Document Test","ar":"Document Test"}',
                        "legacy_city_id": LEGACY_CITY_ID,
                    },
                )
        return city_id
    finally:
        await engine.dispose()


async def refresh_and_reconcile_analytics(settings: Settings) -> tuple[int, int, set[str]]:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            async with session.begin():
                await refresh_operational_analytics(session)
        async with sessions() as session:
            source_count = int(
                await session.scalar(
                    text(
                        "SELECT count(*) FROM operational_domain_events_v1 "
                        "WHERE city_id = :city_id AND event_type = 'DRIVER_APPLICATION_CREATED'"
                    ),
                    {"city_id": LEGACY_CITY_ID},
                )
                or 0
            )
            fact_count = int(
                await session.scalar(
                    text(
                        "SELECT coalesce(sum(sample_count), 0) "
                        "FROM operational_metric_facts_hourly_v1 "
                        "WHERE city_id = :city_id AND metric_code = 'DRIVER_APPLICATION_CREATED'"
                    ),
                    {"city_id": LEGACY_CITY_ID},
                )
                or 0
            )
            columns = set(
                await session.scalars(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema = current_schema() "
                        "AND table_name = 'operational_domain_events_v1'"
                    )
                )
            )
            return source_count, fact_count, columns
    finally:
        await engine.dispose()


async def process_and_verify_document_erasure(
    settings: Settings,
    store: InMemoryDriverDocumentStore,
    document_id: str,
) -> tuple[int, int, int]:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        processed = await DriverDocumentRetentionProcessor(
            sessions,
            store,
            batch_size=10,
        ).process_once()
        async with sessions() as session:
            document_count = int(
                await session.scalar(
                    text(
                        "SELECT count(*) FROM driver_application_documents "
                        "WHERE id = :document_id"
                    ),
                    {"document_id": UUID(document_id)},
                )
                or 0
            )
            audit_count = int(
                await session.scalar(
                    text(
                        "SELECT count(*) FROM driver_document_retention_actions "
                        "WHERE document_id = :document_id"
                    ),
                    {"document_id": UUID(document_id)},
                )
                or 0
            )
        return processed, document_count, audit_count
    finally:
        await engine.dispose()


def expect(response, status_code: int):
    assert response.status_code == status_code, response.text
    return response.json()


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register_and_login(client: TestClient, email: str, display_name: str) -> dict[str, str]:
    expect(
        client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": APPLICANT_PASSWORD,
                "display_name": display_name,
            },
        ),
        201,
    )
    tokens = expect(
        client.post(
            "/api/v1/auth/login",
            json={
                "identifier": email,
                "password": APPLICANT_PASSWORD,
                "device_label": "city recruitment integration",
            },
        ),
        200,
    )
    return bearer(tokens["access_token"])


def operations_login(client: TestClient) -> dict[str, str]:
    tokens = expect(
        client.post(
            "/api/v1/operations/auth/login",
            json={
                "identifier": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
                "device_label": "driver review integration",
            },
        ),
        200,
    )
    return bearer(tokens["access_token"])


def decision_headers(token_headers: dict[str, str], key: str) -> dict[str, str]:
    return {**token_headers, "Idempotency-Key": key}


def test_city_application_review_and_authorization_lifecycle() -> None:
    settings = integration_settings()
    asyncio.run(seed_platform_administrator(settings))
    suffix = uuid4().hex

    with TestClient(create_app(settings=settings)) as client:
        catalog = expect(client.get("/api/v1/drivers/recruiting-cities"), 200)
        assert any(item["id"] == str(LEGACY_CITY_ID) for item in catalog["items"])
        requirements = expect(
            client.get(f"/api/v1/drivers/recruiting-cities/{LEGACY_CITY_ID}/requirements"),
            200,
        )
        assert requirements["city"]["id"] == str(LEGACY_CITY_ID)
        assert requirements["document_upload_available"] is False
        assert [item["evidence_type"] for item in requirements["items"]] == ["PROFILE"]

        applicant_headers = register_and_login(
            client,
            f"city-applicant-{suffix}@example.test",
            "City Applicant",
        )
        other_headers = register_and_login(
            client,
            f"other-city-applicant-{suffix}@example.test",
            "Other Applicant",
        )
        operations_headers = operations_login(client)

        application = expect(
            client.post(
                "/api/v1/drivers/me/city-applications",
                headers=applicant_headers,
                json={"city_id": str(LEGACY_CITY_ID), "display_name": "City Applicant"},
            ),
            201,
        )
        application_id = application["id"]
        assert application["status"] == "NOT_STARTED"
        assert application["complete"] is True
        assert application["editable"] is True
        assert application["authorization"] is None
        assert len(application["evidence"]) == 1

        # The open application is stable and cannot be promoted by client input.
        duplicate = expect(
            client.post(
                "/api/v1/drivers/me/city-applications",
                headers=applicant_headers,
                json={"city_id": str(LEGACY_CITY_ID)},
            ),
            200,
        )
        assert duplicate["id"] == application_id
        assert client.post(
            "/api/v1/drivers/me/city-applications",
            headers=other_headers,
            json={
                "city_id": str(LEGACY_CITY_ID),
                "display_name": "Other Applicant",
                "status": "APPROVED",
            },
        ).status_code == 422
        assert client.get(
            f"/api/v1/drivers/me/city-applications/{application_id}",
            headers=other_headers,
        ).status_code == 404

        # Storage is not simulated: ownership is checked, then the capability fails closed.
        unavailable = client.post(
            f"/api/v1/drivers/me/city-applications/{application_id}/documents",
            headers=applicant_headers,
        )
        assert unavailable.status_code == 503
        assert "not configured" in unavailable.json()["error"]["message"]

        submitted = expect(
            client.post(
                f"/api/v1/drivers/me/city-applications/{application_id}/submit",
                headers=applicant_headers,
            ),
            200,
        )
        assert submitted["status"] == "SUBMITTED"
        assert submitted["submission_revision"] == 1
        assert submitted["optimistic_version"] == 2
        repeated_submit = expect(
            client.post(
                f"/api/v1/drivers/me/city-applications/{application_id}/submit",
                headers=applicant_headers,
            ),
            200,
        )
        assert repeated_submit["optimistic_version"] == 2

        queue = expect(
            client.get(
                "/api/v1/operations/driver-applications",
                params={"city_id": str(LEGACY_CITY_ID), "status": "SUBMITTED"},
                headers=operations_headers,
            ),
            200,
        )
        assert any(item["id"] == application_id for item in queue["items"])

        start_key = str(uuid4())
        start_payload = {
            "expected_version": 2,
            "decision": "START_REVIEW",
            "reason_code": "MANUAL_REVIEW_STARTED",
            "applicant_safe_message": "Your application is now being reviewed.",
        }
        under_review = expect(
            client.post(
                f"/api/v1/operations/driver-applications/{application_id}/decisions",
                headers=decision_headers(operations_headers, start_key),
                json=start_payload,
            ),
            200,
        )
        assert under_review["application"]["status"] == "UNDER_REVIEW"
        assert under_review["application"]["optimistic_version"] == 3
        replay = expect(
            client.post(
                f"/api/v1/operations/driver-applications/{application_id}/decisions",
                headers=decision_headers(operations_headers, start_key),
                json=start_payload,
            ),
            200,
        )
        assert replay == under_review
        assert client.post(
            f"/api/v1/operations/driver-applications/{application_id}/decisions",
            headers=decision_headers(operations_headers, start_key),
            json={**start_payload, "applicant_safe_message": "A different command."},
        ).status_code == 409

        more_information = expect(
            client.post(
                f"/api/v1/operations/driver-applications/{application_id}/decisions",
                headers=decision_headers(operations_headers, str(uuid4())),
                json={
                    "expected_version": 3,
                    "decision": "REQUEST_ADDITIONAL_INFORMATION",
                    "reason_code": "MISSING_OR_INVALID_EVIDENCE",
                    "applicant_safe_message": "Please confirm your profile and submit again.",
                },
            ),
            200,
        )
        assert more_information["application"]["status"] == "ADDITIONAL_INFORMATION_REQUIRED"
        applicant_view = expect(
            client.get(
                f"/api/v1/drivers/me/city-applications/{application_id}",
                headers=applicant_headers,
            ),
            200,
        )
        assert applicant_view["latest_decision"] == {
            key: more_information["application"]["latest_decision"][key]
            for key in ("decision", "reason_code", "message", "created_at")
        }
        assert "reviewer_user_id" not in applicant_view["latest_decision"]

        resubmitted = expect(
            client.post(
                f"/api/v1/drivers/me/city-applications/{application_id}/submit",
                headers=applicant_headers,
            ),
            200,
        )
        assert resubmitted["status"] == "SUBMITTED"
        assert resubmitted["submission_revision"] == 2
        assert resubmitted["optimistic_version"] == 5

        approved = expect(
            client.post(
                f"/api/v1/operations/driver-applications/{application_id}/decisions",
                headers=decision_headers(operations_headers, str(uuid4())),
                json={
                    "expected_version": 5,
                    "decision": "APPROVE",
                    "reason_code": "REQUIREMENTS_CONFIRMED",
                    "applicant_safe_message": "You are approved to drive in Casablanca.",
                    "authorized_service_types": ["ON_DEMAND"],
                },
            ),
            200,
        )
        approved_application = approved["application"]
        assert approved_application["status"] == "APPROVED"
        assert approved_application["authorization"]["status"] == "ACTIVE"
        assert approved_application["authorization"]["city_id"] == str(LEGACY_CITY_ID)
        assert approved_application["authorization"]["service_types"] == ["ON_DEMAND"]
        assert approved_application["authorization"]["scheduled_offers_enabled"] is False
        assert client.post(
            f"/api/v1/drivers/me/city-applications/{application_id}/withdraw",
            headers=applicant_headers,
        ).status_code == 409
        assert client.post(
            "/api/v1/drivers/me/city-applications",
            headers=applicant_headers,
            json={"city_id": str(LEGACY_CITY_ID)},
        ).status_code == 409

        current_user = expect(client.get("/api/v1/me", headers=applicant_headers), 200)
        assert "DRIVER" in current_user["roles"]

        aggregate = expect(
            client.get(
                f"/api/v1/operations/cities/{LEGACY_CITY_ID}/operational-aggregates",
                headers=operations_headers,
            ),
            200,
        )
        assert aggregate["minimum_cell_size"] == 5
        if aggregate["total_applications"] is not None:
            assert aggregate["total_applications"] >= 5
        for item in aggregate["status_counts"]:
            if item["value"] is None:
                assert item["suppressed"] is True
            else:
                assert item["value"] >= 5

        source_count, fact_count, event_columns = asyncio.run(
            refresh_and_reconcile_analytics(settings)
        )
        assert source_count == fact_count
        assert event_columns.isdisjoint(
            {
                "passenger_id",
                "driver_id",
                "user_id",
                "latitude",
                "longitude",
                "notes",
                "payload",
                "provider_reference",
            }
        )

        definitions = expect(
            client.get("/api/v1/operations/analytics/definitions", headers=operations_headers),
            200,
        )
        definition_codes = {item["code"] for item in definitions["items"]}
        assert {
            "DRIVER_APPLICATION_CREATED",
            "FINANCIAL_DRIVER_NET",
            "MATCHING_FAIRNESS_SCORE",
            "DRIVER_WORK_DISTRIBUTION",
        }.issubset(definition_codes)
        facts = expect(
            client.get(
                "/api/v1/operations/analytics/facts",
                headers=operations_headers,
                params={"city_id": str(LEGACY_CITY_ID)},
            ),
            200,
        )
        assert facts["minimum_cell_size"] == 5
        application_facts = [
            item for item in facts["items"]
            if item["metric_code"] == "DRIVER_APPLICATION_CREATED"
        ]
        assert application_facts
        for item in application_facts:
            if item["suppressed"]:
                for field in (
                    "sample_count",
                    "integer_value",
                    "average_duration_seconds",
                    "average_distance_meters",
                    "amount_sum",
                    "average_numeric_value",
                    "average_per_entity",
                    "minimum_per_entity",
                    "maximum_per_entity",
                    "distribution_gini",
                ):
                    assert item[field] is None
        assert client.get(
            "/api/v1/operations/analytics/facts",
            headers=operations_headers,
            params={"city_id": str(uuid4())},
        ).status_code == 404


def test_applicant_can_withdraw_but_not_resubmit_terminal_application() -> None:
    settings = integration_settings()
    suffix = uuid4().hex

    with TestClient(create_app(settings=settings)) as client:
        headers = register_and_login(
            client,
            f"withdraw-city-applicant-{suffix}@example.test",
            "Withdrawing Applicant",
        )
        application = expect(
            client.post(
                "/api/v1/drivers/me/city-applications",
                headers=headers,
                json={
                    "city_id": str(LEGACY_CITY_ID),
                    "display_name": "Withdrawing Applicant",
                },
            ),
            201,
        )
        withdrawn = expect(
            client.post(
                f"/api/v1/drivers/me/city-applications/{application['id']}/withdraw",
                headers=headers,
            ),
            200,
        )
        assert withdrawn["status"] == "WITHDRAWN"
        assert withdrawn["optimistic_version"] == 2
        repeated = expect(
            client.post(
                f"/api/v1/drivers/me/city-applications/{application['id']}/withdraw",
                headers=headers,
            ),
            200,
        )
        assert repeated["optimistic_version"] == 2
        assert client.post(
            f"/api/v1/drivers/me/city-applications/{application['id']}/submit",
            headers=headers,
        ).status_code == 409


def test_scoped_reviewer_can_verify_only_a_vehicle_selected_in_the_application() -> None:
    settings = integration_settings()
    asyncio.run(seed_platform_administrator(settings))
    suffix = uuid4().hex
    city_id = asyncio.run(seed_recruiting_test_city(settings, suffix))

    with TestClient(create_app(settings=settings)) as client:
        operations_headers = operations_login(client)
        requirement = expect(
            client.post(
                f"/api/v1/operations/cities/{city_id}/driver-requirement-versions",
                headers=operations_headers,
                json={
                    "version": f"vehicle-{suffix[:8]}",
                    "effective_from": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
                    "items": [
                        {
                            "requirement_code": "ACTIVE_TAXI_VEHICLE",
                            "evidence_type": "VEHICLE",
                            "required": True,
                            "validity_rule_code": "VEHICLE_OWNED",
                            "display_order": 0,
                            "localized_copy_key": "driver.requirement.active-taxi-vehicle",
                            "localized_label": {
                                "en": "Taxi vehicle",
                                "fr": "Taxi vehicle",
                                "ar": "Taxi vehicle",
                            },
                            "localized_description": {
                                "en": "Select the taxi vehicle for review.",
                                "fr": "Select the taxi vehicle for review.",
                                "ar": "Select the taxi vehicle for review.",
                            },
                        }
                    ],
                },
            ),
            201,
        )
        requirement_id = requirement["id"]
        requirement_item_id = requirement["items"][0]["id"]
        expect(
            client.post(
                f"/api/v1/operations/driver-requirement-versions/{requirement_id}/submit",
                headers=operations_headers,
                json={"expected_version": 1, "reason": "Vehicle review integration."},
            ),
            200,
        )
        expect(
            client.post(
                f"/api/v1/operations/driver-requirement-versions/{requirement_id}/activate",
                headers=operations_headers,
                json={"expected_version": 2, "reason": "Vehicle review integration."},
            ),
            200,
        )

        applicant_headers = register_and_login(
            client,
            f"vehicle-applicant-{suffix}@example.test",
            "Vehicle Applicant",
        )
        application = expect(
            client.post(
                "/api/v1/drivers/me/city-applications",
                headers=applicant_headers,
                json={"city_id": str(city_id), "display_name": "Vehicle Applicant"},
            ),
            201,
        )
        vehicle = expect(
            client.post(
                "/api/v1/drivers/me/vehicles",
                headers=applicant_headers,
                json={
                    "make": "Dacia",
                    "model": "Lodgy",
                    "year": 2022,
                    "color": "White",
                    "registration_number": f"TEST-{suffix[:10]}",
                    "taxi_identifier": f"TAXI-{suffix[:10]}",
                    "passenger_capacity": 6,
                },
            ),
            201,
        )
        application = expect(
            client.patch(
                f"/api/v1/drivers/me/city-applications/{application['id']}",
                headers=applicant_headers,
                json={
                    "expected_version": 1,
                    "evidence": [
                        {
                            "requirement_item_id": requirement_item_id,
                            "vehicle_id": vehicle["id"],
                        }
                    ],
                },
            ),
            200,
        )
        assert application["complete"] is True
        application = expect(
            client.post(
                f"/api/v1/drivers/me/city-applications/{application['id']}/submit",
                headers=applicant_headers,
            ),
            200,
        )

        endpoint = (
            f"/api/v1/operations/driver-applications/{application['id']}"
            f"/vehicles/{vehicle['id']}/verify"
        )
        payload = {
            "expected_application_version": application["optimistic_version"],
            "reason_code": "VEHICLE_REQUIREMENTS_CONFIRMED",
        }
        key = str(uuid4())
        verified = expect(
            client.post(
                endpoint,
                headers=decision_headers(operations_headers, key),
                json=payload,
            ),
            200,
        )
        assert verified["verification_status"] == "VERIFIED"
        assert expect(
            client.post(
                endpoint,
                headers=decision_headers(operations_headers, key),
                json=payload,
            ),
            200,
        ) == verified
        assert client.post(
            endpoint,
            headers=decision_headers(operations_headers, key),
            json={**payload, "expected_application_version": 999},
        ).status_code == 409
        assert client.post(
            endpoint.replace(str(application["id"]), str(uuid4())),
            headers=decision_headers(operations_headers, str(uuid4())),
            json=payload,
        ).status_code == 404

        detail = expect(
            client.get(
                f"/api/v1/operations/driver-applications/{application['id']}",
                headers=operations_headers,
            ),
            200,
        )
        selected = next(
            item
            for item in detail["application"]["evidence"]
            if item["vehicle_id"] == vehicle["id"]
        )
        assert selected["status"] == "ACCEPTED"

        changed_vehicle = expect(
            client.patch(
                f"/api/v1/drivers/me/vehicles/{vehicle['id']}",
                headers=applicant_headers,
                json={"color": "Ivory"},
            ),
            200,
        )
        assert changed_vehicle["verification_status"] == "PENDING"
        changed_detail = expect(
            client.get(
                f"/api/v1/operations/driver-applications/{application['id']}",
                headers=operations_headers,
            ),
            200,
        )
        changed_evidence = next(
            item
            for item in changed_detail["application"]["evidence"]
            if item["vehicle_id"] == vehicle["id"]
        )
        assert changed_evidence["status"] == "PENDING"

        reverified = expect(
            client.post(
                endpoint,
                headers=decision_headers(operations_headers, str(uuid4())),
                json=payload,
            ),
            200,
        )
        assert reverified["verification_status"] == "VERIFIED"


def test_protected_document_upload_review_replacement_and_deletion() -> None:
    settings = integration_settings()
    asyncio.run(seed_platform_administrator(settings))
    suffix = uuid4().hex
    city_id = asyncio.run(seed_recruiting_test_city(settings, suffix))
    store = InMemoryDriverDocumentStore(CleanDocumentScanner(), max_bytes=1024)

    with TestClient(create_app(settings=settings, driver_document_store=store)) as client:
        operations_headers = operations_login(client)
        requirement = expect(
            client.post(
                f"/api/v1/operations/cities/{city_id}/driver-requirement-versions",
                headers=operations_headers,
                json={
                    "version": f"documents-{suffix[:8]}",
                    "effective_from": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
                    "items": [
                        {
                            "requirement_code": "IDENTITY_DOCUMENT",
                            "evidence_type": "DOCUMENT",
                            "required": True,
                            "validity_rule_code": "DOCUMENT_SCANNED_CLEAN",
                            "display_order": 0,
                            "localized_copy_key": "driver.requirement.identity-document",
                            "localized_label": {
                                "en": "Identity document",
                                "fr": "Identity document",
                                "ar": "Identity document",
                            },
                            "localized_description": {
                                "en": "Upload a PDF identity document.",
                                "fr": "Upload a PDF identity document.",
                                "ar": "Upload a PDF identity document.",
                            },
                        }
                    ],
                },
            ),
            201,
        )
        requirement_id = requirement["id"]
        requirement_item_id = requirement["items"][0]["id"]
        submitted_requirement = expect(
            client.post(
                f"/api/v1/operations/driver-requirement-versions/{requirement_id}/submit",
                headers=operations_headers,
                json={"expected_version": 1, "reason": "Document lifecycle integration."},
            ),
            200,
        )
        assert submitted_requirement["status"] == "IN_REVIEW"
        activated_requirement = expect(
            client.post(
                f"/api/v1/operations/driver-requirement-versions/{requirement_id}/activate",
                headers=operations_headers,
                json={"expected_version": 2, "reason": "Document lifecycle integration."},
            ),
            200,
        )
        assert activated_requirement["status"] == "ACTIVE"

        applicant_headers = register_and_login(
            client,
            f"document-applicant-{suffix}@example.test",
            "Document Applicant",
        )
        other_headers = register_and_login(
            client,
            f"document-other-{suffix}@example.test",
            "Other Document Applicant",
        )
        application = expect(
            client.post(
                "/api/v1/drivers/me/city-applications",
                headers=applicant_headers,
                json={"city_id": str(city_id), "display_name": "Document Applicant"},
            ),
            201,
        )
        application_id = application["id"]
        assert application["document_upload_available"] is True
        assert application["complete"] is False

        spoofed = client.post(
            f"/api/v1/drivers/me/city-applications/{application_id}/documents",
            headers=applicant_headers,
            data={
                "requirement_item_id": requirement_item_id,
                "expected_application_version": 1,
            },
            files={"file": ("identity.png", DOCUMENT_PDF, "image/png")},
        )
        assert spoofed.status_code == 422

        hidden = client.post(
            f"/api/v1/drivers/me/city-applications/{application_id}/documents",
            headers=other_headers,
            data={
                "requirement_item_id": requirement_item_id,
                "expected_application_version": 1,
            },
            files={"file": ("identity.pdf", DOCUMENT_PDF, "application/pdf")},
        )
        assert hidden.status_code == 404

        uploaded = expect(
            client.post(
                f"/api/v1/drivers/me/city-applications/{application_id}/documents",
                headers=applicant_headers,
                data={
                    "requirement_item_id": requirement_item_id,
                    "expected_application_version": 1,
                },
                files={"file": ("identity.pdf", DOCUMENT_PDF, "application/pdf")},
            ),
            201,
        )
        first_document_id = uploaded["documents"][0]["id"]
        assert uploaded["optimistic_version"] == 2
        assert uploaded["complete"] is True
        assert uploaded["documents"][0]["scan_status"] == "CLEAN"

        download = client.get(
            f"/api/v1/operations/driver-applications/{application_id}/documents/"
            f"{first_document_id}",
            headers=operations_headers,
        )
        assert download.status_code == 200
        assert download.content == DOCUMENT_PDF
        assert "no-store" in download.headers["Cache-Control"]
        assert download.headers["X-Content-Type-Options"] == "nosniff"
        assert "identity.pdf" not in download.headers["Content-Disposition"]

        replacement = expect(
            client.post(
                f"/api/v1/drivers/me/city-applications/{application_id}/documents",
                headers=applicant_headers,
                data={
                    "requirement_item_id": requirement_item_id,
                    "expected_application_version": 2,
                },
                files={"file": ("replacement.pdf", DOCUMENT_PDF, "application/pdf")},
            ),
            201,
        )
        assert replacement["optimistic_version"] == 3
        assert len(replacement["documents"]) == 1
        replacement_document_id = replacement["documents"][0]["id"]
        assert replacement_document_id != first_document_id
        assert client.get(
            f"/api/v1/operations/driver-applications/{application_id}/documents/"
            f"{first_document_id}",
            headers=operations_headers,
        ).status_code == 404

        deleted = expect(
            client.delete(
                f"/api/v1/drivers/me/city-applications/{application_id}/documents/"
                f"{replacement_document_id}",
                headers=applicant_headers,
                params={"expected_application_version": 3},
            ),
            200,
        )
        assert deleted["optimistic_version"] == 4
        assert deleted["complete"] is False
        assert deleted["documents"] == []

    processed, document_count, audit_count = asyncio.run(
        process_and_verify_document_erasure(
            settings,
            store,
            replacement_document_id,
        )
    )
    assert processed >= 1
    assert document_count == 0
    assert audit_count == 1
