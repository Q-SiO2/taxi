"""CLI entrypoint for isolated synthetic passenger request/cancel evidence."""

import argparse
import asyncio
import json
import sys
from uuid import UUID

from .workload.config import PassengerWorkloadConfig
from .workload.passenger import run_passenger_workload


def parser(*, description: str | None = None, include_interval: bool = True) -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=description or __doc__)
    command.add_argument("--base-url", default="http://127.0.0.1:8000")
    command.add_argument("--city-id", type=UUID, required=True)
    command.add_argument("--pickup", type=float, nargs=2, required=True, metavar=("LAT", "LON"))
    command.add_argument("--destination", type=float, nargs=2, required=True, metavar=("LAT", "LON"))
    command.add_argument("--confirm-synthetic-target", action="store_true")
    command.add_argument("--confirm-nonlocal-target", action="store_true")
    command.add_argument("--users", type=int, default=2)
    command.add_argument("--journeys-per-user", type=int, default=2)
    if include_interval:
        command.add_argument("--interval-seconds", type=float, default=1.0)
    command.add_argument("--request-timeout-seconds", type=float, default=5.0)
    command.add_argument("--duration-seconds", type=float, default=120.0)
    command.add_argument("--p95-budget-ms", type=float, default=1000.0)
    return command


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        config = PassengerWorkloadConfig(**vars(arguments))
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    try:
        result = asyncio.run(run_passenger_workload(config))
    except KeyboardInterrupt:
        print("Workload interrupted; synthetic accounts and ride commands may remain unresolved.", file=sys.stderr)
        return 130
    except Exception:
        # The CLI boundary must not print raw transport, auth or response details.
        # Unexpected failures are not success; keep diagnosis in synthetic tests.
        print("Workload failed unexpectedly; review synthetic state before retrying.", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
