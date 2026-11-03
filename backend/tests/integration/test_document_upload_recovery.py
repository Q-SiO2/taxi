"""Actual PostGIS leases, writer death and upload/orphan lock interleavings."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
import os
import subprocess
import sys
import threading
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from test_mvp_lifecycle import require_integration_settings
from test_migration_serialization import cli
from taximobile_api.domains.auth.models import User
from taximobile_api.domains.drivers.models import DriverProfile
from taximobile_api.domains.driver_applications.documents import (
    attach_clean_document, lock_document_key, reserve_document_upload,
)
from taximobile_api.domains.driver_applications.models import (
    DocumentErasureReason, DriverApplicationDocument, DriverApplicationEvidence,
    DriverCityApplication, DriverDocumentRetentionAction, DriverRequirementItem,
    DriverRequirementVersion,
)
from taximobile_api.domains.driver_applications.presenters import city_application_response
from taximobile_api.domains.driver_applications.service import RecruitmentConflict, owned_application
from taximobile_api.domains.markets.constants import LEGACY_CITY_ID
from taximobile_api.integrations.driver_documents import (
    DriverDocumentNotFound, EncryptedFilesystemDriverDocumentStore,
)
from taximobile_api.workers.driver_document_retention import DriverDocumentRetentionProcessor

pytestmark = pytest.mark.integration
PDF = b"%PDF-1.7\nSynthetic recoverable upload fixture\n%%EOF\n"


class CleanScanner:
    async def require_clean(self, content):
        assert content == PDF


async def seed_application(sessions):
    async with sessions.begin() as session:
        user = User(email=f"recovery-{uuid4().hex}@example.test", password_hash="synthetic-no-login")
        session.add(user)
        await session.flush()
        driver = DriverProfile(user_id=user.id, display_name="Synthetic upload recovery")
        version = DriverRequirementVersion(city_id=LEGACY_CITY_ID, version=uuid4().hex,
                                           effective_from=datetime.now(UTC))
        session.add_all([driver, version])
        await session.flush()
        item = DriverRequirementItem(requirement_version_id=version.id, requirement_code="IDENTITY",
            evidence_type="DOCUMENT", validity_rule_code="DOCUMENT_SCANNED_CLEAN",
            localized_copy_key="driver.identity",
            localized_label={"en": "Identity", "fr": "Identité", "ar": "الهوية"},
            localized_description={"en": "Synthetic fixture", "fr": "Document fictif", "ar": "وثيقة تجريبية"})
        app = DriverCityApplication(driver_id=driver.id, city_id=LEGACY_CITY_ID,
                                    requirement_version_id=version.id)
        session.add_all([item, app])
        await session.flush()
        return app.id, item.id


async def reserve(sessions, app_id, item_id, prepared, expected_version=1):
    async with sessions.begin() as session:
        app = await session.scalar(select(DriverCityApplication).where(
            DriverCityApplication.id == app_id).with_for_update())
        document = await reserve_document_upload(session, app, requirement_item_id=item_id,
            expected_version=expected_version, stored=prepared.stored, retention_days=30)
        return document.id


async def expire(sessions, document_id):
    async with sessions.begin() as session:
        row = await session.get(DriverApplicationDocument, document_id)
        row.uploaded_at = datetime.now(UTC) - timedelta(minutes=20)
        row.deleted_at = row.uploaded_at
        row.upload_lease_until = datetime.now(UTC) - timedelta(minutes=10)


@pytest.mark.parametrize("crash_at", ["before_rename", "after_rename"])
def test_actual_writer_process_death_leaves_hidden_durable_recovery(tmp_path, crash_at):
    async def prove():
        engine = create_async_engine(require_integration_settings().database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        store = EncryptedFilesystemDriverDocumentStore(tmp_path, bytes(range(32)), CleanScanner())
        try:
            app_id, item_id = await seed_application(sessions)
            prepared = await store.prepare(PDF, declared_media_type="application/pdf")
            document_id = await reserve(sessions, app_id, item_id, prepared)
            path = tmp_path.joinpath(*prepared.stored.opaque_storage_key.split("/"))
            # A separate writer really terminates without finally/transaction
            # cleanup. No database or encryption credentials cross its argv.
            child = """import os,sys
from pathlib import Path
from taximobile_api.integrations.driver_documents import EncryptedFilesystemDriverDocumentStore as Store
payload = sys.stdin.buffer.read()
original = os.replace
def die(source, target):
    if sys.argv[2] == 'after_rename': original(source, target)
    os._exit(23)
os.replace = die
Store._atomic_write(Path(sys.argv[1]), payload)
raise AssertionError('The writer did not terminate at the intended point')
"""
            result = await asyncio.to_thread(subprocess.run, [sys.executable, "-c", child, str(path), crash_at],
                input=prepared.payload, capture_output=True, timeout=15,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            assert result.returncode == 23, result.stderr.decode(errors="replace")
            assert path.exists() == (crash_at == "after_rename")
            assert path.with_suffix(".upload").exists() == (crash_at == "before_rename")
            async with sessions() as session:
                app = await session.get(DriverCityApplication, app_id)
                response = await city_application_response(session, app, document_upload_available=True)
                assert response.documents == [] and response.optimistic_version == 1
                assert await session.scalar(select(func.count()).select_from(DriverApplicationEvidence)) == 0
            await store.aclose()
            reopened = EncryptedFilesystemDriverDocumentStore(tmp_path, bytes(range(32)), CleanScanner())
            worker = DriverDocumentRetentionProcessor(sessions, reopened, batch_size=2)
            assert await worker.process_once() == 0  # Active lease survives writer loss.
            await expire(sessions, document_id)
            assert await worker.process_once() == 1
            assert await worker.process_once() == 0
            async with sessions() as session:
                assert await session.get(DriverApplicationDocument, document_id) is None
                action = await session.scalar(select(DriverDocumentRetentionAction).where(
                    DriverDocumentRetentionAction.document_id == document_id))
                assert action.reason == DocumentErasureReason.UPLOAD_UNCOMMITTED
                assert app_id == action.application_id
            assert not path.exists() and not path.with_suffix(".upload").exists()
            await reopened.aclose()
        finally:
            await store.aclose()
            await engine.dispose()
    asyncio.run(prove())


def test_concurrent_finalizers_advance_once_and_loser_recovers_without_erasing_winner(tmp_path):
    async def prove():
        engine = create_async_engine(require_integration_settings().database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        store = EncryptedFilesystemDriverDocumentStore(tmp_path, bytes(range(32)), CleanScanner())
        try:
            app_id, item_id = await seed_application(sessions)
            first = await store.prepare(PDF, declared_media_type="application/pdf")
            second = await store.prepare(PDF, declared_media_type="application/pdf")
            ids = [await reserve(sessions, app_id, item_id, item) for item in (first, second)]
            for item in (first, second):
                await store.publish(item)

            async def finalize(document_id):
                try:
                    async with sessions.begin() as session:
                        app = await session.scalar(select(DriverCityApplication).where(
                            DriverCityApplication.id == app_id).with_for_update())
                        await attach_clean_document(session, app, requirement_item_id=item_id,
                            expected_version=1, document_id=document_id)
                    return document_id
                except RecruitmentConflict:
                    return None
            results = await asyncio.gather(*(finalize(document_id) for document_id in ids))
            winners = [item for item in results if item is not None]
            assert len(winners) == 1
            winner = winners[0]
            loser = next(item for item in ids if item != winner)
            await expire(sessions, loser)
            assert await DriverDocumentRetentionProcessor(sessions, store).process_once() == 1
            async with sessions() as session:
                app = await session.get(DriverCityApplication, app_id)
                evidence = list(await session.scalars(select(DriverApplicationEvidence)))
                assert app.optimistic_version == 2 and len(evidence) == 1
                assert evidence[0].document_id == winner
                row = await session.get(DriverApplicationDocument, winner)
                assert row.upload_lease_until is None and row.deleted_at is None
                assert await store.read(row.opaque_storage_key) == PDF
                assert await session.get(DriverApplicationDocument, loser) is None
            lost = (first, second)[ids.index(loser)]
            with pytest.raises(DriverDocumentNotFound):
                await store.read(lost.stored.opaque_storage_key)
        finally:
            await store.aclose()
            await engine.dispose()
    asyncio.run(prove())


@pytest.mark.parametrize("first_owner", ["erase", "register"])
def test_orphan_delete_and_new_registration_serialize_on_same_key(tmp_path, first_owner):
    async def prove():
        engine = create_async_engine(require_integration_settings().database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        store = EncryptedFilesystemDriverDocumentStore(tmp_path, bytes(range(32)), CleanScanner())
        entered, release = asyncio.Event(), asyncio.Event()
        try:
            app_id, item_id = await seed_application(sessions)
            prepared = await store.prepare(PDF, declared_media_type="application/pdf")
            await store.publish(prepared)  # Old object without a database row.
            path = tmp_path.joinpath(*prepared.stored.opaque_storage_key.split("/"))
            old = (datetime.now(UTC) - timedelta(hours=1)).timestamp()
            os.utime(path, (old, old))
            worker = DriverDocumentRetentionProcessor(sessions, store, batch_size=2)
            original_delete = store.delete

            async def held_delete(key):
                entered.set()
                await asyncio.wait_for(release.wait(), 5)
                await original_delete(key)

            if first_owner == "erase":
                store.delete = held_delete
                eraser = asyncio.create_task(worker.reconcile_orphans_once())
                await asyncio.wait_for(entered.wait(), 5)
                registrar = asyncio.create_task(reserve(sessions, app_id, item_id, prepared))
                # Observe an actual PostgreSQL lock wait, not just scheduler order.
                async with sessions() as observer:
                    async with asyncio.timeout(5):
                        while not await observer.scalar(text("SELECT EXISTS (SELECT 1 FROM pg_locks "
                                "WHERE locktype = 'advisory' AND NOT granted)")):
                            await asyncio.sleep(.01)
                assert not registrar.done()
                release.set()
                assert await eraser == 1
                document_id = await registrar
                await store.publish(prepared)
            else:
                async with sessions.begin() as registrar:
                    await lock_document_key(registrar, prepared.stored.opaque_storage_key)
                    eraser = asyncio.create_task(worker.reconcile_orphans_once())
                    assert await asyncio.wait_for(eraser, 5) == 0
                    app = await registrar.get(DriverCityApplication, app_id)
                    row = await reserve_document_upload(registrar, app, requirement_item_id=item_id,
                        expected_version=1, stored=prepared.stored, retention_days=30)
                    document_id = row.id
            async with sessions.begin() as session:
                app = await session.get(DriverCityApplication, app_id)
                await attach_clean_document(session, app, requirement_item_id=item_id,
                    expected_version=1, document_id=document_id)
            assert await worker.reconcile_orphans_once() == 0
            assert await store.read(prepared.stored.opaque_storage_key) == PDF
        finally:
            release.set()
            await store.aclose()
            await engine.dispose()
    asyncio.run(prove())


def test_expired_upload_cannot_finalize_even_if_object_was_published(tmp_path):
    async def prove():
        engine = create_async_engine(require_integration_settings().database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        store = EncryptedFilesystemDriverDocumentStore(tmp_path, bytes(range(32)), CleanScanner())
        try:
            app_id, item_id = await seed_application(sessions)
            prepared = await store.prepare(PDF, declared_media_type="application/pdf")
            document_id = await reserve(sessions, app_id, item_id, prepared)
            await store.publish(prepared)
            await expire(sessions, document_id)
            with pytest.raises(RecruitmentConflict, match="lease expired"):
                async with sessions.begin() as session:
                    app = await session.get(DriverCityApplication, app_id)
                    await attach_clean_document(session, app, requirement_item_id=item_id,
                        expected_version=1, document_id=document_id)
            async with sessions() as session:
                assert (await session.get(DriverCityApplication, app_id)).optimistic_version == 1
            assert await DriverDocumentRetentionProcessor(sessions, store).process_once() == 1
        finally:
            await store.aclose()
            await engine.dispose()
    asyncio.run(prove())


def test_cancelled_writer_completing_after_lease_erasure_is_caught_by_repeated_sweep(tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="taximobile_api")
    async def prove():
        engine = create_async_engine(require_integration_settings().database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        store = EncryptedFilesystemDriverDocumentStore(tmp_path, bytes(range(32)), CleanScanner())
        started, finish, completed = threading.Event(), threading.Event(), threading.Event()
        original_write = store._atomic_write

        def late_write(path, payload):
            started.set()
            try:
                assert finish.wait(5)
                original_write(path, payload)
            finally:
                completed.set()
        store._atomic_write = late_write
        try:
            app_id, item_id = await seed_application(sessions)
            prepared = await store.prepare(PDF, declared_media_type="application/pdf")
            document_id = await reserve(sessions, app_id, item_id, prepared)
            writer = asyncio.create_task(store.publish(prepared))
            assert await asyncio.to_thread(started.wait, 5)
            writer.cancel()
            with pytest.raises(asyncio.CancelledError):
                await writer
            await expire(sessions, document_id)
            worker = DriverDocumentRetentionProcessor(sessions, store, batch_size=2)
            assert await worker.process_once() == 1
            finish.set()
            assert await asyncio.to_thread(completed.wait, 5)
            assert await store.read(prepared.stored.opaque_storage_key) == PDF
            # A new worker, with no Python future/exception from the request,
            # finds the provider's late completion on a subsequent full sweep.
            reopened = EncryptedFilesystemDriverDocumentStore(tmp_path, bytes(range(32)), CleanScanner())
            recovered = DriverDocumentRetentionProcessor(sessions, reopened, batch_size=2)
            future = datetime.now(UTC) + timedelta(minutes=6)
            assert await recovered.reconcile_orphans_once(now=future) == 1
            assert await recovered.reconcile_orphans_once(now=future) == 0
            with pytest.raises(DriverDocumentNotFound):
                await reopened.read(prepared.stored.opaque_storage_key)
            assert all(prepared.stored.opaque_storage_key not in record.getMessage() for record in caplog.records)
            assert any(record.getMessage() == "Protected document orphan erased." for record in caplog.records)
            async with sessions() as session:
                assert await session.scalar(select(func.count()).select_from(DriverDocumentRetentionAction)) == 1
                assert (await session.get(DriverCityApplication, app_id)).optimistic_version == 1
            await reopened.aclose()
        finally:
            finish.set()
            await store.aclose()
            await engine.dispose()
    logger = logging.getLogger("taximobile_api")
    logger.addHandler(caplog.handler)
    try:
        asyncio.run(prove())
    finally:
        logger.removeHandler(caplog.handler)


def test_final_upload_lock_refreshes_application_cached_before_publication(tmp_path):
    async def prove():
        engine = create_async_engine(require_integration_settings().database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        store = EncryptedFilesystemDriverDocumentStore(tmp_path, bytes(range(32)), CleanScanner())
        try:
            app_id, item_id = await seed_application(sessions)
            prepared = await store.prepare(PDF, declared_media_type="application/pdf")
            document_id = await reserve(sessions, app_id, item_id, prepared)
            await store.publish(prepared)
            async with sessions() as original_request:
                async with original_request.begin():
                    cached = await original_request.get(DriverCityApplication, app_id)
                    assert cached.optimistic_version == 1
                    driver_id = cached.driver_id
                async with sessions.begin() as other_request:
                    current = await other_request.get(DriverCityApplication, app_id)
                    current.optimistic_version = 2
                assert cached.optimistic_version == 1  # Same identity map as a long upload request.
                with pytest.raises(RecruitmentConflict):
                    async with original_request.begin():
                        locked = await owned_application(original_request, app_id, driver_id, lock=True)
                        assert locked is cached and locked.optimistic_version == 2
                        await attach_clean_document(original_request, locked, requirement_item_id=item_id,
                            expected_version=1, document_id=document_id)
            async with sessions() as session:
                assert (await session.get(DriverCityApplication, app_id)).optimistic_version == 2
                assert (await session.get(DriverApplicationDocument, document_id)).upload_lease_until is not None
                assert await session.scalar(select(func.count()).select_from(DriverApplicationEvidence)) == 0
        finally:
            await store.aclose()
            await engine.dispose()
    asyncio.run(prove())


@pytest.mark.parametrize("lock_target", ["document", "evidence", "replacement"])
def test_upload_lease_is_checked_after_waiting_for_the_document_lock(tmp_path, monkeypatch, lock_target):
    async def prove():
        engine = create_async_engine(require_integration_settings().database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        store = EncryptedFilesystemDriverDocumentStore(tmp_path, bytes(range(32)), CleanScanner())
        from taximobile_api.domains.driver_applications import documents
        clock = {"now": datetime.now(UTC)}

        class Clock:
            @classmethod
            def now(cls, zone):
                assert zone is UTC
                return clock["now"]
        finalizer = None
        try:
            app_id, item_id = await seed_application(sessions)
            expected_version = 1
            old_id = None
            if lock_target != "document":
                old = await store.prepare(PDF, declared_media_type="application/pdf")
                old_id = await reserve(sessions, app_id, item_id, old)
                await store.publish(old)
                async with sessions.begin() as session:
                    app = await session.get(DriverCityApplication, app_id)
                    await attach_clean_document(session, app, requirement_item_id=item_id,
                        expected_version=1, document_id=old_id)
                expected_version = 2
            prepared = await store.prepare(PDF, declared_media_type="application/pdf")
            document_id = await reserve(sessions, app_id, item_id, prepared, expected_version)
            await store.publish(prepared)
            clock["now"] = datetime.now(UTC)
            async with sessions.begin() as session:
                row = await session.get(DriverApplicationDocument, document_id)
                row.upload_lease_until = clock["now"] + timedelta(seconds=2)
            monkeypatch.setattr(documents, "datetime", Clock)

            async def finalize():
                async with sessions.begin() as session:
                    app = await session.get(DriverCityApplication, app_id)
                    await attach_clean_document(session, app, requirement_item_id=item_id,
                        expected_version=expected_version, document_id=document_id)

            async with sessions.begin() as lock_holder:
                if lock_target == "evidence":
                    lock = select(DriverApplicationEvidence).where(DriverApplicationEvidence.application_id == app_id)
                else:
                    lock = select(DriverApplicationDocument).where(
                        DriverApplicationDocument.id == (old_id if lock_target == "replacement" else document_id))
                await lock_holder.scalar(lock.with_for_update())
                finalizer = asyncio.create_task(finalize())
                async with sessions() as observer:
                    async with asyncio.timeout(5):
                        while not await observer.scalar(text("SELECT EXISTS (SELECT 1 FROM pg_locks "
                                "WHERE locktype = 'transactionid' AND NOT granted)")):
                            await asyncio.sleep(.01)
                assert not finalizer.done()
                clock["now"] += timedelta(seconds=3)  # The lease expires during the actual SQL wait.
            with pytest.raises(RecruitmentConflict, match="lease expired"):
                await finalizer
            async with sessions() as session:
                assert (await session.get(DriverCityApplication, app_id)).optimistic_version == expected_version
                assert (await session.get(DriverApplicationDocument, document_id)).upload_lease_until is not None
                assert await session.scalar(select(func.count()).select_from(DriverApplicationEvidence)) == (0 if old_id is None else 1)
                if old_id is not None:
                    assert (await session.get(DriverApplicationDocument, old_id)).deleted_at is None
        finally:
            if finalizer is not None:
                await asyncio.gather(finalizer, return_exceptions=True)
            await store.aclose()
            await engine.dispose()
    asyncio.run(prove())


def test_document_lease_migration_roundtrip_on_empty_isolated_database():
    async def prove():
        require_integration_settings()
        code, output = await cli("downgrade", "20261023_0053")
        assert code == 0, output
        code, output = await cli("upgrade", "head")
        assert code == 0, output
        engine = create_async_engine(require_integration_settings().database_url)
        try:
            async with engine.connect() as connection:
                assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261025_0054"
                assert await connection.scalar(text("SELECT count(*) FROM information_schema.columns "
                    "WHERE table_name='driver_application_documents' AND column_name='upload_lease_until'")) == 1
        finally:
            await engine.dispose()
    asyncio.run(prove())


@pytest.mark.parametrize("retained_state", ["pending_upload", "erasure_history"])
def test_document_lease_downgrade_refuses_to_destroy_recovery_or_erasure_history(tmp_path, retained_state):
    async def prove():
        engine = create_async_engine(require_integration_settings().database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        store = EncryptedFilesystemDriverDocumentStore(tmp_path, bytes(range(32)), CleanScanner())
        try:
            app_id, item_id = await seed_application(sessions)
            prepared = await store.prepare(PDF, declared_media_type="application/pdf")
            document_id = await reserve(sessions, app_id, item_id, prepared)
            if retained_state == "erasure_history":
                await expire(sessions, document_id)
                assert await DriverDocumentRetentionProcessor(sessions, store).process_once() == 1
            code, output = await cli("downgrade", "20261023_0053")
            assert code != 0 and "prevents downgrade" in output
            async with sessions() as session:
                assert await session.scalar(text("SELECT version_num FROM alembic_version")) == "20261025_0054"
                if retained_state == "pending_upload":
                    assert (await session.get(DriverApplicationDocument, document_id)).upload_lease_until is not None
                else:
                    assert await session.scalar(select(func.count()).select_from(DriverDocumentRetentionAction)) == 1
        finally:
            await store.aclose()
            await engine.dispose()
    asyncio.run(prove())
