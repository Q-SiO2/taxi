"""Interactive command for creating TaxiMobile's first administrator."""

from __future__ import annotations

import argparse
import asyncio
from getpass import getpass
import sys

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from taximobile_api.core.config import ConfigurationError, Settings
from taximobile_api.db.session import create_session_factory
from taximobile_api.domains.auth.bootstrap import (
    AdministratorAccountConflict,
    InitialAdministratorExists,
    bootstrap_initial_administrator,
)


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        description="Create the first TaxiMobile administrator using the configured database.",
    )
    command.add_argument("--email", required=True, help="Administrator login email address.")
    command.add_argument(
        "--confirm-initial-admin",
        action="store_true",
        help="Confirm this is the controlled initial deployment bootstrap.",
    )
    return command


async def run(email: str, password: str) -> bool:
    settings = Settings.from_environment()
    sessions = create_session_factory(settings)
    async with sessions() as session:
        async with session.begin():
            result = await bootstrap_initial_administrator(session, email=email, password=password)
    return result.created


def validation_summary(error: ValidationError) -> str:
    """Describe invalid fields without echoing submitted values such as passwords."""
    messages = []
    for issue in error.errors(include_input=False, include_url=False):
        location = ".".join(str(part) for part in issue["loc"])
        messages.append(f"{location}: {issue['msg']}")
    return "Invalid administrator details: " + "; ".join(messages)


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if not arguments.confirm_initial_admin:
        print("Refusing bootstrap without --confirm-initial-admin.", file=sys.stderr)
        return 2
    try:
        password = getpass("Initial administrator password: ")
        confirmation = getpass("Confirm password: ")
    except (EOFError, KeyboardInterrupt):
        print("Administrator bootstrap cancelled.", file=sys.stderr)
        return 130
    if password != confirmation:
        print("Passwords do not match.", file=sys.stderr)
        return 2

    try:
        created = asyncio.run(run(arguments.email, password))
    except ValidationError as error:
        print(validation_summary(error), file=sys.stderr)
        return 2
    except (ConfigurationError, InitialAdministratorExists, AdministratorAccountConflict) as error:
        print(str(error), file=sys.stderr)
        return 2
    except SQLAlchemyError:
        print("Administrator bootstrap failed. Verify the database configuration and migrations.", file=sys.stderr)
        return 1

    print("Initial administrator created." if created else "Initial administrator already exists; no change made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
