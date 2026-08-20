from unittest.mock import AsyncMock, patch

from pydantic import ValidationError

from taximobile_api.cli.bootstrap_admin import main
from taximobile_api.domains.auth.schemas import RegisterRequest


def test_cli_requires_explicit_initial_admin_confirmation(capsys) -> None:
    with patch("taximobile_api.cli.bootstrap_admin.getpass") as password_prompt:
        exit_code = main(["--email", "admin@example.com"])

    assert exit_code == 2
    assert "--confirm-initial-admin" in capsys.readouterr().err
    password_prompt.assert_not_called()


def test_cli_refuses_mismatched_hidden_passwords(capsys) -> None:
    with patch(
        "taximobile_api.cli.bootstrap_admin.getpass",
        side_effect=["first-long-password", "different-long-password"],
    ), patch("taximobile_api.cli.bootstrap_admin.run", new=AsyncMock()) as run:
        exit_code = main(["--email", "admin@example.com", "--confirm-initial-admin"])

    assert exit_code == 2
    assert "Passwords do not match" in capsys.readouterr().err
    run.assert_not_awaited()


def test_cli_runs_bootstrap_without_printing_the_password(capsys) -> None:
    password = "a-long-initial-admin-password"
    with patch(
        "taximobile_api.cli.bootstrap_admin.getpass",
        side_effect=[password, password],
    ), patch("taximobile_api.cli.bootstrap_admin.run", new=AsyncMock(return_value=True)) as run:
        exit_code = main(["--email", "ADMIN@example.com", "--confirm-initial-admin"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Initial administrator created" in captured.out
    assert password not in captured.out
    assert password not in captured.err
    run.assert_awaited_once_with("ADMIN@example.com", password)


def test_cli_validation_error_never_echoes_the_password(capsys) -> None:
    password = "too-short"
    try:
        RegisterRequest(email="admin@example.com", password=password, display_name="Admin")
    except ValidationError as validation_error:
        error = validation_error
    else:  # pragma: no cover - protects the test if registration rules regress.
        raise AssertionError("Expected short-password validation to fail")

    with patch(
        "taximobile_api.cli.bootstrap_admin.getpass",
        side_effect=[password, password],
    ), patch("taximobile_api.cli.bootstrap_admin.run", new=AsyncMock(side_effect=error)):
        exit_code = main(["--email", "admin@example.com", "--confirm-initial-admin"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "password" in captured.err
    assert password not in captured.err
