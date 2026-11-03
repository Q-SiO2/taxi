"""Operator-scoped membership authority for admission of new driver work.

Existing accepted rides, support and financial reads deliberately do not use this
gate. Membership is independent of professional/city/vehicle authorization.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.cooperatives.models import (
    Cooperative, CooperativeMembership, CooperativeMembershipStatus, CooperativeStatus,
)
from taximobile_api.domains.markets.models import (
    AssignmentStatus, City, CityConfigurationService, CityConfigurationVersion,
    ConfigurationStatus, Operator, OperatorCityAssignment, ServiceType,
)


def operator_membership_allows(user_id, operator_id, now: datetime):
    """Correlated SQL predicate: bound candidates before scoring or offering."""
    active_member = exists(
        select(CooperativeMembership.id)
        .join(Cooperative, Cooperative.id == CooperativeMembership.cooperative_id)
        .where(
            CooperativeMembership.cooperative_id == Operator.cooperative_id,
            CooperativeMembership.user_id == user_id,
            CooperativeMembership.membership_status == CooperativeMembershipStatus.ACTIVE,
            Cooperative.status == CooperativeStatus.ACTIVE,
            or_(CooperativeMembership.joined_at.is_(None), CooperativeMembership.joined_at <= now),
            or_(CooperativeMembership.ended_at.is_(None), CooperativeMembership.ended_at > now),
        )
        .correlate_except(CooperativeMembership, Cooperative)
    )
    return exists(
        select(Operator.id)
        .where(
            Operator.id == operator_id,
            or_(Operator.requires_active_membership.is_(False), active_member),
        )
        .correlate_except(Operator)
    )


async def driver_membership_is_active(
    session: AsyncSession,
    user_id: UUID,
    operator_id: UUID,
    *,
    now: datetime | None = None,
    serialize_with_changes: bool = False,
) -> bool:
    """Refresh authority, holding shared policy/member locks when admitting work.

    Membership/policy updates take ordinary exclusive PostgreSQL row locks. If
    they commit first this read sees their new state; if admission reads first
    the update waits for that already authorized command. No record is granted
    or modified here. Missing rows fail closed for a required-membership policy.
    """
    statement = select(Operator).where(Operator.id == operator_id)
    if serialize_with_changes:
        statement = statement.with_for_update(read=True)
    operator = await session.scalar(statement.execution_options(populate_existing=True))
    if operator is None:
        return False
    if not operator.requires_active_membership:
        return True
    if operator.cooperative_id is None:
        return False
    statement = (
        select(CooperativeMembership, Cooperative)
        .join(Cooperative, Cooperative.id == CooperativeMembership.cooperative_id)
        .where(
            CooperativeMembership.cooperative_id == operator.cooperative_id,
            CooperativeMembership.user_id == user_id,
        )
    )
    if serialize_with_changes:
        statement = statement.with_for_update(read=True)
    row = (await session.execute(statement.execution_options(populate_existing=True))).first()
    if row is None:
        return False
    membership, organization = row
    current_time = now or datetime.now(UTC)  # after lock waits
    return (
        organization.status == CooperativeStatus.ACTIVE
        and membership.membership_status == CooperativeMembershipStatus.ACTIVE
        and (membership.joined_at is None or membership.joined_at <= current_time)
        and (membership.ended_at is None or membership.ended_at > current_time)
    )


async def online_operator_id(
    session: AsyncSession, city: City, service_type: ServiceType, *, now: datetime,
) -> UUID | None:
    """Resolve the operator from the active city/service configuration only."""
    statement = (
        select(OperatorCityAssignment.operator_id)
        .join(CityConfigurationService,
              CityConfigurationService.operator_city_assignment_id == OperatorCityAssignment.id)
        .join(CityConfigurationVersion,
              CityConfigurationVersion.id == CityConfigurationService.configuration_version_id)
        .where(
            CityConfigurationVersion.id == city.active_configuration_version_id,
            CityConfigurationVersion.status == ConfigurationStatus.ACTIVE,
            CityConfigurationService.service_type == service_type,
            CityConfigurationService.enabled.is_(True),
            OperatorCityAssignment.city_id == city.id,
            OperatorCityAssignment.service_type == service_type,
            OperatorCityAssignment.status == AssignmentStatus.ACTIVE,
            OperatorCityAssignment.effective_from <= now,
            or_(OperatorCityAssignment.effective_until.is_(None),
                OperatorCityAssignment.effective_until > now),
        )
        .limit(2)
    )
    operators = list(await session.scalars(statement))
    return operators[0] if len(operators) == 1 else None
