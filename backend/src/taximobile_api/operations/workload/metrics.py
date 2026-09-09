"""Aggregate-only evidence: never retain URLs, bodies, credentials or user IDs."""

from collections import Counter
from dataclasses import dataclass, field
from math import ceil


def latency_summary(samples: list[float]) -> dict[str, float]:
    ordered = sorted(samples)
    return {
        name: round(ordered[max(0, ceil(rank * len(ordered)) - 1)], 3) if ordered else 0.0
        for name, rank in (("p50", .50), ("p95", .95), ("p99", .99), ("max", 1.0))
    }


@dataclass
class StepMetrics:
    samples: list[float] = field(default_factory=list)
    outcomes: Counter = field(default_factory=Counter)

    def record(self, elapsed_ms: float, outcome: str) -> None:
        self.samples.append(elapsed_ms)
        self.outcomes[outcome] += 1

    def as_dict(self) -> dict:
        failures = sum(count for outcome, count in self.outcomes.items() if outcome != "ok")
        return {
            "requests": len(self.samples),
            "failures": failures,
            "error_rate": round(failures / len(self.samples), 6) if self.samples else 0.0,
            "latency_ms": latency_summary(self.samples),
            "outcomes": dict(sorted(self.outcomes.items())),
        }


@dataclass
class WorkloadMetrics:
    run_id: str
    steps: dict[str, StepMetrics] = field(default_factory=dict)
    failures: Counter = field(default_factory=Counter)
    journey_latencies: list[float] = field(default_factory=list)
    started: int = 0
    completed: int = 0
    provisioned: int = 0
    unresolved_commands: set[str] = field(default_factory=set, repr=False)
    deadline_exceeded: bool = False

    def report(self, *, elapsed: float, planned: int, p95_budget_ms: float) -> dict:
        measured = {key: value.as_dict() for key, value in sorted(self.steps.items())}
        # Per-operation budgets prevent a fast endpoint from hiding a slow one.
        over_budget = sorted(
            key for key, value in self.steps.items()
            if value.samples
            and sorted(value.samples)[ceil(.95 * len(value.samples)) - 1] > p95_budget_ms
        )
        passed = (
            self.completed == planned and not self.failures
            and not self.unresolved_commands and not self.deadline_exceeded and not over_budget
        )
        return {
            "schema_version": 1,
            "scenario": "passenger_request_cancel_v1",
            "evidence_level": "SYNTHETIC_HTTP_WORKLOAD_NOT_DEPLOYMENT_ACCEPTANCE",
            "run_id": self.run_id,
            "passed": passed,
            "planned_journeys": planned,
            "started_journeys": self.started,
            "completed_journeys": self.completed,
            "not_started_journeys": planned - self.started,
            "incomplete_journeys": self.started - self.completed,
            "provisioned_accounts": self.provisioned,
            "unresolved_ride_commands": len(self.unresolved_commands),
            "deadline_exceeded": self.deadline_exceeded,
            "elapsed_seconds": round(elapsed, 3),
            "completed_journeys_per_second": round(self.completed / elapsed, 3) if elapsed > 0 else 0,
            "journey_latency_ms": latency_summary(self.journey_latencies),
            "failures": dict(sorted(self.failures.items())),
            "p95_budget_ms": p95_budget_ms,
            "steps_over_budget": over_budget,
            "steps": measured,
        }
