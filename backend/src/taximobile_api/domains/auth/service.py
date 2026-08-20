"""Account workflows. Roles and account status are assigned only by trusted backend code."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.auth.models import PassengerProfile, Role, Session, User, UserRole, UserStatus
from taximobile_api.domains.auth.schemas import LoginRequest, RegisterRequest, TokenResponse, normalized_login_identifier
from taximobile_api.domains.auth.security import (
    ACCESS_TOKEN_TTL,
    REFRESH_TOKEN_TTL,
    TokenService,
    hash_password,
    new_refresh_token,
    password_hash_needs_rehash,
    refresh_token_hash,
    verify_login_password,
)


class AccountConflict(ValueError):
    pass


class InvalidCredentials(ValueError):
    pass


async def register_passenger(database_session: AsyncSession, request: RegisterRequest) -> User:
    identifiers = []
    if request.phone_number:
        identifiers.append(User.phone_number == request.phone_number)
    if request.email:
        identifiers.append(User.email == request.email)
    if await database_session.scalar(select(User.id).where(or_(*identifiers))):
        raise AccountConflict("An account already exists for those details.")

    user = User(phone_number=request.phone_number, email=request.email, password_hash=hash_password(request.password))
    database_session.add(user)
    await database_session.flush()
    database_session.add(UserRole(user_id=user.id, role=Role.PASSENGER))
    database_session.add(PassengerProfile(user_id=user.id, display_name=request.display_name.strip()))
    await database_session.flush()
    return user


async def login(
    database_session: AsyncSession, request: LoginRequest, tokens: TokenService
) -> TokenResponse:
    identifier = normalized_login_identifier(request.identifier)
    user = await database_session.scalar(
        select(User).where(or_(User.email == identifier, User.phone_number == identifier))
    )
    password_valid = verify_login_password(
        request.password,
        user.password_hash if user is not None else None,
    )
    if user is None or user.status != UserStatus.ACTIVE or not password_valid:
        raise InvalidCredentials("Invalid credentials.")
    if password_hash_needs_rehash(user.password_hash):
        user.password_hash = hash_password(request.password)
    user.last_login_at = datetime.now(UTC)
    return await _create_session_tokens(database_session, user, tokens, request.device_label)


async def rotate_refresh_token(
    database_session: AsyncSession, refresh_token: str, tokens: TokenService
) -> TokenResponse:
    now = datetime.now(UTC)
    session = await database_session.scalar(
        select(Session)
        .join(User, User.id == Session.user_id)
        .where(
            Session.refresh_token_hash == refresh_token_hash(refresh_token),
            Session.expires_at > now,
            User.status == UserStatus.ACTIVE,
        )
        # Serialise rotations for one token. A concurrent second request then
        # observes the first rotation and is handled as a reuse attempt.
        .with_for_update()
    )
    if session is None:
        raise InvalidCredentials("Invalid credentials.")
    if session.revoked_at is not None:
        if session.refresh_rotated_at is not None:
            # A rotated token must never be usable twice. Treat reuse as
            # potential credential theft and invalidate the active descendant
            # session(s), while preserving other device/session families.
            await database_session.execute(
                update(Session)
                .where(
                    Session.refresh_family_id == session.refresh_family_id,
                    Session.revoked_at.is_(None),
                )
                .values(revoked_at=now)
            )
        raise InvalidCredentials("Invalid credentials.")
    session.revoked_at = now
    session.refresh_rotated_at = now
    user = await database_session.get(User, session.user_id)
    assert user is not None
    return await _create_session_tokens(
        database_session,
        user,
        tokens,
        session.device_label,
        refresh_family_id=session.refresh_family_id,
    )


async def _create_session_tokens(
    database_session: AsyncSession,
    user: User,
    tokens: TokenService,
    device_label: str | None,
    *,
    refresh_family_id: UUID | None = None,
) -> TokenResponse:
    refresh_token = new_refresh_token()
    session = Session(
        user_id=user.id,
        refresh_token_hash=refresh_token_hash(refresh_token),
        refresh_family_id=refresh_family_id or uuid4(),
        expires_at=datetime.now(UTC) + REFRESH_TOKEN_TTL,
        device_label=device_label,
    )
    database_session.add(session)
    await database_session.flush()
    return TokenResponse(
        access_token=tokens.create_access_token(user_id=user.id, session_id=session.id),
        refresh_token=refresh_token,
        expires_in=int(ACCESS_TOKEN_TTL.total_seconds()),
    )
