"""Dedicated operations authentication endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.administration.models import OperationsSession
from taximobile_api.domains.administration.operations_auth_schemas import (
    MfaChallengeResponse,
    MfaStepUpRequest,
    MfaStepUpResponse,
    MfaVerificationRequest,
    OperationsGrantSessionResponse,
    OperationsLoginRequest,
    OperationsLogoutResponse,
    OperationsRefreshRequest,
    OperationsSessionResponse,
    OperationsTokenResponse,
)
from taximobile_api.domains.administration.operations_auth_service import (
    InvalidOperationsCredentials,
    OperationsMfaEnrollmentRequired,
    begin_operations_mfa,
    complete_operations_mfa,
    login_operations,
    rotate_operations_refresh_token,
    step_up_operations_mfa,
)
from taximobile_api.domains.administration.operations_mfa import decode_encryption_key
from taximobile_api.domains.administration.operations_dependencies import (
    OperationsSessionIdentity,
    authenticated_operations_principal,
    authenticated_operations_session,
    operations_token_service,
)
from taximobile_api.domains.administration.permissions import OperationsPrincipal
from taximobile_api.domains.administration.service import audit
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.auth.schemas import normalized_login_identifier
from taximobile_api.domains.auth.security import TokenService
from taximobile_api.domains.auth.security import OPERATIONS_REFRESH_TOKEN_TTL


router = APIRouter(prefix="/operations/auth", tags=["operations-auth"])
OPERATIONS_REFRESH_COOKIE = "__Secure-taximobile-operations-refresh"


def _secure_cookie_enabled(request: Request) -> bool:
    return request.app.state.settings.operations_secure_cookie_enabled


def _deliver_operations_tokens(
    request: Request,
    response: Response,
    result: OperationsTokenResponse,
) -> OperationsTokenResponse:
    if not _secure_cookie_enabled(request):
        return result
    if result.refresh_token is None or result.csrf_token is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Secure operations sessions are not available.",
        )
    response.set_cookie(
        key=OPERATIONS_REFRESH_COOKIE,
        value=result.refresh_token,
        max_age=int(OPERATIONS_REFRESH_TOKEN_TTL.total_seconds()),
        secure=True,
        httponly=True,
        samesite="strict",
        path=f"{request.app.state.settings.api_prefix}/operations/auth",
    )
    return result.model_copy(update={"refresh_token": None})


def _mfa_encryption_key(request: Request) -> bytes:
    try:
        return decode_encryption_key(
            request.app.state.settings.operations_mfa_encryption_key
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Operations MFA is not configured.",
        ) from error


@router.post(
    "/login",
    response_model=OperationsTokenResponse | MfaChallengeResponse,
    response_model_exclude_none=True,
)
async def operations_login(
    payload: OperationsLoginRequest,
    request: Request,
    response: Response,
    tokens: TokenService = Depends(operations_token_service),
    session: AsyncSession = Depends(database_session),
) -> OperationsTokenResponse | MfaChallengeResponse:
    client_address = request.client.host if request.client else "unknown"
    key = f"operations-login:{client_address}:{normalized_login_identifier(payload.identifier)}"
    if not await request.app.state.rate_limiter.allow(
        key,
        limit=request.app.state.settings.login_rate_limit_per_minute,
        window_seconds=60,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
        )
    try:
        async with session.begin():
            if request.app.state.settings.operations_password_login_enabled:
                result = await login_operations(
                    session,
                    payload,
                    tokens,
                    secure_cookie=_secure_cookie_enabled(request),
                )
            else:
                return await begin_operations_mfa(session, payload)
        return _deliver_operations_tokens(request, response, result)
    except InvalidOperationsCredentials as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid operations credentials.",
        ) from error
    except OperationsMfaEnrollmentRequired as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operations MFA enrollment is required. Contact the platform security owner.",
        ) from error


@router.post(
    "/mfa/verify",
    response_model=OperationsTokenResponse,
    response_model_exclude_none=True,
)
async def verify_operations_mfa(
    payload: MfaVerificationRequest,
    request: Request,
    response: Response,
    tokens: TokenService = Depends(operations_token_service),
    session: AsyncSession = Depends(database_session),
) -> OperationsTokenResponse:
    client_address = request.client.host if request.client else "unknown"
    key = f"operations-mfa:{client_address}:{payload.challenge_id}"
    if not await request.app.state.rate_limiter.allow(key, limit=5, window_seconds=300):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many MFA attempts. Start sign-in again.",
        )
    async with session.begin():
        result = await complete_operations_mfa(
            session,
            payload.challenge_id,
            payload.code,
            _mfa_encryption_key(request),
            tokens,
            secure_cookie=_secure_cookie_enabled(request),
        )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired MFA challenge.",
        )
    return _deliver_operations_tokens(request, response, result)


@router.post("/mfa/step-up", response_model=MfaStepUpResponse)
async def step_up_operations_session(
    payload: MfaStepUpRequest,
    request: Request,
    identity: OperationsSessionIdentity = Depends(authenticated_operations_session),
    session: AsyncSession = Depends(database_session),
) -> MfaStepUpResponse:
    client_address = request.client.host if request.client else "unknown"
    key = f"operations-mfa-step-up:{client_address}:{identity.user_id}"
    if not await request.app.state.rate_limiter.allow(key, limit=5, window_seconds=300):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many MFA attempts. Try again later.",
        )
    async with session.begin():
        active_session = await session.scalar(
            select(OperationsSession)
            .where(
                OperationsSession.id == identity.session_id,
                OperationsSession.user_id == identity.user_id,
                OperationsSession.revoked_at.is_(None),
            )
            .with_for_update()
        )
        if active_session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Operations authentication is required.",
            )
        verified, verified_at, method = await step_up_operations_mfa(
            session,
            active_session,
            payload.code,
            _mfa_encryption_key(request),
        )
        if verified:
            await audit(
                session,
                actor_user_id=identity.user_id,
                action="OPERATIONS_MFA_STEP_UP_COMPLETED",
                resource_type="operations_session",
                resource_id=active_session.id,
                changes={"method": method},
            )
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code.",
        )
    return MfaStepUpResponse(
        verified_at=verified_at,
        authentication_strength=f"PASSWORD_{method}_MFA",
    )


@router.post(
    "/refresh",
    response_model=OperationsTokenResponse,
    response_model_exclude_none=True,
)
async def operations_refresh(
    request: Request,
    response: Response,
    payload: OperationsRefreshRequest | None = None,
    x_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
    tokens: TokenService = Depends(operations_token_service),
    session: AsyncSession = Depends(database_session),
) -> OperationsTokenResponse:
    secure_cookie = _secure_cookie_enabled(request)
    refresh_token = (
        request.cookies.get(OPERATIONS_REFRESH_COOKIE)
        if secure_cookie
        else payload.refresh_token if payload is not None else None
    )
    if refresh_token is None or (secure_cookie and x_csrf_token is None):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid operations refresh token.",
        )
    try:
        async with session.begin():
            result = await rotate_operations_refresh_token(
                session,
                refresh_token,
                tokens,
                secure_cookie=secure_cookie,
                submitted_csrf_token=x_csrf_token,
            )
        return _deliver_operations_tokens(request, response, result)
    except InvalidOperationsCredentials as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid operations refresh token.",
        ) from error


@router.post("/logout", response_model=OperationsLogoutResponse)
async def operations_logout(
    request: Request,
    response: Response,
    identity: OperationsSessionIdentity = Depends(authenticated_operations_session),
    session: AsyncSession = Depends(database_session),
) -> OperationsLogoutResponse:
    async with session.begin():
        active_session = await session.get(OperationsSession, identity.session_id)
        if active_session is not None and active_session.user_id == identity.user_id:
            active_session.revoked_at = datetime.now(UTC)
    if _secure_cookie_enabled(request):
        response.delete_cookie(
            key=OPERATIONS_REFRESH_COOKIE,
            path=f"{request.app.state.settings.api_prefix}/operations/auth",
            secure=True,
            httponly=True,
            samesite="strict",
        )
    return OperationsLogoutResponse()


@router.get("/session", response_model=OperationsSessionResponse)
async def operations_session(
    principal: OperationsPrincipal = Depends(authenticated_operations_principal),
    session: AsyncSession = Depends(database_session),
) -> OperationsSessionResponse:
    record = await session.get(OperationsSession, principal.session_id)
    return OperationsSessionResponse(
        user_id=principal.user_id,
        session_id=principal.session_id,
        expires_at=record.expires_at if record is not None else None,
        mfa_verified_at=record.mfa_verified_at if record is not None else None,
        authentication_strength=(
            f"PASSWORD_{record.mfa_method}_MFA"
            if record is not None
            and record.mfa_verified_at is not None
            and record.mfa_method is not None
            else "PASSWORD_ONLY_LOCAL"
        ),
        grants=[
            OperationsGrantSessionResponse(
                id=grant.grant_id,
                role_template=grant.role_template.value,
                market_id=grant.market_id,
                operator_id=grant.operator_id,
                city_id=grant.city_id,
                permissions=sorted(permission.value for permission in grant.permissions),
            )
            for grant in principal.grants
        ],
    )
