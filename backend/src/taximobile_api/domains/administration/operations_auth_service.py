"""Password + TOTP operations authentication and rotating sessions."""

from __future__ import annotations

from binascii import Error as BinasciiError
from datetime import UTC, datetime, timedelta
from hmac import compare_digest
from uuid import UUID, uuid4

from cryptography.exceptions import InvalidTag
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.administration.models import (
    AdministrativeGrant,
    OperationsMfaChallenge,
    OperationsMfaCredential,
    OperationsMfaRecoveryCode,
    OperationsSession,
)
from taximobile_api.domains.administration.operations_auth_schemas import (
    MfaChallengeResponse,
    OperationsLoginRequest,
    OperationsTokenResponse,
)
from taximobile_api.domains.administration.operations_mfa import (
    MFA_CHALLENGE_ATTEMPTS,
    MFA_CHALLENGE_SECONDS,
    decrypt_totp_secret,
    recovery_code_hash,
    verify_totp,
)
from taximobile_api.domains.administration.service import audit
from taximobile_api.domains.auth.models import User, UserStatus
from taximobile_api.domains.auth.schemas import normalized_login_identifier
from taximobile_api.domains.auth.security import (
    OPERATIONS_ACCESS_TOKEN_TTL,
    OPERATIONS_REFRESH_TOKEN_TTL,
    TokenService,
    csrf_token_hash,
    hash_password,
    new_csrf_token,
    new_refresh_token,
    password_hash_needs_rehash,
    refresh_token_hash,
    verify_login_password,
)


class InvalidOperationsCredentials(ValueError):
    pass


class OperationsMfaEnrollmentRequired(ValueError):
    pass


async def _has_active_grant(database_session: AsyncSession, user_id: UUID, now: datetime) -> bool:
    return (
        await database_session.scalar(
            select(AdministrativeGrant.id).where(
                AdministrativeGrant.user_id == user_id,
                AdministrativeGrant.revoked_at.is_(None),
                or_(AdministrativeGrant.expires_at.is_(None), AdministrativeGrant.expires_at > now),
            )
        )
        is not None
    )


async def _authenticate_operations_password(
    database_session: AsyncSession,
    request: OperationsLoginRequest,
) -> User:
    now = datetime.now(UTC)
    identifier = normalized_login_identifier(request.identifier)
    user = await database_session.scalar(
        select(User).where(or_(User.email == identifier, User.phone_number == identifier))
    )
    password_valid = verify_login_password(
        request.password,
        user.password_hash if user is not None else None,
    )
    if (
        user is None
        or user.status != UserStatus.ACTIVE
        or not password_valid
        or not await _has_active_grant(database_session, user.id, now)
    ):
        raise InvalidOperationsCredentials("Invalid operations credentials.")
    if password_hash_needs_rehash(user.password_hash):
        user.password_hash = hash_password(request.password)
    user.last_login_at = now
    return user


async def login_operations(
    database_session: AsyncSession,
    request: OperationsLoginRequest,
    tokens: TokenService,
    *,
    secure_cookie: bool = False,
) -> OperationsTokenResponse:
    """Issue the explicitly local/test password-only session."""

    user = await _authenticate_operations_password(database_session, request)
    return await _create_operations_session_tokens(
        database_session,
        user,
        tokens,
        request.device_label,
        secure_cookie=secure_cookie,
    )


async def begin_operations_mfa(
    database_session: AsyncSession,
    request: OperationsLoginRequest,
) -> MfaChallengeResponse:
    """Verify password but issue no bearer credential until MFA succeeds."""

    user = await _authenticate_operations_password(database_session, request)
    credential_id = await database_session.scalar(
        select(OperationsMfaCredential.id).where(OperationsMfaCredential.user_id == user.id)
    )
    if credential_id is None:
        raise OperationsMfaEnrollmentRequired("Operations MFA enrollment is required.")

    now = datetime.now(UTC)
    await database_session.execute(
        update(OperationsMfaChallenge)
        .where(
            OperationsMfaChallenge.user_id == user.id,
            OperationsMfaChallenge.consumed_at.is_(None),
        )
        .values(consumed_at=now)
    )
    challenge = OperationsMfaChallenge(
        user_id=user.id,
        expires_at=now + timedelta(seconds=MFA_CHALLENGE_SECONDS),
        attempt_count=0,
        device_label=request.device_label,
        created_at=now,
    )
    database_session.add(challenge)
    await database_session.flush()
    return MfaChallengeResponse(
        challenge_id=challenge.id,
        expires_in=MFA_CHALLENGE_SECONDS,
    )


async def complete_operations_mfa(
    database_session: AsyncSession,
    challenge_id: UUID,
    submitted_code: str,
    encryption_key: bytes,
    tokens: TokenService,
    *,
    secure_cookie: bool = False,
) -> OperationsTokenResponse | None:
    """Consume one login challenge and issue the first MFA-backed session."""

    now = datetime.now(UTC)
    challenge = await database_session.scalar(
        select(OperationsMfaChallenge)
        .where(OperationsMfaChallenge.id == challenge_id)
        .with_for_update()
    )
    if (
        challenge is None
        or challenge.consumed_at is not None
        or challenge.expires_at <= now
        or challenge.attempt_count >= MFA_CHALLENGE_ATTEMPTS
    ):
        return None
    user = await database_session.get(User, challenge.user_id)
    if (
        user is None
        or user.status != UserStatus.ACTIVE
        or not await _has_active_grant(database_session, challenge.user_id, now)
    ):
        challenge.consumed_at = now
        return None

    method = await _verify_operations_mfa_code(
        database_session,
        challenge.user_id,
        submitted_code,
        encryption_key,
        now,
    )
    challenge.attempt_count += 1
    if method is None:
        if challenge.attempt_count >= MFA_CHALLENGE_ATTEMPTS:
            challenge.consumed_at = now
        return None

    challenge.consumed_at = now
    return await _create_operations_session_tokens(
        database_session,
        user,
        tokens,
        challenge.device_label,
        mfa_verified_at=now,
        mfa_method=method,
        secure_cookie=secure_cookie,
    )


async def step_up_operations_mfa(
    database_session: AsyncSession,
    operations_session: OperationsSession,
    submitted_code: str,
    encryption_key: bytes,
) -> tuple[bool, datetime, str | None]:
    """Reverify possession for a live session without changing its refresh family."""

    now = datetime.now(UTC)
    method = await _verify_operations_mfa_code(
        database_session,
        operations_session.user_id,
        submitted_code,
        encryption_key,
        now,
    )
    if method is None:
        return False, now, None
    operations_session.mfa_verified_at = now
    operations_session.mfa_method = method
    return True, now, method


async def _verify_operations_mfa_code(
    database_session: AsyncSession,
    user_id: UUID,
    submitted_code: str,
    encryption_key: bytes,
    now: datetime,
) -> str | None:
    credential = await database_session.scalar(
        select(OperationsMfaCredential)
        .where(OperationsMfaCredential.user_id == user_id)
        .with_for_update()
    )
    if credential is None:
        return None

    if len(submitted_code) == 6 and submitted_code.isascii() and submitted_code.isdigit():
        try:
            secret = decrypt_totp_secret(
                credential.encrypted_secret,
                credential.secret_nonce,
                encryption_key,
                user_id,
            )
        except (InvalidTag, UnicodeDecodeError, ValueError, BinasciiError):
            # Corrupt ciphertext, a wrong deployment key, and an invalid code
            # share the same external result. No secret or crypto error is logged.
            return None
        counter = verify_totp(
            secret,
            submitted_code,
            timestamp=now.timestamp(),
            last_accepted_counter=credential.last_accepted_counter,
        )
        if counter is not None:
            credential.last_accepted_counter = counter
            credential.updated_at = now
            return "TOTP"

    digest = recovery_code_hash(submitted_code)
    recovery = await database_session.scalar(
        select(OperationsMfaRecoveryCode)
        .where(
            OperationsMfaRecoveryCode.credential_id == credential.id,
            OperationsMfaRecoveryCode.code_hash == digest,
            OperationsMfaRecoveryCode.used_at.is_(None),
        )
        .with_for_update()
    )
    if recovery is not None:
        recovery.used_at = now
        return "RECOVERY_CODE"
    return None


async def rotate_operations_refresh_token(
    database_session: AsyncSession,
    refresh_token: str,
    tokens: TokenService,
    *,
    secure_cookie: bool = False,
    submitted_csrf_token: str | None = None,
) -> OperationsTokenResponse:
    now = datetime.now(UTC)
    session = await database_session.scalar(
        select(OperationsSession)
        .join(User, User.id == OperationsSession.user_id)
        .where(
            OperationsSession.refresh_token_hash == refresh_token_hash(refresh_token),
            OperationsSession.expires_at > now,
            User.status == UserStatus.ACTIVE,
        )
        .with_for_update()
    )
    if session is None:
        raise InvalidOperationsCredentials("Invalid operations credentials.")
    if secure_cookie and (
        submitted_csrf_token is None
        or session.csrf_token_hash is None
        or not compare_digest(
            session.csrf_token_hash,
            csrf_token_hash(submitted_csrf_token),
        )
    ):
        raise InvalidOperationsCredentials("Invalid operations credentials.")
    if session.revoked_at is not None:
        if session.refresh_rotated_at is not None:
            await database_session.execute(
                update(OperationsSession)
                .where(
                    OperationsSession.refresh_family_id == session.refresh_family_id,
                    OperationsSession.revoked_at.is_(None),
                )
                .values(revoked_at=now)
            )
        raise InvalidOperationsCredentials("Invalid operations credentials.")
    if not await _has_active_grant(database_session, session.user_id, now):
        session.revoked_at = now
        raise InvalidOperationsCredentials("Invalid operations credentials.")

    session.revoked_at = now
    session.refresh_rotated_at = now
    user = await database_session.get(User, session.user_id)
    assert user is not None
    return await _create_operations_session_tokens(
        database_session,
        user,
        tokens,
        session.device_label,
        refresh_family_id=session.refresh_family_id,
        mfa_verified_at=session.mfa_verified_at,
        mfa_method=session.mfa_method,
        secure_cookie=secure_cookie,
    )


async def _create_operations_session_tokens(
    database_session: AsyncSession,
    user: User,
    tokens: TokenService,
    device_label: str | None,
    *,
    refresh_family_id: UUID | None = None,
    mfa_verified_at: datetime | None = None,
    mfa_method: str | None = None,
    secure_cookie: bool = False,
) -> OperationsTokenResponse:
    refresh_token = new_refresh_token()
    csrf_token = new_csrf_token() if secure_cookie else None
    session = OperationsSession(
        user_id=user.id,
        refresh_token_hash=refresh_token_hash(refresh_token),
        csrf_token_hash=csrf_token_hash(csrf_token) if csrf_token is not None else None,
        refresh_family_id=refresh_family_id or uuid4(),
        expires_at=datetime.now(UTC) + OPERATIONS_REFRESH_TOKEN_TTL,
        mfa_verified_at=mfa_verified_at,
        mfa_method=mfa_method,
        device_label=device_label,
    )
    database_session.add(session)
    await database_session.flush()
    if refresh_family_id is None:
        await audit(
            database_session,
            actor_user_id=user.id,
            action=(
                "OPERATIONS_MFA_LOGIN_COMPLETED"
                if mfa_verified_at is not None
                else "OPERATIONS_PASSWORD_LOGIN_COMPLETED"
            ),
            resource_type="operations_session",
            resource_id=session.id,
            changes={"mfa_method": mfa_method},
        )
    strength = (
        f"PASSWORD_{mfa_method}_MFA"
        if mfa_verified_at is not None and mfa_method is not None
        else "PASSWORD_ONLY_LOCAL"
    )
    return OperationsTokenResponse(
        access_token=tokens.create_operations_access_token(user_id=user.id, session_id=session.id),
        refresh_token=refresh_token,
        csrf_token=csrf_token,
        expires_in=int(OPERATIONS_ACCESS_TOKEN_TTL.total_seconds()),
        authentication_strength=strength,
    )
