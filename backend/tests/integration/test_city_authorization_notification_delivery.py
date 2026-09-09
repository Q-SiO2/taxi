"""Durable authorization-notice recovery across outbox processor lifetimes."""

import asyncio
from datetime import UTC, datetime, timedelta
from os import environ
from pathlib import Path
import subprocess
import sys

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from scheduled_handoff_fixtures import prepare_handoff_fixture
from test_city_authorization_lifecycle import authorization_for, command
from test_mvp_lifecycle import require_integration_settings
from taximobile_api.core.live_events import LiveEventPublisher
from taximobile_api.domains.notifications.models import (
    DevicePlatform, DeviceRegistrationKind, DeviceToken, Notification,
)
from taximobile_api.domains.outbox.models import OutboxEvent
from taximobile_api.domains.outbox.metrics import collect_outbox_metrics
from taximobile_api.domains.outbox.processor import OutboxProcessor
from taximobile_api.workers.outbox import WebSocketOutboxDelivery


pytestmark = pytest.mark.integration
BACKEND = Path(__file__).resolve().parents[2]
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


CHILD_WORKER = r'''\
import asyncio
import json
import os
import sys
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from taximobile_api.core.live_events import LiveEventPublisher
from taximobile_api.domains.outbox.processor import OutboxProcessor
from taximobile_api.workers.outbox import WebSocketOutboxDelivery

class NoDelivery:
    async def deliver(self, _event):
        raise AssertionError("Claim-only process must not deliver")

class NoLive(LiveEventPublisher):
    async def publish_ride_refresh(self, *_args):
        raise AssertionError("Authorization refresh must not use ride live events")

class Push:
    async def send_refresh(self, **payload):
        safe = {key: str(value) for key, value in payload.items()}
        print("PUSH:" + json.dumps(safe, sort_keys=True), flush=True)

async def main():
    engine = create_async_engine(os.environ["TAXIMOBILE_DATABASE_URL"])
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        if sys.argv[1] == "claim":
            processor = OutboxProcessor(
                sessions, NoDelivery(), worker_id="terminated-authorization-worker"
            )
            events = await processor._claim_due_events()
            print("CLAIMED:" + str(len(events)), flush=True)
            await asyncio.Event().wait()
        else:
            processor = OutboxProcessor(
                sessions,
                WebSocketOutboxDelivery(sessions, NoLive(), Push()),
                worker_id="replacement-authorization-worker",
                lease_seconds=0,
            )
            print("PROCESSED:" + str(await processor.process_once()), flush=True)
    finally:
        await engine.dispose()

asyncio.run(main())
'''


class NoRideLiveEvents(LiveEventPublisher):
    async def publish_ride_refresh(self, *_args):
        raise AssertionError("City-authorization updates are push-only refresh hints.")


class RecordingPush:
    def __init__(self, *, fail=False):
        self.fail = fail
        self.calls = []

    async def send_refresh(self, **payload):
        self.calls.append(payload)
        if self.fail:
            raise RuntimeError("synthetic private provider failure")


async def start_child(mode):
    return await asyncio.create_subprocess_exec(
        sys.executable, "-c", CHILD_WORKER, mode,
        cwd=BACKEND, env=dict(environ),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        creationflags=NO_WINDOW,
    )


def test_authorization_notice_survives_provider_failure_and_processor_restart():
    async def prove():
        engine = create_async_engine(require_integration_settings().database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            ready = await prepare_handoff_fixture(sessions)
            async with sessions.begin() as session:
                # The handoff fixture has unrelated scheduled events. Retire
                # them so each processor claim below is exact and reviewable.
                await session.execute(update(OutboxEvent).values(delivered_at=datetime.now(UTC)))
                session.add(DeviceToken(
                    user_id=ready.user_id,
                    platform=DevicePlatform.ANDROID,
                    registration_kind=DeviceRegistrationKind.FIREBASE_INSTALLATION_ID,
                    token="synthetic-authorization-installation",
                    last_seen_at=datetime.now(UTC),
                ))
                await command(session, ready, "SUSPEND")
                authorization = await authorization_for(session, ready)
                authorization_id = authorization.id

            failing_push = RecordingPush(fail=True)
            first = OutboxProcessor(
                sessions,
                WebSocketOutboxDelivery(sessions, NoRideLiveEvents(), failing_push),
                worker_id="authorization-failing-worker",
            )
            assert await first.process_once() == 1
            assert len(failing_push.calls) == 1
            assert set(failing_push.calls[0]) == {
                "registration_id", "registration_kind", "event_type", "resource_id", "expires_at",
            }
            assert failing_push.calls[0]["event_type"] == "DRIVER_CITY_AUTHORIZATION_CHANGED"
            assert failing_push.calls[0]["resource_id"] == str(authorization_id)

            async with sessions.begin() as session:
                event = await session.scalar(select(OutboxEvent).where(
                    OutboxEvent.topic == "driver.city_authorization.changed",
                ))
                assert event.attempts == 1 and event.delivered_at is None
                assert event.dead_lettered_at is None and event.last_error == "DELIVERY_RETRY"
                assert event.locked_at is None and event.locked_by is None
                assert set(event.payload) == {"authorization_id"}
                event.available_at = datetime.now(UTC) - timedelta(seconds=1)

            failed_snapshot = await collect_outbox_metrics(sessions)
            failed_by_owner = {item.owner: item for item in failed_snapshot.owners}
            assert failed_snapshot.pending_events == 1
            assert failed_snapshot.dead_letter_events == 0
            assert failed_by_owner["driver_compliance"].pending_events == 1
            assert failed_by_owner["driver_compliance"].dead_letter_events == 0
            assert failed_by_owner["dispatch_operations"].pending_events == 0
            assert failed_by_owner["scheduling_operations"].pending_events == 0
            assert failed_by_owner["unclassified"].pending_events == 0

            succeeding_push = RecordingPush()
            restarted = OutboxProcessor(
                sessions,
                WebSocketOutboxDelivery(sessions, NoRideLiveEvents(), succeeding_push),
                worker_id="authorization-restarted-worker",
            )
            assert await restarted.process_once() == 1
            assert len(succeeding_push.calls) == 1
            assert succeeding_push.calls[0]["resource_id"] == str(authorization_id)

            async with sessions() as session:
                event = await session.scalar(select(OutboxEvent).where(
                    OutboxEvent.topic == "driver.city_authorization.changed",
                ))
                assert event.attempts == 2 and event.delivered_at is not None
                assert event.dead_lettered_at is None and event.last_error is None
                assert event.locked_at is None and event.locked_by is None
                assert await session.scalar(select(func.count(Notification.id)).where(
                    Notification.user_id == ready.user_id,
                    Notification.type == "DRIVER_CITY_AUTHORIZATION_CHANGED",
                )) == 1

            delivered_snapshot = await collect_outbox_metrics(sessions)
            delivered_by_owner = {item.owner: item for item in delivered_snapshot.owners}
            assert delivered_snapshot.pending_events == 0
            assert delivered_snapshot.dead_letter_events == 0
            assert delivered_by_owner["driver_compliance"].pending_events == 0
        finally:
            await engine.dispose()

    asyncio.run(prove())


def test_terminated_worker_process_releases_authorization_event_for_replacement():
    async def prove():
        engine = create_async_engine(require_integration_settings().database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        child = None
        try:
            ready = await prepare_handoff_fixture(sessions)
            async with sessions.begin() as session:
                await session.execute(update(OutboxEvent).values(delivered_at=datetime.now(UTC)))
                session.add(DeviceToken(
                    user_id=ready.user_id,
                    platform=DevicePlatform.ANDROID,
                    registration_kind=DeviceRegistrationKind.FIREBASE_INSTALLATION_ID,
                    token="synthetic-process-recovery-installation",
                    last_seen_at=datetime.now(UTC),
                ))
                await command(session, ready, "SUSPEND")
                authorization_id = (await authorization_for(session, ready)).id

            child = await start_child("claim")
            signal = await asyncio.wait_for(child.stdout.readline(), 20)
            assert signal.strip() == b"CLAIMED:1"
            child.kill()
            _, child_error = await asyncio.wait_for(child.communicate(), 10)
            assert require_integration_settings().database_url.encode() not in child_error

            async with sessions() as session:
                event = await session.scalar(select(OutboxEvent).where(
                    OutboxEvent.topic == "driver.city_authorization.changed",
                ))
                assert event.attempts == 1 and event.delivered_at is None
                assert event.locked_by == "terminated-authorization-worker"
                assert event.locked_at is not None and event.last_error is None

            replacement = await start_child("recover")
            output, errors = await asyncio.wait_for(replacement.communicate(), 30)
            assert replacement.returncode == 0, errors.decode("utf-8", errors="replace")
            assert require_integration_settings().database_url.encode() not in output + errors
            lines = output.decode("utf-8").splitlines()
            assert lines[-1] == "PROCESSED:1"
            push_line = next(line for line in lines if line.startswith("PUSH:"))
            assert '"event_type": "DRIVER_CITY_AUTHORIZATION_CHANGED"' in push_line
            assert f'"resource_id": "{authorization_id}"' in push_line
            assert "user_id" not in push_line and "reason" not in push_line and "status" not in push_line

            async with sessions() as session:
                event = await session.scalar(select(OutboxEvent).where(
                    OutboxEvent.topic == "driver.city_authorization.changed",
                ))
                assert event.attempts == 2 and event.delivered_at is not None
                assert event.locked_by is None and event.locked_at is None
                assert await session.scalar(select(func.count(Notification.id)).where(
                    Notification.user_id == ready.user_id,
                    Notification.type == "DRIVER_CITY_AUTHORIZATION_CHANGED",
                )) == 1
        finally:
            if child is not None and child.returncode is None:
                child.kill()
                await child.communicate()
            await engine.dispose()

    asyncio.run(prove())
