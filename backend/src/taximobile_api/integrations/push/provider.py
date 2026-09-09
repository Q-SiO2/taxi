"""Narrow push interface used by the outbox worker."""

from datetime import datetime
from typing import Protocol


class PushProvider(Protocol):
    async def send_refresh(
        self,
        *,
        registration_id: str,
        registration_kind: str,
        event_type: str,
        resource_id: str,
        expires_at: datetime,
    ) -> None: ...

    async def aclose(self) -> None: ...
