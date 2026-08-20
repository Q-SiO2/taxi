"""Warn about credential expiry and close new-dispatch eligibility at expiry."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taximobile_api.core.config import Settings
from taximobile_api.core.metrics import MetricsRegistry
from taximobile_api.domains.drivers.models import (
    CredentialVerificationStatus,
    DriverCredential,
    DriverProfile,
)
from taximobile_api.domains.notifications.service import notify
from taximobile_api.domains.outbox.service import enqueue
from taximobile_api.workers.runtime import run_polling_processor


class CredentialLifecycleProcessor:
    """Process a locked bounded set without duplicating warning notifications."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
        *,
        batch_size: int = 100,
    ) -> None:
        self._sessions = session_factory
        self._warning_days = settings.credential_expiry_warning_days
        self._batch_size = batch_size

    async def process_once(self) -> int:
        now = datetime.now(UTC)
        warning_deadline = now + timedelta(days=self._warning_days)
        processed = 0
        async with self._sessions() as session:
            async with session.begin():
                credentials = list(
                    await session.scalars(
                        select(DriverCredential)
                        .where(
                            DriverCredential.verification_status
                            == CredentialVerificationStatus.VERIFIED,
                            DriverCredential.expires_at.is_not(None),
                            DriverCredential.expires_at <= warning_deadline,
                            or_(
                                DriverCredential.expires_at <= now,
                                DriverCredential.expiry_warning_sent_for.is_(None),
                                DriverCredential.expiry_warning_sent_for
                                != DriverCredential.expires_at,
                            ),
                        )
                        .order_by(DriverCredential.expires_at, DriverCredential.id)
                        .limit(self._batch_size)
                        .with_for_update(skip_locked=True)
                    )
                )
                for credential in credentials:
                    expires_at = credential.expires_at
                    if expires_at is None:
                        continue
                    profile = await session.get(DriverProfile, credential.driver_id)
                    if profile is None:
                        continue
                    if expires_at <= now:
                        credential.verification_status = CredentialVerificationStatus.EXPIRED
                        notification_type = "DRIVER_CREDENTIAL_EXPIRED"
                        title = "Professional credential expired"
                        body = "A professional credential expired. Renew it before receiving new rides."
                        topic = "driver.credential.expired"
                    else:
                        if credential.expiry_warning_sent_for == expires_at:
                            continue
                        credential.expiry_warning_sent_for = expires_at
                        notification_type = "DRIVER_CREDENTIAL_EXPIRING"
                        title = "Professional credential expires soon"
                        body = "Review and renew your professional credential before it expires."
                        topic = "driver.credential.expiring"
                    await notify(
                        session,
                        user_id=profile.user_id,
                        notification_type=notification_type,
                        title=title,
                        body=body,
                        data={"credential_id": str(credential.id)},
                    )
                    await enqueue(
                        session,
                        topic=topic,
                        payload={"credential_id": str(credential.id)},
                    )
                    processed += 1
                return processed


async def run_credential_lifecycle_processor(
    processor: CredentialLifecycleProcessor,
    poll_seconds: float,
    metrics: MetricsRegistry,
) -> None:
    await run_polling_processor(
        worker="credentials",
        processor=processor,
        poll_seconds=poll_seconds,
        metrics=metrics,
    )
