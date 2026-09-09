"""Human-reviewed city authorization changes and assignment serialization.

Use inside one caller-owned transaction after permission/scope and MFA checks.
Application -> driver -> authorization is the write order. Assignment holds the
same driver lock before reading authorization eligibility, so an assignment
that commits first remains history and a restriction that commits first blocks
subsequent assignment. This module never locks or rewrites rides/bookings.
"""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.administration.service import audit
from taximobile_api.domains.auth.authority import user_account_is_active
from taximobile_api.domains.drivers.models import (
    DriverAccountStatus, DriverProfile, Vehicle, VerificationStatus,
)
from taximobile_api.domains.drivers.service import (
    active_vehicle_eligibility_failure, invalid_driver_credentials,
)
from taximobile_api.domains.markets.models import City
from taximobile_api.domains.notifications.service import notify
from taximobile_api.domains.outbox.service import enqueue
from taximobile_api.domains.rides.locking import lock_driver

from .models import (
    CityApplicationStatus, CityAuthorizationStatus, DriverCityApplication,
    DriverCityAuthorization, DriverCityAuthorizationService,
)
from .service import (
    RecruitmentConflict, application_completion, require_expected_version,
    reviewed_service_types_for_city,
)


class AuthorizationAction(StrEnum):
    SUSPEND = "SUSPEND"
    REVOKE = "REVOKE"
    REINSTATE = "REINSTATE"


REASONS = {
    AuthorizationAction.SUSPEND: frozenset({"SAFETY_REVIEW", "ELIGIBILITY_REVIEW"}),
    AuthorizationAction.REVOKE: frozenset({"OPERATING_PERMISSION_WITHDRAWN"}),
    AuthorizationAction.REINSTATE: frozenset({"ELIGIBILITY_REVIEW_PASSED"}),
}


class AuthorizationDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_application_version: int = Field(ge=1)
    action: AuthorizationAction
    reason_code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{2,63}$")

    @model_validator(mode="after")
    def reason_matches_action(self):
        if self.reason_code not in REASONS[self.action]:
            raise ValueError("The reason code is not allowed for this authorization action.")
        return self


def authorization_target(
    current: CityAuthorizationStatus, action: AuthorizationAction,
) -> CityAuthorizationStatus:
    transitions = {
        (CityAuthorizationStatus.ACTIVE, AuthorizationAction.SUSPEND): CityAuthorizationStatus.SUSPENDED,
        (CityAuthorizationStatus.ACTIVE, AuthorizationAction.REVOKE): CityAuthorizationStatus.REVOKED,
        (CityAuthorizationStatus.SUSPENDED, AuthorizationAction.REVOKE): CityAuthorizationStatus.REVOKED,
        (CityAuthorizationStatus.EXPIRED, AuthorizationAction.REVOKE): CityAuthorizationStatus.REVOKED,
        (CityAuthorizationStatus.SUSPENDED, AuthorizationAction.REINSTATE): CityAuthorizationStatus.ACTIVE,
    }
    target = transitions.get((current, action))
    if target is None:
        raise RecruitmentConflict("The authorization state no longer permits this action. Refresh the application.")
    return target


async def require_reinstatement_eligibility(
    session: AsyncSession, application: DriverCityApplication,
    authorization: DriverCityAuthorization, profile: DriverProfile, *, now: datetime,
) -> None:
    if application.status != CityApplicationStatus.APPROVED:
        raise RecruitmentConflict("Reinstatement requires the original approved application.")
    if authorization.valid_from > now or (
        authorization.valid_until is not None and authorization.valid_until <= now
    ):
        raise RecruitmentConflict("The authorization validity period does not permit reinstatement.")
    other_active = await session.scalar(select(DriverCityAuthorization.id).where(
        DriverCityAuthorization.driver_id == profile.id,
        DriverCityAuthorization.city_id == application.city_id,
        DriverCityAuthorization.status == CityAuthorizationStatus.ACTIVE,
        DriverCityAuthorization.id != authorization.id,
    ))
    if other_active is not None:
        raise RecruitmentConflict("Another application already authorizes this driver in the city.")
    if not await user_account_is_active(session, profile.user_id, serialize_with_status_change=True):
        raise RecruitmentConflict("The global account is not active.")
    if profile.account_status != DriverAccountStatus.ACTIVE or profile.verification_status != VerificationStatus.APPROVED:
        raise RecruitmentConflict("The driver's professional status is not eligible.")
    vehicle_id = authorization.vehicle_id or profile.active_vehicle_id
    vehicle = await session.get(Vehicle, vehicle_id, populate_existing=True) if vehicle_id else None
    if active_vehicle_eligibility_failure(profile, vehicle):
        raise RecruitmentConflict("A verified owned vehicle is required for reinstatement.")
    if await session.scalar(select(invalid_driver_credentials(profile.id, now))):
        raise RecruitmentConflict("A professional credential is unverified or expired.")
    completion = await application_completion(session, application, now=now)
    if not completion.complete:
        raise RecruitmentConflict("The city application no longer meets its required evidence checks.")
    services = set(await session.scalars(select(DriverCityAuthorizationService.service_type).where(
        DriverCityAuthorizationService.authorization_id == authorization.id,
    )))
    if not services or not services.issubset(await reviewed_service_types_for_city(session, application.city_id)):
        raise RecruitmentConflict("The authorized services are no longer covered by a reviewed city configuration.")


async def decide_authorization(
    session: AsyncSession, *, application_id: UUID, reviewer_user_id: UUID,
    payload: AuthorizationDecisionRequest, now: datetime | None = None,
) -> DriverCityApplication:
    application = await session.scalar(select(DriverCityApplication).where(
        DriverCityApplication.id == application_id,
    ).with_for_update().execution_options(populate_existing=True))
    if application is None:
        raise RecruitmentConflict("The city application no longer exists.")
    require_expected_version(application.optimistic_version, payload.expected_application_version)
    profile = await lock_driver(session, application.driver_id)
    if profile is None:
        raise RecruitmentConflict("The driver no longer exists.")
    authorization = await session.scalar(select(DriverCityAuthorization).where(
        DriverCityAuthorization.application_id == application.id,
        DriverCityAuthorization.driver_id == profile.id,
        DriverCityAuthorization.city_id == application.city_id,
    ).with_for_update().execution_options(populate_existing=True))
    if authorization is None:
        raise RecruitmentConflict("The application has no city authorization.")
    target = authorization_target(authorization.status, payload.action)
    current_time = now or datetime.now(UTC)
    if payload.action == AuthorizationAction.REINSTATE:
        await require_reinstatement_eligibility(session, application, authorization, profile, now=current_time)
    previous = authorization.status
    authorization.status = target
    authorization.updated_at = current_time
    application.optimistic_version += 1
    application.updated_at = current_time
    city = await session.get(City, application.city_id)
    assert city is not None
    await audit(
        session, actor_user_id=reviewer_user_id,
        action=f"DRIVER_CITY_AUTHORIZATION_{payload.action.value}",
        resource_type="driver_city_authorization", resource_id=authorization.id,
        market_id=city.market_id, city_id=city.id,
        changes={
            "application_id": str(application.id),
            "previous_status": previous.value, "current_status": target.value,
            "reason_code": payload.reason_code,
            "application_version": application.optimistic_version,
        },
    )
    await notify(
        session,
        user_id=profile.user_id,
        notification_type="DRIVER_CITY_AUTHORIZATION_CHANGED",
        title="City authorization updated",
        body=(
            "A reviewer changed your city authorization. Refresh your application "
            "to review your current permission."
        ),
        data={"authorization_id": str(authorization.id)},
    )
    await enqueue(
        session,
        topic="driver.city_authorization.changed",
        payload={"authorization_id": str(authorization.id)},
    )
    await session.flush()
    return application
