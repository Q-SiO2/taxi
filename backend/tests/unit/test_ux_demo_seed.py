import pytest

from taximobile_api.operations.ux_demo_seed import (
    DEMO_CONFIRMATION,
    DemoSeedRefused,
    validate_demo_target,
)


def test_demo_seed_accepts_only_confirmed_loopback_development_database() -> None:
    validate_demo_target(
        environment="development",
        database_url="postgresql+asyncpg://taxi:local@127.0.0.1:5432/taximobile",
        confirmation=DEMO_CONFIRMATION,
    )


@pytest.mark.parametrize(
    ("environment", "database_url", "confirmation"),
    [
        ("production", "postgresql+asyncpg://taxi:secret@127.0.0.1/taximobile", DEMO_CONFIRMATION),
        ("development", "postgresql+asyncpg://taxi:secret@database.internal/taximobile", DEMO_CONFIRMATION),
        ("development", "postgresql+asyncpg://taxi:secret@127.0.0.1/postgres", DEMO_CONFIRMATION),
        ("development", "postgresql+asyncpg://taxi:secret@127.0.0.1/taximobile", "wrong"),
    ],
)
def test_demo_seed_refuses_unsafe_or_unconfirmed_target(
    environment: str,
    database_url: str,
    confirmation: str,
) -> None:
    with pytest.raises(DemoSeedRefused):
        validate_demo_target(
            environment=environment,
            database_url=database_url,
            confirmation=confirmation,
        )
