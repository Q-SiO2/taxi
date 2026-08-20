import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from taximobile_api.domains.auth.router import register
from taximobile_api.domains.auth.schemas import RegisterRequest


class Transaction:
    async def __aenter__(self):
        return None

    async def __aexit__(self, *_):
        return False


class Session:
    def begin(self) -> Transaction:
        return Transaction()


def test_database_registration_race_returns_safe_conflict() -> None:
    limiter = SimpleNamespace(allow=AsyncMock(return_value=True))
    request = SimpleNamespace(
        client=SimpleNamespace(host="127.0.0.1"),
        app=SimpleNamespace(
            state=SimpleNamespace(
                rate_limiter=limiter,
                settings=SimpleNamespace(registration_rate_limit_per_minute=5),
            )
        ),
    )
    payload = RegisterRequest(
        email="passenger@example.ma",
        password="a-long-passenger-password",
        display_name="Passenger",
    )
    private_database_error = IntegrityError(
        "insert user",
        {"email": payload.email},
        RuntimeError("users_email_key private database detail"),
    )

    with patch(
        "taximobile_api.domains.auth.router.register_passenger",
        new=AsyncMock(side_effect=private_database_error),
    ), pytest.raises(HTTPException) as captured:
        asyncio.run(register(payload, request, Session()))

    assert captured.value.status_code == 409
    assert captured.value.detail == "An account already exists for those details."
    assert "passenger@example.ma" not in captured.value.detail
    assert "users_email_key" not in captured.value.detail
