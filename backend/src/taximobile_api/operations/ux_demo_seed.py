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
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from taximobile_api.core.config import Settings
from taximobile_api.domains.auth.models import Role, UserRole
from taximobile_api.domains.auth.schemas import RegisterRequest
from taximobile_api.domains.auth.service import register_passenger
from taximobile_api.domains.cooperatives.models import Cooperative, CooperativeMembership
from taximobile_api.domains.cooperatives.models import CooperativeMembershipStatus
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
from taximobile_api.domains.notifications.models import Notification
from taximobile_api.domains.payments.models import DriverEarning, Payment, PaymentMethod, PaymentStatus
from taximobile_api.domains.pricing.models import FareRecord, PricingModel, PricingRule, PricingRuleStatus
from taximobile_api.domains.rides.models import Ride, RideEvent, RideEventType, RideRating, RideStatus
from taximobile_api.domains.support.models import SupportCategory, SupportTicket, SupportTicketStatus


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
                await add_passenger(
                    session,
                    email=emails["passenger_empty"],
                    password=password,
                    display_name="Omar Empty State",
                )

                driver = DriverProfile(
                    user_id=driver_user.id,
                    display_name="Youssef UX Driver",
                    verification_status=VerificationStatus.APPROVED,
                    account_status=DriverAccountStatus.ACTIVE,
                    availability_status=AvailabilityStatus.EN_ROUTE,
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

                rule = PricingRule(
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
                            user_id=passenger.id,
                            ride_id=pending_cash_ride.id,
                            category=SupportCategory.FARE_DISPUTE,
                            subject="Example fare question",
                            description="Synthetic ticket for local UX review.",
                            status=SupportTicketStatus.OPEN,
                            created_at=now - timedelta(days=1),
                        ),
                        SupportTicket(
                            user_id=driver_user.id,
                            ride_id=settled_ride.id,
                            category=SupportCategory.RIDE_PROBLEM,
                            subject="Example driver support request",
                            description="Synthetic ticket for local UX review.",
                            status=SupportTicketStatus.OPEN,
                            created_at=now - timedelta(days=3),
                        ),
                    ]
                )
        return {
            "database": "local development database",
            "password": password,
            "accounts": {
                "passenger_rich": {
                    "email": emails["passenger_rich"],
                    "purpose": "active ride, map/status, history, receipts, inbox, support",
                },
                "driver_rich": {
                    "email": emails["driver_rich"],
                    "purpose": "approved driver, active ride, vehicle, credential, earnings, inbox",
                },
                "driver_pending": {
                    "email": emails["driver_pending"],
                    "purpose": "pending driver application gate",
                },
                "passenger_empty": {
                    "email": emails["passenger_empty"],
                    "purpose": "passenger empty states and first-ride flow",
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
