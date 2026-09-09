"""Execute an approved four-phase capacity profile against synthetic staging."""

import argparse
import asyncio
import json
from pathlib import Path
import sys

from .workload.capacity_plan import run_capacity_plan
from .workload.capacity_profile import load_capacity_profile
from .workload.monitoring import PrometheusPhaseSampler


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--profile", type=Path, required=True)
    command.add_argument("--base-url", default="http://127.0.0.1:8000")
    command.add_argument("--confirm-synthetic-target", action="store_true")
    command.add_argument("--confirm-nonlocal-target", action="store_true")
    command.add_argument("--confirm-approved-profile", action="store_true")
    command.add_argument("--prometheus-url")
    command.add_argument("--confirm-monitoring-target", action="store_true")
    command.add_argument("--confirm-nonlocal-monitoring-target", action="store_true")
    command.add_argument("--confirm-harness-without-monitoring", action="store_true")
    return command


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        if arguments.confirm_approved_profile is not True:
            raise ValueError("Confirm the reviewed capacity profile before execution.")
        profile = load_capacity_profile(arguments.profile)
        # Build every phase before network I/O so one late invalid phase cannot
        # leave records from earlier phases.
        for phase in profile.phases:
            profile.phase_config(
                phase,
                base_url=arguments.base_url,
                confirm_synthetic_target=arguments.confirm_synthetic_target,
                confirm_nonlocal_target=arguments.confirm_nonlocal_target,
            )
        if bool(arguments.prometheus_url) == bool(arguments.confirm_harness_without_monitoring):
            raise ValueError(
                "Supply a protected Prometheus URL or explicitly confirm a harness run without monitoring."
            )
        monitoring_sampler = None
        if arguments.prometheus_url:
            monitoring_sampler = PrometheusPhaseSampler(
                arguments.prometheus_url,
                sample_interval_seconds=profile.monitoring_sample_interval_seconds,
                query_timeout_seconds=profile.monitoring_query_timeout_seconds,
                thresholds=profile.operational_thresholds,
                confirm_monitoring_target=arguments.confirm_monitoring_target,
                confirm_nonlocal_target=arguments.confirm_nonlocal_monitoring_target,
            )
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    try:
        result = asyncio.run(run_capacity_plan(
            profile,
            base_url=arguments.base_url,
            confirm_synthetic_target=arguments.confirm_synthetic_target,
            confirm_nonlocal_target=arguments.confirm_nonlocal_target,
            monitoring_sampler=monitoring_sampler,
        ))
    except KeyboardInterrupt:
        print("Capacity plan interrupted; reconcile every executed phase before retrying.", file=sys.stderr)
        return 130
    except Exception:
        print("Capacity plan failed unexpectedly; reconcile synthetic state before retrying.", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
