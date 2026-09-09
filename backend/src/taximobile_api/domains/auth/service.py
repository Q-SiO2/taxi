"""Account workflows. Roles and account status are assigned only by trusted backend code."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.administration.models import AdministrativeGrant
from taximobile_api.domains.administration.service import revoke_user_access
from taximobile_api.domains.auth.models import (
    AccountRecoveryCode,
    PassengerProfile,
    Role,
    Session,
    User,
    UserRole,
    UserStatus,
)
from taximobile_api.domains.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    normalized_login_identifier,
)
from taximobile_api.domains.auth.security import (
    ACCESS_TOKEN_TTL,
    REFRESH_TOKEN_TTL,
    TokenService,
    account_recovery_code_hash,
    generate_account_recovery_codes,
    hash_password,
    new_refresh_token,
    password_hash_needs_rehash,
    refresh_token_hash,
    verify_login_password,
    verify_password,
)
from taximobile_api.domains.notifications.service import notify


ACCOUNT_RECOVERY_TTL = timedelta(days=180)


class AccountConflict(ValueError):
    pass


class InvalidCredentials(ValueError):
    pass


class PasswordReuse(ValueError):
    pass


class StaffRecoveryRequired(ValueError):
    pass


@dataclass(frozen=True)
class RecoveryCodeBundle:
    codes: list[str]
    expires_at: datetime


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


async def user_has_staff_identity(database_session: AsyncSession, user_id: UUID) -> bool:
    admin_role = await database_session.scalar(
        select(UserRole.user_id).where(
            UserRole.user_id == user_id,
            UserRole.role == Role.ADMIN,
        )
    )
    if admin_role is not None:
        return True
    grant = await database_session.scalar(
        select(AdministrativeGrant.id).where(AdministrativeGrant.user_id == user_id).limit(1)
    )
    return grant is not None


async def replace_account_recovery_codes(
    database_session: AsyncSession,
    *,
    user_id: UUID,
    current_password: str,
    now: datetime | None = None,
) -> RecoveryCodeBundle:
    issued_at = now or datetime.now(UTC)
    user = await database_session.scalar(
        select(User).where(User.id == user_id).with_for_update()
    )
    if user is None or user.status != UserStatus.ACTIVE or not verify_password(
        current_password,
        user.password_hash,
    ):
        raise InvalidCredentials("Invalid credentials.")
    if await user_has_staff_identity(database_session, user.id):
        raise StaffRecoveryRequired("Operations accounts use the staff MFA recovery procedure.")

    codes = generate_account_recovery_codes()
    expires_at = issued_at + ACCOUNT_RECOVERY_TTL
    await database_session.execute(
        delete(AccountRecoveryCode).where(AccountRecoveryCode.user_id == user.id)
    )
    database_session.add_all(
        AccountRecoveryCode(
            user_id=user.id,
            code_hash=account_recovery_code_hash(code),
            expires_at=expires_at,
            created_at=issued_at,
        )
        for code in codes
    )
    await notify(
        database_session,
        user_id=user.id,
        notification_type="ACCOUNT_RECOVERY_CODES_REPLACED",
        title="Recovery codes replaced",
        body="A new set of offline account recovery codes was created.",
        data={},
    )
    return RecoveryCodeBundle(codes=codes, expires_at=expires_at)


async def reset_password_with_recovery_code(
    database_session: AsyncSession,
    *,
    identifier: str,
    recovery_code: str,
    new_password: str,
    now: datetime | None = None,
) -> bool:
    """Consume one valid code without revealing whether the account exists."""

    reset_at = now or datetime.now(UTC)
    # Always perform the expensive password hash before account lookup so the
    # missing-account path does not become a cheap enumeration oracle.
    replacement_hash = hash_password(new_password)
    normalized_identifier = normalized_login_identifier(identifier)
    user = await database_session.scalar(
        select(User)
        .where(
            or_(
                User.email == normalized_identifier,
                User.phone_number == normalized_identifier,
            )
        )
        .with_for_update()
    )
    if user is None or user.status != UserStatus.ACTIVE:
        return False
    if await user_has_staff_identity(database_session, user.id):
        return False

    code = await database_session.scalar(
        select(AccountRecoveryCode)
        .where(
            AccountRecoveryCode.user_id == user.id,
            AccountRecoveryCode.code_hash == account_recovery_code_hash(recovery_code),
            AccountRecoveryCode.expires_at > reset_at,
        )
        .with_for_update()
    )
    if code is None:
        return False

    user.password_hash = replacement_hash
    user.updated_at = reset_at
    await database_session.execute(
        delete(AccountRecoveryCode).where(AccountRecoveryCode.user_id == user.id)
    )
    await revoke_user_access(
        database_session,
        user_id=user.id,
        revoked_at=reset_at,
    )
    await notify(
        database_session,
        user_id=user.id,
        notification_type="ACCOUNT_PASSWORD_RESET",
        title="Password reset",
        body="Your account password was reset with an offline recovery code.",
        data={},
    )
    return True


async def change_account_password(
    database_session: AsyncSession,
    *,
    user_id: UUID,
    current_password: str,
    new_password: str,
    now: datetime | None = None,
) -> tuple[int, int]:
    changed_at = now or datetime.now(UTC)
    user = await database_session.scalar(
        select(User).where(User.id == user_id).with_for_update()
    )
    if user is None or user.status != UserStatus.ACTIVE or not verify_password(
        current_password,
        user.password_hash,
    ):
        raise InvalidCredentials("Invalid credentials.")
    if verify_password(new_password, user.password_hash):
        raise PasswordReuse("Choose a password different from the current password.")

    user.password_hash = hash_password(new_password)
    user.updated_at = changed_at
    await database_session.execute(
        delete(AccountRecoveryCode).where(AccountRecoveryCode.user_id == user.id)
    )
    sessions_revoked, devices_revoked = await revoke_user_access(
        database_session,
        user_id=user.id,
        revoked_at=changed_at,
    )
    await notify(
        database_session,
        user_id=user.id,
        notification_type="ACCOUNT_PASSWORD_CHANGED",
        title="Password changed",
        body="Your account password was changed and all sessions were signed out.",
        data={},
    )
    return sessions_revoked, devices_revoked


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
