from pathlib import Path
import shutil

import pytest

from taximobile_api.integrations.driver_documents import (
    DriverDocumentNotFound,
    DriverDocumentRejected,
    DriverDocumentUnavailable,
    EncryptedFilesystemDriverDocumentStore,
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
