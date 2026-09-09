"""Strict, target-independent profile for a four-phase capacity exercise."""

from dataclasses import dataclass
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import re
from types import MappingProxyType
from typing import Mapping
from uuid import UUID

from .config import OpenLoopPassengerWorkloadConfig


PHASE_ORDER = ("WARMUP", "STEADY", "BURST", "RECOVERY")
_PROFILE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_APPROVAL_REFERENCE = re.compile(r"^[A-Z0-9][A-Z0-9._/-]{2,63}$")
_ROOT_FIELDS = {
    "schema_version",
    "profile_id",
    "approval_status",
    "approval_reference",
    "scenario",
    "city_id",
    "pickup",
    "destination",
    "request_timeout_seconds",
    "monitoring_sample_interval_seconds",
    "monitoring_query_timeout_seconds",
    "operational_thresholds",
    "cooldown_seconds",
    "phases",
}
_THRESHOLD_FIELDS = {
    "core_targets_up_min",
    "http_5xx_ratio_max",
    "http_p95_latency_seconds_max",
    "worker_seconds_since_success_max",
    "worker_errors_increase_max",
    "outbox_pending_events_max",
    "outbox_oldest_pending_age_seconds_max",
    "outbox_dead_letter_events_max",
    "unhandled_errors_increase_max",
    "log_dropped_lines_increase_max",
    "log_delivery_failures_increase_max",
    "database_metrics_up_min",
    "database_connection_utilization_ratio_max",
    "database_active_connections_max",
    "database_waiting_locks_max",
    "database_deadlocks_increase_max",
    "database_pool_metrics_up_min",
    "database_pool_checked_out_max",
    "database_pool_overflow_max",
    "database_pool_checkout_wait_p95_seconds_max",
    "database_pool_checkout_timeouts_increase_max",
}
_PHASE_FIELDS = {
    "phase",
    "users",
    "journeys_per_user",
    "arrival_rate_per_second",
    "duration_seconds",
    "p95_budget_ms",
    "arrival_lag_budget_ms",
}


def _finite_number(value, *, minimum: float, maximum: float, label: str) -> float:
    if type(value) not in {int, float} or not isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"{label} must be finite and between {minimum} and {maximum}.")
    return value


def _coordinate(value, label: str) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{label} must be a latitude/longitude array.")
    latitude = _finite_number(value[0], minimum=-90, maximum=90, label=f"{label} latitude")
    longitude = _finite_number(value[1], minimum=-180, maximum=180, label=f"{label} longitude")
    return latitude, longitude


@dataclass(frozen=True)
class CapacityPhase:
    phase: str
    users: int
    journeys_per_user: int
    arrival_rate_per_second: float
    duration_seconds: float
    p95_budget_ms: float
    arrival_lag_budget_ms: float

    @property
    def planned_arrivals(self) -> int:
        return self.users * self.journeys_per_user

    def as_dict(self) -> dict:
        return {
            "phase": self.phase,
            "users": self.users,
            "journeys_per_user": self.journeys_per_user,
            "arrival_rate_per_second": self.arrival_rate_per_second,
            "duration_seconds": self.duration_seconds,
            "p95_budget_ms": self.p95_budget_ms,
            "arrival_lag_budget_ms": self.arrival_lag_budget_ms,
        }


@dataclass(frozen=True)
class CapacityProfile:
    profile_id: str
    approval_reference: str
    city_id: UUID
    pickup: tuple[float, float]
    destination: tuple[float, float]
    request_timeout_seconds: float
    monitoring_sample_interval_seconds: float
    monitoring_query_timeout_seconds: float
    operational_thresholds: Mapping[str, float]
    cooldown_seconds: float
    phases: tuple[CapacityPhase, ...]

    @classmethod
    def from_dict(cls, value: object) -> "CapacityProfile":
        if not isinstance(value, dict) or set(value) != _ROOT_FIELDS:
            raise ValueError("Capacity profile must contain exactly the documented root fields.")
        if value["schema_version"] != 1:
            raise ValueError("Capacity profile schema_version must be 1.")
        if value["scenario"] != "passenger_request_cancel_open_loop_v1":
            raise ValueError("Capacity profile scenario is unsupported.")
        if value["approval_status"] != "APPROVED":
            raise ValueError("Capacity profile must carry explicit APPROVED status before execution.")
        profile_id = value["profile_id"]
        approval_reference = value["approval_reference"]
        if not isinstance(profile_id, str) or _PROFILE_ID.fullmatch(profile_id) is None:
            raise ValueError("Capacity profile_id must be a bounded lowercase identifier.")
        if not isinstance(approval_reference, str) or _APPROVAL_REFERENCE.fullmatch(approval_reference) is None:
            raise ValueError("Capacity approval_reference must be a bounded evidence identifier.")
        try:
            city_id = UUID(value["city_id"])
        except (ValueError, TypeError, AttributeError):
            raise ValueError("Capacity profile city_id must be a UUID.") from None
        pickup = _coordinate(value["pickup"], "pickup")
        destination = _coordinate(value["destination"], "destination")
        request_timeout = _finite_number(
            value["request_timeout_seconds"], minimum=.1, maximum=30,
            label="request_timeout_seconds",
        )
        monitoring_interval = _finite_number(
            value["monitoring_sample_interval_seconds"], minimum=5, maximum=60,
            label="monitoring_sample_interval_seconds",
        )
        monitoring_timeout = _finite_number(
            value["monitoring_query_timeout_seconds"], minimum=.5, maximum=10,
            label="monitoring_query_timeout_seconds",
        )
        if monitoring_timeout >= monitoring_interval:
            raise ValueError("Monitoring query timeout must be shorter than its sample interval.")
        raw_thresholds = value["operational_thresholds"]
        if not isinstance(raw_thresholds, dict) or set(raw_thresholds) != _THRESHOLD_FIELDS:
            raise ValueError("Operational thresholds must contain exactly the documented fields.")
        thresholds = MappingProxyType({
            name: _finite_number(raw_thresholds[name], minimum=0, maximum=1_000_000_000, label=name)
            for name in sorted(_THRESHOLD_FIELDS)
        })
        ratio_thresholds = (
            "core_targets_up_min",
            "http_5xx_ratio_max",
            "database_metrics_up_min",
            "database_connection_utilization_ratio_max",
            "database_pool_metrics_up_min",
        )
        if any(not 0 <= thresholds[name] <= 1 for name in ratio_thresholds):
            raise ValueError("Availability and ratio thresholds must be between 0 and 1.")
        cooldown = _finite_number(
            value["cooldown_seconds"], minimum=0, maximum=60,
            label="cooldown_seconds",
        )
        raw_phases = value["phases"]
        if not isinstance(raw_phases, list) or len(raw_phases) != len(PHASE_ORDER):
            raise ValueError("Capacity profile requires exactly four ordered phases.")
        phases: list[CapacityPhase] = []
        for expected_name, raw in zip(PHASE_ORDER, raw_phases, strict=True):
            if not isinstance(raw, dict) or set(raw) != _PHASE_FIELDS:
                raise ValueError("Each capacity phase must contain exactly the documented fields.")
            if raw["phase"] != expected_name:
                raise ValueError("Capacity phases must be WARMUP, STEADY, BURST, RECOVERY in order.")
            users = raw["users"]
            journeys = raw["journeys_per_user"]
            if type(users) is not int or not 1 <= users <= 50:
                raise ValueError("Capacity phase users must be 1..50.")
            if type(journeys) is not int or not 1 <= journeys <= 100:
                raise ValueError("Capacity phase journeys_per_user must be 1..100.")
            phase = CapacityPhase(
                phase=expected_name,
                users=users,
                journeys_per_user=journeys,
                arrival_rate_per_second=_finite_number(
                    raw["arrival_rate_per_second"], minimum=.01, maximum=100,
                    label="arrival_rate_per_second",
                ),
                duration_seconds=_finite_number(
                    raw["duration_seconds"], minimum=1, maximum=600,
                    label="duration_seconds",
                ),
                p95_budget_ms=_finite_number(
                    raw["p95_budget_ms"], minimum=1, maximum=60000,
                    label="p95_budget_ms",
                ),
                arrival_lag_budget_ms=_finite_number(
                    raw["arrival_lag_budget_ms"], minimum=1, maximum=60000,
                    label="arrival_lag_budget_ms",
                ),
            )
            phases.append(phase)
        total_arrivals = sum(phase.planned_arrivals for phase in phases)
        total_duration = sum(phase.duration_seconds for phase in phases) + cooldown * 3
        if total_arrivals > 1000:
            raise ValueError("Capacity profile may schedule at most 1000 total arrivals.")
        if total_duration > 2400:
            raise ValueError("Capacity profile may reserve at most 2400 total seconds.")
        return cls(
            profile_id=profile_id,
            approval_reference=approval_reference,
            city_id=city_id,
            pickup=pickup,
            destination=destination,
            request_timeout_seconds=request_timeout,
            monitoring_sample_interval_seconds=monitoring_interval,
            monitoring_query_timeout_seconds=monitoring_timeout,
            operational_thresholds=thresholds,
            cooldown_seconds=cooldown,
            phases=tuple(phases),
        )

    def phase_config(
        self,
        phase: CapacityPhase,
        *,
        base_url: str,
        confirm_synthetic_target: bool,
        confirm_nonlocal_target: bool,
    ) -> OpenLoopPassengerWorkloadConfig:
        return OpenLoopPassengerWorkloadConfig(
            base_url=base_url,
            city_id=self.city_id,
            pickup=self.pickup,
            destination=self.destination,
            confirm_synthetic_target=confirm_synthetic_target,
            confirm_nonlocal_target=confirm_nonlocal_target,
            users=phase.users,
            journeys_per_user=phase.journeys_per_user,
            interval_seconds=0,
            request_timeout_seconds=self.request_timeout_seconds,
            duration_seconds=phase.duration_seconds,
            p95_budget_ms=phase.p95_budget_ms,
            arrival_rate_per_second=phase.arrival_rate_per_second,
            arrival_lag_budget_ms=phase.arrival_lag_budget_ms,
        )

    def semantic_digest(self) -> str:
        document = {
            "schema_version": 1,
            "profile_id": self.profile_id,
            "approval_status": "APPROVED",
            "approval_reference": self.approval_reference,
            "scenario": "passenger_request_cancel_open_loop_v1",
            "city_id": str(self.city_id),
            "pickup": list(self.pickup),
            "destination": list(self.destination),
            "request_timeout_seconds": self.request_timeout_seconds,
            "monitoring_sample_interval_seconds": self.monitoring_sample_interval_seconds,
            "monitoring_query_timeout_seconds": self.monitoring_query_timeout_seconds,
            "operational_thresholds": dict(self.operational_thresholds),
            "cooldown_seconds": self.cooldown_seconds,
            "phases": [phase.as_dict() for phase in self.phases],
        }
        canonical = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return sha256(canonical.encode("ascii")).hexdigest()


def load_capacity_profile(path: Path) -> CapacityProfile:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Capacity profile must be a regular, non-symlink JSON file.")
    if path.stat().st_size > 65536:
        raise ValueError("Capacity profile exceeds the 64 KiB safety limit.")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, RecursionError):
        raise ValueError("Capacity profile must be valid bounded UTF-8 JSON.") from None
    return CapacityProfile.from_dict(value)
