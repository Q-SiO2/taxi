"""Global account status is part of driver assignment authority."""

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from taximobile_api.domains.auth.authority import (
    active_user_exists,
    lock_user_for_status_change,
    user_account_is_active,
)
from taximobile_api.domains.auth.models import UserStatus


class ScalarSession:
    def __init__(self, result):
        self.result = result
        self.statements = []

    async def scalar(self, statement):
        self.statements.append(statement)
        return self.result


def postgres_sql(statement) -> str:
    return str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (UserStatus.ACTIVE, True),
        (UserStatus.SUSPENDED, False),
        (UserStatus.DEACTIVATED, False),
        (None, False),
    ],
)
def test_account_authority_has_a_closed_active_state(status, expected):
    async def prove():
        session = ScalarSession(status)
        user_id = uuid4()
        assert await user_account_is_active(session, user_id) is expected
        sql = postgres_sql(session.statements[0])
        assert "users.id" in sql and str(user_id) in sql
        assert "FOR SHARE" not in sql

    asyncio.run(prove())


def test_assignment_authority_uses_postgresql_share_lock():
    async def prove():
        session = ScalarSession(UserStatus.ACTIVE)
        assert await user_account_is_active(
            session,
            uuid4(),
            serialize_with_status_change=True,
        )
        assert "FOR SHARE" in postgres_sql(session.statements[0])

    asyncio.run(prove())


def test_status_change_authority_uses_exclusive_refreshing_lock():
    async def prove():
        sentinel = object()
        session = ScalarSession(sentinel)
        assert await lock_user_for_status_change(session, uuid4()) is sentinel
        statement = session.statements[0]
        assert "FOR UPDATE" in postgres_sql(statement)
        assert statement.get_execution_options()["populate_existing"] is True

    asyncio.run(prove())


def test_correlated_active_predicate_has_no_open_status_fallback():
    sql = postgres_sql(active_user_exists(uuid4()).select())
    assert "EXISTS" in sql
    assert "users.status = 'ACTIVE'" in sql
