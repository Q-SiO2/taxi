"""Controlled migration from one legacy ADMIN to the first scoped platform grant."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.administration.models import (
    AdministrativeGrant,
    AdministrativeRoleTemplate,
)
from taximobile_api.domains.administration.service import audit
from taximobile_api.domains.auth.models import Role, User, UserRole, UserStatus
from taximobile_api.domains.markets.models import Market, MarketStatus


INITIAL_PLATFORM_GRANT_LOCK_KEY = 607_194_520_260_813
INITIAL_PLATFORM_ADMIN_QUORUM = 3


class PlatformGrantBootstrapConflict(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class InitialPlatformGrantResult:
    grant_id: UUID
    user_id: UUID
    market_id: UUID
    created: bool


@dataclass(frozen=True, slots=True)
class PlatformAdminQuorumMemberResult:
    grant_id: UUID
    user_id: UUID
    market_id: UUID
    active_quorum_size: int
    created: bool


async def bootstrap_initial_platform_grant(
    database_session: AsyncSession,
    *,
    admin_email: str,
    market_code: str,
) -> InitialPlatformGrantResult:
    """Map exactly one existing bootstrap ADMIN through an audited transaction."""

    normalized_email = admin_email.strip().lower()
    normalized_market_code = market_code.strip().upper()
    await database_session.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": INITIAL_PLATFORM_GRANT_LOCK_KEY},
    )
    market = await database_session.scalar(
        select(Market).where(Market.code == normalized_market_code).with_for_update()
    )
    if market is None or market.status != MarketStatus.ACTIVE:
        raise PlatformGrantBootstrapConflict("The requested active market does not exist.")

    user = await database_session.scalar(
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .where(
            User.email == normalized_email,
            User.status == UserStatus.ACTIVE,
            UserRole.role == Role.ADMIN,
        )
        .with_for_update(of=User)
    )
    if user is None:
        raise PlatformGrantBootstrapConflict(
            "The requested account is not the active legacy bootstrap administrator."
        )

    existing = await database_session.scalar(
        select(AdministrativeGrant)
        .where(
            AdministrativeGrant.role_template == AdministrativeRoleTemplate.PLATFORM_ADMIN,
            AdministrativeGrant.market_id == market.id,
            AdministrativeGrant.revoked_at.is_(None),
        )
        .order_by(AdministrativeGrant.granted_at, AdministrativeGrant.id)
        .limit(1)
    )
    if existing is not None:
        if existing.user_id == user.id:
            return InitialPlatformGrantResult(
                grant_id=existing.id,
                user_id=user.id,
                market_id=market.id,
                created=False,
            )
        raise PlatformGrantBootstrapConflict(
            "A different initial platform administrator already owns this market bootstrap."
        )

    grant = AdministrativeGrant(
        id=uuid4(),
        user_id=user.id,
        role_template=AdministrativeRoleTemplate.PLATFORM_ADMIN,
        market_id=market.id,
        granted_by_user_id=user.id,
        grant_reason="Controlled migration from the single-city bootstrap administrator.",
        granted_at=datetime.now(UTC),
    )
    database_session.add(grant)
    await database_session.flush()
    await audit(
        database_session,
        actor_user_id=user.id,
        action="INITIAL_PLATFORM_ADMIN_GRANTED",
        resource_type="administrative_grant",
        resource_id=grant.id,
        market_id=market.id,
        changes={
            "role_template": AdministrativeRoleTemplate.PLATFORM_ADMIN.value,
            "scope_type": "MARKET",
            "bootstrap_mapping": True,
        },
    )
    return InitialPlatformGrantResult(
        grant_id=grant.id,
        user_id=user.id,
        market_id=market.id,
        created=True,
    )


async def bootstrap_platform_admin_quorum_member(
    database_session: AsyncSession,
    *,
    user_email: str,
    market_code: str,
    change_reference: str,
) -> PlatformAdminQuorumMemberResult:
    """Add only the second or third initial platform administrator offline.

    This deliberately narrow deployment escape hatch closes itself once three
    active, non-expiring administrators exist. Ongoing changes must use the
    online maker-checker workflow.
    """

    normalized_email = user_email.strip().lower()
    normalized_market_code = market_code.strip().upper()
    normalized_reference = change_reference.strip().upper()
    if not 6 <= len(normalized_reference) <= 72:
        raise PlatformGrantBootstrapConflict(
            "The reviewed change reference must contain 6 to 72 characters."
        )
    await database_session.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": INITIAL_PLATFORM_GRANT_LOCK_KEY},
    )
    market = await database_session.scalar(
        select(Market).where(Market.code == normalized_market_code).with_for_update()
    )
    if market is None or market.status != MarketStatus.ACTIVE:
        raise PlatformGrantBootstrapConflict("The requested active market does not exist.")
    target = await database_session.scalar(
        select(User)
        .where(
            User.email == normalized_email,
            User.status == UserStatus.ACTIVE,
        )
        .with_for_update()
    )
    if target is None:
        raise PlatformGrantBootstrapConflict(
            "The quorum member must already have an active registered account."
        )

    active_grants = list(
        await database_session.scalars(
            select(AdministrativeGrant)
            .join(User, User.id == AdministrativeGrant.user_id)
            .where(
                AdministrativeGrant.role_template
                == AdministrativeRoleTemplate.PLATFORM_ADMIN,
                AdministrativeGrant.market_id == market.id,
                AdministrativeGrant.revoked_at.is_(None),
                AdministrativeGrant.expires_at.is_(None),
                User.status == UserStatus.ACTIVE,
            )
            .order_by(AdministrativeGrant.granted_at, AdministrativeGrant.id)
            .with_for_update(of=AdministrativeGrant)
        )
    )
    existing = next(
        (grant for grant in active_grants if grant.user_id == target.id),
        None,
    )
    if existing is not None:
        return PlatformAdminQuorumMemberResult(
            grant_id=existing.id,
            user_id=target.id,
            market_id=market.id,
            active_quorum_size=len({grant.user_id for grant in active_grants}),
            created=False,
        )
    distinct_admin_ids = {grant.user_id for grant in active_grants}
    if not distinct_admin_ids:
        raise PlatformGrantBootstrapConflict(
            "Bootstrap the first platform administrator before adding quorum members."
        )
    if len(distinct_admin_ids) >= INITIAL_PLATFORM_ADMIN_QUORUM:
        raise PlatformGrantBootstrapConflict(
            "The initial three-person platform administrator quorum already exists; "
            "use the maker-checker workflow."
        )

    bootstrap_actor_id = active_grants[0].user_id
    grant = AdministrativeGrant(
        id=uuid4(),
        user_id=target.id,
        role_template=AdministrativeRoleTemplate.PLATFORM_ADMIN,
        market_id=market.id,
        granted_by_user_id=bootstrap_actor_id,
        grant_reason=(
            "Controlled initial three-person operations quorum bootstrap: "
            f"{normalized_reference}"
        ),
        granted_at=datetime.now(UTC),
    )
    database_session.add(grant)
    await database_session.flush()
    new_size = len(distinct_admin_ids) + 1
    await audit(
        database_session,
        actor_user_id=bootstrap_actor_id,
        action="INITIAL_PLATFORM_ADMIN_QUORUM_MEMBER_GRANTED",
        resource_type="administrative_grant",
        resource_id=grant.id,
        market_id=market.id,
        changes={
            "target_user_id": str(target.id),
            "role_template": AdministrativeRoleTemplate.PLATFORM_ADMIN.value,
            "scope_type": "MARKET",
            "change_reference": normalized_reference,
            "active_quorum_size": new_size,
            "bootstrap_mapping": True,
        },
    )
    return PlatformAdminQuorumMemberResult(
        grant_id=grant.id,
        user_id=target.id,
        market_id=market.id,
        active_quorum_size=new_size,
        created=True,
    )
