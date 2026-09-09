"""Physical erasure of soft-deleted or retention-expired driver documents."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taximobile_api.core.metrics import MetricsRegistry
from taximobile_api.domains.driver_applications.models import (
    DocumentErasureReason,
    DriverApplicationDocument,
    DriverApplicationEvidence,
    DriverCityApplication,
    DriverDocumentRetentionAction,
)
from taximobile_api.integrations.driver_documents import ProtectedDriverDocumentStore
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
        self._sessions = sessions
        self._store = store
        self._batch_size = batch_size

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
                        DocumentErasureReason.APPLICANT_DELETED
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
                            retention_due_at=document.retention_deadline,
                            executed_at=now,
                        )
                    )
                    await session.delete(document)
                    processed += 1
        return processed


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
