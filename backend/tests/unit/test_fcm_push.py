import asyncio
import json

import httpx
import pytest

from taximobile_api.integrations.push.fcm import (
    FCM_ERROR_DETAIL_TYPE,
    FcmPushProvider,
    InvalidPushRegistration,
    PushDeliveryUnavailable,
)


class FakeAccessTokenProvider:
    def __init__(self) -> None:
        self.calls: list[bool] = []

    async def access_token(self, *, force_refresh: bool = False) -> str:
        self.calls.append(force_refresh)
        return "refreshed-token" if force_refresh else "initial-token"


def test_fcm_sends_only_minimized_cross_platform_refresh_data() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["Authorization"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"name": "projects/project/messages/message"})

    tokens = FakeAccessTokenProvider()
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = FcmPushProvider("taximobile-staging", tokens, client=client)

    asyncio.run(
        provider.send_refresh(
            registration_id="firebase-installation-id",
            registration_kind="FIREBASE_INSTALLATION_ID",
            event_type="DRIVER_ASSIGNED",
            resource_id="ride-id",
        )
    )
    asyncio.run(client.aclose())

    message = captured["payload"]["message"]
    assert captured["url"].endswith("/v1/projects/taximobile-staging/messages:send")
    assert captured["authorization"] == "Bearer initial-token"
    assert message["fid"] == "firebase-installation-id"
    assert message["data"] == {"type": "DRIVER_ASSIGNED", "resource_id": "ride-id"}
    assert message["android"] == {"priority": "HIGH"}
    assert message["apns"]["headers"] == {"apns-priority": "5", "apns-push-type": "background"}
    assert message["apns"]["payload"] == {"aps": {"content-available": 1}}
    assert set(message) == {"fid", "data", "android", "apns"}
    assert tokens.calls == [False]


def test_fcm_refreshes_authorization_once_after_unauthorized_response() -> None:
    authorizations: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        authorizations.append(request.headers["Authorization"])
        if len(authorizations) == 1:
            return httpx.Response(401, json={"error": {"status": "UNAUTHENTICATED"}})
        return httpx.Response(200, json={"name": "message"})

    tokens = FakeAccessTokenProvider()
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = FcmPushProvider("taximobile-staging", tokens, client=client)

    asyncio.run(
        provider.send_refresh(
            registration_id="fid",
            registration_kind="FIREBASE_INSTALLATION_ID",
            event_type="RIDE_OFFER_AVAILABLE",
            resource_id="ride",
        )
    )
    asyncio.run(client.aclose())

    assert tokens.calls == [False, True]
    assert authorizations == ["Bearer initial-token", "Bearer refreshed-token"]


def test_fcm_distinguishes_invalid_registration_from_retryable_failure() -> None:
    invalid_token_response = httpx.Response(
        404,
        json={
            "error": {
                "status": "NOT_FOUND",
                "details": [
                    {"@type": FCM_ERROR_DETAIL_TYPE, "errorCode": "UNREGISTERED"}
                ],
            }
        },
    )
    responses = iter([invalid_token_response, httpx.Response(503, json={"error": {"status": "UNAVAILABLE"}})])
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: next(responses)))
    provider = FcmPushProvider("taximobile-staging", FakeAccessTokenProvider(), client=client)

    with pytest.raises(InvalidPushRegistration):
        asyncio.run(
            provider.send_refresh(
                registration_id="old",
                registration_kind="LEGACY_FCM_TOKEN",
                event_type="DRIVER_ASSIGNED",
                resource_id="ride",
            )
        )
    with pytest.raises(PushDeliveryUnavailable):
        asyncio.run(
            provider.send_refresh(
                registration_id="current",
                registration_kind="FIREBASE_INSTALLATION_ID",
                event_type="DRIVER_ASSIGNED",
                resource_id="ride",
            )
        )
    asyncio.run(client.aclose())


def test_fcm_preserves_legacy_token_targeting_during_fid_migration() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content)["message"])
        return httpx.Response(200, json={"name": "message"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = FcmPushProvider("taximobile-staging", FakeAccessTokenProvider(), client=client)

    asyncio.run(
        provider.send_refresh(
            registration_id="legacy-token",
            registration_kind="LEGACY_FCM_TOKEN",
            event_type="DRIVER_ASSIGNED",
            resource_id="ride",
        )
    )
    asyncio.run(client.aclose())

    assert captured["token"] == "legacy-token"
    assert "fid" not in captured


def test_fcm_revokes_a_not_found_firebase_installation_id() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(404, json={"error": {"status": "NOT_FOUND"}})
        )
    )
    provider = FcmPushProvider("taximobile-staging", FakeAccessTokenProvider(), client=client)

    with pytest.raises(InvalidPushRegistration):
        asyncio.run(
            provider.send_refresh(
                registration_id="missing-fid",
                registration_kind="FIREBASE_INSTALLATION_ID",
                event_type="DRIVER_ASSIGNED",
                resource_id="ride",
            )
        )
    asyncio.run(client.aclose())
