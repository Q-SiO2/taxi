"""Small migrated fixture for commitment races; never production provisioning.

Applications and policy activation are synthetic fixture facts. Booking creation,
opt-in, offering and acceptance still traverse their real domain services.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select

from taximobile_api.domains.auth.models import User
from taximobile_api.domains.drivers.models import DriverProfile
from taximobile_api.domains.markets.constants import LEGACY_CITY_ID, LEGACY_OPERATOR_ID
from taximobile_api.domains.markets.models import CityConfigurationService, ServiceType
from taximobile_api.domains.pricing.models import (
    BookingType, FinancialPolicyStatus, PricingModel, PricingRule, PricingRuleStatus,
    SchedulingPolicy, SchedulingSurchargeBeneficiary,
)
from taximobile_api.domains.scheduled_bookings.models import ScheduledBookingOffer
from taximobile_api.domains.scheduled_bookings.schemas import ScheduledBookingCreateRequest
from taximobile_api.domains.scheduled_bookings.service import create_scheduled_booking, set_offer_preference

from workload_fixtures import seed_workload_supply


@dataclass(frozen=True)
class AcceptanceFixture:
    now: datetime
    booking_ids: tuple[UUID, ...]
    driver_ids: tuple[UUID, ...]
    passenger_ids: tuple[UUID, ...]
    offer_ids: dict[tuple[UUID, UUID], UUID]
    credentials: tuple[dict, ...] = field(repr=False)


async def seed_acceptance(sessions, *, offsets=(0, 90)):
    # The approved-evidence variant is required by the real opt-in/eligibility
    # guards; its random credentials are used only by the API-boundary tests.
    credentials = await seed_workload_supply(sessions, 2, loginable=True)
    now = datetime.now(UTC)
    async with sessions.begin() as session:
        policy = SchedulingPolicy(
            city_id=LEGACY_CITY_ID, operator_id=LEGACY_OPERATOR_ID,
            service_type=ServiceType.ON_DEMAND, version="synthetic-acceptance-v1",
            status=FinancialPolicyStatus.ACTIVE, surcharge_amount=Decimal("5.00"),
            currency="MAD", beneficiary=SchedulingSurchargeBeneficiary.DRIVER,
            effective_from=now - timedelta(days=1),
        )
        session.add(policy)
        session.add(PricingRule(
            city_id=LEGACY_CITY_ID, operator_id=LEGACY_OPERATOR_ID,
            service_type=ServiceType.ON_DEMAND, booking_type=BookingType.SCHEDULED,
            name="Synthetic scheduled acceptance", version="synthetic-acceptance-v1",
            model=PricingModel.FIXED, fixed_amount=Decimal("35.00"), currency="MAD",
            status=PricingRuleStatus.ACTIVE, effective_from=now - timedelta(days=1),
        ))
        await session.flush()
        configuration = await session.scalar(select(CityConfigurationService).where(
            CityConfigurationService.service_type == ServiceType.ON_DEMAND,
        ))
        configuration.scheduling_policy_version_id = policy.id
        drivers = list(await session.scalars(select(DriverProfile).order_by(DriverProfile.id)))
        for profile in drivers:
            await set_offer_preference(session, profile=profile, city_id=LEGACY_CITY_ID, enabled=True)
        bookings, passengers = [], []
        for offset in offsets:
            passenger = User(email=f"scheduled-{uuid4().hex}@taximobile.invalid",
                             password_hash="!inert-synthetic-passenger")
            session.add(passenger)
            await session.flush()
            booking = await create_scheduled_booking(
                session, passenger_id=passenger.id, now=now,
                payload=ScheduledBookingCreateRequest(
                    city_id=LEGACY_CITY_ID, scheduled_for=now + timedelta(hours=4, minutes=offset),
                    pickup={"latitude": 33.5731, "longitude": -7.5898},
                    destination={"latitude": 33.58, "longitude": -7.61},
                    payment_method="CASH",
                ),
            )
            bookings.append(booking.id)
            passengers.append(passenger.id)
        offers = list(await session.scalars(select(ScheduledBookingOffer)))
        assert len(offers) == len(offsets) * 2
        return AcceptanceFixture(now, tuple(bookings), tuple(d.id for d in drivers), tuple(passengers),
                                 {(o.booking_id, o.driver_id): o.id for o in offers}, tuple(credentials))
