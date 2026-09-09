from base64 import urlsafe_b64encode
from uuid import uuid4

import pytest
from cryptography.exceptions import InvalidTag

from taximobile_api.domains.administration.operations_mfa import (
    RECOVERY_CODE_COUNT,
    decode_encryption_key,
    decrypt_totp_secret,
    encrypt_totp_secret,
    generate_recovery_codes,
    generate_totp_secret,
    provisioning_uri,
    recovery_code_hash,
    totp_code,
    verify_totp,
)


RFC_SHA1_SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"


def test_totp_matches_rfc_6238_sha1_vector_and_rejects_replay() -> None:
    # RFC 6238 publishes 94287082 for timestamp 59; this profile uses its
    # standard six-digit truncation while retaining the same HMAC/counter.
    assert totp_code(RFC_SHA1_SECRET, 1) == "287082"
    accepted = verify_totp(RFC_SHA1_SECRET, "287082", timestamp=59)
    assert accepted == 1
    assert verify_totp(
        RFC_SHA1_SECRET,
        "287082",
        timestamp=59,
        last_accepted_counter=accepted,
    ) is None


def test_totp_accepts_only_one_step_of_clock_skew() -> None:
    current_timestamp = 300.0
    assert verify_totp(
        RFC_SHA1_SECRET,
        totp_code(RFC_SHA1_SECRET, 9),
        timestamp=current_timestamp,
    ) == 9
    assert verify_totp(
        RFC_SHA1_SECRET,
        totp_code(RFC_SHA1_SECRET, 11),
        timestamp=current_timestamp,
    ) == 11
    assert verify_totp(
        RFC_SHA1_SECRET,
        totp_code(RFC_SHA1_SECRET, 12),
        timestamp=current_timestamp,
    ) is None
    assert verify_totp(RFC_SHA1_SECRET, "12 345", timestamp=current_timestamp) is None


def test_seed_encryption_is_bound_to_the_account_and_nonce() -> None:
    user_id = uuid4()
    other_user_id = uuid4()
    key = bytes(range(32))
    secret = generate_totp_secret()
    ciphertext, nonce = encrypt_totp_secret(secret, key, user_id)

    assert len(nonce) == 12
    assert secret.encode() not in ciphertext
    assert decrypt_totp_secret(ciphertext, nonce, key, user_id) == secret
    with pytest.raises(InvalidTag):
        decrypt_totp_secret(ciphertext, nonce, key, other_user_id)


def test_encryption_key_is_strict_base64url_aes_256_material() -> None:
    encoded = urlsafe_b64encode(bytes(range(32))).decode().rstrip("=")
    assert decode_encryption_key(encoded) == bytes(range(32))
    with pytest.raises(ValueError):
        decode_encryption_key("short")
    with pytest.raises(ValueError):
        decode_encryption_key("!" * 43)
    with pytest.raises(ValueError):
        decode_encryption_key(None)


def test_recovery_codes_are_unique_high_entropy_lookup_secrets() -> None:
    codes = generate_recovery_codes()
    assert len(codes) == RECOVERY_CODE_COUNT
    assert len(set(codes)) == RECOVERY_CODE_COUNT
    assert all(len(code) == 23 and code.count("-") == 3 for code in codes)
    assert recovery_code_hash(codes[0]) == recovery_code_hash(codes[0].lower().replace("-", ""))
    assert recovery_code_hash(codes[0]) != recovery_code_hash(codes[1])
    assert recovery_code_hash("abc🚀") != recovery_code_hash("ABC")


def test_provisioning_uri_has_fixed_interoperable_parameters() -> None:
    uri = provisioning_uri(RFC_SHA1_SECRET, "admin@example.test")
    assert uri.startswith("otpauth://totp/TaxiMobile%20Operations:admin%40example.test?")
    assert f"secret={RFC_SHA1_SECRET}" in uri
    assert "issuer=TaxiMobile%20Operations" in uri
    assert "algorithm=SHA1&digits=6&period=30" in uri
