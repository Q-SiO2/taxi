import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, patch
from uuid import uuid4

import pytest

from taximobile_api.domains.auth.models import UserStatus
from taximobile_api.domains.auth.schemas import TokenResponse
from taximobile_api.domains.auth.security import TokenService
from taximobile_api.domains.auth.service import InvalidCredentials, rotate_refresh_token


def test_refresh_rotation_marks_the_old_token_and_preserves_its_family() -> None:
    user_id = uuid4()
    refresh_family_id = uuid4()
    previous_session = SimpleNamespace(
        user_id=user_id,
        revoked_at=None,
        refresh_rotated_at=None,
        refresh_family_id=refresh_family_id,
        device_label="Android phone",
    )
    user = SimpleNamespace(id=user_id, status=UserStatus.ACTIVE)
    database_session = SimpleNamespace(
        scalar=AsyncMock(return_value=previous_session),
        get=AsyncMock(return_value=user),
        execute=AsyncMock(),
    )
    expected = TokenResponse(access_token="access", refresh_token="refresh", expires_in=900)

    with patch(
        "taximobile_api.domains.auth.service._create_session_tokens", new=AsyncMock(return_value=expected)
    ) as create_tokens:
        actual = asyncio.run(
            rotate_refresh_token(database_session, "a" * 32, TokenService("a" * 32))
        )

    assert actual is expected
    assert previous_session.revoked_at is not None
    assert previous_session.refresh_rotated_at == previous_session.revoked_at
    create_tokens.assert_awaited_once_with(
        database_session,
        user,
        ANY,
        "Android phone",
        refresh_family_id=refresh_family_id,
    )
    database_session.execute.assert_not_awaited()


def test_rotated_refresh_token_reuse_revokes_only_its_active_family() -> None:
    previous_session = SimpleNamespace(
        user_id=uuid4(),
        revoked_at=datetime.now(UTC),
        refresh_rotated_at=datetime.now(UTC),
        refresh_family_id=uuid4(),
        device_label="Android phone",
    )
    database_session = SimpleNamespace(
        scalar=AsyncMock(return_value=previous_session),
        get=AsyncMock(),
        execute=AsyncMock(),
    )

    with pytest.raises(InvalidCredentials):
        asyncio.run(rotate_refresh_token(database_session, "a" * 32, TokenService("a" * 32)))

    database_session.execute.assert_awaited_once()
    statement = database_session.execute.await_args.args[0]
    assert previous_session.refresh_family_id in statement.compile().params.values()
    database_session.get.assert_not_awaited()


def test_ordinary_revoked_refresh_token_does_not_revoke_a_session_family() -> None:
    previous_session = SimpleNamespace(
        user_id=uuid4(),
        revoked_at=datetime.now(UTC),
        refresh_rotated_at=None,
        refresh_family_id=uuid4(),
        device_label="Android phone",
    )
    database_session = SimpleNamespace(
        scalar=AsyncMock(return_value=previous_session),
        get=AsyncMock(),
        execute=AsyncMock(),
    )

    with pytest.raises(InvalidCredentials):
        asyncio.run(rotate_refresh_token(database_session, "a" * 32, TokenService("a" * 32)))

    database_session.execute.assert_not_awaited()
