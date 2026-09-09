"""Encrypted, malware-scanned storage for applicant-owned documents.

The database stores only an opaque key and bounded metadata. File bytes are
accepted only after independent media detection and a successful ClamAV scan,
then encrypted with AES-256-GCM before they reach the configured private
filesystem. Any unavailable dependency fails closed.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import re
import struct
import tempfile
from typing import Protocol
from uuid import uuid4

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


ALLOWED_MEDIA_TYPES = frozenset({"application/pdf", "image/jpeg", "image/png"})
_OPAQUE_KEY_PATTERN = re.compile(r"v1/[0-9a-f]{2}/[0-9a-f]{30}\.bin")
_ENCRYPTION_VERSION = b"TMDOC1"
_NONCE_BYTES = 12
_SCAN_CHUNK_BYTES = 64 * 1024


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


class MalwareScanner(Protocol):
    async def require_clean(self, content: bytes) -> None: ...


class ProtectedDriverDocumentStore(Protocol):
    @property
    def available(self) -> bool: ...

    @property
    def max_bytes(self) -> int: ...

    async def store(self, content: bytes, *, declared_media_type: str | None) -> StoredDriverDocument: ...

    async def read(self, opaque_storage_key: str) -> bytes: ...

    async def delete(self, opaque_storage_key: str) -> None: ...


class DisabledDriverDocumentStore:
    def __init__(self, *, max_bytes: int = 10 * 1024 * 1024) -> None:
        self._max_bytes = max_bytes

    @property
    def available(self) -> bool:
        return False

    @property
    def max_bytes(self) -> int:
        return self._max_bytes

    async def store(self, content: bytes, *, declared_media_type: str | None) -> StoredDriverDocument:
        del content, declared_media_type
        raise DriverDocumentUnavailable("Protected driver-document storage is not configured.")

    async def read(self, opaque_storage_key: str) -> bytes:
        del opaque_storage_key
        raise DriverDocumentUnavailable("Protected driver-document storage is not configured.")

    async def delete(self, opaque_storage_key: str) -> None:
        del opaque_storage_key
        raise DriverDocumentUnavailable("Protected driver-document storage is not configured.")


class ClamAVScanner:
    """Small async client for ClamAV's bounded INSTREAM protocol."""

    def __init__(self, host: str, port: int = 3310, timeout_seconds: float = 10.0) -> None:
        self._host = host
        self._port = port
        self._timeout_seconds = timeout_seconds

    async def require_clean(self, content: bytes) -> None:
        writer: asyncio.StreamWriter | None = None
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=self._timeout_seconds,
            )
            writer.write(b"zINSTREAM\0")
            for offset in range(0, len(content), _SCAN_CHUNK_BYTES):
                chunk = content[offset : offset + _SCAN_CHUNK_BYTES]
                writer.write(struct.pack("!I", len(chunk)))
                writer.write(chunk)
            writer.write(struct.pack("!I", 0))
            await asyncio.wait_for(writer.drain(), timeout=self._timeout_seconds)
            response = await asyncio.wait_for(reader.read(4096), timeout=self._timeout_seconds)
        except (OSError, TimeoutError, asyncio.IncompleteReadError) as error:
            raise DriverDocumentUnavailable("Malware scanning is temporarily unavailable.") from error
        finally:
            if writer is not None:
                writer.close()
                try:
                    await writer.wait_closed()
                except OSError:
                    pass

        normalized = response.rstrip(b"\0\r\n")
        if normalized.endswith(b" OK"):
            return
        if normalized.endswith(b" FOUND"):
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

    @property
    def available(self) -> bool:
        return True

    @property
    def max_bytes(self) -> int:
        return self._max_bytes

    async def store(self, content: bytes, *, declared_media_type: str | None) -> StoredDriverDocument:
        if not content:
            raise DriverDocumentRejected("The document is empty.")
        if len(content) > self._max_bytes:
            raise DriverDocumentRejected(f"The document exceeds the {self._max_bytes}-byte limit.")
        detected_media_type = detect_media_type(content)
        normalized_declared = (declared_media_type or "").partition(";")[0].strip().lower()
        if normalized_declared not in ALLOWED_MEDIA_TYPES:
            raise DriverDocumentRejected("The declared document media type is not allowed.")
        if normalized_declared != detected_media_type:
            raise DriverDocumentRejected("The declared and detected document media types do not match.")

        await self._scanner.require_clean(content)
        identifier = uuid4().hex
        opaque_key = f"v1/{identifier[:2]}/{identifier[2:]}.bin"
        path = self._path_for(opaque_key)
        nonce = os.urandom(_NONCE_BYTES)
        encrypted = self._cipher.encrypt(nonce, content, opaque_key.encode("ascii"))
        payload = _ENCRYPTION_VERSION + nonce + encrypted
        await asyncio.to_thread(self._atomic_write, path, payload)
        return StoredDriverDocument(
            opaque_storage_key=opaque_key,
            media_type=detected_media_type,
            byte_size=len(content),
            sha256=sha256(content).hexdigest(),
        )

    async def read(self, opaque_storage_key: str) -> bytes:
        path = self._path_for(opaque_storage_key)
        try:
            payload = await asyncio.to_thread(path.read_bytes)
        except FileNotFoundError as error:
            raise DriverDocumentNotFound("Protected driver document not found.") from error
        except OSError as error:
            raise DriverDocumentUnavailable("Protected driver-document storage is unavailable.") from error
        if not payload.startswith(_ENCRYPTION_VERSION) or len(payload) <= len(_ENCRYPTION_VERSION) + _NONCE_BYTES:
            raise DriverDocumentUnavailable("Protected driver-document data is invalid.")
        offset = len(_ENCRYPTION_VERSION)
        nonce = payload[offset : offset + _NONCE_BYTES]
        ciphertext = payload[offset + _NONCE_BYTES :]
        try:
            return self._cipher.decrypt(nonce, ciphertext, opaque_storage_key.encode("ascii"))
        except InvalidTag as error:
            raise DriverDocumentUnavailable("Protected driver-document integrity validation failed.") from error

    async def delete(self, opaque_storage_key: str) -> None:
        path = self._path_for(opaque_storage_key)
        try:
            await asyncio.to_thread(path.unlink, missing_ok=True)
        except OSError as error:
            raise DriverDocumentUnavailable("Protected driver-document deletion failed.") from error

    def _path_for(self, opaque_storage_key: str) -> Path:
        if not _OPAQUE_KEY_PATTERN.fullmatch(opaque_storage_key):
            raise DriverDocumentNotFound("Protected driver document not found.")
        path = (self._root / Path(*opaque_storage_key.split("/"))).resolve()
        if not path.is_relative_to(self._root):
            raise DriverDocumentNotFound("Protected driver document not found.")
        return path

    @staticmethod
    def _atomic_write(path: Path, payload: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=".upload-", dir=path.parent)
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, path)
        finally:
            temporary_path.unlink(missing_ok=True)


class InMemoryDriverDocumentStore:
    """Deterministic protected-store substitute for route and worker tests."""

    def __init__(self, scanner: MalwareScanner, *, max_bytes: int = 10 * 1024 * 1024) -> None:
        self._scanner = scanner
        self._max_bytes = max_bytes
        self._content: dict[str, bytes] = {}

    @property
    def available(self) -> bool:
        return True

    @property
    def max_bytes(self) -> int:
        return self._max_bytes

    async def store(self, content: bytes, *, declared_media_type: str | None) -> StoredDriverDocument:
        if not content or len(content) > self._max_bytes:
            raise DriverDocumentRejected("The document is empty or exceeds the configured size limit.")
        media_type = detect_media_type(content)
        declared = (declared_media_type or "").partition(";")[0].strip().lower()
        if declared != media_type or declared not in ALLOWED_MEDIA_TYPES:
            raise DriverDocumentRejected("The declared and detected document media types do not match.")
        await self._scanner.require_clean(content)
        identifier = uuid4().hex
        key = f"v1/{identifier[:2]}/{identifier[2:]}.bin"
        self._content[key] = bytes(content)
        return StoredDriverDocument(key, media_type, len(content), sha256(content).hexdigest())

    async def read(self, opaque_storage_key: str) -> bytes:
        try:
            return self._content[opaque_storage_key]
        except KeyError as error:
            raise DriverDocumentNotFound("Protected driver document not found.") from error

    async def delete(self, opaque_storage_key: str) -> None:
        self._content.pop(opaque_storage_key, None)


def detect_media_type(content: bytes) -> str:
    """Detect the small allowlist by signatures and required terminal markers."""

    if content.startswith(b"%PDF-") and content.rstrip().endswith(b"%%EOF"):
        return "application/pdf"
    if content.startswith(b"\xff\xd8\xff") and content.rstrip().endswith(b"\xff\xd9"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n") and b"IEND\xaeB`\x82" in content[-32:]:
        return "image/png"
    raise DriverDocumentRejected("The document is not a supported PDF, JPEG, or PNG file.")


def create_driver_document_store(
    *,
    root: Path | None = None,
    encryption_key: bytes | None = None,
    clamav_host: str | None = None,
    clamav_port: int = 3310,
    clamav_timeout_seconds: float = 10.0,
    max_bytes: int = 10 * 1024 * 1024,
) -> ProtectedDriverDocumentStore:
    """Create a real adapter only when every security dependency is configured."""

    supplied = (root is not None, encryption_key is not None, clamav_host is not None)
    if not any(supplied):
        return DisabledDriverDocumentStore(max_bytes=max_bytes)
    if not all(supplied):
        raise ValueError("Driver-document root, encryption key, and ClamAV host must be configured together.")
    assert root is not None and encryption_key is not None and clamav_host is not None
    return EncryptedFilesystemDriverDocumentStore(
        root,
        encryption_key,
        ClamAVScanner(clamav_host, clamav_port, clamav_timeout_seconds),
        max_bytes=max_bytes,
    )
