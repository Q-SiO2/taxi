import importlib.util
import json
from pathlib import Path
import subprocess

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


def git(root: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        timeout=15,
    )


def test_nested_source_archive_does_not_inherit_parent_git_inventory(tmp_path: Path) -> None:
    git(tmp_path, "init", "--quiet")
    source_file(tmp_path, ".gitignore", "archive/\n")
    archive = tmp_path / "archive"
    source_file(
        archive, "backend/settings.py", 'KEY = "' + "-----BEGIN " + 'PRIVATE KEY-----"'
    )

    paths, tracked = validator.discover_source_files(archive)

    assert not tracked
    assert paths == [archive / "backend/settings.py"]
    with pytest.raises(ValueError, match="private-key-material"):
        validator.validate_workspace(archive)


def test_candidate_mode_scans_untracked_source_but_never_reads_ignored_secrets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    git(tmp_path, "init", "--quiet")
    source_file(tmp_path, ".gitignore", "infra/.env\nbackend/build/\n")
    source_file(tmp_path, "backend/tracked.py", "SAFE = True\n")
    git(tmp_path, "add", "--", ".gitignore", "backend/tracked.py")
    marker = "-----BEGIN " + "PRIVATE KEY-----"
    untracked = source_file(tmp_path, "backend/new.py", f'KEY = "{marker}"')
    ignored = source_file(tmp_path, "infra/.env", f'KEY = "{marker}"')
    generated = source_file(tmp_path, "backend/build/generated.py", f'KEY = "{marker}"')
    original_text = validator._text

    def guarded_text(path: Path) -> str | None:
        assert path not in {ignored, generated}, "local-only material must not be read"
        return original_text(path)

    monkeypatch.setattr(validator, "_text", guarded_text)
    validator.validate_workspace(tmp_path)
    paths, tracked = validator.discover_source_files(tmp_path, include_untracked=True)
    assert tracked and untracked in paths
    assert ignored not in paths and generated not in paths
    with pytest.raises(ValueError, match="backend[/\\\\]new.py.*private-key-material"):
        validator.validate_workspace(tmp_path, include_untracked=True)


def test_candidate_mode_applies_forbidden_filename_rule_before_reading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    git(tmp_path, "init", "--quiet")
    path = source_file(tmp_path, "TaxiMobile/release.p12", "synthetic-signing-fixture")

    def forbidden_read(_: Path) -> str:
        pytest.fail("forbidden candidate files must be rejected without reading their contents")

    monkeypatch.setattr(validator, "_text", forbidden_read)
    paths, tracked = validator.discover_source_files(tmp_path, include_untracked=True)
    assert paths == [path]
    assert validator.scan_files(tmp_path, paths, tracked=tracked) == [
        validator.Finding(Path("TaxiMobile/release.p12"), "forbidden-credential-file")
    ]
