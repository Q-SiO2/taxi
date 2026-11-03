"""Physical erasure of soft-deleted or retention-expired driver documents."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import logging

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taximobile_api.core.metrics import MetricsRegistry
from taximobile_api.domains.driver_applications.documents import UPLOAD_LEASE_SECONDS, lock_document_key
from taximobile_api.domains.driver_applications.models import (
    DocumentErasureReason,
    DriverApplicationDocument,
    DriverApplicationEvidence,
    DriverCityApplication,
    DriverDocumentRetentionAction,
)
from taximobile_api.integrations.driver_documents import (
    DriverDocumentError,
    DriverDocumentNotFound,
    ProtectedDriverDocumentStore,
    require_document_key,
    require_document_page_limit,
)
from taximobile_api.workers.runtime import run_polling_processor


class DriverDocumentRetentionProcessor:
    """Erase object bytes and metadata together in a locked, retryable batch."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        store: ProtectedDriverDocumentStore,
        *,
        batch_size: int = 100,
    ) -> None:
        require_document_page_limit(batch_size)
        self._sessions = sessions
        self._store = store
        self._batch_size = batch_size
        self._orphan_cursor: str | None = None

    async def process_once(self) -> int:
        if not self._store.available:
            return 0
        now = datetime.now(UTC)
        processed = 0
        async with self._sessions() as session:
            async with session.begin():
                rows = (
                    await session.execute(
                        select(DriverApplicationDocument, DriverCityApplication)
                        .join(
                            DriverCityApplication,
                            DriverCityApplication.id
                            == DriverApplicationDocument.application_id,
                        )
                        .where(
                            or_(
                                DriverApplicationDocument.upload_lease_until.is_(None),
                                DriverApplicationDocument.upload_lease_until <= now,
                            ),
                            or_(
                                DriverApplicationDocument.deleted_at.is_not(None),
                                DriverApplicationDocument.retention_deadline <= now,
                            )
                        )
                        .order_by(
                            DriverApplicationDocument.retention_deadline,
                            DriverApplicationDocument.id,
                        )
                        .limit(self._batch_size)
                        .with_for_update(
                            of=DriverApplicationDocument,
                            skip_locked=True,
                        )
                    )
                ).all()
                for document, application in rows:
                    # Delete first. If the later transaction fails, object deletion is
                    # idempotent and the retained row causes a safe retry.
                    await self._store.delete(document.opaque_storage_key)
                    await session.execute(
                        delete(DriverApplicationEvidence).where(
                            DriverApplicationEvidence.document_id == document.id
                        )
                    )
                    reason = (
                        DocumentErasureReason.UPLOAD_UNCOMMITTED
                        if document.upload_lease_until is not None
                        else DocumentErasureReason.APPLICANT_DELETED
                        if document.deleted_at is not None
                        else DocumentErasureReason.RETENTION_EXPIRED
                    )
                    session.add(
                        DriverDocumentRetentionAction(
                            document_id=document.id,
                            application_id=application.id,
                            city_id=application.city_id,
                            reason=reason,
                            retention_policy_version="driver-documents-v1",
                            retention_due_at=document.upload_lease_until or document.retention_deadline,
                            executed_at=now,
                        )
                    )
                    await session.delete(document)
                    processed += 1
        return processed + await self.reconcile_orphans_once(now=now)

    async def reconcile_orphans_once(self, *, now: datetime | None = None) -> int:
        """One bounded listing page; never delete without current DB authority.

        Repeat full sweeps indefinitely: a remote PUT can complete after its
        pending row was already erased. This is separate from lease cleanup.
        """
        if not self._store.available:
            return 0
        now = now or datetime.now(UTC)
        try:
            page = await self._store.objects_page(cursor=self._orphan_cursor, limit=self._batch_size)
        except DriverDocumentError:
            self._orphan_cursor = None
            raise
        erased = 0
        for item in page.objects:
            try:
                require_document_key(item.opaque_storage_key)
            except DriverDocumentNotFound:
                continue
            if item.last_modified.utcoffset() is None:
                continue
            if item.last_modified > now - timedelta(seconds=UPLOAD_LEASE_SECONDS):
                continue
            async with self._sessions() as session:
                async with session.begin():
                    if not await lock_document_key(session, item.opaque_storage_key, wait=False):
                        continue
                    # READ COMMITTED fresh statement after the key lock. The
                    # upload registrar takes that same lock before INSERT.
                    referenced = await session.scalar(select(DriverApplicationDocument.id).where(
                        DriverApplicationDocument.opaque_storage_key == item.opaque_storage_key,
                    ).limit(1))
                    if referenced is not None:
                        continue
                    await self._store.delete(item.opaque_storage_key)
                    # There is no applicant/city/actor for a genuine orphan.
                    # Do not invent an audit principal or retain its raw key.
                    logging.getLogger("taximobile_api").info(
                        "Protected document orphan erased.",
                        extra={"worker": "driver_document_retention"},
                    )
                    erased += 1
        self._orphan_cursor = page.next_cursor
        return erased


async def run_driver_document_retention_processor(
    processor: DriverDocumentRetentionProcessor,
    poll_seconds: float,
    metrics: MetricsRegistry,
) -> None:
    await run_polling_processor(
        worker="driver_document_retention",
        processor=processor,
        poll_seconds=poll_seconds,
        metrics=metrics,
    )
