"""Deployment-only CLI for the first scoped TaxiMobile operations grant."""

from __future__ import annotations

import argparse
import asyncio
import sys

from taximobile_api.core.config import Settings
from taximobile_api.db.session import create_session_factory
from taximobile_api.domains.administration.bootstrap import (
    PlatformGrantBootstrapConflict,
    bootstrap_initial_platform_grant,
)


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        description="Map the existing bootstrap ADMIN to the first market-scoped PLATFORM_ADMIN grant."
    )
    command.add_argument("--admin-email", required=True)
    command.add_argument("--market-code", default="MA")
    command.add_argument(
        "--confirm-market-scope",
        action="store_true",
        help="Confirm this is the reviewed initial market-scope mapping.",
    )
    return command


async def run(*, admin_email: str, market_code: str):
    settings = Settings.from_environment()
    sessions = create_session_factory(settings)
    async with sessions() as session:
        async with session.begin():
            return await bootstrap_initial_platform_grant(
                session,
                admin_email=admin_email,
                market_code=market_code,
            )


def main() -> None:
    arguments = parser().parse_args()
    if not arguments.confirm_market_scope:
        print("Refusing operations bootstrap without --confirm-market-scope.", file=sys.stderr)
        raise SystemExit(2)
    try:
        result = asyncio.run(
            run(admin_email=arguments.admin_email, market_code=arguments.market_code)
        )
    except PlatformGrantBootstrapConflict as error:
        print(f"Operations bootstrap refused: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    except Exception as error:
        print(
            "Operations bootstrap failed. Verify database configuration and migrations.",
            file=sys.stderr,
        )
        raise SystemExit(1) from error
    state = "created" if result.created else "already exists"
    print(
        f"Initial market-scoped platform grant {state} for user {result.user_id} "
        f"in market {result.market_id}."
    )


if __name__ == "__main__":
    main()

