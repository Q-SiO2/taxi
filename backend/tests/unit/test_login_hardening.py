import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from taximobile_api.domains.auth.models import UserStatus
from taximobile_api.domains.auth.schemas import LoginRequest, TokenResponse
from taximobile_api.domains.auth.security import TokenService
from taximobile_api.domains.auth.service import InvalidCredentials, login


def request(password: str = "submitted-password") -> LoginRequest:
    return LoginRequest(identifier="person@example.test", password=password)


def test_missing_account_still_uses_the_constant_work_password_path() -> None:
    database_session = SimpleNamespace(scalar=AsyncMock(return_value=None))

    with patch(
        "taximobile_api.domains.auth.service.verify_login_password",
        return_value=False,
    ) as verify:
        with pytest.raises(InvalidCredentials):
            asyncio.run(login(database_session, request(), TokenService("a" * 32)))

    verify.assert_called_once_with("submitted-password", None)


def test_suspended_account_verifies_its_hash_before_generic_rejection() -> None:
    user = SimpleNamespace(
        id=uuid4(),
        status=UserStatus.SUSPENDED,
        password_hash="stored-argon2-hash",
    )
    database_session = SimpleNamespace(scalar=AsyncMock(return_value=user))

    with patch(
        "taximobile_api.domains.auth.service.verify_login_password",
        return_value=True,
    ) as verify:
        with pytest.raises(InvalidCredentials):
            asyncio.run(login(database_session, request(), TokenService("a" * 32)))

    verify.assert_called_once_with("submitted-password", "stored-argon2-hash")


def test_successful_login_upgrades_outdated_argon2_hash() -> None:
    user = SimpleNamespace(
        id=uuid4(),
        status=UserStatus.ACTIVE,
        password_hash="older-valid-argon2-hash",
        last_login_at=None,
    )
    database_session = SimpleNamespace(scalar=AsyncMock(return_value=user))
    expected = TokenResponse(access_token="access", refresh_token="refresh", expires_in=900)

    with (
        patch("taximobile_api.domains.auth.service.verify_login_password", return_value=True),
        patch("taximobile_api.domains.auth.service.password_hash_needs_rehash", return_value=True),
        patch("taximobile_api.domains.auth.service.hash_password", return_value="upgraded-hash") as rehash,
        patch(
            "taximobile_api.domains.auth.service._create_session_tokens",
            new=AsyncMock(return_value=expected),
        ) as create_tokens,
    ):
        actual = asyncio.run(login(database_session, request(), TokenService("a" * 32)))

    assert actual is expected
    assert user.password_hash == "upgraded-hash"
    assert user.last_login_at is not None
    rehash.assert_called_once_with("submitted-password")
    create_tokens.assert_awaited_once()
