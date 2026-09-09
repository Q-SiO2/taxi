import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest

from taximobile_api.domains.safety.models import SafetyReportCategory, SafetyReportStatus
from taximobile_api.domains.safety.service import create_safety_report_record
from taximobile_api.domains.support.models import SupportCategory, SupportTicketStatus
from taximobile_api.domains.support.service import create_support_ticket_record
from taximobile_api.integrations.case_pager import (
    CasePagerDeliveryError,
    CasePagerMessage,
    DisabledCasePager,
    HttpCasePager,
)
from taximobile_api.workers.case_alerts import safety_is_overdue, support_is_overdue


def pager_message() -> CasePagerMessage:
    due_at = datetime(2026, 8, 30, 12, tzinfo=UTC)
    return CasePagerMessage(
        alert_id=uuid4(),
        city_id=uuid4(),
        case_type="SUPPORT",
        case_id=uuid4(),
        severity="HIGH",
        response_due_at=due_at,
        first_detected_at=due_at + timedelta(minutes=1),
    )


@pytest.mark.asyncio
async def test_disabled_case_pager_never_claims_delivery() -> None:
    assert await DisabledCasePager().send(pager_message()) is False


@pytest.mark.asyncio
async def test_http_case_pager_sends_only_bounded_identifiers_and_timing() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers.get("Authorization")
        captured["payload"] = json.loads(request.content)
        return httpx.Response(202, request=request)

    message = pager_message()
    pager = HttpCasePager(
        url="https://pager.example.test/cases",
        bearer_token="pager-token-that-is-never-in-the-payload",
        timeout_seconds=2,
        transport=httpx.MockTransport(handler),
    )

    assert await pager.send(message) is True
    assert captured["authorization"] == "Bearer pager-token-that-is-never-in-the-payload"
    assert set(captured["payload"]) == {
        "version",
        "alert_id",
        "city_id",
        "case_type",
        "case_id",
        "severity",
        "response_due_at",
        "first_detected_at",
    }
    assert "description" not in captured["payload"]
    assert "message" not in captured["payload"]


@pytest.mark.asyncio
async def test_http_case_pager_raises_a_safe_error_without_provider_details() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="provider secret diagnostic", request=request)

    pager = HttpCasePager(
        url="https://pager.example.test/private-path",
        bearer_token="private-case-pager-token",
        timeout_seconds=2,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(CasePagerDeliveryError) as caught:
        await pager.send(pager_message())
    assert str(caught.value) == "Protected case pager delivery failed."
    assert "pager.example" not in str(caught.value)
    assert "provider secret" not in str(caught.value)
    assert "private-case-pager-token" not in str(caught.value)


def test_overdue_rules_require_an_unacknowledged_nonterminal_case() -> None:
    now = datetime(2026, 8, 30, 13, tzinfo=UTC)
    support = create_support_ticket_record(
        city_id=uuid4(),
        user_id=uuid4(),
        ride_id=None,
        category=SupportCategory.ACCOUNT_ACCESS,
        subject="Account help",
        description="Controlled description.",
        created_at=now - timedelta(hours=5),
    )
    safety = create_safety_report_record(
        city_id=uuid4(),
        ride_id=uuid4(),
        reporter_user_id=uuid4(),
        reported_user_id=uuid4(),
        category=SafetyReportCategory.UNSAFE_DRIVING,
        description="Controlled safety description.",
        created_at=now - timedelta(hours=1),
    )

    assert support_is_overdue(support, now)
    assert safety_is_overdue(safety, now)

    support.first_responded_at = now
    safety.first_acknowledged_at = now
    assert not support_is_overdue(support, now)
    assert not safety_is_overdue(safety, now)

    support.first_responded_at = None
    support.status = SupportTicketStatus.RESOLVED
    safety.first_acknowledged_at = None
    safety.status = SafetyReportStatus.CLOSED
    assert not support_is_overdue(support, now)
    assert not safety_is_overdue(safety, now)
