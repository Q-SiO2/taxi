from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from taximobile_api.domains.auth.security import (
    InvalidAccessToken,
    JWT_ALGORITHM,
    JWT_AUDIENCE,
    JWT_ISSUER,
    TokenService,
    hash_password,
    new_refresh_token,
    password_hash_needs_rehash,
    refresh_token_hash,
    verify_login_password,
    verify_password,
)


def test_password_is_argon2_hash_and_verifies_without_storing_plaintext() -> None:
    password_hash = hash_password("a-long-passphrase-for-testing")

    assert password_hash.startswith("$argon2id$")
    assert "a-long-passphrase-for-testing" not in password_hash
    assert verify_password("a-long-passphrase-for-testing", password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_access_token_is_bound_to_user_and_session() -> None:
    user_id = uuid4()
    session_id = uuid4()
    service = TokenService("a" * 32)

    token = service.create_access_token(
        user_id=user_id,
        session_id=session_id,
    )

    assert service.parse_access_token(token) == (user_id, session_id)


def test_access_token_rejects_another_signing_secret() -> None:
    token = TokenService("a" * 32).create_access_token(user_id=uuid4(), session_id=uuid4())

    with pytest.raises(InvalidAccessToken):
        TokenService("b" * 32).parse_access_token(token)


@pytest.mark.parametrize(
    ("issuer", "audience"),
    [
        ("another-service", JWT_AUDIENCE),
        (JWT_ISSUER, "another-client"),
    ],
)
def test_access_token_rejects_another_security_domain(issuer: str, audience: str) -> None:
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "sid": str(uuid4()),
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=15),
            "iss": issuer,
            "aud": audience,
        },
        "a" * 32,
        algorithm=JWT_ALGORITHM,
    )

    with pytest.raises(InvalidAccessToken):
        TokenService("a" * 32).parse_access_token(token)


def test_access_token_requires_every_identity_and_lifecycle_claim() -> None:
    now = datetime.now(UTC)
    incomplete = jwt.encode(
        {
            "sub": str(uuid4()),
            "sid": str(uuid4()),
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=15),
            "iss": JWT_ISSUER,
            # Audience is deliberately absent.
        },
        "a" * 32,
        algorithm=JWT_ALGORITHM,
    )

    with pytest.raises(InvalidAccessToken):
        TokenService("a" * 32).parse_access_token(incomplete)


def test_refresh_tokens_are_random_and_only_the_hash_is_persistable() -> None:
    first = new_refresh_token()
    second = new_refresh_token()

    assert first != second
    assert refresh_token_hash(first) != first
    assert len(refresh_token_hash(first)) == 64


def test_missing_account_password_uses_dummy_argon2_work_but_never_authenticates() -> None:
    assert not verify_login_password("a-long-passphrase-for-testing", None)


def test_current_argon2_hash_does_not_need_rehash() -> None:
    assert not password_hash_needs_rehash(hash_password("a-long-passphrase-for-testing"))
    assert not password_hash_needs_rehash("not-an-argon2-hash")
