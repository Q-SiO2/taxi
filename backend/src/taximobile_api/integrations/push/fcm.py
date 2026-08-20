"""Firebase Cloud Messaging HTTP v1 data-message adapter.

Messages deliberately contain only a refresh event type and resource ID. They
never duplicate private notification text, location, identity, fare, or payment
data. The receiving app must authenticate and reload the referenced resource.
"""

from __future__ import annotations

import asyncio
from typing import Any, Protocol
from urllib.parse import quote

import httpx


FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
FCM_ERROR_DETAIL_TYPE = "type.googleapis.com/google.firebase.fcm.v1.FcmError"


class PushDeliveryUnavailable(RuntimeError):
    """A retryable FCM authentication, transport, or service failure."""


class InvalidPushRegistration(RuntimeError):
    """FCM has definitively rejected a token or installation ID."""


class AccessTokenProvider(Protocol):
    async def access_token(self, *, force_refresh: bool = False) -> str: ...


class GoogleAdcAccessTokenProvider:
    """Load Google application-default credentials only when FCM is enabled."""

    def __init__(self) -> None:
        self._credentials: Any | None = None
        self._request: Any | None = None
        self._lock = asyncio.Lock()

    async def access_token(self, *, force_refresh: bool = False) -> str:
        async with self._lock:
            try:
                return await asyncio.to_thread(self._access_token_sync, force_refresh)
            except Exception as error:
                raise PushDeliveryUnavailable("FCM authorization is unavailable.") from error

    def _access_token_sync(self, force_refresh: bool) -> str:
        if self._credentials is None:
            import google.auth
            from google.auth.transport.requests import Request

            self._credentials, _ = google.auth.default(scopes=[FCM_SCOPE])
            self._request = Request()
        if force_refresh or not self._credentials.valid:
            self._credentials.refresh(self._request)
        token = self._credentials.token
        if not isinstance(token, str) or not token:
            raise ValueError("Google credentials returned no access token.")
        return token


class FcmPushProvider:
    """Send minimized background refresh hints through FCM HTTP v1."""

    def __init__(
        self,
        project_id: str,
        token_provider: AccessTokenProvider,
        *,
        timeout_seconds: float = 5,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._token_provider = token_provider
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout_seconds)
        encoded_project_id = quote(project_id, safe="")
        self._endpoint = f"https://fcm.googleapis.com/v1/projects/{encoded_project_id}/messages:send"

    async def send_refresh(
        self,
        *,
        registration_id: str,
        registration_kind: str,
        event_type: str,
        resource_id: str,
    ) -> None:
        access_token = await self._token_provider.access_token()
        response = await self._send(
            access_token,
            registration_id,
            registration_kind,
            event_type,
            resource_id,
        )
        if response.status_code == 401:
            access_token = await self._token_provider.access_token(force_refresh=True)
            response = await self._send(
                access_token,
                registration_id,
                registration_kind,
                event_type,
                resource_id,
            )
        if response.is_success:
            return
        if _is_invalid_registration_response(response, registration_kind):
            raise InvalidPushRegistration("FCM rejected the device registration.")
        raise PushDeliveryUnavailable("FCM delivery is temporarily unavailable.")

    async def _send(
        self,
        access_token: str,
        registration_id: str,
        registration_kind: str,
        event_type: str,
        resource_id: str,
    ) -> httpx.Response:
        try:
            target_field = (
                "fid"
                if registration_kind == "FIREBASE_INSTALLATION_ID"
                else "token"
            )
            message = {
                target_field: registration_id,
                "data": {"type": event_type, "resource_id": resource_id},
                "android": {"priority": "HIGH"},
                "apns": {
                    "headers": {"apns-priority": "5", "apns-push-type": "background"},
                    "payload": {"aps": {"content-available": 1}},
                },
            }
            return await self._client.post(
                self._endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
                json={"message": message},
            )
        except httpx.HTTPError as error:
            raise PushDeliveryUnavailable("FCM delivery is temporarily unavailable.") from error

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()


def _is_invalid_registration_response(response: httpx.Response, registration_kind: str) -> bool:
    try:
        error = response.json()["error"]
        details = error.get("details", [])
    except (ValueError, TypeError, KeyError):
        return False
    if (
        registration_kind == "FIREBASE_INSTALLATION_ID"
        and response.status_code == 404
        and error.get("status") == "NOT_FOUND"
    ):
        return True
    for detail in details:
        if not isinstance(detail, dict) or detail.get("@type") != FCM_ERROR_DETAIL_TYPE:
            continue
        if detail.get("errorCode") in {"UNREGISTERED", "INVALID_ARGUMENT", "SENDER_ID_MISMATCH"}:
            return True
    return False
