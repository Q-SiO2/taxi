"""Authentication dependencies that verify both token signatures and server-side sessions."""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.auth.models import Role, Session, User, UserRole, UserStatus
from taximobile_api.domains.auth.security import InvalidAccessToken, TokenService


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class CurrentPrincipal:
    user_id: UUID
    session_id: UUID


def token_service(request: Request) -> TokenService:
    secret = request.app.state.settings.jwt_secret
    if secret is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Authentication is not configured.")
    return TokenService(secret)


async def authenticated_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> CurrentPrincipal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required.")
    try:
        user_id, session_id = token_service(request).parse_access_token(credentials.credentials)
    except InvalidAccessToken as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required.") from error

    factory = request.app.state.session_factory
    async with factory() as database_session:
        statement = (
            select(Session.id)
            .join(User, User.id == Session.user_id)
            .where(
                Session.id == session_id,
                Session.user_id == user_id,
                Session.revoked_at.is_(None),
                User.status == UserStatus.ACTIVE,
            )
        )
        if await database_session.scalar(statement) is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required.")
    return CurrentPrincipal(user_id=user_id, session_id=session_id)


async def administrator(request: Request, principal: CurrentPrincipal = Depends(authenticated_principal)) -> CurrentPrincipal:
    async with request.app.state.session_factory() as database_session:
        role = await database_session.scalar(
            select(UserRole.role).where(UserRole.user_id == principal.user_id, UserRole.role == Role.ADMIN)
        )
    if role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrative permission is required.")
    return principal
