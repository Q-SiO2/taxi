"""Password and token primitives; callers never log their inputs or outputs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from dataclasses import dataclass
from hashlib import sha256
from secrets import choice, token_urlsafe
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError


ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=30)
OPERATIONS_ACCESS_TOKEN_TTL = timedelta(minutes=10)
OPERATIONS_REFRESH_TOKEN_TTL = timedelta(hours=8)
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "taximobile-api"
JWT_AUDIENCE = "taximobile-mobile"
OPERATIONS_JWT_AUDIENCE = "taximobile-operations"
JWT_REQUIRED_CLAIMS = ("sub", "sid", "type", "iat", "exp", "iss", "aud")
ACCOUNT_RECOVERY_CODE_COUNT = 8
ACCOUNT_RECOVERY_CODE_GROUPS = 4
ACCOUNT_RECOVERY_CODE_GROUP_LENGTH = 5
ACCOUNT_RECOVERY_CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
ACCOUNT_RECOVERY_CODE_DOMAIN = "taximobile-account-recovery-v1:"

_password_hasher = PasswordHasher()
# A missing account still performs one full Argon2 verification. The random
# process-local value is never accepted, persisted, or logged; it exists only to
# prevent the account lookup branch from becoming a cheap timing oracle.
_dummy_password_hash = _password_hasher.hash(token_urlsafe(32))


class InvalidAccessToken(ValueError):
    """An access token cannot establish an authenticated session."""


@dataclass(frozen=True, slots=True)
class VerifiedAccessToken:
    """Verified mobile identity and deadline, never the raw bearer credential."""

    user_id: UUID
    session_id: UUID
    expires_at: datetime


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError):
        return False


def verify_login_password(password: str, password_hash: str | None) -> bool:
    """Perform one Argon2 verification even when no account hash exists."""
    verified = verify_password(password, password_hash or _dummy_password_hash)
    return password_hash is not None and verified


def password_hash_needs_rehash(password_hash: str) -> bool:
    """Allow reviewed Argon2 parameter upgrades during a valid login."""
    try:
        return _password_hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return False


def new_refresh_token() -> str:
    return token_urlsafe(48)


def refresh_token_hash(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def generate_account_recovery_codes() -> list[str]:
    """Create independent 100-bit offline secrets suitable for one-time display."""

    codes: list[str] = []
    while len(codes) < ACCOUNT_RECOVERY_CODE_COUNT:
        groups = [
            "".join(
                choice(ACCOUNT_RECOVERY_CODE_ALPHABET)
                for _ in range(ACCOUNT_RECOVERY_CODE_GROUP_LENGTH)
            )
            for _ in range(ACCOUNT_RECOVERY_CODE_GROUPS)
        ]
        code = "-".join(groups)
        if code not in codes:
            codes.append(code)
    return codes


def account_recovery_code_hash(code: str) -> str:
    """Normalize a presented code and return its domain-separated lookup digest."""

    normalized = "".join(character for character in code.upper() if character not in "- \t\r\n")
    material = f"{ACCOUNT_RECOVERY_CODE_DOMAIN}{normalized}"
    return sha256(material.encode("utf-8")).hexdigest()


def new_csrf_token() -> str:
    return token_urlsafe(32)


def csrf_token_hash(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


class TokenService:
    def __init__(self, secret: str) -> None:
        if len(secret) < 32:
            raise ValueError("JWT signing secret must contain at least 32 characters.")
        self._secret = secret

    def create_access_token(self, *, user_id: UUID, session_id: UUID, now: datetime | None = None) -> str:
        issued_at = now or datetime.now(UTC)
        return jwt.encode(
            {
                "sub": str(user_id),
                "sid": str(session_id),
                "type": "access",
                "iat": issued_at,
                "exp": issued_at + ACCESS_TOKEN_TTL,
                "iss": JWT_ISSUER,
                "aud": JWT_AUDIENCE,
            },
            self._secret,
            algorithm=JWT_ALGORITHM,
        )

    def parse_access_token(self, token: str) -> tuple[UUID, UUID]:
        verified = self.parse_access_token_details(token)
        return verified.user_id, verified.session_id

    def parse_access_token_details(self, token: str) -> VerifiedAccessToken:
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=[JWT_ALGORITHM],
                issuer=JWT_ISSUER,
                audience=JWT_AUDIENCE,
                options={"require": list(JWT_REQUIRED_CLAIMS)},
            )
            if claims.get("type") != "access":
                raise InvalidAccessToken("Unexpected token type.")
            if not isinstance(claims.get("sub"), str) or not isinstance(claims.get("sid"), str):
                raise InvalidAccessToken("Invalid session identity.")
            return VerifiedAccessToken(
                UUID(claims["sub"]), UUID(claims["sid"]),
                datetime.fromtimestamp(int(claims["exp"]), UTC),
            )
        except (jwt.PyJWTError, KeyError, ValueError, TypeError, OverflowError, OSError) as error:
            raise InvalidAccessToken("Invalid or expired access token.") from error

    def create_operations_access_token(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        now: datetime | None = None,
    ) -> str:
        """Issue a short-lived token that ordinary mobile routes cannot parse."""

        issued_at = now or datetime.now(UTC)
        return jwt.encode(
            {
                "sub": str(user_id),
                "sid": str(session_id),
                "type": "operations_access",
                "iat": issued_at,
                "exp": issued_at + OPERATIONS_ACCESS_TOKEN_TTL,
                "iss": JWT_ISSUER,
                "aud": OPERATIONS_JWT_AUDIENCE,
            },
            self._secret,
            algorithm=JWT_ALGORITHM,
        )

    def parse_operations_access_token(self, token: str) -> tuple[UUID, UUID]:
        """Parse only the isolated operations audience and token type."""

        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=[JWT_ALGORITHM],
                issuer=JWT_ISSUER,
                audience=OPERATIONS_JWT_AUDIENCE,
                options={"require": list(JWT_REQUIRED_CLAIMS)},
            )
            if claims.get("type") != "operations_access":
                raise InvalidAccessToken("Unexpected token type.")
            return UUID(claims["sub"]), UUID(claims["sid"])
        except (jwt.PyJWTError, KeyError, ValueError) as error:
            raise InvalidAccessToken("Invalid or expired operations access token.") from error
