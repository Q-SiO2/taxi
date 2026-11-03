from datetime import UTC, datetime, timedelta
from pathlib import Path
import ssl

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import pytest

from taximobile_api.core.config import ConfigurationError, Settings
from taximobile_api.db.session import create_session_factory
from taximobile_api.db.transport import DatabaseTLS, DatabaseTLSConfigurationError

URL = "postgresql+asyncpg://fixture:transport-test-only@database.example.test/taximobile_ci_tls"


@pytest.fixture
def ca_pem():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "TaxiMobile unit CA")])
    now = datetime.now(UTC)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1))
            .not_valid_after(now+timedelta(hours=1)).add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .sign(key, hashes.SHA256()))
    return cert.public_bytes(serialization.Encoding.PEM).decode()


def test_production_requires_verified_identity_and_other_environments_are_explicit():
    policy = DatabaseTLS.from_environment({"TAXIMOBILE_ENV": "production"})
    context = policy.connect_args(URL)["ssl"]
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
    assert context.minimum_version >= ssl.TLSVersion.TLSv1_2
    with pytest.raises(DatabaseTLSConfigurationError, match="Production requires"):
        DatabaseTLS.from_environment({"TAXIMOBILE_ENV": "production", "TAXIMOBILE_DATABASE_TLS_MODE": "disable"})
    assert DatabaseTLS.from_environment({"TAXIMOBILE_ENV": "test"}).connect_args(URL) == {"ssl": False}


@pytest.mark.parametrize("mode", ["prefer", "allow", "require", "verify-ca", "false", ""])
def test_weaker_or_ambiguous_modes_are_not_accepted(mode):
    with pytest.raises(DatabaseTLSConfigurationError):
        DatabaseTLS.from_environment({"TAXIMOBILE_DATABASE_TLS_MODE": mode})


@pytest.mark.parametrize("query", ["ssl=disable", "sslmode=require", "sslrootcert=other.pem", "SSL=disable",
                                  "host=%2Ftmp", "hostaddr=127.0.0.1", "service=other", "direct_tls=true"])
def test_url_cannot_override_transport_or_hostname(query):
    with pytest.raises(DatabaseTLSConfigurationError) as error:
        DatabaseTLS("verify-full").connect_args(URL + "?" + query)
    assert "transport-test-only" not in str(error.value) and URL not in str(error.value)


def test_verified_identity_cannot_silently_use_a_unix_socket():
    with pytest.raises(DatabaseTLSConfigurationError, match="explicit TCP"):
        DatabaseTLS("verify-full").connect_args("postgresql+asyncpg:///taximobile_ci_tls")


def test_file_and_pem_ca_inputs_load_equivalent_pinned_trust(tmp_path, ca_pem):
    path = tmp_path / "ca.pem"
    path.write_text(ca_pem)
    file_context = DatabaseTLS("verify-full", ca_file=path).connect_args(URL)["ssl"]
    pem_context = DatabaseTLS("verify-full", ca_pem=ca_pem).connect_args(URL)["ssl"]
    assert file_context.get_ca_certs(binary_form=True) == pem_context.get_ca_certs(binary_form=True)
    assert len(file_context.get_ca_certs(binary_form=True)) == 1
    with pytest.raises(DatabaseTLSConfigurationError, match="one database CA"):
        DatabaseTLS("verify-full", path, ca_pem).connect_args(URL)
    with pytest.raises(DatabaseTLSConfigurationError, match="absolute"):
        DatabaseTLS("verify-full", Path("relative.pem")).connect_args(URL)
    with pytest.raises(DatabaseTLSConfigurationError, match="requires TLS"):
        DatabaseTLS("disable", ca_pem=ca_pem).connect_args(URL)


@pytest.mark.parametrize("kind", ["missing", "malformed"])
def test_trust_load_failure_is_actionable_without_configuration_values(tmp_path, kind):
    path = tmp_path / "ca.pem"
    if kind == "malformed":
        path.write_text("invalid private-looking fixture value must not appear in diagnostics")
    with pytest.raises(DatabaseTLSConfigurationError, match="readable PEM") as error:
        DatabaseTLS("verify-full", ca_file=path).connect_args(URL)
    assert "private-looking" not in str(error.value) and str(path) not in str(error.value)


def test_settings_capture_transport_for_orm_and_reject_production_downgrade(monkeypatch, ca_pem):
    monkeypatch.setenv("TAXIMOBILE_ENV", "test")
    monkeypatch.setenv("TAXIMOBILE_DATABASE_URL", URL)
    monkeypatch.setenv("TAXIMOBILE_DATABASE_TLS_MODE", "verify-full")
    monkeypatch.setenv("TAXIMOBILE_DATABASE_CA_PEM", ca_pem)
    settings = Settings.from_environment()
    monkeypatch.setenv("TAXIMOBILE_DATABASE_TLS_MODE", "disable")
    monkeypatch.delenv("TAXIMOBILE_DATABASE_CA_PEM")
    captured = {}
    def engine(url, **kwargs):
        captured.update(kwargs)
        return object()
    monkeypatch.setattr("taximobile_api.db.session.create_async_engine", engine)
    create_session_factory(settings)
    assert captured["connect_args"]["ssl"].check_hostname
    monkeypatch.setenv("TAXIMOBILE_ENV", "production")
    with pytest.raises(ConfigurationError, match="Production requires"):
        Settings.from_environment()
