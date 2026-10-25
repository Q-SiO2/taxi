from pathlib import Path
import shutil
import os
import asyncio
import threading
from datetime import UTC, datetime, timedelta

import pytest

from taximobile_api.integrations.driver_documents import (
    DriverDocumentNotFound,
    DriverDocumentRejected,
    DriverDocumentUnavailable,
    EncryptedFilesystemDriverDocumentStore,
    InMemoryDriverDocumentStore,
    create_driver_document_store,
    detect_media_type,
)


PDF = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n"
JPEG = b"\xff\xd8\xff\xe0minimal-jpeg\xff\xd9"
PNG = b"\x89PNG\r\n\x1a\nminimal-IEND\xaeB`\x82"


class CleanScanner:
    async def require_clean(self, content: bytes) -> None:
        assert content


class RejectingScanner:
    async def require_clean(self, content: bytes) -> None:
        del content
        raise DriverDocumentRejected("infected")


@pytest.mark.parametrize(
    ("content", "expected"),
    [(PDF, "application/pdf"), (JPEG, "image/jpeg"), (PNG, "image/png")],
)
def test_detect_media_type_uses_file_signatures(content: bytes, expected: str) -> None:
    assert detect_media_type(content) == expected


def test_detect_media_type_rejects_extension_only_or_truncated_content() -> None:
    with pytest.raises(DriverDocumentRejected):
        detect_media_type(b"not-a-pdf.pdf")
    with pytest.raises(DriverDocumentRejected):
        detect_media_type(b"%PDF-1.7 without terminal marker")


@pytest.mark.asyncio
async def test_encrypted_store_round_trip_and_metadata(tmp_path: Path) -> None:
    store = EncryptedFilesystemDriverDocumentStore(
        tmp_path,
        bytes(range(32)),
        CleanScanner(),
        max_bytes=1024,
    )

    stored = await store.store(PDF, declared_media_type="application/pdf")

    assert stored.media_type == "application/pdf"
    assert stored.byte_size == len(PDF)
    assert len(stored.sha256) == 64
    assert await store.read(stored.opaque_storage_key) == PDF
    on_disk = tmp_path.joinpath(*stored.opaque_storage_key.split("/")).read_bytes()
    assert PDF not in on_disk

    await store.delete(stored.opaque_storage_key)
    with pytest.raises(DriverDocumentNotFound):
        await store.read(stored.opaque_storage_key)


@pytest.mark.asyncio
async def test_store_rejects_oversize_mismatch_and_malware(tmp_path: Path) -> None:
    small_store = EncryptedFilesystemDriverDocumentStore(
        tmp_path / "small", bytes(range(32)), CleanScanner(), max_bytes=8
    )
    with pytest.raises(DriverDocumentRejected, match="exceeds"):
        await small_store.store(PDF, declared_media_type="application/pdf")

    store = EncryptedFilesystemDriverDocumentStore(
        tmp_path / "mismatch", bytes(range(32)), CleanScanner()
    )
    with pytest.raises(DriverDocumentRejected, match="do not match"):
        await store.store(PDF, declared_media_type="image/png")

    rejected_store = EncryptedFilesystemDriverDocumentStore(
        tmp_path / "malware", bytes(range(32)), RejectingScanner()
    )
    with pytest.raises(DriverDocumentRejected, match="infected"):
        await rejected_store.store(PDF, declared_media_type="application/pdf")
    assert list((tmp_path / "malware").rglob("*.bin")) == []


@pytest.mark.asyncio
async def test_store_detects_ciphertext_tampering_and_rejects_opaque_key_traversal(
    tmp_path: Path,
) -> None:
    store = EncryptedFilesystemDriverDocumentStore(
        tmp_path, bytes(range(32)), CleanScanner()
    )
    stored = await store.store(PDF, declared_media_type="application/pdf")
    path = tmp_path.joinpath(*stored.opaque_storage_key.split("/"))
    payload = bytearray(path.read_bytes())
    payload[-1] ^= 1
    path.write_bytes(payload)

    with pytest.raises(DriverDocumentUnavailable, match="integrity"):
        await store.read(stored.opaque_storage_key)
    with pytest.raises(DriverDocumentNotFound):
        await store.read("../../outside.bin")


def test_store_factory_is_disabled_or_requires_complete_security_configuration(
    tmp_path: Path,
) -> None:
    assert create_driver_document_store().available is False
    with pytest.raises(ValueError, match="configured together"):
        create_driver_document_store(root=tmp_path)


@pytest.mark.asyncio
@pytest.mark.parametrize("content,media_type", [(PDF,"application/pdf"),(JPEG,"image/jpeg"),(PNG,"image/png")])
async def test_ciphertext_only_copy_recovers_with_the_separate_correct_key(tmp_path: Path, content, media_type):
    source_root = tmp_path / "source"
    restored_root = tmp_path / "isolated-restore"
    key = bytes(range(32))
    original = EncryptedFilesystemDriverDocumentStore(source_root, key, CleanScanner())
    stored = await original.store(content, declared_media_type=media_type)
    payload = source_root.joinpath(*stored.opaque_storage_key.split("/")).read_bytes()
    assert content not in payload
    shutil.copytree(source_root, restored_root)
    wrong_key = EncryptedFilesystemDriverDocumentStore(restored_root, bytes(reversed(key)), CleanScanner())
    with pytest.raises(DriverDocumentUnavailable, match="integrity"):
        await wrong_key.read(stored.opaque_storage_key)
    reopened = EncryptedFilesystemDriverDocumentStore(restored_root, key, CleanScanner())
    assert await reopened.read(stored.opaque_storage_key) == content
    assert restored_root.joinpath(*stored.opaque_storage_key.split("/")).read_bytes() == payload
    assert await original.read(stored.opaque_storage_key) == content


@pytest.mark.asyncio
async def test_relocated_ciphertext_cannot_be_read_under_another_valid_opaque_key(tmp_path: Path):
    store = EncryptedFilesystemDriverDocumentStore(tmp_path, bytes(range(32)), CleanScanner())
    first = await store.store(PDF, declared_media_type="application/pdf")
    second = await store.store(PDF, declared_media_type="application/pdf")
    first_path = tmp_path.joinpath(*first.opaque_storage_key.split("/"))
    second_path = tmp_path.joinpath(*second.opaque_storage_key.split("/"))
    second_path.write_bytes(first_path.read_bytes())
    with pytest.raises(DriverDocumentUnavailable, match="integrity"):
        await store.read(second.opaque_storage_key)
    assert await store.read(first.opaque_storage_key) == PDF


@pytest.mark.asyncio
async def test_failed_atomic_publish_is_explicit_and_removes_temporary_ciphertext(tmp_path: Path, monkeypatch):
    def unavailable_replace(_source, _target):
        raise OSError("private-fixture-storage-path must not reach the HTTP detail")
    monkeypatch.setattr("taximobile_api.integrations.driver_documents.os.replace", unavailable_replace)
    store = EncryptedFilesystemDriverDocumentStore(tmp_path, bytes(range(32)), CleanScanner())
    with pytest.raises(DriverDocumentUnavailable) as error:
        await store.store(PDF, declared_media_type="application/pdf")
    assert "private-fixture" not in str(error.value)
    assert list(tmp_path.rglob("*.bin")) == []
    assert list(tmp_path.rglob(".upload-*")) == []
    assert list(tmp_path.rglob("*.upload")) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["filesystem", "memory"])
async def test_preparation_does_not_publish_and_payload_is_not_in_repr(tmp_path, kind):
    store = (EncryptedFilesystemDriverDocumentStore(tmp_path, bytes(range(32)), CleanScanner())
             if kind == "filesystem" else InMemoryDriverDocumentStore(CleanScanner()))
    prepared = await store.prepare(PDF, declared_media_type="application/pdf")
    assert "PDF" not in repr(prepared) and "payload=" not in repr(prepared)
    with pytest.raises(DriverDocumentNotFound):
        await store.read(prepared.stored.opaque_storage_key)
    if kind == "filesystem":
        assert list(tmp_path.rglob("*.bin")) == []
        assert PDF not in prepared.payload
    assert await store.publish(prepared) == prepared.stored
    assert await store.read(prepared.stored.opaque_storage_key) == PDF
    await store.aclose()


@pytest.mark.asyncio
async def test_filesystem_object_pages_bound_foreign_entries_and_resume(tmp_path):
    store = EncryptedFilesystemDriverDocumentStore(tmp_path, bytes(range(32)), CleanScanner())
    saved = [await store.store(PDF, declared_media_type="application/pdf") for _ in range(4)]
    folder = tmp_path / "v1" / "00"
    folder.mkdir(parents=True, exist_ok=True)
    for i in range(5):
        (folder / f"foreign-{i}.txt").write_text("not an owned object")
    cursor = None
    observed = []
    pages = 0
    while True:
        page = await store.objects_page(cursor=cursor, limit=2)
        pages += 1
        assert len(page.objects) <= 2
        observed.extend(item.opaque_storage_key for item in page.objects)
        assert all(item.last_modified.utcoffset() == timedelta(0) for item in page.objects)
        cursor = page.next_cursor
        if cursor is None:
            break
        assert pages < 20
    assert pages >= 5  # Foreign entries also consume bounded scan work.
    assert sorted(observed) == sorted(item.opaque_storage_key for item in saved)
    await store.aclose()


@pytest.mark.asyncio
async def test_filesystem_crashed_staging_file_is_listed_and_erased_by_its_durable_key(tmp_path):
    store = EncryptedFilesystemDriverDocumentStore(tmp_path, bytes(range(32)), CleanScanner())
    prepared = await store.prepare(PDF, declared_media_type="application/pdf")
    path = tmp_path.joinpath(*prepared.stored.opaque_storage_key.split("/")).with_suffix(".upload")
    path.parent.mkdir(parents=True)
    path.write_bytes(prepared.payload[:20])  # Process died before rename/finally.
    old = (datetime.now(UTC) - timedelta(hours=1)).timestamp()
    os.utime(path, (old, old))
    reopened = EncryptedFilesystemDriverDocumentStore(tmp_path, bytes(range(32)), CleanScanner())
    page = await reopened.objects_page(cursor=None, limit=10)
    assert [item.opaque_storage_key for item in page.objects] == [prepared.stored.opaque_storage_key]
    assert page.objects[0].last_modified < datetime.now(UTC) - timedelta(minutes=59)
    await reopened.delete(prepared.stored.opaque_storage_key)
    assert not path.exists()
    await store.aclose()
    await reopened.aclose()


@pytest.mark.asyncio
async def test_filesystem_read_bounds_ciphertext_before_decryption(tmp_path):
    store = EncryptedFilesystemDriverDocumentStore(tmp_path, bytes(range(32)), CleanScanner(), max_bytes=128)
    saved = await store.store(PDF, declared_media_type="application/pdf")
    path = tmp_path.joinpath(*saved.opaque_storage_key.split("/"))
    path.write_bytes(b"x" * 1024)
    with pytest.raises(DriverDocumentUnavailable, match="object length is invalid"):
        await store.read(saved.opaque_storage_key)
    await store.aclose()


@pytest.mark.asyncio
async def test_repeated_listing_cancellation_keeps_iterator_owned_until_thread_finishes(tmp_path):
    store = EncryptedFilesystemDriverDocumentStore(tmp_path, bytes(range(32)), CleanScanner())
    entered, release = threading.Event(), threading.Event()

    def blocked_listing():
        entered.set()
        assert release.wait(5)
        yield None
    store._walk_objects = blocked_listing
    listing = asyncio.create_task(store.objects_page(cursor=None, limit=1))
    closing = None
    try:
        assert await asyncio.to_thread(entered.wait, 5)
        listing.cancel()
        await asyncio.sleep(0)
        listing.cancel()
        with pytest.raises(asyncio.CancelledError):
            await listing
        closing = asyncio.create_task(store.aclose())
        await asyncio.sleep(.01)
        assert not closing.done(), "Shutdown must not close a generator whose listing thread still owns it"
        release.set()
        await asyncio.wait_for(closing, 2)
        assert store._listing is None
    finally:
        release.set()
        await asyncio.gather(listing, *([closing] if closing is not None else []), return_exceptions=True)
