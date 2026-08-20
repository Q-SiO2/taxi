from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from taximobile_api.core.config import Settings
from taximobile_api.domains.drivers.models import (
    CredentialVerificationStatus,
    DriverCredential,
    DriverProfile,
)
from taximobile_api.domains.notifications.models import Notification
from taximobile_api.domains.outbox.models import OutboxEvent
from taximobile_api.workers.credentials import CredentialLifecycleProcessor


class CredentialSession:
    def __init__(self, credential: DriverCredential, profile: DriverProfile) -> None:
        self.credential = credential
        self.profile = profile
        self.added = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    @asynccontextmanager
    async def begin(self):
        yield

    async def scalars(self, _statement):
        return [self.credential]

    async def get(self, model, identifier):
        if model is DriverProfile and identifier == self.profile.id:
            return self.profile
        return None

    def add(self, value) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        return None


@pytest.mark.asyncio
async def test_expiry_warning_is_durable_and_idempotent() -> None:
    expires_at = datetime.now(UTC) + timedelta(days=10)
    profile = DriverProfile(id=uuid4(), user_id=uuid4(), display_name="Driver")
    credential = DriverCredential(
        id=uuid4(),
        driver_id=profile.id,
        credential_type="DRIVER_LICENSE",
        verification_status=CredentialVerificationStatus.VERIFIED,
        expires_at=expires_at,
    )
    session = CredentialSession(credential, profile)
    processor = CredentialLifecycleProcessor(lambda: session, Settings.from_environment())

    assert await processor.process_once() == 1
    assert credential.expiry_warning_sent_for == expires_at
    assert [item.type for item in session.added if isinstance(item, Notification)] == [
        "DRIVER_CREDENTIAL_EXPIRING"
    ]
    assert [item.topic for item in session.added if isinstance(item, OutboxEvent)] == [
        "driver.credential.expiring"
    ]
    assert await processor.process_once() == 0


@pytest.mark.asyncio
async def test_expired_credential_is_marked_and_notified_without_interrupting_a_ride() -> None:
    profile = DriverProfile(id=uuid4(), user_id=uuid4(), display_name="Driver")
    credential = DriverCredential(
        id=uuid4(),
        driver_id=profile.id,
        credential_type="DRIVER_LICENSE",
        verification_status=CredentialVerificationStatus.VERIFIED,
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    session = CredentialSession(credential, profile)
    processor = CredentialLifecycleProcessor(lambda: session, Settings.from_environment())

    assert await processor.process_once() == 1
    assert credential.verification_status == CredentialVerificationStatus.EXPIRED
    assert [item.type for item in session.added if isinstance(item, Notification)] == [
        "DRIVER_CREDENTIAL_EXPIRED"
    ]
    assert [item.topic for item in session.added if isinstance(item, OutboxEvent)] == [
        "driver.credential.expired"
    ]
