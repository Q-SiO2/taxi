"""Password and token primitives; callers never log their inputs or outputs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError


ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=30)
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "taximobile-api"
JWT_AUDIENCE = "taximobile-mobile"
JWT_REQUIRED_CLAIMS = ("sub", "sid", "type", "iat", "exp", "iss", "aud")

_password_hasher = PasswordHasher()
# A missing account still performs one full Argon2 verification. The random
# process-local value is never accepted, persisted, or logged; it exists only to
# prevent the account lookup branch from becoming a cheap timing oracle.
_dummy_password_hash = _password_hasher.hash(token_urlsafe(32))


class InvalidAccessToken(ValueError):
    """An access token cannot establish an authenticated session."""


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
            return UUID(claims["sub"]), UUID(claims["sid"])
        except (jwt.PyJWTError, KeyError, ValueError) as error:
            raise InvalidAccessToken("Invalid or expired access token.") from error
