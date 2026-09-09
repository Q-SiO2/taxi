"""Account and session HTTP endpoints."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.auth.dependencies import CurrentPrincipal, authenticated_principal, token_service
from taximobile_api.domains.auth.models import PassengerProfile, Session, User, UserRole
from taximobile_api.domains.auth.schemas import (
    AccountRecoveryResetRequest,
    AccountRecoveryResetResponse,
    AccountSessionListResponse,
    AccountSessionResponse,
    AccountSessionRevokeResponse,
    CurrentUserResponse,
    LoginRequest,
    LogoutResponse,
    PassengerProfileResponse,
    PassengerProfileUpdateRequest,
    PasswordChangeRequest,
    PasswordChangeResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    RecoveryCodesCreateRequest,
    RecoveryCodesResponse,
    TokenResponse,
    UserSummary,
    normalized_login_identifier,
)
from taximobile_api.domains.auth.security import TokenService
from taximobile_api.domains.auth.service import (
    AccountConflict,
    InvalidCredentials,
    PasswordReuse,
    StaffRecoveryRequired,
    change_account_password,
    login,
    register_passenger,
    replace_account_recovery_codes,
    reset_password_with_recovery_code,
    rotate_refresh_token,
)
from taximobile_api.domains.notifications.models import DeviceToken


router = APIRouter(tags=["auth"])


async def database_session(request: Request):
    async with request.app.state.session_factory() as session:
        yield session


@router.post("/auth/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    session: AsyncSession = Depends(database_session),
) -> RegisterResponse:
    client_address = request.client.host if request.client else "unknown"
    if not await request.app.state.rate_limiter.allow(
        f"register:{client_address}",
        limit=request.app.state.settings.registration_rate_limit_per_minute,
        window_seconds=60,
    ):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many registration attempts. Try again later.")
    try:
        async with session.begin():
            user = await register_passenger(session, payload)
    except AccountConflict as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except IntegrityError as error:
        # The database uniqueness constraints arbitrate concurrent registration
        # attempts that both passed the friendly pre-check. Never expose a
        # driver message, constraint name, or raw identifier in the response.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account already exists for those details.",
        ) from error
    return RegisterResponse(user=UserSummary(id=user.id, phone_number=user.phone_number, email=user.email))


@router.post(
    "/auth/recovery/reset",
    response_model=AccountRecoveryResetResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reset_account_password(
    payload: AccountRecoveryResetRequest,
    request: Request,
    session: AsyncSession = Depends(database_session),
) -> AccountRecoveryResetResponse:
    client_address = request.client.host if request.client else "unknown"
    if not await request.app.state.rate_limiter.allow(
        f"account-recovery:{client_address}:{payload.identifier}",
        limit=request.app.state.settings.account_recovery_rate_limit_per_hour,
        window_seconds=3600,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many recovery attempts. Try again later.",
        )
    async with session.begin():
        await reset_password_with_recovery_code(
            session,
            identifier=payload.identifier,
            recovery_code=payload.recovery_code,
            new_password=payload.new_password,
        )
    # This response is deliberately identical for absent accounts, invalid or
    # expired codes, staff accounts, and successful resets.
    return AccountRecoveryResetResponse()


@router.post("/auth/login", response_model=TokenResponse)
async def login_endpoint(
    payload: LoginRequest,
    request: Request,
    tokens: TokenService = Depends(token_service),
    session: AsyncSession = Depends(database_session),
) -> TokenResponse:
    client_address = request.client.host if request.client else "unknown"
    key = f"login:{client_address}:{normalized_login_identifier(payload.identifier)}"
    if not await request.app.state.rate_limiter.allow(
        key, limit=request.app.state.settings.login_rate_limit_per_minute, window_seconds=60
    ):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts. Try again later.")
    try:
        async with session.begin():
            return await login(session, payload, tokens)
    except InvalidCredentials as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.") from error


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest,
    tokens: TokenService = Depends(token_service),
    session: AsyncSession = Depends(database_session),
) -> TokenResponse:
    try:
        async with session.begin():
            return await rotate_refresh_token(session, payload.refresh_token, tokens)
    except InvalidCredentials as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.") from error


@router.post("/auth/logout", response_model=LogoutResponse)
async def logout(
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> LogoutResponse:
    async with session.begin():
        active_session = await session.get(Session, principal.session_id)
        if active_session is not None and active_session.user_id == principal.user_id:
            revoked_at = datetime.now(UTC)
            active_session.revoked_at = revoked_at
            await session.execute(
                update(DeviceToken)
                .where(
                    DeviceToken.user_id == principal.user_id,
                    DeviceToken.session_id == principal.session_id,
                    DeviceToken.revoked_at.is_(None),
                )
                .values(revoked_at=revoked_at)
            )
    return LogoutResponse()


@router.post("/auth/recovery-codes", response_model=RecoveryCodesResponse)
async def create_recovery_codes(
    payload: RecoveryCodesCreateRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> RecoveryCodesResponse:
    client_address = request.client.host if request.client else "unknown"
    if not await request.app.state.rate_limiter.allow(
        f"account-security:{client_address}:{principal.user_id}:recovery-codes",
        limit=request.app.state.settings.account_security_rate_limit_per_hour,
        window_seconds=3600,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many account-security attempts. Try again later.",
        )
    try:
        async with session.begin():
            bundle = await replace_account_recovery_codes(
                session,
                user_id=principal.user_id,
                current_password=payload.current_password,
            )
    except InvalidCredentials as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is invalid.",
        ) from error
    except StaffRecoveryRequired as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    return RecoveryCodesResponse(codes=bundle.codes, expires_at=bundle.expires_at)


@router.post("/auth/password/change", response_model=PasswordChangeResponse)
async def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> PasswordChangeResponse:
    client_address = request.client.host if request.client else "unknown"
    if not await request.app.state.rate_limiter.allow(
        f"account-security:{client_address}:{principal.user_id}:password-change",
        limit=request.app.state.settings.account_security_rate_limit_per_hour,
        window_seconds=3600,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many account-security attempts. Try again later.",
        )
    try:
        async with session.begin():
            sessions_revoked, devices_revoked = await change_account_password(
                session,
                user_id=principal.user_id,
                current_password=payload.current_password,
                new_password=payload.new_password,
            )
    except InvalidCredentials as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is invalid.",
        ) from error
    except PasswordReuse as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return PasswordChangeResponse(
        sessions_revoked=sessions_revoked,
        device_registrations_revoked=devices_revoked,
    )


@router.get("/auth/sessions", response_model=AccountSessionListResponse)
async def list_account_sessions(
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> AccountSessionListResponse:
    now = datetime.now(UTC)
    filters = (
        Session.user_id == principal.user_id,
        Session.revoked_at.is_(None),
        Session.expires_at > now,
    )
    records = list(
        await session.scalars(
            select(Session)
            .where(*filters)
            .order_by(Session.created_at.desc(), Session.id.desc())
            .limit(100)
        )
    )
    total = await session.scalar(select(func.count()).select_from(Session).where(*filters))
    return AccountSessionListResponse(
        items=[
            AccountSessionResponse(
                id=record.id,
                device_label=record.device_label,
                current=record.id == principal.session_id,
                created_at=record.created_at,
                expires_at=record.expires_at,
            )
            for record in records
        ],
        total=total or 0,
    )


@router.delete(
    "/auth/sessions/{session_id}",
    response_model=AccountSessionRevokeResponse,
)
async def revoke_account_session(
    session_id: UUID,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> AccountSessionRevokeResponse:
    async with session.begin():
        record = await session.scalar(
            select(Session)
            .where(
                Session.id == session_id,
                Session.user_id == principal.user_id,
                Session.revoked_at.is_(None),
            )
            .with_for_update()
        )
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active session not found.",
            )
        revoked_at = datetime.now(UTC)
        record.revoked_at = revoked_at
        await session.execute(
            update(DeviceToken)
            .where(
                DeviceToken.user_id == principal.user_id,
                DeviceToken.session_id == record.id,
                DeviceToken.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
        )
    return AccountSessionRevokeResponse(current_session=record.id == principal.session_id)


@router.get("/me", response_model=CurrentUserResponse)
async def current_user(
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> CurrentUserResponse:
    user = await session.get(User, principal.user_id)
    profile = await session.scalar(select(PassengerProfile).where(PassengerProfile.user_id == principal.user_id))
    roles = list(await session.scalars(select(UserRole.role).where(UserRole.user_id == principal.user_id)))
    assert user is not None
    return CurrentUserResponse(
        id=user.id,
        roles=[role.value for role in roles],
        profile={"display_name": profile.display_name if profile else ""},
    )


async def passenger_profile_for_user(session: AsyncSession, user_id) -> PassengerProfile:
    profile = await session.scalar(select(PassengerProfile).where(PassengerProfile.user_id == user_id))
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passenger profile not found.")
    return profile


def passenger_profile_response(profile: PassengerProfile) -> PassengerProfileResponse:
    return PassengerProfileResponse(id=profile.id, display_name=profile.display_name)


@router.get("/passenger/profile", response_model=PassengerProfileResponse, tags=["passenger"])
async def get_passenger_profile(
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> PassengerProfileResponse:
    return passenger_profile_response(await passenger_profile_for_user(session, principal.user_id))


@router.patch("/passenger/profile", response_model=PassengerProfileResponse, tags=["passenger"])
async def update_passenger_profile(
    payload: PassengerProfileUpdateRequest,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> PassengerProfileResponse:
    async with session.begin():
        profile = await passenger_profile_for_user(session, principal.user_id)
        profile.display_name = payload.display_name
    return passenger_profile_response(profile)
