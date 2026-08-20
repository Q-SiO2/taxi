"""Privacy-bounded in-process metrics for per-instance operational scraping."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import isfinite
from re import fullmatch
from threading import Lock
from time import time


DEFAULT_DURATION_BUCKETS = (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
KNOWN_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}
KNOWN_WORKERS = ("matching", "outbox", "credentials")


@dataclass(frozen=True, slots=True)
class OutboxMetrics:
    """Aggregate delivery state safe to expose to infrastructure monitoring."""

    available: bool
    pending_events: int = 0
    dead_letter_events: int = 0
    locked_events: int = 0
    oldest_pending_age_seconds: float = 0.0


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

    def render_prometheus(self, *, outbox: OutboxMetrics | None = None) -> str:
        with self._lock:
            request_counts = dict(self._request_counts)
            duration_counts = dict(self._duration_counts)
            duration_sums = dict(self._duration_sums)
            duration_buckets = {key: tuple(value) for key, value in self._duration_bucket_counts.items()}
            error_counts = dict(self._error_counts)
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
        return "\n".join(lines) + "\n"


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
