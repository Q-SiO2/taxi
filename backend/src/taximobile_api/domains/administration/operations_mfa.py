"""Cryptographic primitives for the self-hosted operations MFA boundary."""

from __future__ import annotations

from base64 import b32decode, b32encode, b64decode
from binascii import Error as BinasciiError
from hashlib import sha256
import hmac
import os
from secrets import choice
import struct
from time import time
from urllib.parse import quote
from uuid import UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


TOTP_DIGITS = 6
TOTP_PERIOD_SECONDS = 30
TOTP_ALLOWED_SKEW_STEPS = 1
MFA_CHALLENGE_ATTEMPTS = 5
MFA_CHALLENGE_SECONDS = 300
MFA_RECENT_SECONDS = 600
RECOVERY_CODE_COUNT = 10
_RECOVERY_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


class InvalidMfaEncryptionKey(ValueError):
    pass


def decode_encryption_key(value: str | None) -> bytes:
    """Decode one unpadded base64url AES-256 key with strict length."""

    if value is None:
        raise InvalidMfaEncryptionKey("Operations MFA encryption is not configured.")
    try:
        padding = "=" * (-len(value) % 4)
        key = b64decode(value + padding, altchars=b"-_", validate=True)
    except (BinasciiError, ValueError, TypeError) as error:
        raise InvalidMfaEncryptionKey("Operations MFA encryption key is invalid.") from error
    if len(key) != 32:
        raise InvalidMfaEncryptionKey("Operations MFA encryption key must decode to 32 bytes.")
    return key


def generate_totp_secret() -> str:
    return b32encode(os.urandom(20)).decode("ascii").rstrip("=")


def encrypt_totp_secret(secret: str, key: bytes, user_id: UUID) -> tuple[bytes, bytes]:
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, secret.encode("ascii"), _aad(user_id))
    return ciphertext, nonce


def decrypt_totp_secret(ciphertext: bytes, nonce: bytes, key: bytes, user_id: UUID) -> str:
    return AESGCM(key).decrypt(nonce, ciphertext, _aad(user_id)).decode("ascii")


def _aad(user_id: UUID) -> bytes:
    return f"taximobile:operations-mfa:v1:{user_id}".encode("ascii")


def totp_code(secret: str, counter: int) -> str:
    padded = secret + "=" * (-len(secret) % 8)
    key = b32decode(padded, casefold=True)
    digest = hmac.new(key, struct.pack(">Q", counter), "sha1").digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{value % (10**TOTP_DIGITS):0{TOTP_DIGITS}d}"


def verify_totp(
    secret: str,
    submitted_code: str,
    *,
    timestamp: float | None = None,
    last_accepted_counter: int | None = None,
) -> int | None:
    """Return the accepted counter, rejecting malformed, stale, and replayed codes."""

    if len(submitted_code) != TOTP_DIGITS or not submitted_code.isascii() or not submitted_code.isdigit():
        return None
    current_counter = int((timestamp if timestamp is not None else time()) // TOTP_PERIOD_SECONDS)
    for counter in range(current_counter - TOTP_ALLOWED_SKEW_STEPS, current_counter + TOTP_ALLOWED_SKEW_STEPS + 1):
        if counter < 0 or (last_accepted_counter is not None and counter <= last_accepted_counter):
            continue
        if hmac.compare_digest(totp_code(secret, counter), submitted_code):
            return counter
    return None


def generate_recovery_codes() -> list[str]:
    return [_generate_recovery_code() for _ in range(RECOVERY_CODE_COUNT)]


def _generate_recovery_code() -> str:
    raw = "".join(choice(_RECOVERY_ALPHABET) for _ in range(20))
    return "-".join(raw[index : index + 5] for index in range(0, 20, 5))


def normalize_recovery_code(value: str) -> str:
    return value.strip().upper().replace("-", "")


def recovery_code_hash(value: str) -> str:
    normalized = normalize_recovery_code(value)
    if len(normalized) != 20 or any(character not in _RECOVERY_ALPHABET for character in normalized):
        # Invalid input still receives a deterministic digest so callers can use
        # the same indexed lookup path without ever aliasing a valid code.
        normalized = f"INVALID:{value}"
    return sha256(normalized.encode("utf-8")).hexdigest()


def provisioning_uri(secret: str, account_label: str) -> str:
    issuer = "TaxiMobile Operations"
    return (
        f"otpauth://totp/{quote(issuer, safe='')}:{quote(account_label, safe='')}"
        f"?secret={secret}&issuer={quote(issuer, safe='')}&algorithm=SHA1"
        f"&digits={TOTP_DIGITS}&period={TOTP_PERIOD_SECONDS}"
    )
