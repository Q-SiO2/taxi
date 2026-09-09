"""Minimal protected-channel adapter for overdue support/safety alerts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

import httpx


@dataclass(frozen=True, slots=True)
class CasePagerMessage:
    alert_id: UUID
    city_id: UUID
    case_type: str
    case_id: UUID
    severity: str
    response_due_at: datetime
    first_detected_at: datetime


class CasePagerDeliveryError(RuntimeError):
    """Safe delivery failure without response body, URL, or credential text."""


class CasePager(Protocol):
    async def send(self, message: CasePagerMessage) -> bool:
        """Return false only when no external pager is configured."""


class DisabledCasePager:
    async def send(self, message: CasePagerMessage) -> bool:
        del message
        return False


class HttpCasePager:
    def __init__(
        self,
        *,
        url: str,
        bearer_token: str,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._url = url
        self._bearer_token = bearer_token
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    async def send(self, message: CasePagerMessage) -> bool:
        payload = {
            "version": 1,
            "alert_id": str(message.alert_id),
            "city_id": str(message.city_id),
            "case_type": message.case_type,
            "case_id": str(message.case_id),
            "severity": message.severity,
            "response_due_at": message.response_due_at.isoformat(),
            "first_detected_at": message.first_detected_at.isoformat(),
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                follow_redirects=False,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    self._url,
                    json=payload,
                    headers={"Authorization": f"Bearer {self._bearer_token}"},
                )
                response.raise_for_status()
        except (httpx.HTTPError, ValueError) as error:
            raise CasePagerDeliveryError("Protected case pager delivery failed.") from error
        return True
