"""Narrow push interface used by the outbox worker."""

from typing import Protocol


class PushProvider(Protocol):
    async def send_refresh(
        self,
        *,
        registration_id: str,
        registration_kind: str,
        event_type: str,
        resource_id: str,
    ) -> None: ...

    async def aclose(self) -> None: ...
