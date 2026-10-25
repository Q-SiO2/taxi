"""Bounded private S3 transport for the existing authenticated document envelope.

Factory/API activation also requires the durable upload/outcome workflow. This
transport alone does not establish file/database or process-death reconciliation.
"""

import asyncio
from datetime import UTC, datetime
from functools import partial
from hashlib import sha256
from hmac import compare_digest
from typing import Any, Callable
from uuid import uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from taximobile_api.integrations.document_storage_config import S3DocumentStorageSettings
from taximobile_api.integrations.driver_documents import (
    DriverDocumentNotFound,
    DriverDocumentUnavailable,
    DriverDocumentObject,
    DriverDocumentObjectPage,
    MalwareScanner,
    PreparedDriverDocument,
    StoredDriverDocument,
    decrypt_document_payload,
    encrypted_document_limit,
    encrypt_document_payload,
    require_document_key,
    require_document_page_limit,
    validate_document_upload,
)


class DriverDocumentWriteUncertain(DriverDocumentUnavailable):
    """Internal cleanup metadata; the exception message contains no object key."""

    def __init__(self, stored: StoredDriverDocument):
        super().__init__("Protected document upload could not be confirmed; recovery is required.")
        self.stored = stored


def create_document_s3_client(settings: S3DocumentStorageSettings):
    settings.validate()
    session = boto3.session.Session(aws_access_key_id=settings.access_key_id,
                                    aws_secret_access_key=settings.secret_access_key,
                                    region_name=settings.region)
    client = session.client("s3", endpoint_url=settings.endpoint.rstrip("/"), use_ssl=True, verify=True,
        config=Config(signature_version="s3v4", connect_timeout=settings.timeout_seconds,
                      read_timeout=settings.timeout_seconds, max_pool_connections=settings.max_in_flight,
                      retries={"mode": "standard", "total_max_attempts": 1},
                      s3={"addressing_style": settings.addressing_style}, proxies={},
                      request_checksum_calculation="when_required", response_checksum_validation="when_required",
                      ignore_configured_endpoint_urls=True))
    # S3's separate region redirect handler can replay a PUT even with the
    # standard retry budget set to one. Stop error responses before retry/region
    # handlers; recovery is an explicit same-key readback in the adapter.
    def single_attempt(response, operation, **_kwargs):
        if response is not None and response[0] is not None and response[0].status_code >= 300:
            raise ClientError(response[1], operation.name)
    client.meta.events.register_first("needs-retry.s3", single_attempt,
                                      unique_id="taximobile-document-single-attempt")
    return client


class S3DriverDocumentStore:
    def __init__(self, settings: S3DocumentStorageSettings, encryption_key: bytes,
                 scanner: MalwareScanner, *, max_bytes: int = 10 * 1024 * 1024, client: Any = None):
        settings.validate()
        if len(encryption_key) != 32 or max_bytes < 1:
            raise ValueError("Document storage requires a 32-byte key and a positive size limit.")
        self._settings = settings
        self._cipher = AESGCM(encryption_key)
        self._scanner = scanner
        self._max_bytes = max_bytes
        self._client = create_document_s3_client(settings) if client is None else client
        self._gate = asyncio.Semaphore(settings.max_in_flight)
        self._pending: set[asyncio.Task] = set()
        self._closing = False

    @property
    def available(self) -> bool:
        return not self._closing

    @property
    def max_bytes(self) -> int:
        return self._max_bytes

    async def _run_io(self, operation: Callable):
        if self._closing:
            raise DriverDocumentUnavailable("Protected object storage is closing.")
        deadline = 2 * self._settings.timeout_seconds + 1
        async with asyncio.timeout(deadline):
            await self._gate.acquire()
            if self._closing:
                self._gate.release()
                raise DriverDocumentUnavailable("Protected object storage is closing.")
            job = asyncio.create_task(asyncio.to_thread(operation))
            self._pending.add(job)
            def finished(task):
                self._pending.discard(task)
                self._gate.release()
                if not task.cancelled():
                    task.exception()  # Observe an abandoned SDK exception without emitting its details.
            job.add_done_callback(finished)
            # Caller cancellation/deadline must not free a slot while a blocking
            # SDK operation still runs. The done callback owns release.
            return await asyncio.shield(job)

    def _fetch_payload(self, opaque_storage_key: str) -> bytes:
        response = self._client.get_object(Bucket=self._settings.bucket, Key=opaque_storage_key)
        body = response["Body"]
        try:
            limit = encrypted_document_limit(self._max_bytes)
            length = response.get("ContentLength")
            if not isinstance(length, int) or isinstance(length, bool) or not 0 < length <= limit:
                raise DriverDocumentUnavailable("Protected document object length is invalid.")
            payload = body.read(limit + 1)
            if len(payload) != length or len(payload) > limit:
                raise DriverDocumentUnavailable("Protected document object length is invalid.")
            return payload
        finally:
            body.close()

    async def prepare(self, content: bytes, *, declared_media_type: str | None) -> PreparedDriverDocument:
        media_type = validate_document_upload(content, declared_media_type, self._max_bytes)
        await self._scanner.require_clean(content)
        identifier = uuid4().hex
        key = f"v1/{identifier[:2]}/{identifier[2:]}.bin"
        payload = encrypt_document_payload(self._cipher, key, content)
        stored = StoredDriverDocument(key, media_type, len(content), sha256(content).hexdigest())
        return PreparedDriverDocument(stored, payload)

    async def publish(self, prepared: PreparedDriverDocument) -> StoredDriverDocument:
        stored, payload = prepared.stored, prepared.payload
        key = stored.opaque_storage_key
        require_document_key(key)
        try:
            await self._run_io(partial(self._client.put_object, Bucket=self._settings.bucket, Key=key,
                                      Body=payload, ContentLength=len(payload), ContentType="application/octet-stream",
                                      CacheControl="no-store", IfNoneMatch="*"))
        except (BotoCoreError, ClientError, OSError, TimeoutError):
            # A readback can confirm the exact acknowledged object; never issue
            # another PUT or erase a different object on a key collision.
            try:
                observed = await self._run_io(partial(self._fetch_payload, key))
                if compare_digest(observed, payload):
                    return stored
            except (BotoCoreError, ClientError, OSError, TimeoutError, DriverDocumentUnavailable):
                pass
            raise DriverDocumentWriteUncertain(stored) from None
        return stored

    async def store(self, content: bytes, *, declared_media_type: str | None) -> StoredDriverDocument:
        return await self.publish(await self.prepare(content, declared_media_type=declared_media_type))

    async def read(self, opaque_storage_key: str) -> bytes:
        require_document_key(opaque_storage_key)
        try:
            payload = await self._run_io(partial(self._fetch_payload, opaque_storage_key))
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") in {"NoSuchKey", "404", "NotFound"}:
                raise DriverDocumentNotFound("Protected driver document not found.") from None
            raise DriverDocumentUnavailable("Protected object storage is unavailable.") from None
        except (BotoCoreError, OSError, TimeoutError):
            raise DriverDocumentUnavailable("Protected object storage is unavailable.") from None
        return decrypt_document_payload(self._cipher, opaque_storage_key, payload)

    async def delete(self, opaque_storage_key: str) -> None:
        require_document_key(opaque_storage_key)
        try:
            await self._run_io(partial(self._client.delete_object, Bucket=self._settings.bucket, Key=opaque_storage_key))
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") in {"NoSuchKey", "404", "NotFound"}:
                return
            raise DriverDocumentUnavailable("Protected document erasure could not be confirmed.") from None
        except (BotoCoreError, OSError, TimeoutError):
            raise DriverDocumentUnavailable("Protected document erasure could not be confirmed.") from None

    async def objects_page(self, *, cursor: str | None, limit: int) -> DriverDocumentObjectPage:
        require_document_page_limit(limit)
        if cursor is not None and (not isinstance(cursor, str) or not 0 < len(cursor) <= 4096):
            raise DriverDocumentUnavailable("Protected document listing cursor is invalid.")
        arguments = {"Bucket": self._settings.bucket, "Prefix": "v1/", "MaxKeys": limit}
        if cursor is not None:
            arguments["ContinuationToken"] = cursor
        try:
            response = await self._run_io(partial(self._client.list_objects_v2, **arguments))
        except (BotoCoreError, ClientError, OSError, TimeoutError):
            raise DriverDocumentUnavailable("Protected document listing is unavailable.") from None
        contents = response.get("Contents", [])
        truncated = response.get("IsTruncated")
        next_cursor = response.get("NextContinuationToken") if truncated else None
        if (not isinstance(contents, list) or len(contents) > limit
                or not isinstance(truncated, bool)
                or (truncated and (not isinstance(next_cursor, str) or not 0 < len(next_cursor) <= 4096
                                   or next_cursor == cursor))):
            raise DriverDocumentUnavailable("Protected document listing is invalid.")
        objects = []
        for item in contents:
            if not isinstance(item, dict):
                raise DriverDocumentUnavailable("Protected document listing is invalid.")
            key, modified = item.get("Key"), item.get("LastModified")
            if not isinstance(key, str):
                raise DriverDocumentUnavailable("Protected document listing is invalid.")
            try:
                require_document_key(key)
            except DriverDocumentNotFound:
                continue  # Never erase foreign objects, even under the listed prefix.
            if not isinstance(modified, datetime) or modified.utcoffset() is None:
                raise DriverDocumentUnavailable("Protected document listing is invalid.")
            objects.append(DriverDocumentObject(key, modified.astimezone(UTC)))
        return DriverDocumentObjectPage(tuple(objects), next_cursor)

    async def aclose(self) -> None:
        self._closing = True
        if self._pending:
            _done, pending = await asyncio.wait(tuple(self._pending), timeout=2 * self._settings.timeout_seconds + 1)
            if pending:
                raise DriverDocumentUnavailable("Protected object operations have not drained.")
        await asyncio.wait_for(asyncio.to_thread(self._client.close), timeout=self._settings.timeout_seconds)
