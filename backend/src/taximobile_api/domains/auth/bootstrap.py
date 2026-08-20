"""Controlled initial-administrator creation for deployment operators.

This module is deliberately not wired into an HTTP router. It establishes the
first administrator only; ongoing role management requires a separately designed
and audited administrative workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.auth.models import Role, User, UserRole, UserStatus
from taximobile_api.domains.auth.schemas import RegisterRequest
from taximobile_api.domains.auth.security import hash_password


# Stable application-specific PostgreSQL advisory-lock key. The lock is scoped
# to the surrounding transaction and prevents concurrent first-deployment jobs
# from both observing an empty administrator set.
INITIAL_ADMIN_LOCK_KEY = 607_194_520_260_812


class InitialAdministratorExists(ValueError):
    """A different administrator already owns the deployment bootstrap."""


class AdministratorAccountConflict(ValueError):
    """The requested identifier already belongs to a non-administrator."""


@dataclass(frozen=True, slots=True)
class InitialAdministratorResult:
    user_id: UUID
    email: str
    created: bool


async def bootstrap_initial_administrator(
    database_session: AsyncSession,
    *,
    email: str,
    password: str,
) -> InitialAdministratorResult:
    """Create exactly one initial administrator in the caller's transaction."""

    request = RegisterRequest(
        email=email,
        password=password,
        display_name="Initial administrator",
    )
    assert request.email is not None

    await database_session.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": INITIAL_ADMIN_LOCK_KEY},
    )
    existing_administrator = await database_session.scalar(
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .where(UserRole.role == Role.ADMIN)
        .order_by(User.created_at.asc())
        .limit(1)
    )
    if existing_administrator is not None:
        if existing_administrator.email == request.email:
            return InitialAdministratorResult(
                user_id=existing_administrator.id,
                email=request.email,
                created=False,
            )
        raise InitialAdministratorExists(
            "An initial administrator already exists; this bootstrap command cannot grant additional roles."
        )

    existing_account_id = await database_session.scalar(select(User.id).where(User.email == request.email))
    if existing_account_id is not None:
        raise AdministratorAccountConflict(
            "That email already belongs to an account; bootstrap never promotes an existing account."
        )

    user = User(
        id=uuid4(),
        email=request.email,
        password_hash=hash_password(request.password),
        status=UserStatus.ACTIVE,
    )
    database_session.add(user)
    database_session.add(UserRole(user_id=user.id, role=Role.ADMIN))
    await database_session.flush()
    return InitialAdministratorResult(user_id=user.id, email=request.email, created=True)
