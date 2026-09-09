"""Constant-arrival synthetic passenger workload for isolated capacity tests."""

import asyncio
import json
import sys

from .passenger_workload import parser
from .workload.config import OpenLoopPassengerWorkloadConfig
from .workload.open_loop import run_open_loop_passenger_workload


def command_parser():
    command = parser(description=__doc__, include_interval=False)
    command.add_argument("--arrival-rate-per-second", type=float, default=1.0)
    command.add_argument("--arrival-lag-budget-ms", type=float, default=250.0)
    return command


def main(argv: list[str] | None = None) -> int:
    arguments = command_parser().parse_args(argv)
    try:
        config = OpenLoopPassengerWorkloadConfig(**vars(arguments))
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    try:
        result = asyncio.run(run_open_loop_passenger_workload(config))
    except KeyboardInterrupt:
        print("Capacity workload interrupted; reconcile synthetic ride commands before retrying.", file=sys.stderr)
        return 130
    except Exception:
        print("Capacity workload failed unexpectedly; reconcile synthetic state before retrying.", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
