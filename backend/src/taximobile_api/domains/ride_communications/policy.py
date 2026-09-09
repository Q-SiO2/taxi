from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.drivers.models import DriverProfile
from taximobile_api.domains.drivers.service import DriverMissing, driver_for_user
from taximobile_api.domains.ride_communications.models import (
    RideCoordinationCode,
    RideCoordinationMessage,
)
from taximobile_api.domains.ride_communications.schemas import (
    RideCoordinationSenderRole,
)
from taximobile_api.domains.rides.models import Ride, RideStatus


ACTIVE_COORDINATION_STATUSES = frozenset(
    {
        RideStatus.ACCEPTED,
        RideStatus.DRIVER_EN_ROUTE,
        RideStatus.DRIVER_ARRIVED,
        RideStatus.IN_PROGRESS,
    }
)
PASSENGER_CODES = frozenset(
    {
        RideCoordinationCode.PASSENGER_AT_PICKUP,
        RideCoordinationCode.PASSENGER_NEEDS_MORE_TIME,
        RideCoordinationCode.PASSENGER_CANNOT_FIND_DRIVER,
    }
)
DRIVER_CODES = frozenset(
    {
        RideCoordinationCode.DRIVER_ON_MY_WAY,
        RideCoordinationCode.DRIVER_AT_PICKUP,
        RideCoordinationCode.DRIVER_CANNOT_FIND_PASSENGER,
    }
)
MAX_MESSAGES_PER_PARTICIPANT_PER_RIDE = 100


class RideCoordinationNotFound(Exception):
    pass


class RideCoordinationForbidden(Exception):
    pass


class RideCoordinationClosed(Exception):
    pass


class RideCoordinationCodeForbidden(Exception):
    pass


class RideCoordinationLimitReached(Exception):
    pass


@dataclass(frozen=True)
class RideCoordinationContext:
    ride: Ride
    sender_role: RideCoordinationSenderRole
    recipient_user_id: UUID


def sender_role_for_code(code: RideCoordinationCode) -> RideCoordinationSenderRole:
    if code in PASSENGER_CODES:
        return RideCoordinationSenderRole.PASSENGER
    if code in DRIVER_CODES:
        return RideCoordinationSenderRole.DRIVER
    raise RideCoordinationCodeForbidden("This coordination signal is not supported.")


async def participant_context(
    session: AsyncSession,
    *,
    ride_id: UUID,
    user_id: UUID,
    lock: bool,
) -> RideCoordinationContext:
    statement = select(Ride).where(Ride.id == ride_id)
    if lock:
        statement = statement.with_for_update()
    ride = await session.scalar(statement)
    if ride is None:
        raise RideCoordinationNotFound("Ride not found.")

    if ride.passenger_id == user_id:
        sender_role = RideCoordinationSenderRole.PASSENGER
        if ride.driver_id is None:
            raise RideCoordinationClosed("Coordination starts only after driver assignment.")
        driver = await session.get(DriverProfile, ride.driver_id)
        if driver is None:
            raise RideCoordinationClosed("The assigned driver is unavailable.")
        recipient_user_id = driver.user_id
    else:
        try:
            driver = await driver_for_user(session, user_id)
        except DriverMissing as error:
            raise RideCoordinationForbidden("You cannot access this ride.") from error
        if ride.driver_id != driver.id:
            raise RideCoordinationForbidden("You cannot access this ride.")
        sender_role = RideCoordinationSenderRole.DRIVER
        recipient_user_id = ride.passenger_id

    if ride.status not in ACTIVE_COORDINATION_STATUSES:
        raise RideCoordinationClosed(
            "Coordination is available only during an assigned active ride."
        )
    return RideCoordinationContext(ride, sender_role, recipient_user_id)


async def enforce_sender_limit(
    session: AsyncSession,
    *,
    ride_id: UUID,
    sender_user_id: UUID,
) -> None:
    count = await session.scalar(
        select(func.count())
        .select_from(RideCoordinationMessage)
        .where(
            RideCoordinationMessage.ride_id == ride_id,
            RideCoordinationMessage.sender_user_id == sender_user_id,
        )
    )
    if (count or 0) >= MAX_MESSAGES_PER_PARTICIPANT_PER_RIDE:
        raise RideCoordinationLimitReached(
            "The coordination limit for this ride has been reached."
        )


def compatibility_copy(code: RideCoordinationCode) -> tuple[str, str]:
    """English is a bounded compatibility fallback; clients localize the code."""

    body = {
        RideCoordinationCode.PASSENGER_AT_PICKUP: "Your passenger is at the pickup point.",
        RideCoordinationCode.PASSENGER_NEEDS_MORE_TIME: "Your passenger needs a little more time.",
        RideCoordinationCode.PASSENGER_CANNOT_FIND_DRIVER: "Your passenger cannot find the taxi.",
        RideCoordinationCode.DRIVER_ON_MY_WAY: "Your driver is on the way.",
        RideCoordinationCode.DRIVER_AT_PICKUP: "Your driver is at the pickup point.",
        RideCoordinationCode.DRIVER_CANNOT_FIND_PASSENGER: "Your driver cannot find you.",
    }[code]
    return "Ride update", body
