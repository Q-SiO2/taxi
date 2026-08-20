from uuid import uuid4

import pytest

from taximobile_api.operations.outbox_replay import ReplayRefused, main, validate_request


DATABASE_URL = "postgresql+asyncpg://taxi:private@database.internal/taximobile"


def test_replay_request_requires_exact_target_unique_ids_and_incident() -> None:
    event_ids = (uuid4(), uuid4())
    request = validate_request(
        database_url=DATABASE_URL,
        event_ids=event_ids,
        expected_database_host="DATABASE.INTERNAL.",
        expected_database_name="taximobile",
        incident_reference="INC-2026-001",
    )

    assert request.event_ids == event_ids
    assert request.expected_database_host == "database.internal"


@pytest.mark.parametrize(
    "changes",
    [
        {"event_ids": ()},
        {"event_ids": tuple(uuid4() for _ in range(101))},
        {"event_ids": lambda event_id: (event_id, event_id)},
        {"expected_database_host": "other.internal"},
        {"expected_database_name": "other"},
        {"incident_reference": "private incident with spaces"},
        {"database_url": "sqlite+aiosqlite:///private.db"},
    ],
)
def test_replay_request_refuses_ambiguous_or_mismatched_scope(changes) -> None:
    event_id = uuid4()
    values = {
        "database_url": DATABASE_URL,
        "event_ids": (event_id,),
        "expected_database_host": "database.internal",
        "expected_database_name": "taximobile",
        "incident_reference": "INC-2026-001",
    }
    values.update({key: value(event_id) if callable(value) else value for key, value in changes.items()})

    with pytest.raises(ReplayRefused):
        validate_request(**values)


def test_replay_cli_requires_explicit_execution_confirmation(monkeypatch, capsys) -> None:
    event_id = uuid4()
    monkeypatch.setattr(
        "sys.argv",
        [
            "taximobile-outbox-replay",
            "--event-id",
            str(event_id),
            "--expected-database-host",
            "database.internal",
            "--expected-database-name",
            "taximobile",
            "--incident-reference",
            "INC-2026-001",
        ],
    )

    with pytest.raises(SystemExit) as exit_info:
        main()

    assert exit_info.value.code == 2
    assert "Refusing replay without --execute-reviewed-replay" in capsys.readouterr().err


def test_replay_cli_never_prints_database_exception_messages(monkeypatch, capsys) -> None:
    event_id = uuid4()
    monkeypatch.setenv("TAXIMOBILE_DATABASE_URL", DATABASE_URL)
    monkeypatch.setattr(
        "sys.argv",
        [
            "taximobile-outbox-replay",
            "--event-id",
            str(event_id),
            "--expected-database-host",
            "database.internal",
            "--expected-database-name",
            "taximobile",
            "--incident-reference",
            "INC-2026-001",
            "--execute-reviewed-replay",
        ],
    )

    async def fail_safely(*_args):
        raise RuntimeError("private-database-password")

    monkeypatch.setattr("taximobile_api.operations.outbox_replay.replay_dead_letters", fail_safely)
    with pytest.raises(SystemExit) as exit_info:
        main()

    captured = capsys.readouterr()
    assert exit_info.value.code == 1
    assert "Replay failed safely (RuntimeError)." in captured.err
    assert "private-database-password" not in captured.err
