"""PostGIS-backed Phase 15 route publication, scope, privacy, and booking proof."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from os import getenv
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from geoalchemy2.elements import WKTElement
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from taximobile_api.core.config import Settings
from taximobile_api.domains.administration.bootstrap import (
    bootstrap_initial_platform_grant,
)
from taximobile_api.domains.auth.bootstrap import bootstrap_initial_administrator
from taximobile_api.domains.auth.models import Role, User, UserRole
from taximobile_api.domains.driver_applications.models import (
    CityApplicationStatus,
    CityAuthorizationStatus,
    DriverCityApplication,
    DriverCityAuthorization,
    DriverCityAuthorizationService,
    DriverRequirementVersion,
    RequirementVersionStatus,
)
from taximobile_api.domains.drivers.models import (
    AvailabilityStatus,
    CredentialVerificationStatus,
    DriverAccountStatus,
    DriverCredential,
    DriverLocation,
    DriverProfile,
    DriverVerification,
    Vehicle,
    VehicleStatus,
    VehicleVerificationStatus,
    VerificationStatus,
)
from taximobile_api.domains.markets.constants import LEGACY_MARKET_ID
from taximobile_api.domains.markets.models import (
    City,
    CityConfigurationVersion,
    CityLifecycleStatus,
    CityServiceAreaVersion,
    ConfigurationStatus,
    ServiceAreaStatus,
    ServiceType,
)
from taximobile_api.domains.scheduled_bookings.service import advance_due_bookings
from taximobile_api.domains.scheduled_bookings import service as scheduling_service
from taximobile_api.domains.scheduled_bookings.models import (
    ScheduledBooking, ScheduledBookingOffer, ScheduledBookingCommitment, ScheduledBookingEvent,
)
from taximobile_api.domains.notifications.models import Notification
from taximobile_api.domains.outbox.models import OutboxEvent
from taximobile_api.domains.rides.models import Ride, RideOffer
from taximobile_api.domains.outbox.processor import ClaimedOutboxEvent
from taximobile_api.workers.outbox import WebSocketOutboxDelivery
from taximobile_api.main import create_app
from scheduling_concurrency import prove_scheduling_race
from assignment_concurrency import prove_mixed_assignment


pytestmark = pytest.mark.integration

ADMIN_EMAIL = "fixed-route-admin@example.test"
ADMIN_PASSWORD = "Fixed-route-admin-password-2026"
MANAGER_PASSWORD = "Fixed-route-manager-password-2026"


def integration_settings() -> Settings:
    if getenv("TAXIMOBILE_RUN_INTEGRATION") != "1":
        pytest.skip(
            "Set TAXIMOBILE_RUN_INTEGRATION=1 with an isolated migrated PostGIS database."
        )
    settings = Settings.from_environment()
    if settings.environment != "test" or "taximobile_ci" not in settings.database_url:
        pytest.fail("Fixed-route integration tests require the isolated taximobile_ci database.")
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


async def activate_test_configuration(
    settings: Settings,
    *,
    city_id: str,
    configuration_id: str,
) -> None:
    """Activate an otherwise coherent fixture without duplicating readiness tests.

    City activation and readiness transitions are exhaustively covered by the
    national control-plane suite. This fixture only needs their resulting state
    so the fixed-route participant contract can be exercised independently.
    """

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            async with session.begin():
                city = await session.get(City, UUID(city_id))
                configuration = await session.get(
                    CityConfigurationVersion,
                    UUID(configuration_id),
                )
                assert city is not None and configuration is not None
                service_area = await session.get(
                    CityServiceAreaVersion,
                    configuration.service_area_version_id,
                )
                assert service_area is not None
                service_area.status = ServiceAreaStatus.ACTIVE
                configuration.status = ConfigurationStatus.ACTIVE
                configuration.activated_at = datetime.now(UTC)
                city.active_configuration_version_id = configuration.id
                city.lifecycle_status = CityLifecycleStatus.ACTIVE
    finally:
        await engine.dispose()


async def seed_fixed_route_driver(
    settings: Settings,
    *,
    email: str,
    city_id: str,
    suffix: str,
) -> None:
    """Create a coherent approved city authorization for participant testing.

    Recruitment review itself is covered by its dedicated integration suite.
    This fixture starts from the resulting server-owned records so Phase 15 can
    prove that FIXED_ROUTE authorization, online selection, matching, and offer
    decisions all use the same service type end to end.
    """

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)
    try:
        async with sessions() as session:
            async with session.begin():
                user = await session.scalar(select(User).where(User.email == email))
                assert user is not None
                driver = DriverProfile(
                    user_id=user.id,
                    display_name="Fixed Route Integration Driver",
                    verification_status=VerificationStatus.APPROVED,
                    account_status=DriverAccountStatus.ACTIVE,
                    availability_status=AvailabilityStatus.OFFLINE,
                )
                session.add(driver)
                await session.flush()
                session.add_all(
                    [
                        UserRole(user_id=user.id, role=Role.DRIVER),
                        DriverVerification(
                            driver_id=driver.id,
                            status=VerificationStatus.APPROVED,
                            submitted_at=now - timedelta(days=2),
                            reviewed_at=now - timedelta(days=1),
                        ),
                    ]
                )
                vehicle = Vehicle(
                    driver_id=driver.id,
                    make="Dacia",
                    model="Logan",
                    year=2025,
                    color="White",
                    registration_number=f"FR-{suffix.upper()}",
                    taxi_identifier=f"FR-{suffix[:8].upper()}",
                    passenger_capacity=4,
                    status=VehicleStatus.ACTIVE,
                    verification_status=VehicleVerificationStatus.VERIFIED,
                )
                requirement = await session.scalar(
                    select(DriverRequirementVersion).where(
                        DriverRequirementVersion.city_id == UUID(city_id),
                        DriverRequirementVersion.status == RequirementVersionStatus.ACTIVE,
                    )
                )
                if requirement is None:
                    requirement = DriverRequirementVersion(
                        city_id=UUID(city_id),
                        version=f"fixed-route-driver-{suffix}",
                        status=RequirementVersionStatus.ACTIVE,
                        effective_from=now - timedelta(days=2),
                    )
                    session.add(requirement)
                session.add(vehicle)
                await session.flush()
                driver.active_vehicle_id = vehicle.id
                application = DriverCityApplication(
                    driver_id=driver.id,
                    city_id=UUID(city_id),
                    requirement_version_id=requirement.id,
                    status=CityApplicationStatus.APPROVED,
                    optimistic_version=2,
                    submission_revision=1,
                    submitted_at=now - timedelta(days=2),
                    reviewed_at=now - timedelta(days=1),
                )
                session.add(application)
                await session.flush()
                authorization = DriverCityAuthorization(
                    driver_id=driver.id,
                    city_id=UUID(city_id),
                    application_id=application.id,
                    vehicle_id=vehicle.id,
                    status=CityAuthorizationStatus.ACTIVE,
                    valid_from=now - timedelta(days=1),
                )
                session.add(authorization)
                await session.flush()
                session.add(
                    DriverCityAuthorizationService(
                        authorization_id=authorization.id,
                        service_type=ServiceType.FIXED_ROUTE,
                    )
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
                "device_label": "fixed-route integration",
            },
        ),
        200,
    )


def assert_no_supply_data(value) -> None:
    forbidden_fragments = (
        "driver",
        "taxi",
        "candidate",
        "queue",
        "available_count",
        "online_count",
        "location_count",
    )
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = key.lower()
            assert not any(fragment in normalized for fragment in forbidden_fragments), key
            assert_no_supply_data(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_supply_data(child)


@pytest.mark.parametrize("handoff_case", [
    "unfulfilled", "direct", "suspended", "vehicle-expired", "credential-expired",
    "missing-location", "stale-location", "future-location", "outside-area",
    "offline", "paused", "offered", "wrong-city", "wrong-service",
    "race-handoff-handoff", "race-cancel-handoff", "race-handoff-cancel",
    "race-offline-handoff", "race-accept-cancel",
    "mixed-immediate-first", "mixed-scheduled-first",
])
def test_published_routes_are_scoped_public_supply_private_and_bookable(monkeypatch, handoff_case) -> None:
    settings = integration_settings()
    asyncio.run(seed_platform_administrator(settings))
    suffix = uuid4().hex[:12]
    effective_from = datetime.now(UTC) - timedelta(minutes=1)

    async def scheduling_snapshot():
        """Observe durable business and delivery rows through a fresh connection."""
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with sessions() as session:
                snapshot = {}
                for model in (ScheduledBooking, ScheduledBookingOffer, ScheduledBookingCommitment, Ride):
                    snapshot[model.__tablename__] = list((await session.execute(
                        select(model.id, model.status).order_by(model.id)
                    )).all())
                snapshot["events"] = list(await session.scalars(
                    select(ScheduledBookingEvent.id).order_by(ScheduledBookingEvent.id)
                ))
                snapshot["drivers"] = list((await session.execute(
                    select(DriverProfile.id, DriverProfile.account_status,
                           DriverProfile.availability_status, DriverProfile.active_vehicle_id)
                    .order_by(DriverProfile.id)
                )).all())
                snapshot["notifications"] = list((await session.execute(
                    select(Notification.id, Notification.type, Notification.user_id, Notification.data)
                    .order_by(Notification.id)
                )).all())
                snapshot["outbox"] = list((await session.execute(
                    select(OutboxEvent.id, OutboxEvent.topic, OutboxEvent.payload)
                    .order_by(OutboxEvent.id)
                )).all())
                return snapshot
        finally:
            await engine.dispose()

    def assert_delivery_pair(topic, hint, resource_key, resource_id):
        snapshot = asyncio.run(scheduling_snapshot())
        assert len([
            row for row in snapshot["outbox"]
            if row.topic == topic and row.payload.get(resource_key) == resource_id
        ]) == 1
        assert len([
            row for row in snapshot["notifications"]
            if row.type == hint and row.data.get(resource_key) == resource_id
        ]) == 1

    original_enqueue = scheduling_service.enqueue

    def fail_after_enqueue(topic):
        async def injected(session, **kwargs):
            await original_enqueue(session, **kwargs)
            if kwargs["topic"] == topic:
                # Flush first: rollback must undo actual SQL, not only pending ORM objects.
                await session.flush()
                raise RuntimeError("Injected scheduling outbox failure")
        return injected

    with TestClient(create_app(settings=settings)) as client:
        operations = login(
            client,
            "/api/v1/operations/auth/login",
            ADMIN_EMAIL,
            ADMIN_PASSWORD,
        )
        platform_headers = bearer(operations["access_token"])

        def create_city(label: str, longitude: float, latitude: float) -> dict:
            return expect(
                client.post(
                    "/api/v1/operations/cities",
                    headers=platform_headers,
                    json={
                        "market_id": str(LEGACY_MARKET_ID),
                        "code": f"route-{label}-{suffix}",
                        "localized_name": {
                            "en": f"{label} route test",
                            "fr": f"{label} test itinéraire",
                            "ar": "مدينة اختبار الخطوط",
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

        city_a = create_city("rabat", -6.84, 34.02)
        city_b = create_city("tangier", -5.83, 35.76)

        def create_operator_assignment(city: dict, label: str) -> tuple[dict, dict]:
            operator = expect(
                client.post(
                    "/api/v1/operations/operators",
                    headers=platform_headers,
                    json={
                        "market_id": str(LEGACY_MARKET_ID),
                        "name": f"{label} fixed-route operator {suffix}",
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
                        "service_type": "FIXED_ROUTE",
                        "effective_from": effective_from.isoformat(),
                    },
                ),
                201,
            )
            return operator, assignment

        operator_a, assignment_a = create_operator_assignment(city_a, "Primary")
        operator_b, _ = create_operator_assignment(city_b, "Other-city")

        route_a = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/fixed-routes",
                headers=platform_headers,
                json={"operator_id": operator_a["id"], "code": "RABAT_01"},
            ),
            201,
        )
        route_a_alternate = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/fixed-routes",
                headers=platform_headers,
                json={"operator_id": operator_a["id"], "code": "RABAT_02"},
            ),
            201,
        )
        route_b = expect(
            client.post(
                f"/api/v1/operations/cities/{city_b['id']}/fixed-routes",
                headers=platform_headers,
                json={"operator_id": operator_b["id"], "code": "TANGIER_01"},
            ),
            201,
        )

        manager_email = f"route-manager-{suffix}@example.test"
        expect(
            client.post(
                "/api/v1/auth/register",
                json={
                    "email": manager_email,
                    "password": MANAGER_PASSWORD,
                    "display_name": "Scoped Route Manager",
                },
            ),
            201,
        )
        manager_mobile = login(
            client,
            "/api/v1/auth/login",
            manager_email,
            MANAGER_PASSWORD,
        )
        manager_user = expect(
            client.get(
                "/api/v1/me",
                headers=bearer(manager_mobile["access_token"]),
            ),
            200,
        )
        expect(
            client.post(
                "/api/v1/operations/administrative-grants",
                headers=platform_headers,
                json={
                    "user_id": manager_user["id"],
                    "role_template": "CITY_MANAGER",
                    "city_id": city_a["id"],
                    "reason": "Phase 15 fixed-route city scope proof.",
                },
            ),
            201,
        )
        manager_operations = login(
            client,
            "/api/v1/operations/auth/login",
            manager_email,
            MANAGER_PASSWORD,
        )
        manager_headers = bearer(manager_operations["access_token"])
        scoped_routes = expect(
            client.get(
                f"/api/v1/operations/cities/{city_a['id']}/fixed-routes",
                headers=manager_headers,
                params={"operator_id": operator_a["id"]},
            ),
            200,
        )
        assert {item["id"] for item in scoped_routes["items"]} == {
            route_a["id"],
            route_a_alternate["id"],
        }
        assert client.get(
            f"/api/v1/operations/cities/{city_b['id']}/fixed-routes",
            headers=manager_headers,
            params={"operator_id": operator_b["id"]},
        ).status_code == 404
        assert client.get(
            f"/api/v1/operations/fixed-routes/{route_b['id']}",
            headers=manager_headers,
        ).status_code == 404

        service_area = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/service-area-versions",
                headers=platform_headers,
                json={
                    "version": f"route-area-{suffix}",
                    "boundary": {
                        "type": "MultiPolygon",
                        "coordinates": [
                            [[[-7.0, 33.85], [-6.65, 33.85], [-6.65, 34.2], [-7.0, 34.2], [-7.0, 33.85]]]
                        ],
                    },
                    "effective_from": effective_from.isoformat(),
                },
            ),
            201,
        )
        for target, expected_version in (("IN_REVIEW", 1), ("APPROVED", 2)):
            service_area = expect(
                client.post(
                    f"/api/v1/operations/service-area-versions/{service_area['id']}/transitions",
                    headers=platform_headers,
                    json={
                        "target_status": target,
                        "expected_version": expected_version,
                        "reason": f"Route service area {target.lower()} integration proof.",
                    },
                ),
                200,
            )

        tariff = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/pricing-rules",
                headers=platform_headers,
                json={
                    "operator_id": operator_a["id"],
                    "service_type": "FIXED_ROUTE",
                    "booking_type": "IMMEDIATE",
                    "name": "Rabat 01 complete-direction fare",
                    "version": f"route-fare-{suffix}",
                    "model": "FIXED",
                    "fixed_amount": "8.00",
                    "currency": "MAD",
                    "effective_from": effective_from.isoformat(),
                },
            ),
            201,
        )
        tariff = expect(
            client.post(
                f"/api/v1/operations/pricing-rules/{tariff['id']}/submit",
                headers=platform_headers,
                json={
                    "expected_version": 1,
                    "reason": "Submit the complete-direction tariff for review.",
                },
            ),
            200,
        )
        assert tariff["status"] == "IN_REVIEW"
        assert tariff["fixed_route_direction_id"] is None

        fee = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/operator-fee-policies",
                headers=platform_headers,
                json={
                    "operator_id": operator_a["id"],
                    "service_type": "FIXED_ROUTE",
                    "version": f"route-fee-{suffix}",
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
            fee = expect(
                client.post(
                    f"/api/v1/operations/operator-fee-policies/{fee['id']}/{command}",
                    headers=platform_headers,
                    json={
                        "expected_version": expected_version,
                        "reason": f"Fixed-route fee {command} integration proof.",
                    },
                ),
                200,
            )

        scheduling_policy = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/scheduling-policies",
                headers=platform_headers,
                json={
                    "operator_id": operator_a["id"],
                    "service_type": "FIXED_ROUTE",
                    "version": f"route-scheduling-{suffix}",
                    "surcharge_amount": "3.00",
                    "currency": "MAD",
                    "beneficiary": "DRIVER",
                    "minimum_lead_minutes": 60,
                    "maximum_horizon_days": 30,
                    "offer_open_minutes_before": 1440,
                    "offer_response_seconds": 300,
                    "commitment_deadline_minutes_before": 180,
                    "handoff_minutes_before": 30,
                    "protected_duration_minutes": 90,
                    "conflict_buffer_before_minutes": 30,
                    "conflict_buffer_after_minutes": 30,
                    "passenger_cancel_cutoff_minutes": 60,
                    "driver_cancel_cutoff_minutes": 120,
                    "surcharge_refund_mode": "FULL_BEFORE_CUTOFF",
                    "fallback_matching_enabled": True,
                    "effective_from": effective_from.isoformat(),
                },
            ),
            201,
        )
        for command, expected_version in (("submit", 1), ("activate", 2)):
            scheduling_policy = expect(
                client.post(
                    f"/api/v1/operations/scheduling-policies/{scheduling_policy['id']}/{command}",
                    headers=platform_headers,
                    json={
                        "expected_version": expected_version,
                        "reason": f"Fixed-route scheduling {command} integration proof.",
                    },
                ),
                200,
            )

        payment_capability = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/payment-capability-versions",
                headers=platform_headers,
                json={
                    "operator_id": operator_a["id"],
                    "service_type": "FIXED_ROUTE",
                    "version": f"fixed-route-cash-{suffix}",
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
                    headers=platform_headers,
                    json={
                        "expected_version": payment_capability["optimistic_version"],
                        "reason": f"Fixed-route cash capability {command} integration proof.",
                    },
                ),
                200,
            )
        assert payment_capability["status"] == "ACTIVE"

        fare_options = expect(
            client.get(
                f"/api/v1/operations/cities/{city_a['id']}/fixed-route-fare-options",
                headers=manager_headers,
                params={"operator_id": operator_a["id"]},
            ),
            200,
        )
        assert fare_options["items"] == [
            {
                "id": tariff["id"],
                "version": tariff["version"],
                "name": tariff["name"],
                "status": "IN_REVIEW",
                "fixed_amount": "8.00",
                "currency": "MAD",
                "effective_from": tariff["effective_from"],
                "effective_until": None,
            }
        ]
        assert client.get(
            f"/api/v1/operations/cities/{city_b['id']}/fixed-route-fare-options",
            headers=manager_headers,
            params={"operator_id": operator_b["id"]},
        ).status_code == 404

        route_version = expect(
            client.post(
                f"/api/v1/operations/fixed-routes/{route_a['id']}/versions",
                headers=manager_headers,
                json={
                    "version": f"published-{suffix}",
                    "localized_name": {
                        "en": "Central station to university",
                        "fr": "Gare centrale vers université",
                        "ar": "المحطة المركزية إلى الجامعة",
                    },
                    "localized_description": {
                        "en": "A complete flat-fare direction.",
                        "fr": "Un trajet complet à tarif fixe.",
                        "ar": "مسار كامل بتعرفة ثابتة.",
                    },
                    "effective_from": effective_from.isoformat(),
                    "directions": [
                        {
                            "direction_code": "OUTBOUND",
                            "start_location_name": {
                                "en": "Central station",
                                "fr": "Gare centrale",
                                "ar": "المحطة المركزية",
                            },
                            "finish_location_name": {
                                "en": "University",
                                "fr": "Université",
                                "ar": "الجامعة",
                            },
                            "start": {"longitude": -6.84, "latitude": 34.02},
                            "finish": {"longitude": -6.80, "latitude": 34.00},
                            "geometry": {
                                "type": "LineString",
                                "coordinates": [[-6.84, 34.02], [-6.82, 34.01], [-6.80, 34.00]],
                            },
                            "flat_fare_policy_version_id": tariff["id"],
                            "stops": [
                                {
                                    "localized_name": {
                                        "en": "Avenue stop",
                                        "fr": "Arrêt avenue",
                                        "ar": "محطة الشارع",
                                    },
                                    "location": {"longitude": -6.82, "latitude": 34.01},
                                }
                            ],
                        }
                    ],
                },
            ),
            201,
        )
        direction = route_version["directions"][0]
        tariff = expect(
            client.post(
                f"/api/v1/operations/pricing-rules/{tariff['id']}/activate",
                headers=platform_headers,
                json={
                    "expected_version": 2,
                    "reason": "Activate the tariff after its immutable direction is bound.",
                },
            ),
            200,
        )
        assert tariff["fixed_route_direction_id"] == direction["id"]
        assert tariff["status"] == "ACTIVE"
        for command, expected_version, expected_status in (
            ("submit", 1, "IN_REVIEW"),
            ("publish", 2, "PUBLISHED"),
        ):
            route_version = expect(
                client.post(
                    f"/api/v1/operations/fixed-route-versions/{route_version['id']}/{command}",
                    headers=manager_headers,
                    json={
                        "expected_version": expected_version,
                        "reason": f"Route version {command} integration proof.",
                    },
                ),
                200,
            )
            assert route_version["status"] == expected_status
        direction = route_version["directions"][0]

        # Binding consumes the fare option. A second route exercises the inverse
        # geometry-first workflow and proves active fares are scoped per direction.
        assert expect(
            client.get(
                f"/api/v1/operations/cities/{city_a['id']}/fixed-route-fare-options",
                headers=manager_headers,
                params={"operator_id": operator_a["id"]},
            ),
            200,
        )["items"] == []
        alternate_route_version = expect(
            client.post(
                f"/api/v1/operations/fixed-routes/{route_a_alternate['id']}/versions",
                headers=manager_headers,
                json={
                    "version": f"published-alternate-{suffix}",
                    "localized_name": {
                        "en": "Old town to business district",
                        "fr": "Médina vers quartier d'affaires",
                        "ar": "المدينة القديمة إلى حي الأعمال",
                    },
                    "localized_description": {
                        "en": "A second independently priced direction.",
                        "fr": "Un second trajet tarifé indépendamment.",
                        "ar": "مسار ثانٍ بتعرفة مستقلة.",
                    },
                    "effective_from": effective_from.isoformat(),
                    "directions": [
                        {
                            "direction_code": "OUTBOUND",
                            "start_location_name": {
                                "en": "Old town",
                                "fr": "Médina",
                                "ar": "المدينة القديمة",
                            },
                            "finish_location_name": {
                                "en": "Business district",
                                "fr": "Quartier d'affaires",
                                "ar": "حي الأعمال",
                            },
                            "start": {"longitude": -6.85, "latitude": 34.03},
                            "finish": {"longitude": -6.77, "latitude": 33.99},
                            "geometry": {
                                "type": "LineString",
                                "coordinates": [[-6.85, 34.03], [-6.81, 34.01], [-6.77, 33.99]],
                            },
                            "stops": [],
                        }
                    ],
                },
            ),
            201,
        )
        alternate_direction = alternate_route_version["directions"][0]
        assert alternate_direction["flat_fare_policy_version_id"] is None
        assert alternate_direction["flat_fare"] is None

        alternate_tariff = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/pricing-rules",
                headers=platform_headers,
                json={
                    "operator_id": operator_a["id"],
                    "service_type": "FIXED_ROUTE",
                    "booking_type": "IMMEDIATE",
                    "fixed_route_direction_id": alternate_direction["id"],
                    "name": "Rabat 02 complete-direction fare",
                    "version": f"route-fare-alternate-{suffix}",
                    "model": "FIXED",
                    "fixed_amount": "12.00",
                    "currency": "MAD",
                    "effective_from": effective_from.isoformat(),
                },
            ),
            201,
        )
        assert alternate_tariff["fixed_route_direction_id"] == alternate_direction["id"]
        for command, expected_version, expected_status in (
            ("submit", 1, "IN_REVIEW"),
            ("activate", 2, "ACTIVE"),
        ):
            alternate_tariff = expect(
                client.post(
                    f"/api/v1/operations/pricing-rules/{alternate_tariff['id']}/{command}",
                    headers=platform_headers,
                    json={
                        "expected_version": expected_version,
                        "reason": f"Alternate direction fare {command} integration proof.",
                    },
                ),
                200,
            )
            assert alternate_tariff["status"] == expected_status
        # A direction-scoped activation must not replace an active fare belonging
        # to another direction in the same city/operator/service/booking scope.
        first_tariff_after_alternate_activation = expect(
            client.get(
                f"/api/v1/operations/pricing-rules/{tariff['id']}",
                headers=platform_headers,
            ),
            200,
        )
        assert first_tariff_after_alternate_activation["status"] == "ACTIVE"

        for command, expected_version, expected_status in (
            ("submit", 1, "IN_REVIEW"),
            ("publish", 2, "PUBLISHED"),
        ):
            alternate_route_version = expect(
                client.post(
                    f"/api/v1/operations/fixed-route-versions/{alternate_route_version['id']}/{command}",
                    headers=manager_headers,
                    json={
                        "expected_version": expected_version,
                        "reason": f"Alternate route version {command} integration proof.",
                    },
                ),
                200,
            )
            assert alternate_route_version["status"] == expected_status
        alternate_direction = alternate_route_version["directions"][0]

        configuration = expect(
            client.post(
                f"/api/v1/operations/cities/{city_a['id']}/configuration-versions",
                headers=platform_headers,
                json={
                    "version": f"route-config-{suffix}",
                    "service_area_version_id": service_area["id"],
                    "services": [
                        {
                            "service_type": "FIXED_ROUTE",
                            "operator_city_assignment_id": assignment_a["id"],
                            "operator_fee_policy_version_id": fee["id"],
                            "scheduling_policy_version_id": scheduling_policy["id"],
                            "payment_capability_version_id": payment_capability["id"],
                            "enabled": True,
                        }
                    ],
                    "routes": [
                        {
                            "fixed_route_version_id": route_version["id"],
                            "immediate_booking_enabled": True,
                            "scheduled_booking_enabled": True,
                        },
                        {
                            "fixed_route_version_id": alternate_route_version["id"],
                            "immediate_booking_enabled": True,
                            "scheduled_booking_enabled": True,
                        }
                    ],
                },
            ),
            201,
        )
        asyncio.run(
            activate_test_configuration(
                settings,
                city_id=city_a["id"],
                configuration_id=configuration["id"],
            )
        )

        cities = expect(client.get("/api/v1/cities"), 200)
        public_city = next(item for item in cities["items"] if item["id"] == city_a["id"])
        assert public_city["booking_available"] is True
        catalog = expect(
            client.get(f"/api/v1/cities/{city_a['id']}/fixed-routes"),
            200,
        )
        assert catalog["city"]["booking_available"] is True
        public_routes = {item["code"]: item for item in catalog["routes"]}
        assert set(public_routes) == {"RABAT_01", "RABAT_02"}
        first_public_direction = public_routes["RABAT_01"]["versions"][0]["directions"][0]
        alternate_public_direction = public_routes["RABAT_02"]["versions"][0]["directions"][0]
        assert first_public_direction["immediate_booking_enabled"] is True
        assert first_public_direction["scheduled_booking_enabled"] is True
        assert first_public_direction["flat_fare"] == "8.00"
        assert alternate_public_direction["immediate_booking_enabled"] is True
        assert alternate_public_direction["scheduled_booking_enabled"] is True
        assert alternate_public_direction["flat_fare"] == "12.00"
        assert_no_supply_data(cities)
        assert_no_supply_data(catalog)

        public_direction = expect(
            client.get(f"/api/v1/fixed-route-directions/{direction['id']}"),
            200,
        )
        assert public_direction["directions"][0]["flat_fare"] == "8.00"
        assert_no_supply_data(public_direction)
        public_alternate_direction = expect(
            client.get(f"/api/v1/fixed-route-directions/{alternate_direction['id']}"),
            200,
        )
        assert public_alternate_direction["directions"][0]["flat_fare"] == "12.00"
        assert_no_supply_data(public_alternate_direction)

        driver_email = f"route-driver-{suffix}@example.test"
        expect(
            client.post(
                "/api/v1/auth/register",
                json={
                    "email": driver_email,
                    "password": MANAGER_PASSWORD,
                    "display_name": "Fixed Route Integration Driver",
                },
            ),
            201,
        )
        asyncio.run(
            seed_fixed_route_driver(
                settings,
                email=driver_email,
                city_id=city_a["id"],
                suffix=suffix,
            )
        )
        driver_session = login(
            client,
            "/api/v1/auth/login",
            driver_email,
            MANAGER_PASSWORD,
        )
        driver_headers = bearer(driver_session["access_token"])
        preference = expect(
            client.patch(
                "/api/v1/drivers/me/scheduled-offer-preference",
                headers=driver_headers,
                json={"city_id": city_a["id"], "enabled": True},
            ),
            200,
        )
        assert preference["enabled"] is True
        preferences = expect(
            client.get(
                "/api/v1/drivers/me/scheduled-offer-preferences",
                headers=driver_headers,
            ),
            200,
        )
        assert preferences["items"] == [preference]
        expect(
            client.post(
                "/api/v1/drivers/me/location",
                headers=driver_headers,
                json={
                    "latitude": 34.02,
                    "longitude": -6.84,
                    "observed_at": datetime.now(UTC).isoformat(),
                    "accuracy": 6.0,
                },
            ),
            200,
        )
        online = expect(
            client.post(
                "/api/v1/drivers/me/availability/online",
                headers=driver_headers,
                json={
                    "city_id": city_a["id"],
                    "service_type": "FIXED_ROUTE",
                },
            ),
            200,
        )
        assert online["status"] == "AVAILABLE"
        assert online["city_id"] == city_a["id"]
        assert online["service_type"] == "FIXED_ROUTE"
        # Selecting a vehicle is an offline-only command, including when the
        # request races an assignment or repeats the existing selection.
        assert client.post(
            "/api/v1/drivers/me/active-vehicle", headers=driver_headers,
            json={"vehicle_id": online["vehicle_id"]},
        ).status_code == 409

        passenger_email = f"route-passenger-{suffix}@example.test"
        expect(
            client.post(
                "/api/v1/auth/register",
                json={
                    "email": passenger_email,
                    "password": MANAGER_PASSWORD,
                    "display_name": "Fixed Route Passenger",
                },
            ),
            201,
        )
        passenger = login(
            client,
            "/api/v1/auth/login",
            passenger_email,
            MANAGER_PASSWORD,
        )
        passenger_headers = bearer(passenger["access_token"])
        scheduled_for = datetime.now(UTC) + timedelta(hours=4)
        scheduled_payload = {
            "city_id": city_a["id"],
            "fixed_route_direction_version_id": direction["id"],
            "scheduled_for": scheduled_for.isoformat(),
            "payment_method": "CASH",
        }
        scheduled_estimate = expect(
            client.post(
                "/api/v1/scheduled-bookings/estimate",
                headers=passenger_headers,
                json=scheduled_payload,
            ),
            200,
        )
        assert scheduled_estimate["economics"]["passenger_total"] == "11.00"
        assert scheduled_estimate["cancellation_terms"]["surcharge_refund_mode"] == "FULL_BEFORE_CUTOFF"
        before_failed_creation = asyncio.run(scheduling_snapshot())
        with monkeypatch.context() as patch:
            patch.setattr(scheduling_service, "enqueue", fail_after_enqueue("scheduled.offer.created"))
            with pytest.raises(RuntimeError, match="Injected scheduling outbox failure"):
                client.post(
                    "/api/v1/scheduled-bookings",
                    headers={**passenger_headers, "Idempotency-Key": f"rollback-schedule-{suffix}"},
                    json=scheduled_payload,
                )
        assert asyncio.run(scheduling_snapshot()) == before_failed_creation
        scheduled = expect(
            client.post(
                "/api/v1/scheduled-bookings",
                headers={
                    **passenger_headers,
                    "Idempotency-Key": f"scheduled-fixed-route-{suffix}",
                },
                json={
                    **scheduled_payload,
                    "expected_pricing_rule_version": scheduled_estimate["economics"]["pricing_rule_version"],
                    "expected_operator_fee_policy_version": scheduled_estimate["economics"]["operator_fee_policy_version"],
                    "expected_scheduling_policy_version": scheduled_estimate["economics"]["scheduling_policy_version"],
                },
            ),
            201,
        )
        assert scheduled["status"] == "OFFERING"
        assert scheduled["driver_committed"] is False
        assert scheduled["economics"]["transport_fare"] == "8.00"
        assert scheduled["economics"]["scheduling_surcharge"] == "3.00"
        assert scheduled["economics"]["passenger_total"] == "11.00"
        scheduled_offer = expect(
            client.get("/api/v1/drivers/me/scheduled-offers", headers=driver_headers),
            200,
        )["items"][0]
        assert_delivery_pair("scheduled.offer.created", "SCHEDULED_OFFER", "offer_id", scheduled_offer["id"])
        before_creation_replay = asyncio.run(scheduling_snapshot())
        replay = expect(client.post(
            "/api/v1/scheduled-bookings",
            headers={**passenger_headers, "Idempotency-Key": f"scheduled-fixed-route-{suffix}"},
            json={
                **scheduled_payload,
                "expected_pricing_rule_version": scheduled_estimate["economics"]["pricing_rule_version"],
                "expected_operator_fee_policy_version": scheduled_estimate["economics"]["operator_fee_policy_version"],
                "expected_scheduling_policy_version": scheduled_estimate["economics"]["scheduling_policy_version"],
            },
        ), 201)
        assert replay == scheduled
        assert asyncio.run(scheduling_snapshot()) == before_creation_replay
        with monkeypatch.context() as patch:
            patch.setattr(scheduling_service, "enqueue", fail_after_enqueue("scheduled.driver.committed"))
            with pytest.raises(RuntimeError, match="Injected scheduling outbox failure"):
                client.post(
                    f"/api/v1/scheduled-offers/{scheduled_offer['id']}/accept",
                    headers=driver_headers,
                )
        assert asyncio.run(scheduling_snapshot()) == before_creation_replay
        if handoff_case == "race-accept-cancel":
            asyncio.run(prove_scheduling_race(settings, UUID(scheduled["id"]), "accept-cancel"))
            return
        first_commitment = expect(
            client.post(
                f"/api/v1/scheduled-offers/{scheduled_offer['id']}/accept",
                headers=driver_headers,
            ),
            200,
        )
        assert first_commitment["booking_id"] == scheduled["id"]
        assert first_commitment["status"] == "ACTIVE"
        assert_delivery_pair("scheduled.driver.committed", "SCHEDULED_DRIVER_COMMITTED", "booking_id", scheduled["id"])
        before_accept_replay = asyncio.run(scheduling_snapshot())
        assert client.post(
            f"/api/v1/scheduled-offers/{scheduled_offer['id']}/accept", headers=driver_headers,
        ).status_code == 409
        assert asyncio.run(scheduling_snapshot()) == before_accept_replay

        if handoff_case.startswith("mixed-"):
            asyncio.run(prove_mixed_assignment(settings, UUID(scheduled["id"]),
                immediate_first=handoff_case == "mixed-immediate-first"))
            return

        if handoff_case.startswith("race-"):
            asyncio.run(prove_scheduling_race(settings, UUID(scheduled["id"]), handoff_case.removeprefix("race-")))
            return

        async def attempt_dispatch(*, apply_readiness_case=False):
            engine = create_async_engine(settings.database_url)
            sessions = async_sessionmaker(engine, expire_on_commit=False)
            try:
                async with sessions() as session:
                    async with session.begin():
                        booking = await session.get(ScheduledBooking, UUID(scheduled["id"]))
                        # Advance the simulated driver's observation alongside
                        # the existing simulated handoff clock. This is test
                        # setup, not a bypass of production readiness checks.
                        profile = await session.scalar(select(DriverProfile).join(User).where(User.email == driver_email))
                        location = await session.scalar(select(DriverLocation).where(
                            DriverLocation.driver_id == profile.id,
                        ).order_by(DriverLocation.observed_at.desc(), DriverLocation.id.desc()).limit(1))
                        case = handoff_case if apply_readiness_case else "direct"
                        if location is not None:
                            location.observed_at = scheduled_for
                            if case == "stale-location":
                                location.observed_at -= timedelta(seconds=settings.matching_location_freshness_seconds + 1)
                            elif case == "future-location":
                                location.observed_at += timedelta(seconds=61)
                            elif case == "outside-area":
                                location.point = WKTElement("POINT(0 0)", srid=4326)
                        if case == "missing-location":
                            await session.execute(delete(DriverLocation).where(DriverLocation.driver_id == profile.id))
                        availability_cases = {
                            "offline": AvailabilityStatus.OFFLINE,
                            "paused": AvailabilityStatus.PAUSED,
                            "offered": AvailabilityStatus.OFFERED_RIDE,
                        }
                        if case in availability_cases:
                            profile.availability_status = availability_cases[case]
                        elif case == "wrong-city":
                            profile.online_city_id = UUID(city_b["id"])
                        elif case == "wrong-service":
                            profile.online_service_type = ServiceType.ON_DEMAND
                        await session.flush()
                        await scheduling_service.handoff_booking(
                            session, booking, now=scheduled_for, matching_settings=settings,
                        )
            finally:
                await engine.dispose()

        with monkeypatch.context() as patch:
            patch.setattr(scheduling_service, "enqueue", fail_after_enqueue("scheduled.dispatch.started"))
            with pytest.raises(RuntimeError, match="Injected scheduling outbox failure"):
                asyncio.run(attempt_dispatch())
        assert asyncio.run(scheduling_snapshot()) == before_accept_replay

        if handoff_case != "unfulfilled":
            # This branch uses the same real city, policy, published route and
            # committed booking as the full public-route lifecycle, but ends
            # with a durable successful handoff instead of cancellation.
            if handoff_case != "direct":
                replacement_email = f"replacement-{suffix}@example.test"
                expect(client.post("/api/v1/auth/register", json={
                    "email": replacement_email, "password": MANAGER_PASSWORD,
                    "display_name": "Replacement Integration Driver",
                }), 201)
                asyncio.run(seed_fixed_route_driver(
                    settings, email=replacement_email, city_id=city_a["id"],
                    suffix=f"replacement-{suffix}",
                ))
                replacement_session = login(client, "/api/v1/auth/login", replacement_email, MANAGER_PASSWORD)
                replacement_headers = bearer(replacement_session["access_token"])
                expect(client.post("/api/v1/drivers/me/location", headers=replacement_headers, json={
                    "latitude": 34.02, "longitude": -6.84,
                    "observed_at": datetime.now(UTC).isoformat(), "accuracy": 6.0,
                }), 200)
                expect(client.post("/api/v1/drivers/me/availability/online", headers=replacement_headers, json={
                    "city_id": city_a["id"], "service_type": "FIXED_ROUTE",
                }), 200)

                async def invalidate_committed_driver():
                    engine = create_async_engine(settings.database_url)
                    sessions = async_sessionmaker(engine, expire_on_commit=False)
                    try:
                        async with sessions() as session, session.begin():
                            profile = await session.scalar(select(DriverProfile).join(User).where(User.email == driver_email))
                            assert profile is not None
                            if handoff_case == "suspended":
                                profile.account_status = DriverAccountStatus.SUSPENDED
                            elif handoff_case == "vehicle-expired":
                                vehicle = await session.get(Vehicle, profile.active_vehicle_id)
                                vehicle.verification_status = VehicleVerificationStatus.EXPIRED
                            elif handoff_case == "credential-expired":
                                session.add(DriverCredential(
                                    driver_id=profile.id, credential_type="DRIVER_LICENSE",
                                    verification_status=CredentialVerificationStatus.VERIFIED,
                                    expires_at=datetime.now(UTC) - timedelta(seconds=1),
                                ))
                    finally:
                        await engine.dispose()

                asyncio.run(invalidate_committed_driver())

            topic = "scheduled.dispatch.started" if handoff_case == "direct" else "scheduled.fallback.matching"
            hint = "SCHEDULED_DISPATCH_STARTED" if handoff_case == "direct" else "SCHEDULED_FALLBACK_MATCHING"
            before_handoff = asyncio.run(scheduling_snapshot())
            with monkeypatch.context() as patch:
                patch.setattr(scheduling_service, "enqueue", fail_after_enqueue(topic))
                with pytest.raises(RuntimeError, match="Injected scheduling outbox failure"):
                    asyncio.run(attempt_dispatch(apply_readiness_case=True))
            assert asyncio.run(scheduling_snapshot()) == before_handoff

            asyncio.run(attempt_dispatch(apply_readiness_case=True))
            assert_delivery_pair(topic, hint, "booking_id", scheduled["id"])
            committed_handoff = asyncio.run(scheduling_snapshot())
            asyncio.run(attempt_dispatch(apply_readiness_case=True))
            assert asyncio.run(scheduling_snapshot()) == committed_handoff
            result = expect(client.get(f"/api/v1/scheduled-bookings/{scheduled['id']}", headers=passenger_headers), 200)
            assert result["status"] == "LIVE_RIDE_CREATED"
            live_id = result["live_ride_id"]
            assert live_id is not None
            live = expect(client.get(f"/api/v1/rides/{live_id}", headers=passenger_headers), 200)
            assert live["status"] == ("ACCEPTED" if handoff_case == "direct" else "MATCHING")
            if handoff_case == "direct":
                assert client.post("/api/v1/drivers/me/availability/offline", headers=driver_headers).status_code == 409
                assert client.post(
                    "/api/v1/drivers/me/active-vehicle", headers=driver_headers,
                    json={"vehicle_id": online["vehicle_id"]},
                ).status_code == 409

            async def verify_committed_participants_and_hint():
                engine = create_async_engine(settings.database_url)
                sessions = async_sessionmaker(engine, expire_on_commit=False)
                try:
                    async with sessions() as session:
                        booking = await session.get(ScheduledBooking, UUID(scheduled["id"]))
                        ride = await session.get(Ride, UUID(live_id))
                        commitment = await session.get(ScheduledBookingCommitment, UUID(first_commitment["id"]))
                        assert ride.scheduled_booking_id == booking.id
                        assert ride.passenger_id == booking.passenger_id
                        assert commitment.status.value == ("FULFILLED" if handoff_case == "direct" else "RELEASED")
                        if handoff_case == "direct":
                            assert ride.driver_id == commitment.driver_id
                        else:
                            assert ride.driver_id is None
                            offers = list(await session.scalars(select(RideOffer).where(RideOffer.ride_id == ride.id)))
                            assert len(offers) == 1
                            replacement = await session.scalar(select(DriverProfile).join(User).where(User.email == replacement_email))
                            assert offers[0].driver_id == replacement.id
                            assert offers[0].driver_id != commitment.driver_id
                        notification = await session.scalar(select(Notification).where(
                            Notification.type == hint, Notification.data["booking_id"].astext == scheduled["id"],
                        ))
                        assert notification.user_id == booking.passenger_id
                        assert notification.data == {"booking_id": scheduled["id"], "ride_id": live_id}
                        event = await session.scalar(select(OutboxEvent).where(
                            OutboxEvent.topic == topic, OutboxEvent.payload["booking_id"].astext == scheduled["id"],
                        ))
                        assert event.payload == {"booking_id": scheduled["id"]}
                        claimed = ClaimedOutboxEvent(event.id, event.topic, event.payload, event.created_at)
                        passenger_id = booking.passenger_id
                    hints = []

                    class Delivery(WebSocketOutboxDelivery):
                        async def _push_refresh(self, user_id, resource_id, event_type, expires_at):
                            hints.append((user_id, resource_id, event_type))

                    await Delivery(sessions, object()).deliver(claimed)
                    assert hints == [(passenger_id, UUID(scheduled["id"]), hint)]
                finally:
                    await engine.dispose()

            asyncio.run(verify_committed_participants_and_hint())
            return

        overlapping = expect(
            client.post(
                "/api/v1/scheduled-bookings",
                headers={
                    **passenger_headers,
                    "Idempotency-Key": f"scheduled-overlap-{suffix}",
                },
                json={
                    "city_id": city_a["id"],
                    "fixed_route_direction_version_id": alternate_direction["id"],
                    "scheduled_for": (scheduled_for + timedelta(minutes=30)).isoformat(),
                    "payment_method": "CASH",
                },
            ),
            201,
        )
        overlap_offer = expect(
            client.get("/api/v1/drivers/me/scheduled-offers", headers=driver_headers),
            200,
        )["items"][0]
        assert overlap_offer["booking_id"] == overlapping["id"]
        assert client.post(
            f"/api/v1/scheduled-offers/{overlap_offer['id']}/accept",
            headers=driver_headers,
        ).status_code == 409
        cancelled = expect(
            client.post(
                f"/api/v1/scheduled-bookings/{scheduled['id']}/cancel",
                headers={
                    **passenger_headers,
                    "Idempotency-Key": f"cancel-scheduled-{suffix}",
                },
                json={"reason": "Integration overlap release proof."},
            ),
            200,
        )
        assert cancelled["status"] == "CANCELLED"
        assert cancelled["cancellation_financial_outcome"] == "NO_CHARGE"
        second_commitment = expect(
            client.post(
                f"/api/v1/scheduled-offers/{overlap_offer['id']}/accept",
                headers=driver_headers,
            ),
            200,
        )
        assert second_commitment["booking_id"] == overlapping["id"]
        assert len(
            expect(
                client.get(
                    "/api/v1/drivers/me/scheduled-commitments",
                    headers=driver_headers,
                ),
                200,
            )["items"]
        ) == 1
        assert client.post(
            "/api/v1/rides/estimate",
            headers=passenger_headers,
            json={
                "fixed_route_direction_version_id": direction["id"],
                "pickup": {"latitude": 34.02, "longitude": -6.84},
            },
        ).status_code == 422
        estimate = expect(
            client.post(
                "/api/v1/rides/estimate",
                headers=passenger_headers,
                json={
                    "city_id": city_a["id"],
                    "fixed_route_direction_version_id": direction["id"],
                },
            ),
            200,
        )
        assert estimate["estimate"]["service_type"] == "FIXED_ROUTE"
        assert estimate["estimate"]["amount"] == "8.00"
        assert estimate["estimate"]["fixed_route"]["route_code"] == "RABAT_01"
        assert "CASH" in estimate["payment_methods"]

        ride = expect(
            client.post(
                "/api/v1/rides",
                headers={
                    **passenger_headers,
                    "Idempotency-Key": f"fixed-route-decline-{suffix}",
                },
                json={
                    "city_id": city_a["id"],
                    "fixed_route_direction_version_id": direction["id"],
                    "payment_method": "CASH",
                },
            ),
            201,
        )
        assert ride["service_type"] == "FIXED_ROUTE"
        assert ride["fixed_route"]["direction_version_id"] == direction["id"]

        offered = expect(
            client.get(
                "/api/v1/drivers/me/ride-offers",
                headers=driver_headers,
            ),
            200,
        )["offers"]
        assert len(offered) == 1
        assert offered[0]["ride_id"] == ride["id"]
        assert offered[0]["service_type"] == "FIXED_ROUTE"
        assert offered[0]["estimated_fare"] == {"amount": "8.00", "currency": "MAD"}
        assert offered[0]["fixed_route"]["direction_version_id"] == direction["id"]
        assert offered[0]["fixed_route"]["start_location_name"]["en"] == "Central station"
        assert offered[0]["fixed_route"]["finish_location_name"]["en"] == "University"
        expect(
            client.post(
                f"/api/v1/ride-offers/{offered[0]['id']}/decline",
                headers=driver_headers,
                json={"reason": "Direction is not suitable right now."},
            ),
            200,
        )
        declined_ride = expect(
            client.get(f"/api/v1/rides/{ride['id']}", headers=passenger_headers),
            200,
        )
        assert declined_ride["status"] == "UNMATCHED"

        accepted_ride = expect(
            client.post(
                "/api/v1/rides",
                headers={
                    **passenger_headers,
                    "Idempotency-Key": f"fixed-route-accept-{suffix}",
                },
                json={
                    "city_id": city_a["id"],
                    "fixed_route_direction_version_id": direction["id"],
                    "payment_method": "CASH",
                },
            ),
            201,
        )
        accepted_offer = expect(
            client.get(
                "/api/v1/drivers/me/ride-offers",
                headers=driver_headers,
            ),
            200,
        )["offers"][0]
        accepted = expect(
            client.post(
                f"/api/v1/ride-offers/{accepted_offer['id']}/accept",
                headers=driver_headers,
            ),
            200,
        )
        assert accepted == {"ride_id": accepted_ride["id"], "status": "ACCEPTED"}
        driver_rides = expect(
            client.get("/api/v1/drivers/me/rides", headers=driver_headers),
            200,
        )["items"]
        assert driver_rides[0]["id"] == accepted_ride["id"]
        assert driver_rides[0]["service_type"] == "FIXED_ROUTE"
        assert driver_rides[0]["fixed_route"]["direction_version_id"] == direction["id"]

        # The committed driver now has a conflicting live ride. At handoff the
        # immutable fallback policy invokes normal matching; because no other
        # eligible online taxi exists, its temporary ride/outbox work is rolled
        # back and the scheduled aggregate becomes explicitly unfulfilled.
        async def run_scheduled_handoff(expected_unfulfilled=1) -> None:
            engine = create_async_engine(settings.database_url, pool_pre_ping=True)
            sessions = async_sessionmaker(engine, expire_on_commit=False)
            try:
                async with sessions() as session:
                    async with session.begin():
                        counts = await advance_due_bookings(
                            session,
                            now=scheduled_for,
                            matching_settings=settings,
                        )
                        assert counts["unfulfilled"] == expected_unfulfilled
            finally:
                await engine.dispose()

        before_failed_handoff = asyncio.run(scheduling_snapshot())
        with monkeypatch.context() as patch:
            patch.setattr(scheduling_service, "enqueue", fail_after_enqueue("scheduled.unfulfilled"))
            with pytest.raises(RuntimeError, match="Injected scheduling outbox failure"):
                asyncio.run(run_scheduled_handoff())
        assert asyncio.run(scheduling_snapshot()) == before_failed_handoff
        asyncio.run(run_scheduled_handoff())
        unfulfilled = expect(
            client.get(
                f"/api/v1/scheduled-bookings/{overlapping['id']}",
                headers=passenger_headers,
            ),
            200,
        )
        assert unfulfilled["status"] == "UNFULFILLED"
        assert unfulfilled["live_ride_id"] is None
        assert_delivery_pair("scheduled.unfulfilled", "SCHEDULED_UNFULFILLED", "booking_id", overlapping["id"])
        after_unfulfilled = asyncio.run(scheduling_snapshot())
        assert not any(
            row.topic in {"scheduled.dispatch.started", "scheduled.fallback.matching"}
            for row in after_unfulfilled["outbox"]
        )
        assert after_unfulfilled["rides"] == before_failed_handoff["rides"]
        prior_outbox_ids = {row.id for row in before_failed_handoff["outbox"]}
        assert [row.topic for row in after_unfulfilled["outbox"] if row.id not in prior_outbox_ids] == [
            "scheduled.unfulfilled"
        ]
        prior_notification_ids = {row.id for row in before_failed_handoff["notifications"]}
        assert [row.type for row in after_unfulfilled["notifications"] if row.id not in prior_notification_ids] == [
            "SCHEDULED_UNFULFILLED"
        ]
        asyncio.run(run_scheduled_handoff(expected_unfulfilled=0))
        assert asyncio.run(scheduling_snapshot()) == after_unfulfilled

        # A paused city keeps its public route orientation but cannot advertise booking.
        async def pause_city() -> None:
            engine = create_async_engine(settings.database_url, pool_pre_ping=True)
            sessions = async_sessionmaker(engine, expire_on_commit=False)
            try:
                async with sessions() as session:
                    async with session.begin():
                        city = await session.get(City, UUID(city_a["id"]))
                        assert city is not None
                        city.lifecycle_status = CityLifecycleStatus.PAUSED
            finally:
                await engine.dispose()

        asyncio.run(pause_city())
        paused_catalog = expect(
            client.get(f"/api/v1/cities/{city_a['id']}/fixed-routes"),
            200,
        )
        assert paused_catalog["city"]["lifecycle_status"] == "PAUSED"
        assert paused_catalog["city"]["booking_available"] is False
        paused_directions = [
            item
            for route in paused_catalog["routes"]
            for version in route["versions"]
            for item in version["directions"]
        ]
        assert all(item["immediate_booking_enabled"] is False for item in paused_directions)
        assert all(item["scheduled_booking_enabled"] is False for item in paused_directions)
        assert client.post(
            "/api/v1/rides/estimate",
            headers=passenger_headers,
            json={"fixed_route_direction_version_id": direction["id"]},
        ).status_code == 409
