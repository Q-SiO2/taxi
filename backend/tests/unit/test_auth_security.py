from datetime import UTC, datetime, timedelta
from base64 import urlsafe_b64encode
from hashlib import sha256
import hmac
from uuid import uuid4

import jwt
import pytest

from taximobile_api.domains.auth.security import (
    ACCOUNT_RECOVERY_CODE_COUNT,
    InvalidAccessToken,
    JWT_ALGORITHM,
    JWT_AUDIENCE,
    JWT_ISSUER,
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


def test_operations_token_uses_a_distinct_audience_and_type() -> None:
    user_id = uuid4()
    session_id = uuid4()
    service = TokenService("a" * 32)

    mobile = service.create_access_token(user_id=user_id, session_id=session_id)
    operations = service.create_operations_access_token(user_id=user_id, session_id=session_id)

    assert service.parse_operations_access_token(operations) == (user_id, session_id)
    with pytest.raises(InvalidAccessToken):
        service.parse_operations_access_token(mobile)
    with pytest.raises(InvalidAccessToken):
        service.parse_access_token(operations)


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


@pytest.mark.parametrize("parser", ["parse_access_token", "parse_operations_access_token"])
def test_deeply_nested_signed_payload_is_an_invalid_token_not_a_raw_recursion_error(parser) -> None:
    secret = "a" * 32
    header = urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=")
    # Construct bytes without recursively encoding Python containers. Signature
    # validation must succeed so this exercises the hostile JSON payload boundary.
    payload = b'{"nested":' + b"[" * 2000 + b"0" + b"]" * 2000 + b"}"
    encoded = header + b"." + urlsafe_b64encode(payload).rstrip(b"=")
    signature = urlsafe_b64encode(hmac.new(secret.encode(), encoded, sha256).digest()).rstrip(b"=")
    token = (encoded + b"." + signature).decode("ascii")
    with pytest.raises(InvalidAccessToken):
        getattr(TokenService(secret), parser)(token)


@pytest.mark.parametrize("claim", ["exp", "iat"])
@pytest.mark.parametrize("value", [None, [], {}])
@pytest.mark.parametrize("operations", [False, True])
def test_malformed_numeric_claims_fail_as_invalid_tokens(claim, value, operations) -> None:
    service = TokenService("a" * 32)
    create = service.create_operations_access_token if operations else service.create_access_token
    parse = service.parse_operations_access_token if operations else service.parse_access_token
    valid = create(user_id=uuid4(), session_id=uuid4())
    payload = jwt.decode(valid, options={"verify_signature": False})
    payload[claim] = value
    malformed = jwt.encode(payload, "a" * 32, algorithm=JWT_ALGORITHM)
    with pytest.raises(InvalidAccessToken):
        parse(malformed)


def test_refresh_tokens_are_random_and_only_the_hash_is_persistable() -> None:
    first = new_refresh_token()
    second = new_refresh_token()

    assert first != second
    assert refresh_token_hash(first) != first
    assert len(refresh_token_hash(first)) == 64


def test_account_recovery_codes_are_unique_high_entropy_lookup_secrets() -> None:
    codes = generate_account_recovery_codes()

    assert len(codes) == ACCOUNT_RECOVERY_CODE_COUNT
    assert len(set(codes)) == ACCOUNT_RECOVERY_CODE_COUNT
    assert all(len(code) == 23 and code.count("-") == 3 for code in codes)
    assert account_recovery_code_hash(codes[0]) == account_recovery_code_hash(
        codes[0].lower().replace("-", " ")
    )
    assert account_recovery_code_hash(codes[0]) != account_recovery_code_hash(codes[1])


def test_account_and_operations_recovery_codes_use_distinct_hash_domains() -> None:
    from taximobile_api.domains.administration.operations_mfa import recovery_code_hash

    code = "23456-789AB-CDEFG-HJKLM"

    assert account_recovery_code_hash(code) != recovery_code_hash(code)


def test_missing_account_password_uses_dummy_argon2_work_but_never_authenticates() -> None:
    assert not verify_login_password("a-long-passphrase-for-testing", None)


def test_current_argon2_hash_does_not_need_rehash() -> None:
    assert not password_hash_needs_rehash(hash_password("a-long-passphrase-for-testing"))
    assert not password_hash_needs_rehash("not-an-argon2-hash")
