"""Sequential four-phase capacity execution with aggregate-only evidence."""

import asyncio
from time import perf_counter

from .capacity_profile import CapacityProfile
from .open_loop import run_open_loop_passenger_workload


async def run_capacity_plan(
    profile: CapacityProfile,
    *,
    base_url: str,
    confirm_synthetic_target: bool,
    confirm_nonlocal_target: bool,
    transport=None,
    monitoring_sampler=None,
) -> dict:
    started = perf_counter()
    phase_results = []
    for index, phase in enumerate(profile.phases):
        config = profile.phase_config(
            phase,
            base_url=base_url,
            confirm_synthetic_target=confirm_synthetic_target,
            confirm_nonlocal_target=confirm_nonlocal_target,
        )
        if monitoring_sampler is None:
            result = await run_open_loop_passenger_workload(config, transport=transport)
            monitoring = {"status": "NOT_CONFIGURED"}
        else:
            monitoring_stopped = asyncio.Event()
            monitoring_task = asyncio.create_task(
                monitoring_sampler.sample_until(monitoring_stopped)
            )
            try:
                result = await run_open_loop_passenger_workload(config, transport=transport)
            except BaseException:
                monitoring_stopped.set()
                # Do not orphan a sampler or let its cleanup error replace the
                # workload exception that made this phase indeterminate.
                await asyncio.gather(monitoring_task, return_exceptions=True)
                raise
            finally:
                monitoring_stopped.set()
            monitoring = await monitoring_task
        phase_results.append({"phase": phase.phase, "result": result, "monitoring": monitoring})
        if not result["passed"] or monitoring["status"] == "INCOMPLETE":
            break
        if index + 1 < len(profile.phases) and profile.cooldown_seconds:
            await asyncio.sleep(profile.cooldown_seconds)
    executed = len(phase_results)
    workload_passed = executed == len(profile.phases) and all(
        item["result"]["passed"] for item in phase_results
    )
    monitoring_complete = monitoring_sampler is not None and all(
        item["monitoring"]["status"] == "COMPLETE" for item in phase_results
    ) and executed == len(profile.phases)
    passed = workload_passed and (monitoring_sampler is None or monitoring_complete)
    return {
        "schema_version": 1,
        "scenario": "passenger_capacity_plan_v1",
        "evidence_level": "SYNTHETIC_HTTP_WORKLOAD_NOT_DEPLOYMENT_ACCEPTANCE",
        "profile_id": profile.profile_id,
        "profile_sha256": profile.semantic_digest(),
        "approval_reference": profile.approval_reference,
        "passed": passed,
        "workload_passed": workload_passed,
        "monitoring_evidence_complete": monitoring_complete,
        "planned_phases": list(phase.phase for phase in profile.phases),
        "executed_phases": executed,
        "unexecuted_phases": list(phase.phase for phase in profile.phases[executed:]),
        "planned_arrivals": sum(phase.planned_arrivals for phase in profile.phases),
        "released_arrivals": sum(
            item["result"]["load_shape"]["released_arrivals"] for item in phase_results
        ),
        "completed_journeys": sum(item["result"]["completed_journeys"] for item in phase_results),
        "unresolved_ride_commands": sum(
            item["result"]["unresolved_ride_commands"] for item in phase_results
        ),
        "elapsed_seconds": round(perf_counter() - started, 3),
        "phases": phase_results,
    }
