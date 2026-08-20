from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from taximobile_api.domains.auth.dependencies import CurrentPrincipal
from taximobile_api.domains.auth.models import Session
from taximobile_api.domains.auth.router import logout
from taximobile_api.domains.notifications.models import DevicePlatform, DeviceRegistrationKind
from taximobile_api.domains.notifications.router import register_device, revoke_device
from taximobile_api.domains.notifications.schemas import (
    DeviceRegistrationRequest,
    DeviceRevocationRequest,
)


class FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None


class FakeResult:
    def __init__(self, row=None):
        self.row = row

    def one(self):
        assert self.row is not None
        return self.row


class RecordingSession:
    def __init__(self, row=None, stored_session=None):
        self.row = row
        self.stored_session = stored_session
        self.statements = []

    def begin(self):
        return FakeTransaction()

    async def execute(self, statement):
        self.statements.append(statement)
        return FakeResult(self.row)

    async def get(self, model, identifier):
        assert model is Session
        if self.stored_session is not None:
            assert self.stored_session.id == identifier
        return self.stored_session


@pytest.mark.asyncio
async def test_registration_uses_atomic_global_token_ownership_transfer() -> None:
    device_id = uuid4()
    principal = CurrentPrincipal(user_id=uuid4(), session_id=uuid4())
    session = RecordingSession(
        row=(device_id, DevicePlatform.ANDROID, DeviceRegistrationKind.FIREBASE_INSTALLATION_ID)
    )

    response = await register_device(
        DeviceRegistrationRequest(
            platform=DevicePlatform.ANDROID,
            registration_kind=DeviceRegistrationKind.FIREBASE_INSTALLATION_ID,
            registration_id="firebase-installation-id",
        ),
        principal,
        session,
    )

    sql = str(session.statements[0].compile(dialect=postgresql.dialect())).lower()
    assert "on conflict (registration_kind, token) do update" in sql
    assert "user_id =" in sql
    assert "session_id =" in sql
    assert "revoked_at =" in sql
    assert response.id == device_id


@pytest.mark.asyncio
async def test_revocation_is_scoped_to_authenticated_owner_platform_and_token() -> None:
    principal = CurrentPrincipal(user_id=uuid4(), session_id=uuid4())
    session = RecordingSession()

    response = await revoke_device(
        DeviceRevocationRequest(
            platform=DevicePlatform.IOS,
            registration_kind=DeviceRegistrationKind.FIREBASE_INSTALLATION_ID,
            registration_id="firebase-installation-id",
        ),
        principal,
        session,
    )

    compiled = session.statements[0].compile(dialect=postgresql.dialect())
    sql = str(compiled).lower()
    assert "device_tokens.user_id" in sql
    assert "device_tokens.session_id" in sql
    assert "device_tokens.platform" in sql
    assert "device_tokens.registration_kind" in sql
    assert "device_tokens.token" in sql
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_backend_logout_revokes_only_registrations_bound_to_current_session() -> None:
    principal = CurrentPrincipal(user_id=uuid4(), session_id=uuid4())
    stored_session = Session(
        id=principal.session_id,
        user_id=principal.user_id,
        refresh_token_hash="0" * 64,
        refresh_family_id=uuid4(),
        expires_at=datetime.now(UTC) + timedelta(days=1),
        revoked_at=None,
        refresh_rotated_at=None,
        device_label="unit test",
    )
    session = RecordingSession(stored_session=stored_session)

    response = await logout(principal, session)

    assert response.success is True
    assert stored_session.revoked_at is not None
    sql = str(session.statements[0].compile(dialect=postgresql.dialect())).lower()
    assert "device_tokens.user_id" in sql
    assert "device_tokens.session_id" in sql
    assert "device_tokens.revoked_at is null" in sql


def test_blank_device_tokens_are_rejected_without_normalizing_provider_values() -> None:
    with pytest.raises(ValidationError):
        DeviceRegistrationRequest(
            platform=DevicePlatform.ANDROID,
            registration_kind=DeviceRegistrationKind.FIREBASE_INSTALLATION_ID,
            registration_id="   ",
        )

    request = DeviceRegistrationRequest(
        platform=DevicePlatform.ANDROID,
        registration_kind=DeviceRegistrationKind.FIREBASE_INSTALLATION_ID,
        registration_id="exact-id",
    )
    assert request.registration_id == "exact-id"
