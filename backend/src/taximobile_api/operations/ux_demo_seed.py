"""Create additive synthetic UX-review data in a confirmed local database only."""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import json
from secrets import token_hex
from urllib.parse import urlparse

from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from taximobile_api.core.config import Settings
from taximobile_api.domains.administration.models import (
    AdministrativeGrant,
    AdministrativeRoleTemplate,
)
from taximobile_api.domains.auth.models import Role, UserRole
from taximobile_api.domains.auth.schemas import RegisterRequest
from taximobile_api.domains.auth.service import register_passenger
from taximobile_api.domains.analytics.service import refresh_operational_analytics
from taximobile_api.domains.cooperatives.models import Cooperative, CooperativeMembership
from taximobile_api.domains.cooperatives.models import CooperativeMembershipStatus
from taximobile_api.domains.driver_applications.models import (
    ApplicationEvidenceStatus,
    CityApplicationStatus,
    CityAuthorizationStatus,
    DriverApplicationEvidence,
    DriverCityApplication,
    DriverCityAuthorization,
    DriverCityAuthorizationService,
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
from taximobile_api.domains.fixed_routes.models import (
    CityConfigurationRoute,
    FixedRoute,
    FixedRouteDirection,
    FixedRouteDirectionCode,
    FixedRoutePublicationStatus,
    FixedRouteStatus,
    FixedRouteStop,
    FixedRouteVersion,
)
from taximobile_api.domains.notifications.models import Notification
from taximobile_api.domains.payments.models import DriverEarning, Payment, PaymentMethod, PaymentStatus
from taximobile_api.domains.pricing.models import (
    BookingType,
    FareRecord,
    FinancialPolicyStatus,
    OperatorFeeCalculationMode,
    OperatorFeeFundingMode,
    OperatorFeePolicy,
    PricingModel,
    PricingRoundingRule,
    PricingRule,
    PricingRuleStatus,
    SchedulingPolicy,
    SchedulingRefundMode,
    SchedulingSurchargeBeneficiary,
)
from taximobile_api.domains.rides.models import Ride, RideEvent, RideEventType, RideRating, RideStatus
from taximobile_api.domains.rides.schemas import Coordinate
from taximobile_api.domains.scheduled_bookings.models import ScheduledBookingOffer
from taximobile_api.domains.scheduled_bookings.schemas import ScheduledBookingCreateRequest
from taximobile_api.domains.scheduled_bookings.service import (
    accept_offer as accept_scheduled_offer,
    create_scheduled_booking,
    set_offer_preference,
)
from taximobile_api.domains.support.models import SupportCategory, SupportTicket, SupportTicketStatus
from taximobile_api.domains.markets.constants import (
    LEGACY_CITY_ID,
    LEGACY_DRIVER_PROFILE_REQUIREMENT_ITEM_ID,
    LEGACY_DRIVER_REQUIREMENT_VERSION_ID,
    LEGACY_OPERATOR_ID,
)
from taximobile_api.domains.markets.models import (
    AssignmentStatus,
    City,
    CityConfigurationService,
    CityConfigurationVersion,
    ConfigurationStatus,
    OperatorCityAssignment,
    ServiceType,
)


DEMO_CONFIRMATION = "CONFIRM_LOCAL_UX_DEMO_DATA"
LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


class DemoSeedRefused(ValueError):
    """The requested target is not an explicitly confirmed local development database."""


def validate_demo_target(*, environment: str, database_url: str, confirmation: str) -> None:
    parsed = urlparse(database_url.replace("postgresql+asyncpg://", "postgresql://", 1))
    database_name = parsed.path.removeprefix("/")
    if confirmation != DEMO_CONFIRMATION:
        raise DemoSeedRefused(f"Pass --confirm {DEMO_CONFIRMATION} after reviewing the target.")
    if environment != "development":
        raise DemoSeedRefused("UX demo data is allowed only with TAXIMOBILE_ENV=development.")
    if parsed.hostname not in LOOPBACK_HOSTS:
        raise DemoSeedRefused("UX demo data requires a loopback PostgreSQL host.")
    if not database_name or database_name in {"postgres", "template0", "template1"}:
        raise DemoSeedRefused("UX demo data requires a named application database.")


def point(latitude: float, longitude: float) -> WKTElement:
    return WKTElement(f"POINT({longitude} {latitude})", srid=4326)


def line_string(coordinates: list[tuple[float, float]]) -> WKTElement:
    points = ", ".join(f"{longitude} {latitude}" for latitude, longitude in coordinates)
    return WKTElement(f"LINESTRING({points})", srid=4326)


async def add_passenger(session, *, email: str, password: str, display_name: str):
    return await register_passenger(
        session,
        RegisterRequest(email=email, password=password, display_name=display_name),
    )


def assigned_ride(
    *,
    passenger_id,
    driver: DriverProfile,
    vehicle: Vehicle,
    rule: PricingRule,
    status: RideStatus,
    pickup: tuple[float, float, str],
    destination: tuple[float, float, str],
    created_at: datetime,
) -> Ride:
    accepted_at = created_at + timedelta(minutes=2)
    return Ride(
        city_id=LEGACY_CITY_ID,
        operator_id=LEGACY_OPERATOR_ID,
        passenger_id=passenger_id,
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        assigned_driver_name=driver.display_name,
        assigned_vehicle_make=vehicle.make,
        assigned_vehicle_model=vehicle.model,
        assigned_vehicle_color=vehicle.color,
        assigned_taxi_identifier=vehicle.taxi_identifier,
        quoted_pricing_rule_id=rule.id,
        quoted_amount=rule.fixed_amount,
        quoted_currency=rule.currency,
        status=status,
        pickup_point=point(pickup[0], pickup[1]),
        destination_point=point(destination[0], destination[1]),
        pickup_address=pickup[2],
        destination_address=destination[2],
        accepted_at=accepted_at,
        en_route_at=accepted_at + timedelta(minutes=1) if status != RideStatus.ACCEPTED else None,
        arrived_at=accepted_at + timedelta(minutes=8)
        if status in {RideStatus.DRIVER_ARRIVED, RideStatus.IN_PROGRESS, RideStatus.COMPLETED}
        else None,
        started_at=accepted_at + timedelta(minutes=10)
        if status in {RideStatus.IN_PROGRESS, RideStatus.COMPLETED}
        else None,
        created_at=created_at,
        updated_at=created_at,
    )


async def add_completed_ride(
    session,
    *,
    passenger_id,
    driver: DriverProfile,
    vehicle: Vehicle,
    rule: PricingRule,
    pickup: tuple[float, float, str],
    destination: tuple[float, float, str],
    created_at: datetime,
    settled: bool,
    rating: int | None,
) -> Ride:
    ride = assigned_ride(
        passenger_id=passenger_id,
        driver=driver,
        vehicle=vehicle,
        rule=rule,
        status=RideStatus.COMPLETED,
        pickup=pickup,
        destination=destination,
        created_at=created_at,
    )
    ride.completed_at = created_at + timedelta(minutes=24)
    ride.completed_point = point(destination[0], destination[1])
    session.add(ride)
    await session.flush()

    amount = Decimal(str(rule.fixed_amount))
    session.add(
        FareRecord(
            ride_id=ride.id,
            pricing_rule_id=rule.id,
            base_amount=amount,
            total_amount=amount,
            currency=rule.currency,
            snapshot={
                "tariff_version": rule.version,
                "model": PricingModel.FIXED.value,
                "base_fare": str(amount),
                "total": str(amount),
                "currency": rule.currency,
            },
            calculated_at=ride.completed_at,
            finalized_at=ride.completed_at,
        )
    )
    payment = Payment(
        ride_id=ride.id,
        payer_id=passenger_id,
        amount=amount,
        currency=rule.currency,
        method=PaymentMethod.CASH,
        status=PaymentStatus.COMPLETED if settled else PaymentStatus.PENDING,
        completed_at=ride.completed_at + timedelta(minutes=1) if settled else None,
        created_at=ride.completed_at,
    )
    session.add(payment)
    await session.flush()
    if settled:
        session.add(
            DriverEarning(
                driver_id=driver.id,
                ride_id=ride.id,
                payment_id=payment.id,
                gross_amount=amount,
                fee_amount=Decimal("0.00"),
                adjustment_amount=Decimal("0.00"),
                net_amount=amount,
                transport_fare_amount=amount,
                scheduling_surcharge_amount=Decimal("0.00"),
                operator_fee_amount=Decimal("0.00"),
                operator_allocation_amount=Decimal("0.00"),
                currency=rule.currency,
                settled_at=payment.completed_at,
            )
        )
    if rating is not None:
        session.add(
            RideRating(
                ride_id=ride.id,
                reviewer_id=passenger_id,
                reviewed_user_id=driver.user_id,
                score=rating,
                comment="Friendly, safe ride through Casablanca.",
                created_at=ride.completed_at + timedelta(minutes=3),
            )
        )
    session.add(
        RideEvent(
            ride_id=ride.id,
            event_type=RideEventType.STATUS_CHANGED,
            previous_status=RideStatus.IN_PROGRESS,
            new_status=RideStatus.COMPLETED,
            actor_user_id=driver.user_id,
            created_at=ride.completed_at,
        )
    )
    return ride


async def seed_demo(settings: Settings) -> dict[str, object]:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    suffix = token_hex(4)
    password = f"Demo-{token_hex(6)}-Aa9!"
    now = datetime.now(UTC)
    emails = {
        "passenger_rich": f"ux-passenger-{suffix}@example.test",
        "driver_rich": f"ux-driver-{suffix}@example.test",
        "driver_pending": f"ux-driver-pending-{suffix}@example.test",
        "passenger_empty": f"ux-empty-{suffix}@example.test",
        "operations_recruitment": f"ux-operations-{suffix}@example.test",
    }
    try:
        async with sessions() as session:
            async with session.begin():
                passenger = await add_passenger(
                    session,
                    email=emails["passenger_rich"],
                    password=password,
                    display_name="Salma UX Passenger",
                )
                driver_user = await add_passenger(
                    session,
                    email=emails["driver_rich"],
                    password=password,
                    display_name="Youssef UX Driver",
                )
                pending_user = await add_passenger(
                    session,
                    email=emails["driver_pending"],
                    password=password,
                    display_name="Nadia Pending Driver",
                )
                empty_passenger = await add_passenger(
                    session,
                    email=emails["passenger_empty"],
                    password=password,
                    display_name="Omar Empty State",
                )
                operations_user = await add_passenger(
                    session,
                    email=emails["operations_recruitment"],
                    password=password,
                    display_name="Amal UX Recruitment Reviewer",
                )
                session.add_all(
                    [
                        AdministrativeGrant(
                            user_id=operations_user.id,
                            role_template=AdministrativeRoleTemplate.CITY_MANAGER,
                            city_id=LEGACY_CITY_ID,
                            granted_by_user_id=operations_user.id,
                            grant_reason="Synthetic local UX city-management grant.",
                            granted_at=now,
                        ),
                        AdministrativeGrant(
                            user_id=operations_user.id,
                            role_template=AdministrativeRoleTemplate.DRIVER_REVIEWER,
                            city_id=LEGACY_CITY_ID,
                            granted_by_user_id=operations_user.id,
                            grant_reason="Synthetic local UX driver-review grant.",
                            granted_at=now,
                        ),
                        AdministrativeGrant(
                            user_id=operations_user.id,
                            role_template=AdministrativeRoleTemplate.ANALYST,
                            city_id=LEGACY_CITY_ID,
                            granted_by_user_id=operations_user.id,
                            grant_reason="Synthetic local UX aggregate-view grant.",
                            granted_at=now,
                        ),
                    ]
                )

                driver = DriverProfile(
                    user_id=driver_user.id,
                    display_name="Youssef UX Driver",
                    verification_status=VerificationStatus.APPROVED,
                    account_status=DriverAccountStatus.ACTIVE,
                    availability_status=AvailabilityStatus.EN_ROUTE,
                    online_city_id=LEGACY_CITY_ID,
                    online_service_type=ServiceType.ON_DEMAND,
                )
                pending_driver = DriverProfile(
                    user_id=pending_user.id,
                    display_name="Nadia Pending Driver",
                    verification_status=VerificationStatus.SUBMITTED,
                    account_status=DriverAccountStatus.PENDING,
                    availability_status=AvailabilityStatus.OFFLINE,
                )
                session.add_all([driver, pending_driver])
                await session.flush()
                session.add_all(
                    [
                        UserRole(user_id=driver_user.id, role=Role.DRIVER),
                        UserRole(user_id=driver_user.id, role=Role.COOPERATIVE_MEMBER),
                        DriverVerification(
                            driver_id=driver.id,
                            status=VerificationStatus.APPROVED,
                            submitted_at=now - timedelta(days=90),
                            reviewed_at=now - timedelta(days=88),
                        ),
                        DriverVerification(
                            driver_id=pending_driver.id,
                            status=VerificationStatus.SUBMITTED,
                            submitted_at=now - timedelta(days=2),
                        ),
                    ]
                )

                vehicle = Vehicle(
                    driver_id=driver.id,
                    make="Dacia",
                    model="Logan",
                    year=2024,
                    color="White",
                    registration_number=f"UX-{suffix.upper()}",
                    taxi_identifier=f"CASA-{suffix[:4].upper()}",
                    passenger_capacity=4,
                    status=VehicleStatus.ACTIVE,
                    verification_status=VehicleVerificationStatus.VERIFIED,
                )
                session.add(vehicle)
                await session.flush()
                driver.active_vehicle_id = vehicle.id
                approved_application = DriverCityApplication(
                    driver_id=driver.id,
                    city_id=LEGACY_CITY_ID,
                    requirement_version_id=LEGACY_DRIVER_REQUIREMENT_VERSION_ID,
                    status=CityApplicationStatus.APPROVED,
                    optimistic_version=2,
                    submission_revision=1,
                    submitted_at=now - timedelta(days=90),
                    reviewed_at=now - timedelta(days=88),
                )
                pending_application = DriverCityApplication(
                    driver_id=pending_driver.id,
                    city_id=LEGACY_CITY_ID,
                    requirement_version_id=LEGACY_DRIVER_REQUIREMENT_VERSION_ID,
                    status=CityApplicationStatus.SUBMITTED,
                    optimistic_version=2,
                    submission_revision=1,
                    submitted_at=now - timedelta(days=2),
                )
                session.add_all([approved_application, pending_application])
                await session.flush()
                # Four unlisted synthetic applicants make the submitted funnel
                # cell reach the privacy threshold while approved/review-time
                # cells remain suppressed. This exercises both UI states.
                for index in range(4):
                    funnel_user = await add_passenger(
                        session,
                        email=f"ux-funnel-{index}-{suffix}@example.test",
                        password=password,
                        display_name=f"Synthetic Funnel Applicant {index + 1}",
                    )
                    funnel_driver = DriverProfile(
                        user_id=funnel_user.id,
                        display_name=f"Synthetic Funnel Applicant {index + 1}",
                        verification_status=VerificationStatus.SUBMITTED,
                        account_status=DriverAccountStatus.PENDING,
                        availability_status=AvailabilityStatus.OFFLINE,
                    )
                    session.add(funnel_driver)
                    await session.flush()
                    funnel_application = DriverCityApplication(
                        driver_id=funnel_driver.id,
                        city_id=LEGACY_CITY_ID,
                        requirement_version_id=LEGACY_DRIVER_REQUIREMENT_VERSION_ID,
                        status=CityApplicationStatus.SUBMITTED,
                        optimistic_version=2,
                        submission_revision=1,
                        submitted_at=now - timedelta(days=index + 3),
                    )
                    session.add(funnel_application)
                    await session.flush()
                    session.add_all(
                        [
                            DriverVerification(
                                driver_id=funnel_driver.id,
                                status=VerificationStatus.SUBMITTED,
                                submitted_at=now - timedelta(days=index + 3),
                            ),
                            DriverApplicationEvidence(
                                application_id=funnel_application.id,
                                requirement_item_id=LEGACY_DRIVER_PROFILE_REQUIREMENT_ITEM_ID,
                                profile_id=funnel_driver.id,
                                status=ApplicationEvidenceStatus.PENDING,
                            ),
                        ]
                    )
                authorization = DriverCityAuthorization(
                    driver_id=driver.id,
                    city_id=LEGACY_CITY_ID,
                    application_id=approved_application.id,
                    vehicle_id=vehicle.id,
                    status=CityAuthorizationStatus.ACTIVE,
                    scheduled_offers_enabled=False,
                    valid_from=now - timedelta(days=88),
                )
                session.add(authorization)
                await session.flush()
                session.add_all(
                    [
                        DriverApplicationEvidence(
                            application_id=approved_application.id,
                            requirement_item_id=LEGACY_DRIVER_PROFILE_REQUIREMENT_ITEM_ID,
                            profile_id=driver.id,
                            status=ApplicationEvidenceStatus.ACCEPTED,
                        ),
                        DriverApplicationEvidence(
                            application_id=pending_application.id,
                            requirement_item_id=LEGACY_DRIVER_PROFILE_REQUIREMENT_ITEM_ID,
                            profile_id=pending_driver.id,
                            status=ApplicationEvidenceStatus.PENDING,
                        ),
                        DriverCityAuthorizationService(
                            authorization_id=authorization.id,
                            service_type=ServiceType.ON_DEMAND,
                        ),
                        DriverCityAuthorizationService(
                            authorization_id=authorization.id,
                            service_type=ServiceType.FIXED_ROUTE,
                        ),
                    ]
                )
                session.add(
                    DriverCredential(
                        driver_id=driver.id,
                        credential_type="DRIVER_LICENSE",
                        verification_status=CredentialVerificationStatus.VERIFIED,
                        issued_at=now - timedelta(days=400),
                        expires_at=now + timedelta(days=24),
                    )
                )

                cooperative = Cooperative(
                    name="Casablanca UX Taxi Cooperative",
                    legal_identifier=f"ux-cooperative-{suffix}",
                )
                session.add(cooperative)
                await session.flush()
                session.add(
                    CooperativeMembership(
                        cooperative_id=cooperative.id,
                        user_id=driver_user.id,
                        membership_status=CooperativeMembershipStatus.ACTIVE,
                        joined_at=now - timedelta(days=730),
                        membership_number=f"UX-{suffix.upper()}",
                    )
                )

                city = await session.get(City, LEGACY_CITY_ID, with_for_update=True)
                if city is None or city.active_configuration_version_id is None:
                    raise RuntimeError("The Casablanca compatibility city must have an active configuration.")
                current_configuration = await session.get(
                    CityConfigurationVersion,
                    city.active_configuration_version_id,
                    with_for_update=True,
                )
                if current_configuration is None:
                    raise RuntimeError("The active Casablanca configuration could not be loaded.")
                current_services = list(
                    await session.scalars(
                        select(CityConfigurationService).where(
                            CityConfigurationService.configuration_version_id
                            == current_configuration.id
                        )
                    )
                )
                current_routes = list(
                    await session.scalars(
                        select(CityConfigurationRoute).where(
                            CityConfigurationRoute.configuration_version_id
                            == current_configuration.id
                        )
                    )
                )
                configured_fixed_service = next(
                    (
                        service
                        for service in current_services
                        if service.service_type == ServiceType.FIXED_ROUTE
                    ),
                    None,
                )
                if configured_fixed_service is None:
                    fixed_assignment = OperatorCityAssignment(
                        operator_id=LEGACY_OPERATOR_ID,
                        city_id=LEGACY_CITY_ID,
                        service_type=ServiceType.FIXED_ROUTE,
                        effective_from=now - timedelta(minutes=1),
                        status=AssignmentStatus.ACTIVE,
                        created_by_user_id=operations_user.id,
                    )
                    fixed_fee_policy = OperatorFeePolicy(
                        city_id=LEGACY_CITY_ID,
                        operator_id=LEGACY_OPERATOR_ID,
                        service_type=ServiceType.FIXED_ROUTE,
                        version=f"ux-route-zero-fee-{suffix}",
                        status=FinancialPolicyStatus.ACTIVE,
                        calculation_mode=OperatorFeeCalculationMode.FLAT_PER_COMPLETED_BOOKING,
                        funding_mode=OperatorFeeFundingMode.DRIVER_SETTLEMENT_DEDUCTION,
                        eligible_base_code="TRANSPORT_FARE",
                        flat_amount=Decimal("0.00"),
                        currency="MAD",
                        rounding_rule=PricingRoundingRule.HALF_UP_0_01,
                        minimum_driver_net=Decimal("0.00"),
                        effective_from=now - timedelta(minutes=1),
                        created_by_user_id=operations_user.id,
                        submitted_by_user_id=operations_user.id,
                        submitted_at=now,
                        activated_by_user_id=operations_user.id,
                        activated_at=now,
                    )
                    session.add_all([fixed_assignment, fixed_fee_policy])
                    await session.flush()
                    fixed_assignment_id = fixed_assignment.id
                    fixed_fee_policy_id = fixed_fee_policy.id
                else:
                    if configured_fixed_service.operator_fee_policy_version_id is None:
                        raise RuntimeError(
                            "The configured fixed-route service is missing its operator fee policy."
                        )
                    fixed_assignment_id = configured_fixed_service.operator_city_assignment_id
                    fixed_fee_policy_id = configured_fixed_service.operator_fee_policy_version_id

                configured_on_demand_service = next(
                    (
                        service
                        for service in current_services
                        if service.service_type == ServiceType.ON_DEMAND and service.enabled
                    ),
                    None,
                )
                if (
                    configured_on_demand_service is None
                    or configured_on_demand_service.operator_fee_policy_version_id is None
                ):
                    raise RuntimeError(
                        "The configured on-demand service is missing its active operator-fee policy."
                    )
                on_demand_schedule_policy = SchedulingPolicy(
                    city_id=LEGACY_CITY_ID,
                    operator_id=LEGACY_OPERATOR_ID,
                    service_type=ServiceType.ON_DEMAND,
                    version=f"ux-on-demand-schedule-{suffix}",
                    status=FinancialPolicyStatus.ACTIVE,
                    surcharge_amount=Decimal("4.00"),
                    currency="MAD",
                    beneficiary=SchedulingSurchargeBeneficiary.DRIVER,
                    collection_timing_code="AT_RIDE_SETTLEMENT",
                    minimum_lead_minutes=60,
                    maximum_horizon_days=30,
                    offer_open_minutes_before=1440,
                    offer_response_seconds=600,
                    commitment_deadline_minutes_before=180,
                    handoff_minutes_before=30,
                    protected_duration_minutes=90,
                    conflict_buffer_before_minutes=30,
                    conflict_buffer_after_minutes=30,
                    passenger_cancel_cutoff_minutes=60,
                    driver_cancel_cutoff_minutes=120,
                    surcharge_refund_mode=SchedulingRefundMode.FULL_BEFORE_CUTOFF,
                    fallback_matching_enabled=True,
                    effective_from=now - timedelta(minutes=1),
                    created_by_user_id=operations_user.id,
                    submitted_by_user_id=operations_user.id,
                    submitted_at=now,
                    activated_by_user_id=operations_user.id,
                    activated_at=now,
                )
                fixed_schedule_policy = SchedulingPolicy(
                    city_id=LEGACY_CITY_ID,
                    operator_id=LEGACY_OPERATOR_ID,
                    service_type=ServiceType.FIXED_ROUTE,
                    version=f"ux-fixed-schedule-{suffix}",
                    status=FinancialPolicyStatus.ACTIVE,
                    surcharge_amount=Decimal("3.00"),
                    currency="MAD",
                    beneficiary=SchedulingSurchargeBeneficiary.OPERATOR,
                    collection_timing_code="AT_RIDE_SETTLEMENT",
                    minimum_lead_minutes=60,
                    maximum_horizon_days=30,
                    offer_open_minutes_before=1440,
                    offer_response_seconds=600,
                    commitment_deadline_minutes_before=180,
                    handoff_minutes_before=30,
                    protected_duration_minutes=75,
                    conflict_buffer_before_minutes=30,
                    conflict_buffer_after_minutes=30,
                    passenger_cancel_cutoff_minutes=60,
                    driver_cancel_cutoff_minutes=120,
                    surcharge_refund_mode=SchedulingRefundMode.FULL_BEFORE_CUTOFF,
                    fallback_matching_enabled=True,
                    effective_from=now - timedelta(minutes=1),
                    created_by_user_id=operations_user.id,
                    submitted_by_user_id=operations_user.id,
                    submitted_at=now,
                    activated_by_user_id=operations_user.id,
                    activated_at=now,
                )
                scheduled_on_demand_rule = PricingRule(
                    city_id=LEGACY_CITY_ID,
                    operator_id=LEGACY_OPERATOR_ID,
                    service_type=ServiceType.ON_DEMAND,
                    booking_type=BookingType.SCHEDULED,
                    name="Casablanca scheduled UX fare",
                    version=f"ux-scheduled-fare-{suffix}",
                    model=PricingModel.FIXED,
                    fixed_amount=Decimal("35.00"),
                    currency="MAD",
                    effective_from=now - timedelta(minutes=1),
                    status=PricingRuleStatus.ACTIVE,
                    created_by_user_id=operations_user.id,
                    submitted_by_user_id=operations_user.id,
                    submitted_at=now,
                    activated_by_user_id=operations_user.id,
                    activated_at=now,
                )
                session.add_all(
                    [
                        on_demand_schedule_policy,
                        fixed_schedule_policy,
                        scheduled_on_demand_rule,
                    ]
                )
                await session.flush()

                fixed_route = FixedRoute(
                    city_id=LEGACY_CITY_ID,
                    operator_id=LEGACY_OPERATOR_ID,
                    code=f"UX_CASA_{suffix.upper()}",
                    status=FixedRouteStatus.ACTIVE,
                    created_by_user_id=operations_user.id,
                )
                session.add(fixed_route)
                await session.flush()
                fixed_route_version = FixedRouteVersion(
                    fixed_route_id=fixed_route.id,
                    version=f"ux-published-{suffix}",
                    localized_name={
                        "en": "Casa-Port to Hassan II Mosque",
                        "fr": "Casa-Port vers Mosquée Hassan II",
                        "ar": "محطة الدار البيضاء الميناء إلى مسجد الحسن الثاني",
                    },
                    localized_description={
                        "en": "Synthetic complete-direction route for local UX review.",
                        "fr": "Itinéraire synthétique complet pour la revue UX locale.",
                        "ar": "مسار اصطناعي كامل لمراجعة تجربة الاستخدام محلياً.",
                    },
                    status=FixedRoutePublicationStatus.PUBLISHED,
                    effective_from=now - timedelta(minutes=1),
                    optimistic_version=3,
                    created_by_user_id=operations_user.id,
                    submitted_by_user_id=operations_user.id,
                    submitted_at=now,
                    published_by_user_id=operations_user.id,
                    published_at=now,
                )
                session.add(fixed_route_version)
                await session.flush()
                fixed_direction = FixedRouteDirection(
                    route_version_id=fixed_route_version.id,
                    direction_code=FixedRouteDirectionCode.OUTBOUND,
                    start_location_name={
                        "en": "Casa-Port railway station",
                        "fr": "Gare Casa-Port",
                        "ar": "محطة الدار البيضاء الميناء",
                    },
                    finish_location_name={
                        "en": "Hassan II Mosque",
                        "fr": "Mosquée Hassan II",
                        "ar": "مسجد الحسن الثاني",
                    },
                    start_point=point(33.5898, -7.6039),
                    finish_point=point(33.6084, -7.6327),
                    static_geometry=line_string(
                        [
                            (33.5898, -7.6039),
                            (33.5980, -7.6190),
                            (33.6084, -7.6327),
                        ]
                    ),
                )
                session.add(fixed_direction)
                await session.flush()
                fixed_route_rule = PricingRule(
                    city_id=LEGACY_CITY_ID,
                    operator_id=LEGACY_OPERATOR_ID,
                    service_type=ServiceType.FIXED_ROUTE,
                    booking_type=BookingType.IMMEDIATE,
                    fixed_route_direction_id=fixed_direction.id,
                    name="Casa-Port to Hassan II Mosque flat fare",
                    version=f"ux-route-fare-{suffix}",
                    model=PricingModel.FIXED,
                    fixed_amount=Decimal("8.00"),
                    currency="MAD",
                    effective_from=now - timedelta(minutes=1),
                    status=PricingRuleStatus.ACTIVE,
                    created_by_user_id=operations_user.id,
                    submitted_by_user_id=operations_user.id,
                    submitted_at=now,
                    activated_by_user_id=operations_user.id,
                    activated_at=now,
                )
                session.add(fixed_route_rule)
                await session.flush()
                fixed_direction.flat_fare_policy_version_id = fixed_route_rule.id
                session.add(
                    FixedRouteStop(
                        direction_id=fixed_direction.id,
                        sequence=1,
                        localized_name={
                            "en": "Marina avenue",
                            "fr": "Avenue de la Marina",
                            "ar": "شارع المارينا",
                        },
                        point=point(33.5980, -7.6190),
                    )
                )

                demo_configuration = CityConfigurationVersion(
                    city_id=LEGACY_CITY_ID,
                    version=f"ux-fixed-routes-{suffix}",
                    status=ConfigurationStatus.ACTIVE,
                    service_area_version_id=current_configuration.service_area_version_id,
                    driver_requirement_version_id=current_configuration.driver_requirement_version_id,
                    optimistic_version=4,
                    created_by_user_id=operations_user.id,
                    submitted_by_user_id=operations_user.id,
                    submitted_at=now,
                    approved_by_user_id=operations_user.id,
                    approved_at=now,
                    activated_by_user_id=operations_user.id,
                    activated_at=now,
                )
                session.add(demo_configuration)
                await session.flush()
                for service in current_services:
                    if service.service_type == ServiceType.FIXED_ROUTE:
                        continue
                    session.add(
                        CityConfigurationService(
                            configuration_version_id=demo_configuration.id,
                            service_type=service.service_type,
                            operator_city_assignment_id=service.operator_city_assignment_id,
                            tariff_version_id=service.tariff_version_id,
                            operator_fee_policy_version_id=service.operator_fee_policy_version_id,
                            scheduling_policy_version_id=(
                                on_demand_schedule_policy.id
                                if service.service_type == ServiceType.ON_DEMAND
                                else service.scheduling_policy_version_id
                            ),
                            enabled=service.enabled,
                        )
                    )
                session.add(
                    CityConfigurationService(
                        configuration_version_id=demo_configuration.id,
                        service_type=ServiceType.FIXED_ROUTE,
                        operator_city_assignment_id=fixed_assignment_id,
                        operator_fee_policy_version_id=fixed_fee_policy_id,
                        scheduling_policy_version_id=fixed_schedule_policy.id,
                        enabled=True,
                    )
                )
                for configured_route in current_routes:
                    session.add(
                        CityConfigurationRoute(
                            configuration_version_id=demo_configuration.id,
                            fixed_route_version_id=configured_route.fixed_route_version_id,
                            immediate_booking_enabled=configured_route.immediate_booking_enabled,
                            scheduled_booking_enabled=configured_route.scheduled_booking_enabled,
                        )
                    )
                session.add(
                    CityConfigurationRoute(
                        configuration_version_id=demo_configuration.id,
                        fixed_route_version_id=fixed_route_version.id,
                        immediate_booking_enabled=True,
                        scheduled_booking_enabled=True,
                    )
                )
                current_configuration.status = ConfigurationStatus.REPLACED
                city.active_configuration_version_id = demo_configuration.id
                city.optimistic_version += 1
                await session.flush()

                await set_offer_preference(
                    session,
                    profile=driver,
                    city_id=LEGACY_CITY_ID,
                    enabled=True,
                )
                committed_booking = await create_scheduled_booking(
                    session,
                    passenger_id=passenger.id,
                    payload=ScheduledBookingCreateRequest(
                        scheduled_for=now + timedelta(hours=4),
                        fixed_route_direction_version_id=fixed_direction.id,
                        passenger_note="Synthetic committed fixed-route booking for UX review.",
                        payment_method=PaymentMethod.CASH,
                    ),
                    now=now,
                )
                committed_offer = await session.scalar(
                    select(ScheduledBookingOffer).where(
                        ScheduledBookingOffer.booking_id == committed_booking.id,
                        ScheduledBookingOffer.driver_id == driver.id,
                    )
                )
                if committed_offer is None:
                    raise RuntimeError("The demo scheduled booking did not create a driver offer.")
                await accept_scheduled_offer(
                    session,
                    offer=committed_offer,
                    booking=committed_booking,
                    profile=driver,
                    now=now,
                )
                await create_scheduled_booking(
                    session,
                    passenger_id=empty_passenger.id,
                    payload=ScheduledBookingCreateRequest(
                        scheduled_for=now + timedelta(hours=8),
                        city_id=LEGACY_CITY_ID,
                        pickup=Coordinate(
                            latitude=33.5731,
                            longitude=-7.5898,
                            address="United Nations Square",
                        ),
                        destination=Coordinate(
                            latitude=33.5950,
                            longitude=-7.6802,
                            address="Ain Diab corniche",
                        ),
                        passenger_note="Synthetic offering booking for empty-state account review.",
                        payment_method=PaymentMethod.CASH,
                    ),
                    now=now,
                )

                active_on_demand_rules = list(
                    await session.scalars(
                        select(PricingRule)
                        .where(
                            PricingRule.city_id == LEGACY_CITY_ID,
                            PricingRule.operator_id == LEGACY_OPERATOR_ID,
                            PricingRule.service_type == ServiceType.ON_DEMAND,
                            PricingRule.booking_type == BookingType.IMMEDIATE,
                            PricingRule.status == PricingRuleStatus.ACTIVE,
                        )
                        .with_for_update()
                    )
                )
                for active_rule in active_on_demand_rules:
                    active_rule.status = PricingRuleStatus.REPLACED
                if active_on_demand_rules:
                    await session.flush()

                rule = PricingRule(
                    city_id=LEGACY_CITY_ID,
                    operator_id=LEGACY_OPERATOR_ID,
                    service_type=ServiceType.ON_DEMAND,
                    booking_type=BookingType.IMMEDIATE,
                    name="Casablanca UX fixed fare",
                    version=f"ux-demo-{suffix}",
                    model=PricingModel.FIXED,
                    fixed_amount=Decimal("35.00"),
                    currency="MAD",
                    effective_from=now - timedelta(minutes=1),
                    status=PricingRuleStatus.ACTIVE,
                )
                session.add(rule)
                await session.flush()

                settled_ride = await add_completed_ride(
                    session,
                    passenger_id=passenger.id,
                    driver=driver,
                    vehicle=vehicle,
                    rule=rule,
                    pickup=(33.5898, -7.6039, "Casa-Port railway station"),
                    destination=(33.6084, -7.6327, "Hassan II Mosque"),
                    created_at=now - timedelta(days=8),
                    settled=True,
                    rating=5,
                )
                pending_cash_ride = await add_completed_ride(
                    session,
                    passenger_id=passenger.id,
                    driver=driver,
                    vehicle=vehicle,
                    rule=rule,
                    pickup=(33.5811, -7.6352, "Maarif neighborhood"),
                    destination=(33.5950, -7.6802, "Ain Diab corniche"),
                    created_at=now - timedelta(days=2),
                    settled=False,
                    rating=None,
                )
                active_ride = assigned_ride(
                    passenger_id=passenger.id,
                    driver=driver,
                    vehicle=vehicle,
                    rule=rule,
                    status=RideStatus.DRIVER_EN_ROUTE,
                    pickup=(33.5731, -7.5898, "United Nations Square"),
                    destination=(33.5899, -7.6039, "Casa-Port railway station"),
                    created_at=now - timedelta(minutes=12),
                )
                session.add(active_ride)
                await session.flush()
                session.add_all(
                    [
                        RideEvent(
                            ride_id=active_ride.id,
                            event_type=RideEventType.STATUS_CHANGED,
                            previous_status=RideStatus.ACCEPTED,
                            new_status=RideStatus.DRIVER_EN_ROUTE,
                            actor_user_id=driver_user.id,
                            created_at=now - timedelta(minutes=9),
                        ),
                        DriverLocation(
                            driver_id=driver.id,
                            point=point(33.5750, -7.5920),
                            observed_at=now - timedelta(minutes=1),
                            accuracy_meters=7.0,
                        ),
                    ]
                )

                session.add_all(
                    [
                        Notification(
                            user_id=passenger.id,
                            type="DRIVER_ASSIGNED",
                            title="Driver assigned",
                            body="Youssef is heading to your pickup.",
                            data={"ride_id": str(active_ride.id)},
                            created_at=now - timedelta(minutes=10),
                        ),
                        Notification(
                            user_id=passenger.id,
                            type="RIDE_CANCELLED",
                            title="Earlier ride cancelled",
                            body="A previous request was cancelled safely.",
                            data={"ride_id": str(pending_cash_ride.id)},
                            read_at=now - timedelta(days=1),
                            created_at=now - timedelta(days=2),
                        ),
                        Notification(
                            user_id=driver_user.id,
                            type="DRIVER_CREDENTIAL_EXPIRING",
                            title="Credential expiring",
                            body="Review your driver credential before it expires.",
                            data={"driver_id": str(driver.id)},
                            created_at=now - timedelta(hours=3),
                        ),
                        SupportTicket(
                            city_id=pending_cash_ride.city_id,
                            user_id=passenger.id,
                            ride_id=pending_cash_ride.id,
                            category=SupportCategory.FARE_DISPUTE,
                            subject="Example fare question",
                            description="Synthetic ticket for local UX review.",
                            status=SupportTicketStatus.OPEN,
                            response_due_at=now,
                            created_at=now - timedelta(days=1),
                        ),
                        SupportTicket(
                            city_id=settled_ride.city_id,
                            user_id=driver_user.id,
                            ride_id=settled_ride.id,
                            category=SupportCategory.RIDE_PROBLEM,
                            subject="Example driver support request",
                            description="Synthetic ticket for local UX review.",
                            status=SupportTicketStatus.OPEN,
                            response_due_at=now - timedelta(days=2),
                            created_at=now - timedelta(days=3),
                        ),
                    ]
                )
        async with sessions() as session:
            async with session.begin():
                await refresh_operational_analytics(session, now=now)
        return {
            "database": "local development database",
            "password": password,
            "accounts": {
                "passenger_rich": {
                    "email": emails["passenger_rich"],
                    "purpose": "active ride plus a committed scheduled fixed route, map/status, history, receipts, inbox, support",
                },
                "driver_rich": {
                    "email": emails["driver_rich"],
                    "purpose": "approved on-demand/fixed-route driver, scheduled opt-in/offers/commitment, active ride, vehicle, credential, earnings, inbox",
                },
                "driver_pending": {
                    "email": emails["driver_pending"],
                    "purpose": "pending driver application gate",
                },
                "passenger_empty": {
                    "email": emails["passenger_empty"],
                    "purpose": "first-ride flow, a scheduled booking still offering, and the published fixed-route catalog",
                },
                "operations_recruitment": {
                    "email": emails["operations_recruitment"],
                    "purpose": "city requirements, scheduling policies/exceptions, fixed-route publication, scoped driver review, and privacy-bounded rollout analytics",
                },
            },
        }
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed synthetic local TaxiMobile UX-review accounts.")
    parser.add_argument("--confirm", required=True, help="Exact local-only confirmation phrase.")
    arguments = parser.parse_args()
    settings = Settings.from_environment()
    try:
        validate_demo_target(
            environment=settings.environment,
            database_url=settings.database_url,
            confirmation=arguments.confirm,
        )
    except DemoSeedRefused as error:
        parser.error(str(error))
    print(json.dumps(asyncio.run(seed_demo(settings)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
