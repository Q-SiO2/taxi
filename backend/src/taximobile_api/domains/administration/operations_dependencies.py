"""Authentication and scope expansion for the isolated operations namespace."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, Callable
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import or_, select

from taximobile_api.domains.administration.models import AdministrativeGrant, OperationsSession
from taximobile_api.domains.administration.permissions import (
    GrantAuthorization,
    OperationsPermission,
    OperationsPrincipal,
    ROLE_PERMISSIONS,
)
from taximobile_api.domains.administration.operations_mfa import MFA_RECENT_SECONDS
from taximobile_api.domains.auth.models import User, UserStatus
from taximobile_api.domains.auth.security import InvalidAccessToken, TokenService
from taximobile_api.domains.markets.models import (
    AssignmentStatus,
    City,
    Operator,
    OperatorCityAssignment,
)


operations_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class OperationsSessionIdentity:
    user_id: UUID
    session_id: UUID


def operations_token_service(request: Request) -> TokenService:
    secret = request.app.state.settings.jwt_secret
    if secret is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Operations authentication is not configured.",
        )
    return TokenService(secret)


async def _expand_grant(database_session, grant: AdministrativeGrant) -> GrantAuthorization | None:
    """Resolve parent/child IDs once; permission checks still retain grant boundaries."""

    market_id = grant.market_id
    operator_id = grant.operator_id
    city_id = grant.city_id
    operator_ids: set[UUID] = set()
    city_ids: set[UUID] = set()

    if market_id is not None:
        operator_ids.update(
            await database_session.scalars(select(Operator.id).where(Operator.market_id == market_id))
        )
        city_ids.update(await database_session.scalars(select(City.id).where(City.market_id == market_id)))
    elif operator_id is not None:
        operator = await database_session.get(Operator, operator_id)
        if operator is None:
            return None
        market_id = operator.market_id
        operator_ids.add(operator.id)
        now = datetime.now(UTC)
        city_ids.update(
            await database_session.scalars(
                select(OperatorCityAssignment.city_id).where(
                    OperatorCityAssignment.operator_id == operator.id,
                    OperatorCityAssignment.status == AssignmentStatus.ACTIVE,
                    OperatorCityAssignment.effective_from <= now,
                    or_(
                        OperatorCityAssignment.effective_until.is_(None),
                        OperatorCityAssignment.effective_until > now,
                    ),
                )
            )
        )
    elif city_id is not None:
        city = await database_session.get(City, city_id)
        if city is None:
            return None
        market_id = city.market_id
        city_ids.add(city.id)
        now = datetime.now(UTC)
        operator_ids.update(
            await database_session.scalars(
                select(OperatorCityAssignment.operator_id).where(
                    OperatorCityAssignment.city_id == city.id,
                    OperatorCityAssignment.status == AssignmentStatus.ACTIVE,
                    OperatorCityAssignment.effective_from <= now,
                    or_(
                        OperatorCityAssignment.effective_until.is_(None),
                        OperatorCityAssignment.effective_until > now,
                    ),
                )
            )
        )

    return GrantAuthorization(
        grant_id=grant.id,
        role_template=grant.role_template,
        permissions=ROLE_PERMISSIONS[grant.role_template],
        market_id=market_id,
        operator_id=operator_id,
        city_id=city_id,
        covered_operator_ids=frozenset(operator_ids),
        covered_city_ids=frozenset(city_ids),
    )


async def authenticated_operations_session(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(operations_bearer_scheme),
    ],
) -> OperationsSessionIdentity:
    """Require an operations-audience token and live session without grant expansion."""

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Operations authentication is required.")
    try:
        user_id, session_id = operations_token_service(request).parse_operations_access_token(
            credentials.credentials
        )
    except InvalidAccessToken as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Operations authentication is required.",
        ) from error

    now = datetime.now(UTC)
    async with request.app.state.session_factory() as database_session:
        valid_session = await database_session.scalar(
            select(OperationsSession.id)
            .join(User, User.id == OperationsSession.user_id)
            .where(
                OperationsSession.id == session_id,
                OperationsSession.user_id == user_id,
                OperationsSession.revoked_at.is_(None),
                OperationsSession.expires_at > now,
                User.status == UserStatus.ACTIVE,
            )
        )
        if valid_session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Operations authentication is required.",
            )

    return OperationsSessionIdentity(user_id=user_id, session_id=session_id)


async def authenticated_operations_principal(
    request: Request,
    identity: Annotated[
        OperationsSessionIdentity,
        Depends(authenticated_operations_session),
    ],
) -> OperationsPrincipal:
    """Expand active scoped grants for an already authenticated operations session."""

    now = datetime.now(UTC)
    async with request.app.state.session_factory() as database_session:
        grants = list(
            await database_session.scalars(
                select(AdministrativeGrant).where(
                    AdministrativeGrant.user_id == identity.user_id,
                    AdministrativeGrant.revoked_at.is_(None),
                    or_(AdministrativeGrant.expires_at.is_(None), AdministrativeGrant.expires_at > now),
                )
            )
        )
        expanded = [await _expand_grant(database_session, grant) for grant in grants]

    authorizations = tuple(item for item in expanded if item is not None)
    if not authorizations:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="An active scoped operations grant is required.",
        )
    return OperationsPrincipal(
        user_id=identity.user_id,
        session_id=identity.session_id,
        grants=authorizations,
    )


async def require_recent_operations_mfa(
    request: Request,
    identity: Annotated[
        OperationsSessionIdentity,
        Depends(authenticated_operations_session),
    ],
) -> OperationsSessionIdentity:
    """Require a successful second factor within the fixed step-up window."""

    if request.app.state.settings.operations_password_login_enabled:
        # This switch is explicitly local/test scaffolding and production rejects it.
        return identity
    cutoff = datetime.now(UTC) - timedelta(seconds=MFA_RECENT_SECONDS)
    async with request.app.state.session_factory() as database_session:
        verified = await database_session.scalar(
            select(OperationsSession.id).where(
                OperationsSession.id == identity.session_id,
                OperationsSession.user_id == identity.user_id,
                OperationsSession.revoked_at.is_(None),
                OperationsSession.mfa_verified_at.is_not(None),
                OperationsSession.mfa_verified_at >= cutoff,
            )
        )
    if verified is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Recent operations MFA verification is required.",
        )
    return identity


def require_operations_permission(
    permission: OperationsPermission,
) -> Callable[..., OperationsPrincipal]:
    async def dependency(
        principal: OperationsPrincipal = Depends(authenticated_operations_principal),
    ) -> OperationsPrincipal:
        if not any(permission in grant.permissions for grant in principal.grants):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The required scoped operations permission is not granted.",
            )
        return principal

    return dependency
