"""Encrypted, malware-scanned storage for applicant-owned documents.

The database stores only an opaque key and bounded metadata. File bytes are
accepted only after independent media detection and a successful ClamAV scan,
then encrypted with AES-256-GCM before they reach the configured private
filesystem. Any unavailable dependency fails closed.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
import os
from pathlib import Path
import re
import struct
from typing import Protocol
from uuid import uuid4

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from taximobile_api.integrations.document_storage_config import S3DocumentStorageSettings


ALLOWED_MEDIA_TYPES = frozenset({"application/pdf", "image/jpeg", "image/png"})
_OPAQUE_KEY_PATTERN = re.compile(r"v1/[0-9a-f]{2}/[0-9a-f]{30}\.bin")
_ENCRYPTION_VERSION = b"TMDOC1"
_NONCE_BYTES = 12
_SCAN_CHUNK_BYTES = 64 * 1024
_SCAN_RESPONSE_MAX_BYTES = 4096


class DriverDocumentError(RuntimeError):
    """Base class for safe document pipeline failures."""


class DriverDocumentUnavailable(DriverDocumentError):
    """A required private storage or scanning dependency is unavailable."""


class DriverDocumentRejected(DriverDocumentError):
    """The submitted bytes violate policy or failed malware scanning."""


class DriverDocumentNotFound(DriverDocumentError):
    """The opaque object does not exist in protected storage."""


@dataclass(frozen=True, slots=True)
class StoredDriverDocument:
    opaque_storage_key: str
    media_type: str
    byte_size: int
    sha256: str


@dataclass(frozen=True, slots=True)
class PreparedDriverDocument:
    """Scanned metadata and private bytes, not yet published to storage."""

    stored: StoredDriverDocument
    payload: bytes = field(repr=False)


@dataclass(frozen=True, slots=True)
class DriverDocumentObject:
    opaque_storage_key: str
    last_modified: datetime


@dataclass(frozen=True, slots=True)
class DriverDocumentObjectPage:
    objects: tuple[DriverDocumentObject, ...]
    next_cursor: str | None


class MalwareScanner(Protocol):
    async def require_clean(self, content: bytes) -> None: ...


class ProtectedDriverDocumentStore(Protocol):
    @property
    def available(self) -> bool: ...

    @property
    def max_bytes(self) -> int: ...

    async def prepare(self, content: bytes, *, declared_media_type: str | None) -> PreparedDriverDocument: ...

    async def publish(self, prepared: PreparedDriverDocument) -> StoredDriverDocument: ...

    async def store(self, content: bytes, *, declared_media_type: str | None) -> StoredDriverDocument: ...

    async def read(self, opaque_storage_key: str) -> bytes: ...

    async def delete(self, opaque_storage_key: str) -> None: ...

    async def objects_page(self, *, cursor: str | None, limit: int) -> DriverDocumentObjectPage: ...

    async def aclose(self) -> None: ...


class DisabledDriverDocumentStore:
    def __init__(self, *, max_bytes: int = 10 * 1024 * 1024) -> None:
        self._max_bytes = max_bytes

    @property
    def available(self) -> bool:
        return False

    @property
    def max_bytes(self) -> int:
        return self._max_bytes

    async def prepare(self, content: bytes, *, declared_media_type: str | None) -> PreparedDriverDocument:
        del content, declared_media_type
        raise DriverDocumentUnavailable("Protected driver-document storage is not configured.")

    async def publish(self, prepared: PreparedDriverDocument) -> StoredDriverDocument:
        del prepared
        raise DriverDocumentUnavailable("Protected driver-document storage is not configured.")

    async def store(self, content: bytes, *, declared_media_type: str | None) -> StoredDriverDocument:
        del content, declared_media_type
        raise DriverDocumentUnavailable("Protected driver-document storage is not configured.")

    async def read(self, opaque_storage_key: str) -> bytes:
        del opaque_storage_key
        raise DriverDocumentUnavailable("Protected driver-document storage is not configured.")

    async def delete(self, opaque_storage_key: str) -> None:
        del opaque_storage_key
        raise DriverDocumentUnavailable("Protected driver-document storage is not configured.")

    async def objects_page(self, *, cursor: str | None, limit: int) -> DriverDocumentObjectPage:
        raise DriverDocumentUnavailable("Protected driver-document storage is not configured.")

    async def aclose(self) -> None:
        pass


class ClamAVScanner:
    """Small async client for ClamAV's bounded INSTREAM protocol."""

    def __init__(self, host: str, port: int = 3310, timeout_seconds: float = 10.0) -> None:
        self._host = host
        self._port = port
        self._timeout_seconds = timeout_seconds

    async def require_clean(self, content: bytes) -> None:
        writer: asyncio.StreamWriter | None = None
        try:
            # One deadline bounds connect, backpressure and the complete reply.
            # INSTREAM is a non-session command: consume through daemon EOF so
            # a clean prefix cannot hide a trailing error or additional record.
            async with asyncio.timeout(self._timeout_seconds):
                reader, writer = await asyncio.open_connection(self._host, self._port)
                writer.write(b"zINSTREAM\0")
                for offset in range(0, len(content), _SCAN_CHUNK_BYTES):
                    chunk = content[offset : offset + _SCAN_CHUNK_BYTES]
                    writer.write(struct.pack("!I", len(chunk)))
                    writer.write(chunk)
                    await writer.drain()
                writer.write(struct.pack("!I", 0))
                await writer.drain()
                response = bytearray()
                while True:
                    part = await reader.read(_SCAN_RESPONSE_MAX_BYTES + 1 - len(response))
                    if not part:
                        break
                    response.extend(part)
                    if len(response) > _SCAN_RESPONSE_MAX_BYTES:
                        raise DriverDocumentUnavailable("The malware scanner returned an invalid result.")
        except (OSError, TimeoutError, asyncio.IncompleteReadError) as error:
            raise DriverDocumentUnavailable("Malware scanning is temporarily unavailable.") from error
        finally:
            if writer is not None:
                writer.close()
                try:
                    await asyncio.wait_for(writer.wait_closed(), timeout=min(1.0, self._timeout_seconds))
                except (OSError, TimeoutError):
                    writer.transport.abort()

        if response == b"stream: OK\0":
            return
        if re.fullmatch(rb"stream: [^\x00\r\n]+ FOUND\x00", response):
            raise DriverDocumentRejected("The document failed the malware safety scan.")
        raise DriverDocumentUnavailable("The malware scanner returned an invalid result.")


class EncryptedFilesystemDriverDocumentStore:
    """Private local-volume adapter using opaque names and authenticated encryption."""

    def __init__(
        self,
        root: Path,
        encryption_key: bytes,
        scanner: MalwareScanner,
        *,
        max_bytes: int = 10 * 1024 * 1024,
    ) -> None:
        if len(encryption_key) != 32:
            raise ValueError("Driver-document encryption key must contain exactly 32 bytes.")
        if max_bytes < 1:
            raise ValueError("Driver-document maximum size must be positive.")
        self._root = root.expanduser().resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._cipher = AESGCM(encryption_key)
        self._scanner = scanner
        self._max_bytes = max_bytes
        self._listing_lock = asyncio.Lock()
        self._listing: Iterator[DriverDocumentObject | None] | None = None
        self._listing_cursor: str | None = None

    @property
    def available(self) -> bool:
        return True

    @property
    def max_bytes(self) -> int:
        return self._max_bytes

    async def prepare(self, content: bytes, *, declared_media_type: str | None) -> PreparedDriverDocument:
        detected_media_type = validate_document_upload(content, declared_media_type, self._max_bytes)

        await self._scanner.require_clean(content)
        identifier = uuid4().hex
        opaque_key = f"v1/{identifier[:2]}/{identifier[2:]}.bin"
        payload = encrypt_document_payload(self._cipher, opaque_key, content)
        return PreparedDriverDocument(StoredDriverDocument(
            opaque_storage_key=opaque_key,
            media_type=detected_media_type,
            byte_size=len(content),
            sha256=sha256(content).hexdigest(),
        ), payload)

    async def publish(self, prepared: PreparedDriverDocument) -> StoredDriverDocument:
        path = self._path_for(prepared.stored.opaque_storage_key)
        try:
            await asyncio.to_thread(self._atomic_write, path, prepared.payload)
        except OSError as error:
            raise DriverDocumentUnavailable("Protected driver-document storage is unavailable.") from error
        return prepared.stored

    async def store(self, content: bytes, *, declared_media_type: str | None) -> StoredDriverDocument:
        return await self.publish(await self.prepare(content, declared_media_type=declared_media_type))

    async def read(self, opaque_storage_key: str) -> bytes:
        path = self._path_for(opaque_storage_key)
        try:
            payload = await asyncio.to_thread(self._read_payload, path)
        except FileNotFoundError as error:
            raise DriverDocumentNotFound("Protected driver document not found.") from error
        except OSError as error:
            raise DriverDocumentUnavailable("Protected driver-document storage is unavailable.") from error
        return decrypt_document_payload(self._cipher, opaque_storage_key, payload)

    def _read_payload(self, path: Path) -> bytes:
        limit = encrypted_document_limit(self._max_bytes)
        with path.open("rb") as stream:
            payload = stream.read(limit + 1)
        if not 0 < len(payload) <= limit:
            raise DriverDocumentUnavailable("Protected document object length is invalid.")
        return payload

    async def delete(self, opaque_storage_key: str) -> None:
        path = self._path_for(opaque_storage_key)
        try:
            await asyncio.to_thread(path.unlink, missing_ok=True)
            await asyncio.to_thread(path.with_suffix(".upload").unlink, missing_ok=True)
        except OSError as error:
            raise DriverDocumentUnavailable("Protected driver-document deletion failed.") from error

    def _walk_objects(self) -> Iterator[DriverDocumentObject | None]:
        # Fixed shards avoid sorting/loading an entire directory. Each yielded
        # entry, including foreign names, consumes one page work slot.
        if (self._root / "v1").is_symlink():
            return
        for shard in range(256):
            directory = self._root / "v1" / f"{shard:02x}"
            if directory.is_symlink() or not directory.resolve().is_relative_to(self._root):
                continue
            try:
                entries = os.scandir(directory)
            except FileNotFoundError:
                continue
            with entries:
                for entry in entries:
                    name = entry.name
                    if name.endswith(".upload"):
                        name = name[:-7] + ".bin"
                    key = f"v1/{shard:02x}/{name}"
                    if not _OPAQUE_KEY_PATTERN.fullmatch(key) or not entry.is_file(follow_symlinks=False):
                        yield None
                        continue
                    try:
                        modified = entry.stat(follow_symlinks=False).st_mtime
                    except FileNotFoundError:
                        yield None
                        continue
                    yield DriverDocumentObject(key, datetime.fromtimestamp(modified, UTC))

    async def objects_page(self, *, cursor: str | None, limit: int) -> DriverDocumentObjectPage:
        require_document_page_limit(limit)
        await self._listing_lock.acquire()
        try:
            if cursor is None:
                if self._listing is not None:
                    self._listing.close()
                self._listing = self._walk_objects()
                self._listing_cursor = uuid4().hex
            elif cursor != self._listing_cursor or self._listing is None:
                raise DriverDocumentUnavailable("Protected document listing cursor expired.")

            def page() -> DriverDocumentObjectPage:
                objects = []
                for _ in range(limit):
                    try:
                        item = next(self._listing)
                    except StopIteration:
                        self._listing = None
                        self._listing_cursor = None
                        break
                    if item is not None:
                        objects.append(item)
                return DriverDocumentObjectPage(tuple(objects), self._listing_cursor)

            job = asyncio.create_task(asyncio.to_thread(page))
        except BaseException:
            self._listing_lock.release()
            raise

        def finished(task):
            # The job owns release, including when a caller is cancelled more
            # than once. Shutdown cannot close an executing generator.
            self._listing_lock.release()
            if not task.cancelled():
                task.exception()  # Observe abandoned I/O errors without logging private paths.
        job.add_done_callback(finished)
        try:
            return await asyncio.shield(job)
        except OSError:
            raise DriverDocumentUnavailable("Protected document listing is unavailable.") from None

    async def aclose(self) -> None:
        async with self._listing_lock:
            if self._listing is not None:
                self._listing.close()
                self._listing = None
            self._listing_cursor = None

    def _path_for(self, opaque_storage_key: str) -> Path:
        require_document_key(opaque_storage_key)
        path = (self._root / Path(*opaque_storage_key.split("/"))).resolve()
        if not path.is_relative_to(self._root):
            raise DriverDocumentNotFound("Protected driver document not found.")
        return path

    @staticmethod
    def _atomic_write(path: Path, payload: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        # The durable opaque key also names its staging file. A process crash
        # cannot leave an untraceable random temporary file outside reconciliation.
        temporary_path = path.with_suffix(".upload")
        created = False
        try:
            with temporary_path.open("xb") as stream:
                created = True
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, path)
        finally:
            if created:
                temporary_path.unlink(missing_ok=True)


class InMemoryDriverDocumentStore:
    """Deterministic protected-store substitute for route and worker tests."""

    def __init__(self, scanner: MalwareScanner, *, max_bytes: int = 10 * 1024 * 1024) -> None:
        self._scanner = scanner
        self._max_bytes = max_bytes
        self._content: dict[str, bytes] = {}
        self._modified: dict[str, datetime] = {}

    @property
    def available(self) -> bool:
        return True

    @property
    def max_bytes(self) -> int:
        return self._max_bytes

    async def prepare(self, content: bytes, *, declared_media_type: str | None) -> PreparedDriverDocument:
        media_type = validate_document_upload(content, declared_media_type, self._max_bytes)
        await self._scanner.require_clean(content)
        identifier = uuid4().hex
        key = f"v1/{identifier[:2]}/{identifier[2:]}.bin"
        return PreparedDriverDocument(
            StoredDriverDocument(key, media_type, len(content), sha256(content).hexdigest()), bytes(content)
        )

    async def publish(self, prepared: PreparedDriverDocument) -> StoredDriverDocument:
        require_document_key(prepared.stored.opaque_storage_key)
        self._content[prepared.stored.opaque_storage_key] = prepared.payload
        self._modified[prepared.stored.opaque_storage_key] = datetime.now(UTC)
        return prepared.stored

    async def store(self, content: bytes, *, declared_media_type: str | None) -> StoredDriverDocument:
        return await self.publish(await self.prepare(content, declared_media_type=declared_media_type))

    async def read(self, opaque_storage_key: str) -> bytes:
        try:
            return self._content[opaque_storage_key]
        except KeyError as error:
            raise DriverDocumentNotFound("Protected driver document not found.") from error

    async def delete(self, opaque_storage_key: str) -> None:
        self._content.pop(opaque_storage_key, None)
        self._modified.pop(opaque_storage_key, None)

    async def objects_page(self, *, cursor: str | None, limit: int) -> DriverDocumentObjectPage:
        require_document_page_limit(limit)
        # This substitute is intentionally in-memory; real adapters page the
        # provider/directory instead of sorting their entire object population.
        keys = [key for key in sorted(self._content) if cursor is None or key > cursor]
        chosen = keys[:limit]
        return DriverDocumentObjectPage(
            tuple(DriverDocumentObject(key, self._modified[key]) for key in chosen),
            chosen[-1] if len(keys) > limit else None,
        )

    async def aclose(self) -> None:
        pass


def detect_media_type(content: bytes) -> str:
    """Detect the small allowlist by signatures and required terminal markers."""

    if content.startswith(b"%PDF-") and content.rstrip().endswith(b"%%EOF"):
        return "application/pdf"
    if content.startswith(b"\xff\xd8\xff") and content.rstrip().endswith(b"\xff\xd9"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n") and b"IEND\xaeB`\x82" in content[-32:]:
        return "image/png"
    raise DriverDocumentRejected("The document is not a supported PDF, JPEG, or PNG file.")


def require_document_key(opaque_storage_key: str) -> None:
    if not _OPAQUE_KEY_PATTERN.fullmatch(opaque_storage_key):
        raise DriverDocumentNotFound("Protected driver document not found.")


def require_document_page_limit(limit: int) -> None:
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 1000:
        raise ValueError("Document object pages require a limit between 1 and 1000.")


def validate_document_upload(content: bytes, declared_media_type: str | None, max_bytes: int) -> str:
    if not content:
        raise DriverDocumentRejected("The document is empty.")
    if len(content) > max_bytes:
        raise DriverDocumentRejected(f"The document exceeds the {max_bytes}-byte limit.")
    detected = detect_media_type(content)
    declared = (declared_media_type or "").partition(";")[0].strip().lower()
    if declared not in ALLOWED_MEDIA_TYPES:
        raise DriverDocumentRejected("The declared document media type is not allowed.")
    if declared != detected:
        raise DriverDocumentRejected("The declared and detected document media types do not match.")
    return detected


def encrypt_document_payload(cipher: AESGCM, opaque_storage_key: str, content: bytes) -> bytes:
    require_document_key(opaque_storage_key)
    nonce = os.urandom(_NONCE_BYTES)
    return _ENCRYPTION_VERSION + nonce + cipher.encrypt(nonce, content, opaque_storage_key.encode("ascii"))


def decrypt_document_payload(cipher: AESGCM, opaque_storage_key: str, payload: bytes) -> bytes:
    require_document_key(opaque_storage_key)
    if not payload.startswith(_ENCRYPTION_VERSION) or len(payload) <= len(_ENCRYPTION_VERSION) + _NONCE_BYTES:
        raise DriverDocumentUnavailable("Protected driver-document data is invalid.")
    offset = len(_ENCRYPTION_VERSION)
    try:
        return cipher.decrypt(payload[offset:offset + _NONCE_BYTES], payload[offset + _NONCE_BYTES:], opaque_storage_key.encode("ascii"))
    except InvalidTag as error:
        raise DriverDocumentUnavailable("Protected driver-document integrity validation failed.") from error


def encrypted_document_limit(max_bytes: int) -> int:
    return max_bytes + len(_ENCRYPTION_VERSION) + _NONCE_BYTES + 16  # AES-GCM authentication tag


def create_driver_document_store(
    *,
    backend: str = "filesystem",
    s3_settings: S3DocumentStorageSettings | None = None,
    root: Path | None = None,
    encryption_key: bytes | None = None,
    clamav_host: str | None = None,
    clamav_port: int = 3310,
    clamav_timeout_seconds: float = 10.0,
    max_bytes: int = 10 * 1024 * 1024,
) -> ProtectedDriverDocumentStore:
    """Create a real adapter only when every security dependency is configured."""

    if backend not in {"filesystem", "s3"}:
        raise ValueError("Driver-document storage backend must be filesystem or s3.")
    if (backend == "filesystem" and s3_settings is not None) or (backend == "s3" and root is not None):
        raise ValueError("Document S3 and filesystem settings cannot be mixed.")
    supplied = (root is not None or s3_settings is not None or backend == "s3",
                encryption_key is not None, clamav_host is not None)
    if not any(supplied):
        return DisabledDriverDocumentStore(max_bytes=max_bytes)
    if not all(supplied):
        raise ValueError("Driver-document persistence, encryption key, and ClamAV host must be configured together.")
    assert encryption_key is not None and clamav_host is not None
    scanner = ClamAVScanner(clamav_host, clamav_port, clamav_timeout_seconds)
    if backend == "s3":
        if s3_settings is None:
            raise ValueError("Document S3 settings must be configured together with encryption/scanning.")
        from taximobile_api.integrations.s3_driver_documents import S3DriverDocumentStore
        return S3DriverDocumentStore(s3_settings, encryption_key, scanner, max_bytes=max_bytes)
    assert root is not None
    return EncryptedFilesystemDriverDocumentStore(
        root,
        encryption_key,
        scanner,
        max_bytes=max_bytes,
    )
