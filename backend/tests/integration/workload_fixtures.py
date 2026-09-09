"""Inert synthetic driver supply for the real-HTTP passenger workload tests."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4
from secrets import token_urlsafe

from geoalchemy2.elements import WKTElement

from taximobile_api.domains.auth.models import User, UserRole, Role
from taximobile_api.domains.auth.security import hash_password
from taximobile_api.domains.drivers.models import (
    AvailabilityStatus, DriverAccountStatus, DriverLocation, DriverProfile,
    Vehicle, VehicleVerificationStatus, VerificationStatus,
)
from taximobile_api.domains.driver_applications.models import (
    DriverCityApplication, DriverCityAuthorization, DriverCityAuthorizationService,
    DriverApplicationEvidence, ApplicationEvidenceStatus, CityApplicationStatus,
)
from taximobile_api.domains.markets.constants import LEGACY_CITY_ID, LEGACY_DRIVER_REQUIREMENT_VERSION_ID, LEGACY_DRIVER_PROFILE_REQUIREMENT_ITEM_ID
from taximobile_api.domains.markets.models import ServiceType


async def seed_workload_supply(sessions, count, *, loginable=False):
    credentials = []
    async with sessions.begin() as session:
        for _ in range(count):
            user = User(email=f"supply-{uuid4().hex}@taximobile.invalid",
                        password_hash="!inert-synthetic-supply")
            password = token_urlsafe(32) if loginable else None
            if password is not None:
                user.password_hash = hash_password(password)
            session.add(user)
            await session.flush()
            if password is not None:
                credentials.append({"user_id": str(user.id), "identifier": user.email, "password": password})
                session.add(UserRole(user_id=user.id, role=Role.DRIVER))
            driver = DriverProfile(
                user_id=user.id, display_name="Synthetic workload supply",
                account_status=DriverAccountStatus.ACTIVE,
                verification_status=VerificationStatus.APPROVED,
                availability_status=AvailabilityStatus.OFFLINE if loginable else AvailabilityStatus.AVAILABLE,
                online_city_id=LEGACY_CITY_ID, online_service_type=ServiceType.ON_DEMAND,
                available_since=datetime.now(UTC) - timedelta(minutes=5),
            )
            session.add(driver)
            await session.flush()
            vehicle = Vehicle(driver_id=driver.id, make="Synthetic", model="Fixture", year=2025,
                              color="grey", registration_number=f"TEST-{uuid4().hex}",
                              verification_status=VehicleVerificationStatus.VERIFIED)
            session.add(vehicle)
            await session.flush()
            driver.active_vehicle_id = vehicle.id
            application = DriverCityApplication(driver_id=driver.id, city_id=LEGACY_CITY_ID,
                                                requirement_version_id=LEGACY_DRIVER_REQUIREMENT_VERSION_ID)
            session.add(application)
            await session.flush()
            if loginable:
                application.status = CityApplicationStatus.APPROVED
                session.add(DriverApplicationEvidence(
                    application_id=application.id, requirement_item_id=LEGACY_DRIVER_PROFILE_REQUIREMENT_ITEM_ID,
                    profile_id=driver.id, status=ApplicationEvidenceStatus.ACCEPTED,
                ))
            authorization = DriverCityAuthorization(
                driver_id=driver.id, city_id=LEGACY_CITY_ID, application_id=application.id,
                vehicle_id=vehicle.id, valid_from=datetime.now(UTC) - timedelta(days=1),
            )
            session.add(authorization)
            await session.flush()
            session.add(DriverCityAuthorizationService(authorization_id=authorization.id,
                                                       service_type=ServiceType.ON_DEMAND))
            session.add(DriverLocation(driver_id=driver.id,
                                       point=WKTElement("POINT(-7.5898 33.5731)", srid=4326),
                                       observed_at=datetime.now(UTC), accuracy_meters=5))
    return credentials
