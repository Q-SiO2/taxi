"""Privacy-bounded in-process metrics for per-instance operational scraping."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import isfinite
from re import fullmatch
from threading import Lock
from time import time

from taximobile_api.core.notification_policy import DEAD_LETTER_OWNERS


DEFAULT_DURATION_BUCKETS = (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
DATABASE_POOL_WAIT_BUCKETS = (
    0.001,
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
    30.0,
    60.0,
)
KNOWN_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}
KNOWN_LEGACY_ADMIN_OUTCOMES = ("blocked", "served")
KNOWN_SECURITY_INCIDENT_SEVERITIES = ("SEV1", "SEV2", "SEV3", "SEV4")
KNOWN_WORKERS = (
    "matching",
    "outbox",
    "credentials",
    "scheduling",
    "analytics",
    "case_alerts",
    "case_retention",
    "driver_document_retention",
)


@dataclass(frozen=True, slots=True)
class OutboxOwnerMetrics:
    """One fixed operational ownership bucket; never a topic or user label."""

    owner: str
    pending_events: int = 0
    dead_letter_events: int = 0
    locked_events: int = 0
    oldest_pending_age_seconds: float = 0.0

    def __post_init__(self) -> None:
        if self.owner not in DEAD_LETTER_OWNERS | {"unclassified"}:
            raise ValueError("Unknown outbox operational owner")


@dataclass(frozen=True, slots=True)
class OutboxMetrics:
    """Aggregate delivery state safe to expose to infrastructure monitoring."""

    available: bool
    pending_events: int = 0
    dead_letter_events: int = 0
    locked_events: int = 0
    oldest_pending_age_seconds: float = 0.0
    owners: tuple[OutboxOwnerMetrics, ...] = ()


@dataclass(frozen=True, slots=True)
class SecurityIncidentSeverityMetrics:
    """One fixed incident-severity bucket without incident or scope identity."""

    incident_severity: str
    open_incidents: int = 0
    containment_overdue: int = 0
    postmortem_pending: int = 0
    postmortem_overdue: int = 0

    def __post_init__(self) -> None:
        if self.incident_severity not in KNOWN_SECURITY_INCIDENT_SEVERITIES:
            raise ValueError("Unknown security incident severity")
        values = (
            self.open_incidents,
            self.containment_overdue,
            self.postmortem_pending,
            self.postmortem_overdue,
        )
        if any(type(value) is not int or value < 0 for value in values):
            raise ValueError(
                "Security incident metrics must be non-negative integers"
            )
        if self.containment_overdue > self.open_incidents:
            raise ValueError("Overdue containment cannot exceed open incidents")
        if self.postmortem_overdue > self.postmortem_pending:
            raise ValueError("Overdue postmortems cannot exceed pending postmortems")


@dataclass(frozen=True, slots=True)
class SecurityIncidentMetrics:
    """Aggregate incident deadlines safe for protected infrastructure scraping."""

    available: bool
    severities: tuple[SecurityIncidentSeverityMetrics, ...] = ()

    def __post_init__(self) -> None:
        actual = tuple(item.incident_severity for item in self.severities)
        if self.available and actual != KNOWN_SECURITY_INCIDENT_SEVERITIES:
            raise ValueError(
                "Available security incident metrics require every fixed severity"
            )
        if not self.available and self.severities:
            raise ValueError(
                "Unavailable security incident metrics cannot carry stale values"
            )


@dataclass(frozen=True, slots=True)
class DatabaseMetrics:
    """Fixed current-database capacity facts with no database or session labels."""

    available: bool
    connections: int = 0
    active_connections: int = 0
    connection_limit: int = 0
    waiting_locks: int = 0
    deadlocks_total: int = 0

    def __post_init__(self) -> None:
        values = (
            self.connections,
            self.active_connections,
            self.connection_limit,
            self.waiting_locks,
            self.deadlocks_total,
        )
        if any(type(value) is not int or value < 0 for value in values):
            raise ValueError("Database metrics must be non-negative integers")
        if self.available and (
            self.connection_limit == 0
            or self.active_connections > self.connections
        ):
            raise ValueError("Available database metrics are inconsistent")


@dataclass(frozen=True, slots=True)
class DatabasePoolMetrics:
    """Fixed per-process SQLAlchemy pool counts without connection labels."""

    available: bool
    size: int = 0
    checked_in: int = 0
    checked_out: int = 0
    overflow: int = 0
    checkout_wait_count: int = 0
    checkout_wait_sum_seconds: float = 0.0
    checkout_wait_bucket_counts: tuple[int, ...] = (0,) * len(DATABASE_POOL_WAIT_BUCKETS)
    checkout_timeouts_total: int = 0

    def __post_init__(self) -> None:
        values = (
            self.size,
            self.checked_in,
            self.checked_out,
            self.overflow,
            self.checkout_wait_count,
            self.checkout_timeouts_total,
        )
        if any(type(value) is not int or value < 0 for value in values):
            raise ValueError("Database pool metrics must be non-negative integers")
        if self.available and (self.size == 0 or self.checked_in > self.size):
            raise ValueError("Available database pool metrics are inconsistent")
        if (
            type(self.checkout_wait_sum_seconds) not in {int, float}
            or not isfinite(self.checkout_wait_sum_seconds)
            or self.checkout_wait_sum_seconds < 0
            or len(self.checkout_wait_bucket_counts) != len(DATABASE_POOL_WAIT_BUCKETS)
            or any(
                type(value) is not int or not 0 <= value <= self.checkout_wait_count
                for value in self.checkout_wait_bucket_counts
            )
            or any(
                current > following
                for current, following in zip(
                    self.checkout_wait_bucket_counts,
                    self.checkout_wait_bucket_counts[1:],
                )
            )
            or self.checkout_timeouts_total > self.checkout_wait_count
        ):
            raise ValueError("Database pool wait metrics are inconsistent")


class MetricsRegistry:
    """Collect low-cardinality process metrics without request or business data."""

    def __init__(
        self,
        duration_buckets: tuple[float, ...] = DEFAULT_DURATION_BUCKETS,
        *,
        workers_enabled: bool = True,
    ) -> None:
        if not duration_buckets or any(bucket <= 0 for bucket in duration_buckets):
            raise ValueError("Duration buckets must be positive")
        if tuple(sorted(set(duration_buckets))) != duration_buckets:
            raise ValueError("Duration buckets must be unique and increasing")
        self._duration_buckets = duration_buckets
        self._workers_enabled = workers_enabled
        self._request_counts: dict[tuple[str, str, str], int] = defaultdict(int)
        self._duration_counts: dict[tuple[str, str], int] = defaultdict(int)
        self._duration_sums: dict[tuple[str, str], float] = defaultdict(float)
        self._duration_bucket_counts: dict[tuple[str, str], list[int]] = {}
        self._error_counts: dict[str, int] = defaultdict(int)
        self._legacy_admin_requests: dict[str, int] = defaultdict(int)
        self._worker_runs: dict[tuple[str, str], int] = defaultdict(int)
        self._worker_items: dict[str, int] = defaultdict(int)
        self._worker_last_success: dict[str, float] = defaultdict(float)
        self._lock = Lock()

    def observe_request(self, *, method: str, route: str, status_code: int, duration_seconds: float) -> None:
        normalized_method = method.upper() if method.upper() in KNOWN_METHODS else "OTHER"
        normalized_route = route if route.startswith("/") and "?" not in route else "_unmatched"
        status_class = f"{status_code // 100}xx" if 100 <= status_code <= 599 else "other"
        duration = max(0.0, duration_seconds)
        duration_key = (normalized_method, normalized_route)
        with self._lock:
            self._request_counts[(normalized_method, normalized_route, status_class)] += 1
            self._duration_counts[duration_key] += 1
            self._duration_sums[duration_key] += duration
            bucket_counts = self._duration_bucket_counts.setdefault(
                duration_key,
                [0 for _ in self._duration_buckets],
            )
            for index, upper_bound in enumerate(self._duration_buckets):
                if duration <= upper_bound:
                    bucket_counts[index] += 1

    def record_unhandled_error(self, error_type: str) -> None:
        safe_type = error_type if fullmatch(r"[A-Za-z_][A-Za-z0-9_.]{0,127}", error_type) else "UnknownError"
        with self._lock:
            self._error_counts[safe_type] += 1

    def record_legacy_admin_request(self, outcome: str) -> None:
        """Count only a fixed served/blocked outcome, never a requested path."""

        if outcome not in KNOWN_LEGACY_ADMIN_OUTCOMES:
            raise ValueError("Unknown legacy administration request outcome")
        with self._lock:
            self._legacy_admin_requests[outcome] += 1

    def record_worker_success(
        self,
        worker: str,
        *,
        processed: int,
        observed_at: float | None = None,
    ) -> None:
        _validate_worker(worker)
        if isinstance(processed, bool) or not isinstance(processed, int) or processed < 0:
            raise ValueError("Processed worker item count must be a non-negative integer")
        timestamp = time() if observed_at is None else observed_at
        if not isfinite(timestamp) or timestamp < 0:
            raise ValueError("Worker observation timestamp must be finite and non-negative")
        with self._lock:
            self._worker_runs[(worker, "success")] += 1
            self._worker_items[worker] += processed
            self._worker_last_success[worker] = timestamp

    def record_worker_failure(self, worker: str) -> None:
        _validate_worker(worker)
        with self._lock:
            self._worker_runs[(worker, "error")] += 1

    def all_workers_have_succeeded(self) -> bool:
        """Whether every fixed worker completed at least one successful iteration."""
        with self._lock:
            return all(self._worker_last_success.get(worker, 0.0) > 0 for worker in KNOWN_WORKERS)

    def render_prometheus(
        self,
        *,
        outbox: OutboxMetrics | None = None,
        database: DatabaseMetrics | None = None,
        database_pool: DatabasePoolMetrics | None = None,
        security_incidents: SecurityIncidentMetrics | None = None,
    ) -> str:
        with self._lock:
            request_counts = dict(self._request_counts)
            duration_counts = dict(self._duration_counts)
            duration_sums = dict(self._duration_sums)
            duration_buckets = {key: tuple(value) for key, value in self._duration_bucket_counts.items()}
            error_counts = dict(self._error_counts)
            legacy_admin_requests = dict(self._legacy_admin_requests)
            worker_runs = dict(self._worker_runs)
            worker_items = dict(self._worker_items)
            worker_last_success = dict(self._worker_last_success)

        lines = [
            "# HELP taximobile_http_requests_total Completed HTTP requests by normalized route and status class.",
            "# TYPE taximobile_http_requests_total counter",
        ]
        for (method, route, status_class), count in sorted(request_counts.items()):
            labels = _labels(method=method, route=route, status_class=status_class)
            lines.append(f"taximobile_http_requests_total{{{labels}}} {count}")

        lines.extend(
            [
                "# HELP taximobile_http_request_duration_seconds HTTP request duration by normalized route.",
                "# TYPE taximobile_http_request_duration_seconds histogram",
            ]
        )
        for (method, route), count in sorted(duration_counts.items()):
            bucket_counts = duration_buckets[(method, route)]
            for upper_bound, bucket_count in zip(self._duration_buckets, bucket_counts, strict=True):
                labels = _labels(method=method, route=route, le=_number(upper_bound))
                lines.append(f"taximobile_http_request_duration_seconds_bucket{{{labels}}} {bucket_count}")
            infinite_labels = _labels(method=method, route=route, le="+Inf")
            lines.append(f"taximobile_http_request_duration_seconds_bucket{{{infinite_labels}}} {count}")
            labels = _labels(method=method, route=route)
            lines.append(f"taximobile_http_request_duration_seconds_sum{{{labels}}} {_number(duration_sums[(method, route)])}")
            lines.append(f"taximobile_http_request_duration_seconds_count{{{labels}}} {count}")

        lines.extend(
            [
                "# HELP taximobile_unhandled_errors_total Unhandled exceptions by safe exception class.",
                "# TYPE taximobile_unhandled_errors_total counter",
            ]
        )
        for error_type, count in sorted(error_counts.items()):
            lines.append(f"taximobile_unhandled_errors_total{{{_labels(error_type=error_type)}}} {count}")

        lines.extend(
            [
                "# HELP taximobile_legacy_admin_http_requests_total "
                "Requests addressed to the transitional administration namespace.",
                "# TYPE taximobile_legacy_admin_http_requests_total counter",
            ]
        )
        for outcome in KNOWN_LEGACY_ADMIN_OUTCOMES:
            lines.append(
                "taximobile_legacy_admin_http_requests_total"
                f'{{outcome="{outcome}"}} {legacy_admin_requests.get(outcome, 0)}'
            )

        if self._workers_enabled:
            lines.extend(
                [
                    "# HELP taximobile_worker_iterations_total Background worker iterations by fixed worker and outcome.",
                    "# TYPE taximobile_worker_iterations_total counter",
                ]
            )
            for worker in KNOWN_WORKERS:
                for outcome in ("success", "error"):
                    labels = _labels(worker=worker, outcome=outcome)
                    lines.append(
                        f"taximobile_worker_iterations_total{{{labels}}} "
                        f"{worker_runs.get((worker, outcome), 0)}"
                    )

            lines.extend(
                [
                    "# HELP taximobile_worker_items_processed_total Items processed by each fixed background worker.",
                    "# TYPE taximobile_worker_items_processed_total counter",
                ]
            )
            for worker in KNOWN_WORKERS:
                lines.append(
                    f"taximobile_worker_items_processed_total{{{_labels(worker=worker)}}} "
                    f"{worker_items.get(worker, 0)}"
                )

            lines.extend(
                [
                    "# HELP taximobile_worker_last_success_unixtime Unix timestamp of the last successful worker iteration.",
                    "# TYPE taximobile_worker_last_success_unixtime gauge",
                ]
            )
            for worker in KNOWN_WORKERS:
                lines.append(
                    f"taximobile_worker_last_success_unixtime{{{_labels(worker=worker)}}} "
                    f"{_number(worker_last_success.get(worker, 0.0))}"
                )

        if outbox is not None:
            lines.extend(_render_outbox_metrics(outbox))
        if database is not None:
            lines.extend(_render_database_metrics(database))
        if database_pool is not None:
            lines.extend(_render_database_pool_metrics(database_pool))
        if security_incidents is not None:
            lines.extend(_render_security_incident_metrics(security_incidents))
        return "\n".join(lines) + "\n"


def _render_security_incident_metrics(
    incidents: SecurityIncidentMetrics,
) -> list[str]:
    lines = [
        "# HELP taximobile_security_incident_metrics_available "
        "Whether the aggregate security incident deadline snapshot was read "
        "successfully.",
        "# TYPE taximobile_security_incident_metrics_available gauge",
        "taximobile_security_incident_metrics_available "
        f"{1 if incidents.available else 0}",
    ]
    if not incidents.available:
        return lines
    lines.extend(
        [
            "# HELP taximobile_security_incidents_open "
            "Non-closed security incidents by fixed severity.",
            "# TYPE taximobile_security_incidents_open gauge",
            "# HELP taximobile_security_incidents_containment_overdue "
            "Uncontained security incidents beyond their containment deadline "
            "by fixed severity.",
            "# TYPE taximobile_security_incidents_containment_overdue gauge",
            "# HELP taximobile_security_incidents_postmortem_pending "
            "Closed security incidents awaiting postmortem completion by fixed severity.",
            "# TYPE taximobile_security_incidents_postmortem_pending gauge",
            "# HELP taximobile_security_incidents_postmortem_overdue "
            "Closed security incidents beyond their postmortem deadline by fixed severity.",
            "# TYPE taximobile_security_incidents_postmortem_overdue gauge",
        ]
    )
    for bucket in incidents.severities:
        labels = _labels(incident_severity=bucket.incident_severity)
        lines.extend(
            [
                "taximobile_security_incidents_open"
                f"{{{labels}}} {bucket.open_incidents}",
                "taximobile_security_incidents_containment_overdue"
                f"{{{labels}}} {bucket.containment_overdue}",
                "taximobile_security_incidents_postmortem_pending"
                f"{{{labels}}} {bucket.postmortem_pending}",
                "taximobile_security_incidents_postmortem_overdue"
                f"{{{labels}}} {bucket.postmortem_overdue}",
            ]
        )
    return lines


def _render_database_pool_metrics(pool: DatabasePoolMetrics) -> list[str]:
    lines = [
        "# HELP taximobile_database_pool_metrics_available "
        "Whether the local SQLAlchemy pool snapshot was read successfully.",
        "# TYPE taximobile_database_pool_metrics_available gauge",
        f"taximobile_database_pool_metrics_available {1 if pool.available else 0}",
    ]
    if not pool.available:
        return lines
    lines.extend(
        [
            "# HELP taximobile_database_pool_size "
            "Configured persistent pool size for this process.",
            "# TYPE taximobile_database_pool_size gauge",
            f"taximobile_database_pool_size {pool.size}",
            "# HELP taximobile_database_pool_checked_in "
            "Idle pooled connections in this process.",
            "# TYPE taximobile_database_pool_checked_in gauge",
            f"taximobile_database_pool_checked_in {pool.checked_in}",
            "# HELP taximobile_database_pool_checked_out "
            "Checked-out connections in this process.",
            "# TYPE taximobile_database_pool_checked_out gauge",
            f"taximobile_database_pool_checked_out {pool.checked_out}",
            "# HELP taximobile_database_pool_overflow "
            "Current overflow connections in this process.",
            "# TYPE taximobile_database_pool_overflow gauge",
            f"taximobile_database_pool_overflow {pool.overflow}",
            "# HELP taximobile_database_pool_checkout_wait_seconds "
            "Time spent waiting for a database connection, including timed-out attempts.",
            "# TYPE taximobile_database_pool_checkout_wait_seconds histogram",
        ]
    )
    for upper_bound, count in zip(
        DATABASE_POOL_WAIT_BUCKETS,
        pool.checkout_wait_bucket_counts,
        strict=True,
    ):
        lines.append(
            "taximobile_database_pool_checkout_wait_seconds_bucket"
            f'{{le="{_number(upper_bound)}"}} {count}'
        )
    lines.extend(
        [
            "taximobile_database_pool_checkout_wait_seconds_bucket"
            f'{{le="+Inf"}} {pool.checkout_wait_count}',
            "taximobile_database_pool_checkout_wait_seconds_sum "
            f"{_number(pool.checkout_wait_sum_seconds)}",
            "taximobile_database_pool_checkout_wait_seconds_count "
            f"{pool.checkout_wait_count}",
            "# HELP taximobile_database_pool_checkout_timeouts_total "
            "Database connection checkout attempts that reached the configured timeout.",
            "# TYPE taximobile_database_pool_checkout_timeouts_total counter",
            "taximobile_database_pool_checkout_timeouts_total "
            f"{pool.checkout_timeouts_total}",
        ]
    )
    return lines


def _render_database_metrics(database: DatabaseMetrics) -> list[str]:
    lines = [
        "# HELP taximobile_database_metrics_available Whether aggregate PostgreSQL state was read successfully.",
        "# TYPE taximobile_database_metrics_available gauge",
        f"taximobile_database_metrics_available {1 if database.available else 0}",
    ]
    if not database.available:
        return lines
    utilization = (
        database.connections / database.connection_limit
        if database.connection_limit > 0
        else 0.0
    )
    lines.extend(
        [
            "# HELP taximobile_database_connections Connections to the current application database.",
            "# TYPE taximobile_database_connections gauge",
            f"taximobile_database_connections {database.connections}",
            "# HELP taximobile_database_active_connections Active connections to the current application database.",
            "# TYPE taximobile_database_active_connections gauge",
            f"taximobile_database_active_connections {database.active_connections}",
            "# HELP taximobile_database_connection_limit PostgreSQL server max_connections setting.",
            "# TYPE taximobile_database_connection_limit gauge",
            f"taximobile_database_connection_limit {database.connection_limit}",
            "# HELP taximobile_database_connection_utilization_ratio "
            "Current database connections divided by the server limit.",
            "# TYPE taximobile_database_connection_utilization_ratio gauge",
            f"taximobile_database_connection_utilization_ratio {_number(utilization)}",
            "# HELP taximobile_database_waiting_locks Ungranted locks for the current application database.",
            "# TYPE taximobile_database_waiting_locks gauge",
            f"taximobile_database_waiting_locks {database.waiting_locks}",
            "# HELP taximobile_database_deadlocks_total Deadlocks recorded for the current application database.",
            "# TYPE taximobile_database_deadlocks_total counter",
            f"taximobile_database_deadlocks_total {database.deadlocks_total}",
        ]
    )
    return lines


def _render_outbox_metrics(outbox: OutboxMetrics) -> list[str]:
    lines = [
        "# HELP taximobile_outbox_metrics_available Whether aggregate outbox state was read successfully.",
        "# TYPE taximobile_outbox_metrics_available gauge",
        f"taximobile_outbox_metrics_available {1 if outbox.available else 0}",
    ]
    if not outbox.available:
        # Omitting stale values is safer than reporting zeros during a database
        # incident. The availability gauge gives monitoring an explicit signal.
        return lines
    lines.extend(
        [
            "# HELP taximobile_outbox_pending_events Undelivered, non-dead-letter outbox events.",
            "# TYPE taximobile_outbox_pending_events gauge",
            f"taximobile_outbox_pending_events {outbox.pending_events}",
            "# HELP taximobile_outbox_dead_letter_events Outbox events requiring operator review.",
            "# TYPE taximobile_outbox_dead_letter_events gauge",
            f"taximobile_outbox_dead_letter_events {outbox.dead_letter_events}",
            "# HELP taximobile_outbox_locked_events Pending outbox events currently carrying a worker lease.",
            "# TYPE taximobile_outbox_locked_events gauge",
            f"taximobile_outbox_locked_events {outbox.locked_events}",
            "# HELP taximobile_outbox_oldest_pending_age_seconds Age of the oldest pending event, or zero when empty.",
            "# TYPE taximobile_outbox_oldest_pending_age_seconds gauge",
            f"taximobile_outbox_oldest_pending_age_seconds {_number(max(0.0, outbox.oldest_pending_age_seconds))}",
        ]
    )
    lines.extend(
        [
            "# HELP taximobile_outbox_owner_pending_events "
            "Pending outbox events by fixed operational owner.",
            "# TYPE taximobile_outbox_owner_pending_events gauge",
            "# HELP taximobile_outbox_owner_dead_letter_events "
            "Dead-lettered outbox events by fixed operational owner.",
            "# TYPE taximobile_outbox_owner_dead_letter_events gauge",
            "# HELP taximobile_outbox_owner_locked_events "
            "Leased pending outbox events by fixed operational owner.",
            "# TYPE taximobile_outbox_owner_locked_events gauge",
            "# HELP taximobile_outbox_owner_oldest_pending_age_seconds "
            "Oldest pending age by fixed operational owner.",
            "# TYPE taximobile_outbox_owner_oldest_pending_age_seconds gauge",
        ]
    )
    for owner in sorted(outbox.owners, key=lambda item: item.owner):
        labels = _labels(owner=owner.owner)
        lines.extend(
            [
                f"taximobile_outbox_owner_pending_events{{{labels}}} {owner.pending_events}",
                f"taximobile_outbox_owner_dead_letter_events{{{labels}}} "
                f"{owner.dead_letter_events}",
                f"taximobile_outbox_owner_locked_events{{{labels}}} {owner.locked_events}",
                f"taximobile_outbox_owner_oldest_pending_age_seconds{{{labels}}} "
                f"{_number(max(0.0, owner.oldest_pending_age_seconds))}",
            ]
        )
    return lines


def _validate_worker(worker: str) -> None:
    if worker not in KNOWN_WORKERS:
        raise ValueError(f"Unknown background worker: {worker}")


def _labels(**values: str) -> str:
    return ",".join(f'{name}="{_escape(value)}"' for name, value in values.items())


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _number(value: float) -> str:
    return format(value, ".12g")
