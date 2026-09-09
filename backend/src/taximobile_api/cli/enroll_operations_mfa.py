"""Guarded trusted-terminal enrollment for an operations TOTP factor."""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from getpass import getpass
import sys
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from taximobile_api.core.config import ConfigurationError, Settings
from taximobile_api.db.session import create_session_factory
from taximobile_api.domains.administration.models import (
    AdministrativeGrant,
    OperationsMfaCredential,
    OperationsMfaRecoveryCode,
    OperationsSession,
)
from taximobile_api.domains.administration.operations_mfa import (
    decode_encryption_key,
    encrypt_totp_secret,
    generate_recovery_codes,
    generate_totp_secret,
    provisioning_uri,
    recovery_code_hash,
    verify_totp,
)
from taximobile_api.domains.administration.service import audit
from taximobile_api.domains.auth.models import User, UserStatus
from taximobile_api.domains.auth.schemas import normalized_login_identifier


class MfaEnrollmentConflict(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class EnrollmentTarget:
    user_id: UUID
    email: str
    existing_credential_id: UUID | None


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        description="Enroll one existing scoped operations account in authenticator-app MFA.",
    )
    command.add_argument("--email", required=True)
    command.add_argument(
        "--confirm-enrollment",
        action="store_true",
        help="Confirm that this trusted terminal is authorized to provision this factor.",
    )
    command.add_argument(
        "--replace-existing",
        action="store_true",
        help=(
            "Replace an existing factor after the platform security owner has "
            "completed the documented account-recovery verification."
        ),
    )
    return command


async def preflight(
    settings: Settings,
    email: str,
    *,
    replace_existing: bool,
) -> EnrollmentTarget:
    sessions = create_session_factory(settings)
    normalized = normalized_login_identifier(email)
    if "@" not in normalized:
        raise MfaEnrollmentConflict("A valid operations account email is required.")
    async with sessions() as session:
        user = await session.scalar(select(User).where(User.email == normalized))
        if user is None or user.status != UserStatus.ACTIVE:
            raise MfaEnrollmentConflict("Active operations account not found.")
        now = datetime.now(UTC)
        grant = await session.scalar(
            select(AdministrativeGrant.id).where(
                AdministrativeGrant.user_id == user.id,
                AdministrativeGrant.revoked_at.is_(None),
                or_(AdministrativeGrant.expires_at.is_(None), AdministrativeGrant.expires_at > now),
            )
        )
        if grant is None:
            raise MfaEnrollmentConflict("The account has no active scoped operations grant.")
        existing = await session.scalar(
            select(OperationsMfaCredential.id).where(OperationsMfaCredential.user_id == user.id)
        )
        if existing is not None and not replace_existing:
            raise MfaEnrollmentConflict("The account already has an MFA credential.")
        if existing is None and replace_existing:
            raise MfaEnrollmentConflict("The account has no existing MFA credential to replace.")
        return EnrollmentTarget(
            user_id=user.id,
            email=user.email or normalized,
            existing_credential_id=existing,
        )


async def persist_enrollment(
    settings: Settings,
    target: EnrollmentTarget,
    secret: str,
    confirmation_code: str,
    recovery_codes: list[str],
) -> None:
    accepted_counter = verify_totp(secret, confirmation_code)
    if accepted_counter is None:
        raise MfaEnrollmentConflict("The authenticator confirmation code is invalid.")
    key = decode_encryption_key(settings.operations_mfa_encryption_key)
    ciphertext, nonce = encrypt_totp_secret(secret, key, target.user_id)
    now = datetime.now(UTC)
    sessions = create_session_factory(settings)
    async with sessions() as session:
        async with session.begin():
            user = await session.scalar(
                select(User).where(
                    User.id == target.user_id,
                    User.status == UserStatus.ACTIVE,
                ).with_for_update()
            )
            if user is None:
                raise MfaEnrollmentConflict("The account is no longer active.")
            existing = await session.scalar(
                select(OperationsMfaCredential)
                .where(OperationsMfaCredential.user_id == user.id)
                .with_for_update()
            )
            if target.existing_credential_id is None and existing is not None:
                raise MfaEnrollmentConflict("The account was enrolled concurrently.")
            if target.existing_credential_id is not None:
                if existing is None or existing.id != target.existing_credential_id:
                    raise MfaEnrollmentConflict("The existing MFA credential changed; restart recovery.")
                await session.delete(existing)
                await session.execute(
                    update(OperationsSession)
                    .where(
                        OperationsSession.user_id == user.id,
                        OperationsSession.revoked_at.is_(None),
                    )
                    .values(revoked_at=now)
                )
                await session.flush()
            credential = OperationsMfaCredential(
                user_id=user.id,
                encrypted_secret=ciphertext,
                secret_nonce=nonce,
                last_accepted_counter=accepted_counter,
                enabled_at=now,
                created_at=now,
                updated_at=now,
            )
            session.add(credential)
            await session.flush()
            session.add_all(
                OperationsMfaRecoveryCode(
                    credential_id=credential.id,
                    code_hash=recovery_code_hash(code),
                    created_at=now,
                )
                for code in recovery_codes
            )
            await audit(
                session,
                actor_user_id=user.id,
                action=(
                    "OPERATIONS_MFA_REPLACED"
                    if target.existing_credential_id is not None
                    else "OPERATIONS_MFA_ENROLLED"
                ),
                resource_type="operations_mfa_credential",
                resource_id=credential.id,
                changes={
                    "method": "TOTP",
                    "recovery_code_count": len(recovery_codes),
                    "replaced_existing": target.existing_credential_id is not None,
                    "all_operations_sessions_revoked": target.existing_credential_id is not None,
                },
            )


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if not arguments.confirm_enrollment:
        print("Refusing MFA enrollment without --confirm-enrollment.", file=sys.stderr)
        return 2
    try:
        settings = Settings.from_environment()
        decode_encryption_key(settings.operations_mfa_encryption_key)
        target = asyncio.run(
            preflight(
                settings,
                arguments.email,
                replace_existing=arguments.replace_existing,
            )
        )
    except (ConfigurationError, MfaEnrollmentConflict, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    except SQLAlchemyError:
        print("MFA enrollment preflight failed. Verify database configuration and migrations.", file=sys.stderr)
        return 1

    secret = generate_totp_secret()
    recovery_codes = generate_recovery_codes()
    if target.existing_credential_id is not None:
        print("Replacing the existing MFA factor will revoke every operations session.")
    print("Add this account to a standards-compatible authenticator app.")
    print("Provisioning URI (contains the MFA seed; do not record or share it):")
    print(provisioning_uri(secret, target.email))
    try:
        confirmation_code = getpass("Current six-digit authenticator code: ")
    except (EOFError, KeyboardInterrupt):
        print("MFA enrollment cancelled; nothing was stored.", file=sys.stderr)
        return 130

    try:
        asyncio.run(
            persist_enrollment(
                settings,
                target,
                secret,
                confirmation_code,
                recovery_codes,
            )
        )
    except (MfaEnrollmentConflict, IntegrityError) as error:
        print(f"MFA enrollment refused: {error}", file=sys.stderr)
        return 2
    except SQLAlchemyError:
        print("MFA enrollment failed. No recovery code should be treated as active.", file=sys.stderr)
        return 1

    print("MFA enrollment complete. Store these single-use recovery codes offline now:")
    for code in recovery_codes:
        print(code)
    print("They cannot be displayed again.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
