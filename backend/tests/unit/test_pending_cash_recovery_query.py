"""Query shape and fail-closed response; participant isolation has separate HTTP tests."""
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from fastapi import HTTPException
import pytest
from sqlalchemy.dialects import postgresql

from taximobile_api.domains.drivers.service import DriverMissing
from taximobile_api.domains.payments.router import pending_driver_cash_payments


@pytest.mark.asyncio
async def test_queue_is_owned_completed_pending_cash_oldest_first_with_no_passenger_data():
    driver_id, user_id = uuid4(), uuid4()
    now = datetime.now(UTC)
    payment = SimpleNamespace(id=uuid4(), ride_id=uuid4(), amount=Decimal('35.00'), currency='MAD', created_at=now)
    session = AsyncMock()
    result = Mock()
    result.all.return_value = [(payment, now)]
    session.execute.return_value = result
    session.scalar.return_value = 22
    with patch('taximobile_api.domains.payments.router.driver_for_user', AsyncMock(return_value=SimpleNamespace(id=driver_id))) as owned:
        queue = await pending_driver_cash_payments(page=2, limit=20, principal=SimpleNamespace(user_id=user_id), session=session)
    owned.assert_awaited_once_with(session, user_id)
    sql = str(session.execute.call_args.args[0].compile(dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}))
    assert str(driver_id) in sql
    for predicate in ("rides.driver_id =", "rides.status = 'COMPLETED'", "payments.method = 'CASH'", "payments.status = 'PENDING'", "ORDER BY payments.created_at ASC, payments.id ASC", "OFFSET 20"):
        assert predicate in sql
    assert queue.page == 2 and queue.total == 22
    assert set(queue.items[0].model_dump()) == {'payment_id', 'ride_id', 'amount', 'currency', 'created_at', 'completed_at', 'method', 'status'}
    assert queue.items[0].amount == Decimal('35.00')
    session.commit.assert_not_called()
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_queue_returns_empty_only_after_a_successful_server_read():
    session = AsyncMock()
    result = Mock()
    result.all.return_value = []
    session.execute.return_value = result
    session.scalar.return_value = 0
    with patch('taximobile_api.domains.payments.router.driver_for_user', AsyncMock(return_value=SimpleNamespace(id=uuid4()))):
        queue = await pending_driver_cash_payments(page=1, limit=20, principal=SimpleNamespace(user_id=uuid4()), session=session)
    assert queue.items == [] and queue.total == 0


@pytest.mark.asyncio
async def test_non_driver_is_rejected_before_querying_payments():
    session = AsyncMock()
    with patch('taximobile_api.domains.payments.router.driver_for_user', AsyncMock(side_effect=DriverMissing('Driver profile not found.'))):
        with pytest.raises(HTTPException) as failure:
            await pending_driver_cash_payments(page=1, limit=20, principal=SimpleNamespace(user_id=uuid4()), session=session)
    assert failure.value.status_code == 404
    session.execute.assert_not_called()
