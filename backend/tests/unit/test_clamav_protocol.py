"""Real loopback TCP protocol probes; these do not substitute for a ClamAV daemon."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import struct

import pytest

from taximobile_api.integrations.driver_documents import (
    ClamAVScanner,
    DriverDocumentRejected,
    DriverDocumentUnavailable,
    EncryptedFilesystemDriverDocumentStore,
)


PDF = b"%PDF-1.7\nsynthetic scanner protocol fixture\n%%EOF\n"


@asynccontextmanager
async def scanner_server(parts, *, delay=0, hold=False, before_reply_delay=0):
    received = []
    tasks = set()
    release = asyncio.Event()

    async def serve(reader, writer):
        task = asyncio.current_task()
        tasks.add(task)
        try:
            assert await reader.readuntil(b"\0") == b"zINSTREAM\0"
            chunks = []
            while True:
                size = struct.unpack("!I", await reader.readexactly(4))[0]
                if size == 0:
                    break
                assert 0 < size <= 64 * 1024
                chunks.append(await reader.readexactly(size))
            received.append(b"".join(chunks))
            if before_reply_delay:
                await asyncio.sleep(before_reply_delay)
            for part in parts:
                writer.write(part)
                await writer.drain()
                if delay:
                    await asyncio.sleep(delay)
            if hold:
                await release.wait()
        except (ConnectionError, asyncio.IncompleteReadError):
            # A bounded/cancelled client deliberately closes an unfinished reply.
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except ConnectionError:
                pass
            tasks.discard(task)

    server = await asyncio.start_server(serve, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        yield port, received
    finally:
        release.set()
        server.close()
        await server.wait_closed()
        pending = tuple(tasks)
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)


@pytest.mark.asyncio
async def test_scanner_streams_all_chunks_and_accepts_a_complete_clean_reply():
    content = PDF + b"x" * (2 * 64 * 1024)
    async with scanner_server([b"stream: OK\0"]) as (port, received):
        await ClamAVScanner("127.0.0.1", port, 2).require_clean(content)
    assert received == [content]


@pytest.mark.asyncio
async def test_clean_reply_may_cross_tcp_fragments_and_delimiter():
    async with scanner_server([b"str", b"eam: ", b"OK", b"\0"], delay=0.02) as (port, received):
        await ClamAVScanner("127.0.0.1", port, 2).require_clean(PDF)
    assert received == [PDF]


@pytest.mark.asyncio
@pytest.mark.parametrize("reply", [
    b"", b"stream: OK", b"stream: OK\n", b"stream: OK\r\n", b"other: OK\0",
    b"scan error OK\0", b" stream: OK\0", b"stream: OK\0stream: OK\0",
    b"stream: OK\0stream: Eicar-Signature FOUND\0", b"stream: failed ERROR\0",
    b"stream: \0", b"stream: FOUND\0", b"x" * 4097 + b" OK\0",
])
async def test_invalid_unterminated_multiple_or_oversized_replies_never_persist(tmp_path: Path, reply):
    async with scanner_server([reply]) as (port, received):
        store = EncryptedFilesystemDriverDocumentStore(tmp_path, bytes(range(32)), ClamAVScanner("127.0.0.1", port, 2))
        with pytest.raises(DriverDocumentUnavailable):
            await store.store(PDF, declared_media_type="application/pdf")
    assert received == [PDF]
    assert list(tmp_path.rglob("*.bin")) == []
    assert list(tmp_path.rglob(".upload-*")) == []


@pytest.mark.asyncio
async def test_malware_reply_is_rejected_without_echoing_scanner_details(tmp_path: Path):
    signature = b"PrivateFixture-Signature"
    async with scanner_server([b"stream: " + signature + b" FOUND\0"]) as (port, _received):
        store = EncryptedFilesystemDriverDocumentStore(tmp_path, bytes(range(32)), ClamAVScanner("127.0.0.1", port, 2))
        with pytest.raises(DriverDocumentRejected) as error:
            await store.store(PDF, declared_media_type="application/pdf")
    assert signature.decode() not in str(error.value)
    assert list(tmp_path.rglob("*.bin")) == []


@pytest.mark.asyncio
async def test_clean_prefix_without_connection_completion_times_out_and_never_persists(tmp_path: Path):
    async with scanner_server([b"stream: OK\0"], hold=True) as (port, _received):
        store = EncryptedFilesystemDriverDocumentStore(tmp_path, bytes(range(32)), ClamAVScanner("127.0.0.1", port, 0.1))
        with pytest.raises(DriverDocumentUnavailable):
            await asyncio.wait_for(store.store(PDF, declared_media_type="application/pdf"), 2)
    assert list(tmp_path.rglob("*.bin")) == []


@pytest.mark.asyncio
async def test_cancelled_scan_propagates_and_never_persists(tmp_path: Path):
    async with scanner_server([], hold=True) as (port, received):
        store = EncryptedFilesystemDriverDocumentStore(tmp_path, bytes(range(32)), ClamAVScanner("127.0.0.1", port, 2))
        task = asyncio.create_task(store.store(PDF, declared_media_type="application/pdf"))
        async with asyncio.timeout(2):
            while not received:
                await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert list(tmp_path.rglob("*.bin")) == []


@pytest.mark.asyncio
async def test_one_deadline_covers_connection_and_reply_instead_of_resetting_each_phase(monkeypatch):
    original_connect = asyncio.open_connection
    async def delayed_connect(*args, **kwargs):
        await asyncio.sleep(0.09)
        return await original_connect(*args, **kwargs)
    async with scanner_server([b"stream: OK\0"], before_reply_delay=0.09) as (port, received):
        monkeypatch.setattr(asyncio, "open_connection", delayed_connect)
        with pytest.raises(DriverDocumentUnavailable):
            await ClamAVScanner("127.0.0.1", port, 0.15).require_clean(PDF)
    assert received == [PDF]
