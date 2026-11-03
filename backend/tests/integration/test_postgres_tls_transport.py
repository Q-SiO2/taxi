"""Opt-in real PostgreSQL TLS probes; never borrow the ordinary cloning fixture.

The operator supplies authenticated loopback-only isolated targets and generated
CA fixtures. These probes issue reads and an already-current no-op migration.
They cannot accept a hosted deployment or certificate rotation.
"""

import asyncio
from dataclasses import replace
import os
from pathlib import Path
import ssl
import subprocess
import sys

import pytest
import asyncpg
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.engine import make_url

from taximobile_api.core.config import Settings
from taximobile_api.core.live_events import PostgresLiveEventListener
from taximobile_api.core.realtime import EventHub
from taximobile_api.db.session import create_session_factory
from taximobile_api.db.transport import DatabaseTLS

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def isolated_integration_database():
    """Replace cloning with strict opt-in guards for existing TLS-only targets."""
    if os.getenv("TAXIMOBILE_RUN_TLS_INTEGRATION") != "1":
        pytest.skip("Requires explicit isolated PostgreSQL TLS fixtures")
    assert os.getenv("TAXIMOBILE_ENV") == "test"
    for name in ("TAXIMOBILE_TLS_TEST_DATABASE_URL", "TAXIMOBILE_TLS_TEST_MIGRATION_URL", "TAXIMOBILE_TLS_TEST_PLAIN_URL"):
        url = make_url(os.environ[name])
        assert url.drivername == "postgresql+asyncpg" and url.host in {"localhost", "127.0.0.1"}
        assert url.database and (url.database.startswith(("taximobile_ci", "taximobile_restore_"))
                                 or (name == "TAXIMOBILE_TLS_TEST_PLAIN_URL" and url.database == "postgres"))
        assert url.port and url.port >= 1024
    for name in ("TAXIMOBILE_TLS_TEST_CA_FILE", "TAXIMOBILE_TLS_TEST_WRONG_CA_FILE"):
        assert Path(os.environ[name]).is_absolute() and Path(os.environ[name]).is_file()
    yield


def policy(wrong=False):
    name = "TAXIMOBILE_TLS_TEST_WRONG_CA_FILE" if wrong else "TAXIMOBILE_TLS_TEST_CA_FILE"
    return DatabaseTLS("verify-full", ca_file=Path(os.environ[name]))


async def observed_tls(url, tls):
    settings = replace(Settings.from_environment(), database_url=url, database_tls=tls)
    factory = create_session_factory(settings)
    try:
        async with factory() as session:
            return (await session.execute(text("SELECT ssl, version FROM pg_stat_ssl WHERE pid=pg_backend_pid()"))).one()
    finally:
        await factory.kw["bind"].dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("input_kind", ["file", "pem"])
async def test_actual_orm_connection_is_encrypted_with_verified_trust(input_kind):
    tls = policy() if input_kind == "file" else DatabaseTLS("verify-full", ca_pem=Path(os.environ["TAXIMOBILE_TLS_TEST_CA_FILE"]).read_text())
    active, version = await observed_tls(os.environ["TAXIMOBILE_TLS_TEST_DATABASE_URL"], tls)
    assert active and version in {"TLSv1.2", "TLSv1.3"}


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["untrusted_ca", "wrong_hostname", "no_server_tls"])
async def test_actual_handshake_rejects_unverified_or_plaintext_endpoints(failure):
    url = os.environ["TAXIMOBILE_TLS_TEST_DATABASE_URL"]
    tls = policy(wrong=failure == "untrusted_ca")
    if failure == "wrong_hostname":
        url = make_url(url).set(host="127.0.0.1").render_as_string(hide_password=False)
    if failure == "no_server_tls":
        with pytest.raises(ConnectionError, match="rejected SSL"):
            await observed_tls(os.environ["TAXIMOBILE_TLS_TEST_PLAIN_URL"], tls)
    else:
        with pytest.raises(ssl.SSLCertVerificationError):
            await observed_tls(url, tls)


@pytest.mark.asyncio
async def test_actual_listener_registers_over_tls_and_bad_ca_stays_unready(monkeypatch):
    async def authorized(_principal):
        return True
    actual_connect = asyncpg.connect
    rejected = asyncio.Event()
    failures = []
    async def observed_connect(*args, **kwargs):
        assert isinstance(kwargs["ssl"], ssl.SSLContext) and kwargs["ssl"].check_hostname
        try:
            return await actual_connect(*args, **kwargs)
        except Exception as error:
            failures.append(type(error).__name__)
            rejected.set()
            raise
    monkeypatch.setattr("taximobile_api.core.live_events.asyncpg.connect", observed_connect)
    for wrong in (False, True):
        listener = PostgresLiveEventListener(os.environ["TAXIMOBILE_TLS_TEST_DATABASE_URL"], EventHub(authorized), tls=policy(wrong), reconnect_seconds=0.05)
        task = asyncio.create_task(listener.run())
        try:
            if wrong:
                await asyncio.wait_for(rejected.wait(), timeout=5)
                assert "SSLCertVerificationError" in failures
                with pytest.raises(TimeoutError):
                    await listener.wait_until_ready(0.3)
                assert not listener.is_ready
            else:
                await listener.wait_until_ready(5)
                assert await listener._connection.fetchval("SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()")
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


@pytest.mark.parametrize("wrong", [False, True])
def test_migration_uses_the_same_trust_boundary(wrong):
    async def current_revision():
        factory = create_session_factory(replace(Settings.from_environment(), database_url=os.environ["TAXIMOBILE_TLS_TEST_MIGRATION_URL"], database_tls=policy()))
        try:
            async with factory() as session:
                return await session.scalar(text("SELECT version_num FROM alembic_version"))
        finally:
            await factory.kw["bind"].dispose()
    assert asyncio.run(current_revision()) == ScriptDirectory.from_config(Config("alembic.ini")).get_current_head(), "TLS migration probe requires an already-current isolated fixture"
    environment = os.environ.copy()
    environment.update(TAXIMOBILE_DATABASE_URL=os.environ["TAXIMOBILE_TLS_TEST_MIGRATION_URL"], TAXIMOBILE_DATABASE_TLS_MODE="verify-full",
                       TAXIMOBILE_DATABASE_CA_FILE=str(policy(wrong).ca_file))
    environment.pop("TAXIMOBILE_DATABASE_CA_PEM", None)
    completed = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=Path(__file__).resolve().parents[2],
                               env=environment, capture_output=True, timeout=45)
    assert (completed.returncode == 0) is (not wrong), "Migration trust outcome differed from the configured CA"
    if wrong:
        assert b"CERTIFICATE_VERIFY_FAILED" in completed.stderr
