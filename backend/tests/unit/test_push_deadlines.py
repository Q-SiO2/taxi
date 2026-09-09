"""Deterministic deadline and partial-device-failure contract tests."""

import asyncio
from datetime import UTC, datetime, timedelta
import json
from uuid import uuid4

import httpx
import pytest

from taximobile_api.domains.notifications.models import DeviceRegistrationKind, DeviceToken
from taximobile_api.domains.outbox.processor import ClaimedOutboxEvent
from taximobile_api.integrations.push.fcm import FcmPushProvider, InvalidPushRegistration
from taximobile_api.workers.outbox import (
    NotificationTransportUnavailable,
    WebSocketOutboxDelivery,
)


@pytest.mark.parametrize("remaining", [-10, 0, 0.9, 1, 17.9, 9000])
def test_provider_deadline_bounds_queue_and_suppresses_expired_hints(monkeypatch, remaining):
    clock = 1800000000.0
    monkeypatch.setattr("taximobile_api.integrations.push.fcm.time", lambda: clock)
    messages = []
    token_calls = []

    class Tokens:
        async def access_token(self, **_kwargs):
            token_calls.append(True)
            return "test-token"

    def respond(request):
        messages.append(json.loads(request.content)["message"])
        return httpx.Response(200, json={"name": "message"})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            provider = FcmPushProvider("test-project", Tokens(), client=client)
            await provider.send_refresh(
                registration_id="test-fid", registration_kind="FIREBASE_INSTALLATION_ID",
                event_type="DRIVER_ASSIGNED", resource_id=str(uuid4()),
                expires_at=datetime.fromtimestamp(clock + remaining, UTC),
            )

    asyncio.run(run())
    if remaining < 1:
        assert messages == []
        assert token_calls == []
    else:
        assert len(messages) == 1
        bounded = min(remaining, 900)
        assert messages[0]["android"]["ttl"] == f"{int(bounded)}s"
        assert messages[0]["apns"]["headers"]["apns-expiration"] == str(int(clock + bounded))
        assert set(messages[0]["data"]) == {"type", "resource_id"}


@pytest.mark.parametrize("elapsed_during_auth", [3, 21])
def test_authentication_latency_cannot_extend_source_deadline(monkeypatch, elapsed_during_auth):
    clock = [1800000000.0]
    monkeypatch.setattr("taximobile_api.integrations.push.fcm.time", lambda: clock[0])
    messages = []

    class Tokens:
        async def access_token(self, **_kwargs):
            clock[0] += elapsed_during_auth
            return "test-token"

    def respond(request):
        messages.append(json.loads(request.content)["message"])
        return httpx.Response(200)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            await FcmPushProvider("test", Tokens(), client=client).send_refresh(
                registration_id="fid", registration_kind="FIREBASE_INSTALLATION_ID",
                event_type="DRIVER_ASSIGNED", resource_id=str(uuid4()),
                expires_at=datetime.fromtimestamp(1800000020, UTC),
            )

    asyncio.run(run())
    if elapsed_during_auth >= 20:
        assert messages == []
    else:
        assert messages[0]["android"]["ttl"] == "17s"
        assert messages[0]["apns"]["headers"]["apns-expiration"] == "1800000020"


@pytest.mark.parametrize("refresh_latency", [4, 30])
def test_401_retry_keeps_original_deadline(monkeypatch, refresh_latency):
    clock = [1800000000.0]
    monkeypatch.setattr("taximobile_api.integrations.push.fcm.time", lambda: clock[0])
    messages = []

    class Tokens:
        async def access_token(self, *, force_refresh=False):
            if force_refresh:
                clock[0] += refresh_latency
            return "test-token"

    def respond(request):
        messages.append(json.loads(request.content)["message"])
        return httpx.Response(401 if len(messages) == 1 else 200)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            await FcmPushProvider("test", Tokens(), client=client).send_refresh(
                registration_id="fid", registration_kind="FIREBASE_INSTALLATION_ID",
                event_type="DRIVER_ASSIGNED", resource_id=str(uuid4()),
                expires_at=datetime.fromtimestamp(1800000020, UTC),
            )

    asyncio.run(run())
    assert messages[0]["android"]["ttl"] == "20s"
    if refresh_latency >= 20:
        assert len(messages) == 1
    else:
        assert messages[1]["android"]["ttl"] == "16s"
        assert messages[1]["apns"]["headers"]["apns-expiration"] == "1800000020"


def test_naive_provider_deadline_fails_before_credentials():
    class Tokens:
        async def access_token(self, **_kwargs):
            raise AssertionError("Naive expiry must fail before credentials.")

    async def run():
        provider = FcmPushProvider("test", Tokens())
        try:
            with pytest.raises(ValueError, match="timezone-aware"):
                await provider.send_refresh(
                    registration_id="fid", registration_kind="FIREBASE_INSTALLATION_ID",
                    event_type="DRIVER_ASSIGNED", resource_id=str(uuid4()),
                    expires_at=datetime(2030, 1, 1),
                )
        finally:
            await provider.aclose()

    asyncio.run(run())


@pytest.mark.parametrize("source_remaining", [None, 10, -1])
def test_worker_carries_minimum_source_and_policy_deadline(source_remaining):
    now = datetime.now(UTC)
    event = ClaimedOutboxEvent(uuid4(), "ride.offer.created", {}, now - timedelta(seconds=240))
    calls = []

    class Publisher:
        async def publish_ride_refresh(self, *_args):
            calls.append("live")

    class Delivery(WebSocketOutboxDelivery):
        async def _push_refresh(self, _user, _resource, _type, expires_at):
            calls.append(expires_at)

    source_expiry = now + timedelta(seconds=source_remaining) if source_remaining is not None else None
    delivery = Delivery(lambda: None, Publisher())
    asyncio.run(delivery._publish_refresh(
        uuid4(), uuid4(), "RIDE_OFFER_AVAILABLE", event, source_expires_at=source_expiry,
    ))
    if source_remaining == -1:
        assert calls == []
    else:
        assert calls == ["live", source_expiry or now + timedelta(seconds=60)]


@pytest.mark.parametrize("failure", ["transient", "invalid", "revoke-failed", "cancelled"])
def test_bad_registration_does_not_starve_later_devices(failure):
    user_id = uuid4()
    devices = [
        DeviceToken(id=uuid4(), user_id=user_id, token=token,
                    registration_kind=DeviceRegistrationKind.FIREBASE_INSTALLATION_ID)
        for token in ("first", "second")
    ]
    calls = []
    revoked = []
    expiry = datetime.now(UTC) + timedelta(seconds=20)

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def scalars(self, _statement):
            return devices

    class Push:
        async def send_refresh(self, **payload):
            calls.append(payload["registration_id"])
            assert payload["expires_at"] == expiry
            if payload["registration_id"] == "first":
                if failure == "transient":
                    raise RuntimeError("Private provider response")
                if failure == "cancelled":
                    raise asyncio.CancelledError()
                raise InvalidPushRegistration("Invalid")

    class Delivery(WebSocketOutboxDelivery):
        async def _revoke_device(self, device_id):
            revoked.append(device_id)
            if failure == "revoke-failed":
                raise RuntimeError("Database unavailable")

    delivery = Delivery(lambda: Session(), object(), Push())
    async def run():
        await delivery._push_refresh(user_id, uuid4(), "DRIVER_ASSIGNED", expiry)

    if failure in {"transient", "revoke-failed"}:
        with pytest.raises(NotificationTransportUnavailable):
            asyncio.run(run())
    elif failure == "cancelled":
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(run())
    else:
        asyncio.run(run())
    assert calls == (["first"] if failure == "cancelled" else ["first", "second"])
    assert revoked == ([devices[0].id] if failure in {"invalid", "revoke-failed"} else [])
