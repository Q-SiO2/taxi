"""Static guards for release-critical backend container invariants.

The CI image scan remains the authority for vulnerability findings. These narrow
checks prevent an ordinary Dockerfile edit from dropping the conditions that
made the currently verified minimal image possible before that slower scan runs.
"""

from pathlib import Path
import re


DOCKERFILE = Path(__file__).resolve().parents[3] / "backend" / "Dockerfile"


def test_backend_image_uses_a_digest_pinned_alpine_cpython_runtime() -> None:
    content = DOCKERFILE.read_text(encoding="utf-8")

    assert re.search(
        r"^FROM python:3\.12-alpine@sha256:[0-9a-f]{64}$",
        content,
        flags=re.MULTILINE,
    )
    assert "python:3.12-slim" not in content


def test_backend_image_updates_alpine_security_packages_and_runs_unprivileged() -> None:
    content = DOCKERFILE.read_text(encoding="utf-8")

    assert "apk upgrade --no-cache" in content
    assert "adduser --uid 2000 --system --disabled-password --no-create-home" in content
    assert "USER taximobile" in content
    assert "chmod 0700 /var/lib/taximobile/driver-documents" in content
    assert "chmod 0750 /var/log/taximobile" in content
