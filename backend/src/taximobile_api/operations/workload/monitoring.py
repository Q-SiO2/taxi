"""Privacy-bounded Prometheus sampling for synthetic capacity phases."""

import asyncio
from collections import Counter
import json
from math import ceil, isfinite
from urllib.parse import urlsplit

import httpx

from taximobile_api.operations.performance_smoke import is_local_target


PROMETHEUS_QUERIES = {
    "core_targets_up": 'min(up{job=~"taximobile-api|taximobile-worker|taximobile-loki|taximobile-alloy"})',
    "http_request_rate_per_second": "sum(rate(taximobile_http_requests_total[1m]))",
    "http_5xx_ratio": (
        'sum(rate(taximobile_http_requests_total{status_class="5xx"}[1m])) '
        "/ clamp_min(sum(rate(taximobile_http_requests_total[1m])), 0.001)"
    ),
    "http_p95_latency_seconds": (
        "histogram_quantile(0.95, sum by (le) "
        "(rate(taximobile_http_request_duration_seconds_bucket[1m])))"
    ),
    "worker_seconds_since_success": "max(time() - taximobile_worker_last_success_unixtime)",
    "worker_errors_total": 'sum(taximobile_worker_iterations_total{outcome="error"})',
    "outbox_pending_events": "max(taximobile_outbox_owner_pending_events)",
    "outbox_oldest_pending_age_seconds": "max(taximobile_outbox_owner_oldest_pending_age_seconds)",
    "outbox_dead_letter_events": "max(taximobile_outbox_owner_dead_letter_events)",
    "unhandled_errors_total": "sum(taximobile_unhandled_errors_total) or vector(0)",
    "log_dropped_lines_total": "sum(loki_process_dropped_lines_total) or vector(0)",
    "log_delivery_failures_total": (
        "(sum(loki_write_dropped_entries_total) or vector(0)) + "
        "(sum(loki_write_batch_retries_total) or vector(0))"
    ),
    "database_metrics_up": "min(taximobile_database_metrics_available)",
    "database_connection_utilization_ratio": (
        "max(taximobile_database_connection_utilization_ratio)"
    ),
    "database_active_connections": "max(taximobile_database_active_connections)",
    "database_waiting_locks": "max(taximobile_database_waiting_locks)",
    "database_deadlocks_total": "max(taximobile_database_deadlocks_total)",
    "database_pool_metrics_up": "min(taximobile_database_pool_metrics_available)",
    "database_pool_checked_out": "max(taximobile_database_pool_checked_out)",
    "database_pool_overflow": "max(taximobile_database_pool_overflow)",
    "database_pool_checkout_wait_p95_seconds": (
        "(histogram_quantile(0.95, sum by (le) "
        "(rate(taximobile_database_pool_checkout_wait_seconds_bucket[1m]))) "
        "and on() (sum(rate(taximobile_database_pool_checkout_wait_seconds_count[1m])) > 0)) "
        "or vector(0)"
    ),
    "database_pool_checkout_timeouts_total": (
        "sum(taximobile_database_pool_checkout_timeouts_total) or vector(0)"
    ),
}
COUNTER_METRICS = {
    "worker_errors_total",
    "unhandled_errors_total",
    "log_dropped_lines_total",
    "log_delivery_failures_total",
    "database_deadlocks_total",
    "database_pool_checkout_timeouts_total",
}
THRESHOLD_CHECKS = {
    "core_targets_up_min": ("core_targets_up", "min", "minimum"),
    "http_5xx_ratio_max": ("http_5xx_ratio", "max", "maximum"),
    "http_p95_latency_seconds_max": ("http_p95_latency_seconds", "max", "maximum"),
    "worker_seconds_since_success_max": ("worker_seconds_since_success", "max", "maximum"),
    "worker_errors_increase_max": ("worker_errors_total", "increase", "maximum"),
    "outbox_pending_events_max": ("outbox_pending_events", "max", "maximum"),
    "outbox_oldest_pending_age_seconds_max": (
        "outbox_oldest_pending_age_seconds", "max", "maximum",
    ),
    "outbox_dead_letter_events_max": ("outbox_dead_letter_events", "max", "maximum"),
    "unhandled_errors_increase_max": ("unhandled_errors_total", "increase", "maximum"),
    "log_dropped_lines_increase_max": ("log_dropped_lines_total", "increase", "maximum"),
    "log_delivery_failures_increase_max": (
        "log_delivery_failures_total", "increase", "maximum",
    ),
    "database_metrics_up_min": ("database_metrics_up", "min", "minimum"),
    "database_connection_utilization_ratio_max": (
        "database_connection_utilization_ratio", "max", "maximum",
    ),
    "database_active_connections_max": (
        "database_active_connections", "max", "maximum",
    ),
    "database_waiting_locks_max": ("database_waiting_locks", "max", "maximum"),
    "database_deadlocks_increase_max": (
        "database_deadlocks_total", "increase", "maximum",
    ),
    "database_pool_metrics_up_min": (
        "database_pool_metrics_up", "min", "minimum",
    ),
    "database_pool_checked_out_max": (
        "database_pool_checked_out", "max", "maximum",
    ),
    "database_pool_overflow_max": (
        "database_pool_overflow", "max", "maximum",
    ),
    "database_pool_checkout_wait_p95_seconds_max": (
        "database_pool_checkout_wait_p95_seconds", "max", "maximum",
    ),
    "database_pool_checkout_timeouts_increase_max": (
        "database_pool_checkout_timeouts_total", "increase", "maximum",
    ),
}


def _validate_origin(origin: str, *, confirm_nonlocal: bool) -> str:
    try:
        url = urlsplit(origin)
        port = url.port
        valid = (
            url.scheme in {"http", "https"}
            and bool(url.hostname)
            and url.username is None
            and url.password is None
            and url.path in {"", "/"}
            and not url.query
            and not url.fragment
            and (port is None or 1 <= port <= 65535)
            and origin.isascii()
            and not any(character.isspace() for character in origin)
            and "\\" not in origin
        )
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("Prometheus target must be an HTTP origin without credentials, path or query.")
    if not is_local_target(origin) and (url.scheme != "https" or confirm_nonlocal is not True):
        raise ValueError("Nonlocal Prometheus targets require HTTPS and explicit confirmation.")
    return origin.rstrip("/")


def _summary(values: list[float], *, counter: bool) -> dict:
    ordered = sorted(values)
    result = {
        "samples": len(values),
        "min": round(ordered[0], 6),
        "average": round(sum(values) / len(values), 6),
        "p50": round(ordered[ceil(.5 * len(ordered)) - 1], 6),
        "p95": round(ordered[ceil(.95 * len(ordered)) - 1], 6),
        "p99": round(ordered[ceil(.99 * len(ordered)) - 1], 6),
        "max": round(ordered[-1], 6),
    }
    if counter:
        increase = 0.0
        for previous, current in zip(values, values[1:]):
            increase += current - previous if current >= previous else current
        result["increase"] = round(max(0.0, increase), 6)
    return result


class PrometheusPhaseSampler:
    def __init__(
        self,
        origin: str,
        *,
        sample_interval_seconds: float,
        query_timeout_seconds: float,
        thresholds: dict[str, float],
        confirm_monitoring_target: bool,
        confirm_nonlocal_target: bool,
        transport=None,
    ) -> None:
        if confirm_monitoring_target is not True:
            raise ValueError("Confirm the protected Prometheus target before sampling.")
        self.origin = _validate_origin(origin, confirm_nonlocal=confirm_nonlocal_target)
        if (
            type(sample_interval_seconds) not in {int, float}
            or not isfinite(sample_interval_seconds)
            or not 5 <= sample_interval_seconds <= 60
            or type(query_timeout_seconds) not in {int, float}
            or not isfinite(query_timeout_seconds)
            or not .5 <= query_timeout_seconds <= 10
            or query_timeout_seconds >= sample_interval_seconds
        ):
            raise ValueError("Prometheus sampling timings are outside the reviewed bounds.")
        if set(thresholds) != set(THRESHOLD_CHECKS):
            raise ValueError("Prometheus thresholds do not match the fixed evidence contract.")
        if any(
            type(value) not in {int, float}
            or not isfinite(value)
            or not 0 <= value <= 1_000_000_000
            for value in thresholds.values()
        ):
            raise ValueError("Prometheus thresholds must be finite numbers from zero to one billion.")
        ratio_thresholds = (
            "core_targets_up_min",
            "http_5xx_ratio_max",
            "database_metrics_up_min",
            "database_connection_utilization_ratio_max",
            "database_pool_metrics_up_min",
        )
        if any(not 0 <= thresholds[name] <= 1 for name in ratio_thresholds):
            raise ValueError("Prometheus availability and ratio thresholds must be between zero and one.")
        self.sample_interval_seconds = sample_interval_seconds
        self.query_timeout_seconds = query_timeout_seconds
        self.thresholds = dict(thresholds)
        self.transport = transport

    async def _query(self, client: httpx.AsyncClient, expression: str) -> tuple[str, float | None]:
        outcome = "invalid_response"
        try:
            async with asyncio.timeout(self.query_timeout_seconds):
                async with client.stream("GET", "/api/v1/query", params={"query": expression}) as response:
                    if response.status_code != 200:
                        return f"http_{response.status_code}", None
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > 65536:
                            return "oversized_response", None
            try:
                document = json.loads(body)
                result = document["data"]["result"]
                if (
                    document.get("status") != "success"
                    or document["data"].get("resultType") != "vector"
                    or not isinstance(result, list)
                    or len(result) != 1
                    or result[0].get("metric") != {}
                    or not isinstance(result[0].get("value"), list)
                    or len(result[0]["value"]) != 2
                ):
                    return outcome, None
                value = float(result[0]["value"][1])
                if not isfinite(value):
                    return outcome, None
                return "ok", value
            except (KeyError, TypeError, ValueError, UnicodeError, RecursionError):
                return outcome, None
        except (httpx.HTTPError, TimeoutError):
            return "transport_error", None

    async def sample_until(self, stopped: asyncio.Event) -> dict:
        values = {name: [] for name in PROMETHEUS_QUERIES}
        failures: Counter[str] = Counter()
        rounds = 0
        async with httpx.AsyncClient(
            base_url=self.origin,
            timeout=self.query_timeout_seconds,
            follow_redirects=False,
            trust_env=False,
            limits=httpx.Limits(
                max_connections=len(PROMETHEUS_QUERIES),
                max_keepalive_connections=len(PROMETHEUS_QUERIES),
            ),
            transport=self.transport,
        ) as client:
            while True:
                rounds += 1
                results = await asyncio.gather(*(
                    self._query(client, expression)
                    for expression in PROMETHEUS_QUERIES.values()
                ))
                for name, (outcome, value) in zip(PROMETHEUS_QUERIES, results, strict=True):
                    if outcome == "ok":
                        values[name].append(value)
                    else:
                        failures[f"{name}:{outcome}"] += 1
                if stopped.is_set():
                    break
                try:
                    await asyncio.wait_for(stopped.wait(), timeout=self.sample_interval_seconds)
                    break
                except TimeoutError:
                    pass

        metrics = {
            name: _summary(samples, counter=name in COUNTER_METRICS)
            for name, samples in values.items()
            if samples
        }
        threshold_failures = []
        for threshold_name, (metric_name, statistic, direction) in THRESHOLD_CHECKS.items():
            if metric_name not in metrics:
                threshold_failures.append(threshold_name)
                continue
            observed = metrics[metric_name][statistic]
            threshold = self.thresholds[threshold_name]
            exceeded = observed < threshold if direction == "minimum" else observed > threshold
            if exceeded:
                threshold_failures.append(threshold_name)
        complete = (
            rounds > 0
            and not failures
            and all(len(samples) == rounds for samples in values.values())
            and not threshold_failures
        )
        return {
            "status": "COMPLETE" if complete else "INCOMPLETE",
            "sample_rounds": rounds,
            "query_failures": dict(sorted(failures.items())),
            "threshold_failures": sorted(threshold_failures),
            "thresholds": dict(sorted(self.thresholds.items())),
            "metrics": dict(sorted(metrics.items())),
        }
