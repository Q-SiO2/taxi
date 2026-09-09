"""Assignment checks for city-scoped support and safety operations."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.administration.models import (
    AdministrativeGrant,
    AdministrativeRoleTemplate,
)
from taximobile_api.domains.auth.models import User, UserStatus
from taximobile_api.domains.markets.models import City


async def has_active_city_case_grant(
    session: AsyncSession,
    *,
    user_id: UUID,
    city_id: UUID,
    city_role: AdministrativeRoleTemplate,
) -> bool:
    """Return whether an active user may own this city's restricted queue.

    Case ownership is deliberately narrower than a generic operations account:
    the assignee needs the exact city role, or a platform-admin grant covering
    the city's market. Expired and revoked grants never remain assignable.
    """

    market_id = await session.scalar(select(City.market_id).where(City.id == city_id))
    if market_id is None:
        return False

    now = datetime.now(UTC)
    grant_id = await session.scalar(
        select(AdministrativeGrant.id)
        .join(User, User.id == AdministrativeGrant.user_id)
        .where(
            AdministrativeGrant.user_id == user_id,
            User.status == UserStatus.ACTIVE,
            AdministrativeGrant.revoked_at.is_(None),
            or_(
                AdministrativeGrant.expires_at.is_(None),
                AdministrativeGrant.expires_at > now,
            ),
            or_(
                and_(
                    AdministrativeGrant.role_template == city_role,
                    AdministrativeGrant.city_id == city_id,
                ),
                and_(
                    AdministrativeGrant.role_template
                    == AdministrativeRoleTemplate.PLATFORM_ADMIN,
                    AdministrativeGrant.market_id == market_id,
                ),
            ),
        )
        .limit(1)
    )
    return grant_id is not None
