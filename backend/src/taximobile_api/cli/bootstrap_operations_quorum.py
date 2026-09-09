"""Deployment-only CLI for the initial three-person operations quorum."""

from __future__ import annotations

import argparse
import asyncio
import sys

from taximobile_api.core.config import Settings
from taximobile_api.db.session import create_session_factory
from taximobile_api.domains.administration.bootstrap import (
    PlatformGrantBootstrapConflict,
    bootstrap_platform_admin_quorum_member,
)


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        description=(
            "Add the second or third reviewed platform administrator to the "
            "initial market quorum."
        )
    )
    command.add_argument("--user-email", required=True)
    command.add_argument("--market-code", default="MA")
    command.add_argument("--change-reference", required=True)
    command.add_argument(
        "--confirm-initial-quorum",
        action="store_true",
        help="Confirm this is a separately reviewed initial quorum member.",
    )
    return command


async def run(*, user_email: str, market_code: str, change_reference: str):
    settings = Settings.from_environment()
    sessions = create_session_factory(settings)
    async with sessions() as session:
        async with session.begin():
            return await bootstrap_platform_admin_quorum_member(
                session,
                user_email=user_email,
                market_code=market_code,
                change_reference=change_reference,
            )


def main() -> None:
    arguments = parser().parse_args()
    if not arguments.confirm_initial_quorum:
        print(
            "Refusing quorum bootstrap without --confirm-initial-quorum.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    try:
        result = asyncio.run(
            run(
                user_email=arguments.user_email,
                market_code=arguments.market_code,
                change_reference=arguments.change_reference,
            )
        )
    except PlatformGrantBootstrapConflict as error:
        print(f"Operations quorum bootstrap refused: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    except Exception as error:
        print(
            "Operations quorum bootstrap failed. Verify configuration and migrations.",
            file=sys.stderr,
        )
        raise SystemExit(1) from error
    state = "created" if result.created else "already exists"
    print(
        f"Initial platform administrator quorum member {state} for user "
        f"{result.user_id} in market {result.market_id}; active quorum size "
        f"is {result.active_quorum_size}."
    )


if __name__ == "__main__":
    main()
