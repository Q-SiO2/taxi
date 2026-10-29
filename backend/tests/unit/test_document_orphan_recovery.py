"""Recovery fails closed when database or namespace authority is missing."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import pytest

from taximobile_api.integrations.driver_documents import (
    DriverDocumentObject, DriverDocumentObjectPage, InMemoryDriverDocumentStore,
)
from taximobile_api.workers.driver_document_retention import DriverDocumentRetentionProcessor


class CleanScanner:
    async def require_clean(self, content):
        assert content


@pytest.mark.asyncio
async def test_orphan_recovery_never_erases_when_database_is_unavailable():
    store = InMemoryDriverDocumentStore(CleanScanner())
    saved = await store.store(b"%PDF-1.7\nsynthetic fixture\n%%EOF", declared_media_type="application/pdf")
    store._modified[saved.opaque_storage_key] -= timedelta(hours=1)

    @asynccontextmanager
    async def unavailable():
        raise RuntimeError("synthetic unavailable database")
        yield

    worker = DriverDocumentRetentionProcessor(unavailable, store)
    with pytest.raises(RuntimeError, match="unavailable database"):
        await worker.reconcile_orphans_once()
    assert await store.read(saved.opaque_storage_key) == b"%PDF-1.7\nsynthetic fixture\n%%EOF"


@pytest.mark.asyncio
async def test_orphan_worker_rejects_foreign_keys_and_recent_or_naive_objects_before_database_access():
    store = InMemoryDriverDocumentStore(CleanScanner())
    key = "v1/ab/" + "c" * 30 + ".bin"
    now = datetime.now(UTC)

    async def page(*, cursor, limit):
        assert cursor is None and limit == 3
        return DriverDocumentObjectPage((
            DriverDocumentObject("../../foreign.bin", now - timedelta(hours=1)),
            DriverDocumentObject(key, now),
            DriverDocumentObject(key, now.replace(tzinfo=None)),
        ), None)

    def forbidden_database():
        raise AssertionError("An ineligible listing must never reach database/deletion")
    store.objects_page = page
    worker = DriverDocumentRetentionProcessor(forbidden_database, store, batch_size=3)
    assert await worker.reconcile_orphans_once() == 0
