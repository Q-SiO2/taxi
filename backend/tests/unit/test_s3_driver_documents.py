import asyncio
from dataclasses import replace
import io
from pathlib import Path
import threading
from datetime import UTC, datetime

from botocore.exceptions import ClientError, ReadTimeoutError
from botocore.awsrequest import AWSResponse
from botocore.stub import ANY, Stubber
import pytest

from taximobile_api.integrations.document_storage_config import S3DocumentStorageSettings
from taximobile_api.integrations.driver_documents import (
    DriverDocumentNotFound, DriverDocumentRejected, DriverDocumentUnavailable,
    EncryptedFilesystemDriverDocumentStore,
)
from taximobile_api.integrations.s3_driver_documents import (
    DriverDocumentWriteUncertain, S3DriverDocumentStore, create_document_s3_client,
)

PDF = b"%PDF-1.7\nsynthetic private S3 fixture\n%%EOF\n"
KEY = bytes(range(32))


def settings(**changes):
    return replace(S3DocumentStorageSettings("https://s3.example.test", "document-fixture-bucket",
                   "document-fixture-access", "document-fixture-secret-only"), **changes)


class Scanner:
    def __init__(self, rejection=None):
        self.rejection = rejection
    async def require_clean(self, content):
        assert content
        if self.rejection:
            raise self.rejection


class Objects:
    def __init__(self):
        self.objects = {}
        self.calls = []
        self.put_error = None
        self.commit_before_error = False
        self.read_error = None
        self.delete_error = None
        self.bodies = []
        self.closed = False
        self.list_response = {"IsTruncated": False}
    def put_object(self, **kwargs):
        self.calls.append(("put", kwargs))
        if self.put_error is None or self.commit_before_error:
            assert kwargs["IfNoneMatch"] == "*" and kwargs["Key"] not in self.objects
            self.objects[kwargs["Key"]] = kwargs["Body"]
        if self.put_error:
            raise self.put_error
        return {}
    def get_object(self, **kwargs):
        self.calls.append(("get", kwargs))
        if self.read_error:
            raise self.read_error
        if kwargs["Key"] not in self.objects:
            raise ClientError({"Error":{"Code":"NoSuchKey"}}, "GetObject")
        payload = self.objects[kwargs["Key"]]
        body = io.BytesIO(payload)
        self.bodies.append(body)
        return {"ContentLength":len(payload),"Body":body}
    def delete_object(self, **kwargs):
        self.calls.append(("delete", kwargs))
        if self.delete_error:
            raise self.delete_error
        self.objects.pop(kwargs["Key"], None)
        return {}
    def close(self):
        self.closed = True
    def list_objects_v2(self, **kwargs):
        self.calls.append(("list", kwargs))
        return self.list_response


@pytest.mark.asyncio
async def test_s3_preparation_performs_no_remote_call_before_durable_registration():
    client = Objects()
    store = S3DriverDocumentStore(settings(), KEY, Scanner(), client=client)
    prepared = await store.prepare(PDF, declared_media_type="application/pdf")
    assert client.calls == [] and client.objects == {}
    assert PDF not in prepared.payload and "payload=" not in repr(prepared)
    assert await store.publish(prepared) == prepared.stored
    assert [method for method, _ in client.calls] == ["put"]
    assert await store.read(prepared.stored.opaque_storage_key) == PDF
    await store.aclose()


@pytest.mark.asyncio
async def test_s3_listing_is_bounded_private_and_passes_the_opaque_cursor():
    client = create_document_s3_client(settings())
    key = "v1/ab/" + "c" * 30 + ".bin"
    now = datetime.now(UTC)
    with Stubber(client) as stub:
        stub.add_response("list_objects_v2", {"IsTruncated": True, "NextContinuationToken": "next-page",
            "Contents": [{"Key": key, "LastModified": now}, {"Key": "v1/foreign.txt", "LastModified": now}]},
            {"Bucket": settings().bucket, "Prefix": "v1/", "MaxKeys": 2})
        stub.add_response("list_objects_v2", {"IsTruncated": False},
            {"Bucket": settings().bucket, "Prefix": "v1/", "MaxKeys": 2, "ContinuationToken": "next-page"})
        store = S3DriverDocumentStore(settings(), KEY, Scanner(), client=client)
        page = await store.objects_page(cursor=None, limit=2)
        assert page.next_cursor == "next-page"
        assert [(item.opaque_storage_key, item.last_modified) for item in page.objects] == [(key, now)]
        last = await store.objects_page(cursor=page.next_cursor, limit=2)
        assert last.objects == () and last.next_cursor is None
        stub.assert_no_pending_responses()
        await store.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("response", [
    {"IsTruncated": True},
    {"IsTruncated": True, "NextContinuationToken": "same"},
    {"IsTruncated": "false"},
    {"IsTruncated": False, "Contents": [{"Key": "v1/ab/" + "c" * 30 + ".bin", "LastModified": datetime(2026, 1, 1)}]},
    {"IsTruncated": False, "Contents": [{"Key": 123}]},
    {"IsTruncated": False, "Contents": [{}, {}]},
])
async def test_s3_listing_rejects_malformed_provider_pages(response):
    client = Objects()
    client.list_response = response
    store = S3DriverDocumentStore(settings(), KEY, Scanner(), client=client)
    with pytest.raises(DriverDocumentUnavailable, match="listing is invalid"):
        await store.objects_page(cursor="same", limit=1)
    assert [method for method, _ in client.calls] == ["list"]
    await store.aclose()


def test_real_sdk_uses_explicit_credentials_verified_tls_and_one_attempt(monkeypatch):
    monkeypatch.setenv("AWS_ENDPOINT_URL_S3", "http://unreviewed.example.test")
    client = create_document_s3_client(settings())
    try:
        config = client.meta.config
        assert client.meta.endpoint_url == "https://s3.example.test"
        assert config.signature_version == "s3v4" and config.retries["total_max_attempts"] == 1
        assert config.connect_timeout == 5 and config.read_timeout == 5
        assert config.max_pool_connections == 2 and config.s3["addressing_style"] == "virtual"
        # Botocore consumes this option during endpoint resolution rather than
        # retaining it in client.meta.config; assert the resulting endpoint above.
        assert config.proxies == {}
        assert client._endpoint.http_session._verify is True
        assert client._request_signer._credentials.access_key == settings().access_key_id
    finally:
        client.close()


@pytest.mark.asyncio
async def test_sdk_model_accepts_the_exact_conditional_ciphertext_upload():
    client = create_document_s3_client(settings())
    with Stubber(client) as stub:
        stub.add_response("put_object", {}, {"Bucket":settings().bucket,"Key":ANY,"Body":ANY,
                          "ContentLength":len(PDF)+34,"ContentType":"application/octet-stream",
                          "CacheControl":"no-store","IfNoneMatch":"*"})
        store = S3DriverDocumentStore(settings(),KEY,Scanner(),client=client)
        saved = await store.store(PDF,declared_media_type="application/pdf")
        assert saved.byte_size == len(PDF) and saved.media_type == "application/pdf"
        stub.assert_no_pending_responses()
        await store.aclose()


@pytest.mark.asyncio
async def test_private_encrypted_roundtrip_read_body_closure_and_idempotent_erasure():
    client = Objects();store=S3DriverDocumentStore(settings(),KEY,Scanner(),client=client)
    saved=await store.store(PDF,declared_media_type="application/pdf")
    put=client.calls[0][1]
    assert PDF not in put["Body"] and put["ContentType"]=="application/octet-stream"
    assert set(put)=={"Bucket","Key","Body","ContentLength","ContentType","CacheControl","IfNoneMatch"}
    assert await store.read(saved.opaque_storage_key)==PDF
    assert all(body.closed for body in client.bodies)
    await store.delete(saved.opaque_storage_key);await store.delete(saved.opaque_storage_key)
    with pytest.raises(DriverDocumentNotFound):await store.read(saved.opaque_storage_key)
    await store.aclose();assert client.closed and not store.available


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["malware","unavailable","wrong_media","oversized"])
async def test_invalid_or_unscanned_plaintext_never_reaches_the_sdk(failure):
    error=DriverDocumentRejected("fixture") if failure=="malware" else DriverDocumentUnavailable("fixture") if failure=="unavailable" else None
    client=Objects();store=S3DriverDocumentStore(settings(),KEY,Scanner(error),client=client,max_bytes=8 if failure=="oversized" else 1024)
    with pytest.raises((DriverDocumentRejected,DriverDocumentUnavailable)):
        await store.store(PDF,declared_media_type="image/png" if failure=="wrong_media" else "application/pdf")
    assert client.calls==[]
    await store.aclose()


@pytest.mark.asyncio
async def test_acknowledgement_loss_is_confirmed_by_exact_readback_without_reupload():
    client=Objects();client.put_error=ReadTimeoutError(endpoint_url="https://private-fixture.example.test")
    client.commit_before_error=True
    store=S3DriverDocumentStore(settings(),KEY,Scanner(),client=client)
    saved=await store.store(PDF,declared_media_type="application/pdf")
    assert [call[0] for call in client.calls]==["put","get"]
    assert await store.read(saved.opaque_storage_key)==PDF
    await store.aclose()


@pytest.mark.asyncio
async def test_unconfirmed_write_retains_internal_recovery_identity_without_secret_error_or_retry():
    client=Objects();client.put_error=ReadTimeoutError(endpoint_url="https://private-fixture.example.test")
    store=S3DriverDocumentStore(settings(),KEY,Scanner(),client=client)
    with pytest.raises(DriverDocumentWriteUncertain) as error:
        await store.store(PDF,declared_media_type="application/pdf")
    assert [call[0] for call in client.calls]==["put","get"]
    assert error.value.stored.byte_size==len(PDF)
    assert error.value.stored.opaque_storage_key not in str(error.value)
    assert "private-fixture" not in str(error.value)
    await store.aclose()


@pytest.mark.asyncio
async def test_cross_adapter_ciphertext_recovery_and_wrong_key_rejection(tmp_path: Path):
    client=Objects();remote=S3DriverDocumentStore(settings(),KEY,Scanner(),client=client)
    saved=await remote.store(PDF,declared_media_type="application/pdf")
    path=tmp_path.joinpath(*saved.opaque_storage_key.split("/"));path.parent.mkdir(parents=True)
    path.write_bytes(client.objects[saved.opaque_storage_key])
    local=EncryptedFilesystemDriverDocumentStore(tmp_path,KEY,Scanner())
    assert await local.read(saved.opaque_storage_key)==PDF
    second=await local.store(PDF,declared_media_type="application/pdf")
    client.objects[second.opaque_storage_key]=tmp_path.joinpath(*second.opaque_storage_key.split("/")).read_bytes()
    assert await remote.read(second.opaque_storage_key)==PDF
    wrong=S3DriverDocumentStore(settings(),bytes(reversed(KEY)),Scanner(),client=client)
    with pytest.raises(DriverDocumentUnavailable,match="integrity"):await wrong.read(saved.opaque_storage_key)
    await remote.aclose();await wrong.aclose()


@pytest.mark.asyncio
async def test_oversized_and_tampered_objects_are_rejected_with_closed_response_bodies():
    client=Objects();store=S3DriverDocumentStore(settings(),KEY,Scanner(),client=client,max_bytes=1024)
    saved=await store.store(PDF,declared_media_type="application/pdf")
    original=client.objects[saved.opaque_storage_key]
    for payload in (b"x"*1059, original[:-1]+bytes([original[-1]^1])):
        client.objects[saved.opaque_storage_key]=payload
        with pytest.raises(DriverDocumentUnavailable):await store.read(saved.opaque_storage_key)
        assert client.bodies[-1].closed
    await store.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["read","delete"])
async def test_provider_denials_are_not_silently_accepted_or_exposed(operation):
    client=Objects();error=ClientError({"Error":{"Code":"AccessDenied","Message":"private-fixture"}},"GetObject")
    client.read_error=error;client.delete_error=error
    store=S3DriverDocumentStore(settings(),KEY,Scanner(),client=client)
    with pytest.raises(DriverDocumentUnavailable) as failure:
        await getattr(store,operation)("v1/aa/"+"b"*30+".bin")
    assert "private-fixture" not in str(failure.value)
    await store.aclose()


@pytest.mark.asyncio
async def test_invalid_keys_do_not_reach_the_sdk():
    client=Objects();store=S3DriverDocumentStore(settings(),KEY,Scanner(),client=client)
    for operation in (store.read,store.delete):
        with pytest.raises(DriverDocumentNotFound):await operation("../../other")
    assert not client.calls
    await store.aclose()


@pytest.mark.asyncio
async def test_cancelled_waiter_does_not_release_an_active_sdk_slot():
    client=Objects();store=S3DriverDocumentStore(settings(max_in_flight=1),KEY,Scanner(),client=client)
    started=threading.Event();release=threading.Event();second_started=threading.Event()
    def blocked():
        started.set();assert release.wait(3)
    task=asyncio.create_task(store._run_io(blocked))
    assert await asyncio.to_thread(started.wait,2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):await task
    second=asyncio.create_task(store._run_io(second_started.set))
    try:
        await asyncio.sleep(.03);assert not second_started.is_set()
    finally:
        release.set()
        await asyncio.wait_for(second,2)
        await store.aclose()
    assert second_started.is_set() and not store._pending


@pytest.mark.asyncio
@pytest.mark.parametrize("status,code", [(503,"SlowDown"),(301,"PermanentRedirect"),(400,"AuthorizationHeaderMalformed")])
async def test_real_sdk_error_responses_never_trigger_a_second_put_or_region_discovery(monkeypatch,status,code):
    class Raw(io.BytesIO):
        def stream(self,amt=1024,decode_content=False):
            while part:=self.read(amt):
                yield part
    requests=[]
    def send(request):
        requests.append((request.method,request.url))
        assert len(requests)<8,"SDK replayed a request unexpectedly"
        assert request.url.startswith("https://document-fixture-bucket.s3.example.test/")
        if request.method=="PUT":
            body=f'<Error><Code>{code}</Code><Region>unreviewed-region</Region></Error>'.encode()
            return AWSResponse(request.url,status,{"Content-Length":str(len(body)),"x-amz-bucket-region":"unreviewed-region"},Raw(body))
        body=b'<Error><Code>NoSuchKey</Code></Error>'
        return AWSResponse(request.url,404,{"Content-Length":str(len(body))},Raw(body))
    client=create_document_s3_client(settings())
    monkeypatch.setattr(client._endpoint.http_session,"send",send)
    store=S3DriverDocumentStore(settings(),KEY,Scanner(),client=client)
    try:
        with pytest.raises(DriverDocumentWriteUncertain):
            await store.store(PDF,declared_media_type="application/pdf")
        assert [method for method,_url in requests]==["PUT","GET"]
    finally:
        await store.aclose()
