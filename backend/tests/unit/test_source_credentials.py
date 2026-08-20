import importlib.util
import json
from pathlib import Path

import pytest


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
VALIDATOR_PATH = WORKSPACE_ROOT / "infra" / "scripts" / "validate_source_credentials.py"

spec = importlib.util.spec_from_file_location("validate_source_credentials", VALIDATOR_PATH)
assert spec is not None and spec.loader is not None
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def source_file(root: Path, relative: str, content: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_private_key_is_reported_without_copying_its_value(tmp_path: Path) -> None:
    marker = "-----BEGIN " + "PRIVATE KEY-----"
    path = source_file(tmp_path, "backend/config.py", f'KEY = "{marker} secret"')

    findings = validator.scan_files(tmp_path, [path], tracked=True)

    assert findings == [validator.Finding(Path("backend/config.py"), "private-key-material")]
    assert "secret" not in str(findings)


def test_arbitrarily_named_service_account_document_is_rejected(tmp_path: Path) -> None:
    path = source_file(
        tmp_path,
        "infra/provider.json",
        json.dumps({"type": "service_account", "private_key_id": "not-printed"}),
    )

    findings = validator.scan_files(tmp_path, [path], tracked=True)

    assert findings == [validator.Finding(Path("infra/provider.json"), "service-account-document")]
    assert "not-printed" not in str(findings)


@pytest.mark.parametrize(
    ("token", "expected_rule"),
    [
        ("AKIA" + "A" * 16, "aws-access-key-id"),
        ("AIza" + "A" * 35, "google-api-key"),
        ("ghp_" + "A" * 36, "github-access-token"),
        ("xoxb-" + "A" * 20, "slack-access-token"),
        ("sk_" + "live_" + "A" * 20, "stripe-live-secret"),
    ],
)
def test_recognized_live_token_formats_are_redacted(tmp_path: Path, token: str, expected_rule: str) -> None:
    path = source_file(tmp_path, "backend/settings.py", f'TOKEN = "{token}"')

    findings = validator.scan_files(tmp_path, [path], tracked=True)

    assert findings == [validator.Finding(Path("backend/settings.py"), expected_rule)]
    assert token not in str(findings)


def test_tracked_provider_and_keystore_files_are_rejected_by_name(tmp_path: Path) -> None:
    firebase = source_file(tmp_path, "TaxiMobile/androidApp/google-services.json", "{}")
    keystore = source_file(tmp_path, "TaxiMobile/release.jks", "binary-looking-placeholder")

    findings = validator.scan_files(tmp_path, [firebase, keystore], tracked=True)

    assert findings == [
        validator.Finding(
            Path("TaxiMobile/androidApp/google-services.json"),
            "forbidden-credential-file",
        ),
        validator.Finding(Path("TaxiMobile/release.jks"), "forbidden-credential-file"),
    ]


def test_build_output_local_files_and_symlinks_are_not_scanned(tmp_path: Path) -> None:
    build_secret = source_file(
        tmp_path,
        "backend/build/generated.py",
        'TOKEN = "sk_' + 'live_' + 'A' * 20 + '"',
    )
    local_env = source_file(tmp_path, "infra/.env", "CMI_SECRET=local-only")
    outside = source_file(tmp_path, "outside/provider.json", '{"type":"service_account"}')

    findings = validator.scan_files(
        tmp_path,
        [build_secret, local_env, outside],
        tracked=False,
    )

    assert findings == []


def test_documented_placeholders_do_not_trigger_high_confidence_rules(tmp_path: Path) -> None:
    path = source_file(
        tmp_path,
        "docs/security.md",
        "Use environment variables for TAXIMOBILE_JWT_SECRET and CMI credentials.",
    )

    assert validator.scan_files(tmp_path, [path], tracked=True) == []


def test_committed_workspace_passes_the_source_credential_gate() -> None:
    validator.validate_workspace(WORKSPACE_ROOT)
