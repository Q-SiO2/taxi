import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from taximobile_api.domains.auth.bootstrap import (
    AdministratorAccountConflict,
    InitialAdministratorExists,
    bootstrap_initial_administrator,
)
from taximobile_api.domains.auth.models import Role, User, UserRole


def test_bootstrap_creates_only_an_admin_role() -> None:
    session = AsyncMock()
    session.scalar = AsyncMock(side_effect=[None, None])
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()

    with patch("taximobile_api.domains.auth.bootstrap.hash_password", return_value="safe-password-hash"):
        result = asyncio.run(
            bootstrap_initial_administrator(
                session,
                email="  ADMIN@Example.COM ",
                password="a-long-initial-admin-password",
            )
        )

    added = [call.args[0] for call in session.add.call_args_list]
    user = next(record for record in added if isinstance(record, User))
    role = next(record for record in added if isinstance(record, UserRole))
    assert result.created is True
    assert result.email == "admin@example.com"
    assert user.email == "admin@example.com"
    assert user.password_hash == "safe-password-hash"
    assert role.user_id == user.id
    assert role.role == Role.ADMIN
    session.execute.assert_awaited_once()
    session.flush.assert_awaited_once()


def test_bootstrap_is_idempotent_for_same_existing_admin() -> None:
    administrator = User(id=uuid4(), email="admin@example.com", password_hash="existing")
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=administrator)
    session.add = MagicMock()

    result = asyncio.run(
        bootstrap_initial_administrator(
            session,
            email="admin@example.com",
            password="a-long-unused-password",
        )
    )

    assert result.created is False
    assert result.user_id == administrator.id
    session.add.assert_not_called()


def test_bootstrap_refuses_a_second_administrator() -> None:
    administrator = User(id=uuid4(), email="first@example.com", password_hash="existing")
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=administrator)
    session.add = MagicMock()

    with pytest.raises(InitialAdministratorExists):
        asyncio.run(
            bootstrap_initial_administrator(
                session,
                email="second@example.com",
                password="a-long-unused-password",
            )
        )

    session.add.assert_not_called()


def test_bootstrap_never_promotes_an_existing_ordinary_account() -> None:
    session = AsyncMock()
    session.scalar = AsyncMock(side_effect=[None, uuid4()])
    session.add = MagicMock()

    with pytest.raises(AdministratorAccountConflict):
        asyncio.run(
            bootstrap_initial_administrator(
                session,
                email="passenger@example.com",
                password="a-long-unused-password",
            )
        )

    session.add.assert_not_called()
