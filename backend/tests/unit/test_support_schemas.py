import asyncio

import pytest
from pydantic import ValidationError
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from taximobile_api.domains.support.models import SupportCategory
from taximobile_api.domains.support.schemas import SupportTicketCreateRequest
from taximobile_api.domains.support.router import user_can_reference_ride


def test_support_ticket_accepts_the_documented_ride_problem_shape() -> None:
    request = SupportTicketCreateRequest(
        category=SupportCategory.RIDE_PROBLEM,
        subject="Problem with ride",
        description="The pickup marker was incorrect.",
    )

    assert request.category == SupportCategory.RIDE_PROBLEM


def test_support_ticket_rejects_empty_or_unexpected_content() -> None:
    with pytest.raises(ValidationError):
        SupportTicketCreateRequest(category=SupportCategory.OTHER, subject="", description="x")
    with pytest.raises(ValidationError):
        SupportTicketCreateRequest(category=SupportCategory.OTHER, subject="Help", description="x", priority="HIGH")


def test_ride_references_require_participant_ownership() -> None:
    passenger_id = uuid4()
    other_user_id = uuid4()
    ride_id = uuid4()
    session = AsyncMock()
    session.get.return_value = SimpleNamespace(passenger_id=passenger_id, driver_id=None)
    session.scalar.return_value = None

    assert asyncio.run(user_can_reference_ride(session, passenger_id, ride_id))
    assert not asyncio.run(user_can_reference_ride(session, other_user_id, ride_id))
