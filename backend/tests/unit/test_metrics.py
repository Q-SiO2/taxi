from taximobile_api.core.metrics import (
    DATABASE_POOL_WAIT_BUCKETS,
    DatabaseMetrics,
    DatabasePoolMetrics,
    MetricsRegistry,
    OutboxMetrics,
    OutboxOwnerMetrics,
    SecurityIncidentMetrics,
    SecurityIncidentSeverityMetrics,
)


def test_metrics_use_normalized_bounded_labels_and_cumulative_buckets() -> None:
    registry = MetricsRegistry(duration_buckets=(0.1, 0.5))
    registry.observe_request(
        method="GET",
        route="/api/v1/rides/{ride_id}",
        status_code=200,
        duration_seconds=0.25,
    )
    registry.observe_request(
        method="UNTRUSTED-METHOD",
        route="/private/path?email=passenger@example.com",
        status_code=503,
        duration_seconds=0.75,
    )
    registry.record_unhandled_error("RuntimeError")
    registry.record_unhandled_error("unsafe\nlabel")

    output = registry.render_prometheus()

    assert 'method="GET",route="/api/v1/rides/{ride_id}",status_class="2xx"} 1' in output
    assert 'method="GET",route="/api/v1/rides/{ride_id}",le="0.1"} 0' in output
    assert 'method="GET",route="/api/v1/rides/{ride_id}",le="0.5"} 1' in output
    assert 'method="OTHER",route="_unmatched",status_class="5xx"} 1' in output
    assert 'error_type="RuntimeError"} 1' in output
    assert 'error_type="UnknownError"} 1' in output
    assert "passenger@example.com" not in output
    assert "UNTRUSTED-METHOD" not in output


def test_metrics_expose_only_fixed_legacy_admin_served_and_blocked_outcomes() -> None:
    registry = MetricsRegistry()
    registry.record_legacy_admin_request("served")
    registry.record_legacy_admin_request("blocked")
    registry.record_legacy_admin_request("blocked")

    output = registry.render_prometheus()

    assert (
        'taximobile_legacy_admin_http_requests_total{outcome="served"} 1'
        in output
    )
    assert (
        'taximobile_legacy_admin_http_requests_total{outcome="blocked"} 2'
        in output
    )
    assert "/admin" not in "\n".join(
        line
        for line in output.splitlines()
        if line.startswith("taximobile_legacy_admin_http_requests_total{")
    )

    try:
        registry.record_legacy_admin_request("private-route-value")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected an unbounded legacy-admin outcome to fail")


def test_metrics_reject_invalid_histogram_buckets() -> None:
    for buckets in ((), (0.5, 0.1), (0.1, 0.1), (-1.0,)):
        try:
            MetricsRegistry(duration_buckets=buckets)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected invalid buckets to be rejected: {buckets}")


def test_metrics_render_fixed_worker_series_and_last_success() -> None:
    registry = MetricsRegistry()
    registry.record_worker_success("matching", processed=4, observed_at=123.5)
    registry.record_worker_failure("outbox")

    output = registry.render_prometheus()

    assert 'taximobile_worker_iterations_total{worker="matching",outcome="success"} 1' in output
    assert 'taximobile_worker_iterations_total{worker="outbox",outcome="error"} 1' in output
    assert 'taximobile_worker_items_processed_total{worker="matching"} 4' in output
    assert 'taximobile_worker_last_success_unixtime{worker="matching"} 123.5' in output
    assert 'taximobile_worker_last_success_unixtime{worker="outbox"} 0' in output


def test_api_only_registry_omits_worker_series_so_missing_scrapes_can_alert() -> None:
    output = MetricsRegistry(workers_enabled=False).render_prometheus()

    assert "taximobile_worker_iterations_total" not in output
    assert "taximobile_worker_items_processed_total" not in output
    assert "taximobile_worker_last_success_unixtime" not in output


def test_metrics_reject_unknown_workers_and_invalid_item_counts() -> None:
    registry = MetricsRegistry()

    for worker, processed in (("private-user-id", 1), ("matching", -1), ("matching", True)):
        try:
            registry.record_worker_success(worker, processed=processed)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected invalid worker telemetry to be rejected")

    try:
        registry.record_worker_failure("arbitrary-worker")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected arbitrary worker label to be rejected")

    for invalid_timestamp in (-1.0, float("inf"), float("nan")):
        try:
            registry.record_worker_success(
                "matching",
                processed=0,
                observed_at=invalid_timestamp,
            )
        except ValueError:
            pass
        else:
            raise AssertionError("Expected invalid worker timestamp to be rejected")


def test_metrics_render_privacy_bounded_outbox_gauges() -> None:
    output = MetricsRegistry().render_prometheus(
        outbox=OutboxMetrics(
            available=True,
            pending_events=7,
            dead_letter_events=2,
            locked_events=1,
            oldest_pending_age_seconds=12.5,
            owners=(
                OutboxOwnerMetrics(
                    owner="driver_compliance",
                    pending_events=3,
                    dead_letter_events=2,
                    locked_events=1,
                    oldest_pending_age_seconds=7.5,
                ),
            ),
        )
    )

    assert "taximobile_outbox_metrics_available 1" in output
    assert "taximobile_outbox_pending_events 7" in output
    assert "taximobile_outbox_dead_letter_events 2" in output
    assert "taximobile_outbox_locked_events 1" in output
    assert "taximobile_outbox_oldest_pending_age_seconds 12.5" in output
    assert 'taximobile_outbox_owner_pending_events{owner="driver_compliance"} 3' in output
    assert 'taximobile_outbox_owner_dead_letter_events{owner="driver_compliance"} 2' in output
    assert 'taximobile_outbox_owner_locked_events{owner="driver_compliance"} 1' in output
    assert 'taximobile_outbox_owner_oldest_pending_age_seconds{owner="driver_compliance"} 7.5' in output
    assert "resource_id" not in output
    assert "payload" not in output


def test_unavailable_outbox_metrics_do_not_report_misleading_zero_counts() -> None:
    output = MetricsRegistry().render_prometheus(outbox=OutboxMetrics(available=False))

    assert "taximobile_outbox_metrics_available 0" in output
    assert "taximobile_outbox_pending_events" not in output
    assert "taximobile_outbox_dead_letter_events" not in output


def test_metrics_render_only_fixed_security_incident_severity_deadlines() -> None:
    output = MetricsRegistry().render_prometheus(
        security_incidents=SecurityIncidentMetrics(
            available=True,
            severities=(
                SecurityIncidentSeverityMetrics("SEV1", 2, 1, 0, 0),
                SecurityIncidentSeverityMetrics("SEV2", 1, 0, 1, 1),
                SecurityIncidentSeverityMetrics("SEV3"),
                SecurityIncidentSeverityMetrics("SEV4"),
            ),
        )
    )

    assert "taximobile_security_incident_metrics_available 1" in output
    assert (
        'taximobile_security_incidents_open{incident_severity="SEV1"} 2'
        in output
    )
    assert (
        'taximobile_security_incidents_containment_overdue{incident_severity="SEV1"} 1'
        in output
    )
    assert (
        'taximobile_security_incidents_postmortem_overdue{incident_severity="SEV2"} 1'
        in output
    )
    assert "market_id" not in output
    assert "incident_id" not in output


def test_unavailable_security_incident_metrics_omit_stale_counts() -> None:
    output = MetricsRegistry().render_prometheus(
        security_incidents=SecurityIncidentMetrics(available=False)
    )

    assert "taximobile_security_incident_metrics_available 0" in output
    assert "taximobile_security_incidents_open" not in output


def test_metrics_render_unlabelled_database_capacity_gauges_and_counter() -> None:
    output = MetricsRegistry().render_prometheus(database=DatabaseMetrics(
        available=True,
        connections=25,
        active_connections=7,
        connection_limit=100,
        waiting_locks=2,
        deadlocks_total=3,
    ))

    assert "taximobile_database_metrics_available 1" in output
    assert "taximobile_database_connections 25" in output
    assert "taximobile_database_active_connections 7" in output
    assert "taximobile_database_connection_limit 100" in output
    assert "taximobile_database_connection_utilization_ratio 0.25" in output
    assert "taximobile_database_waiting_locks 2" in output
    assert "taximobile_database_deadlocks_total 3" in output
    assert "database_name" not in output
    assert "session" not in output


def test_unavailable_database_metrics_omit_stale_zero_capacity_values() -> None:
    output = MetricsRegistry().render_prometheus(
        database=DatabaseMetrics(available=False)
    )

    assert "taximobile_database_metrics_available 0" in output
    assert "taximobile_database_connections" not in output
    assert "taximobile_database_deadlocks_total" not in output


def test_database_metrics_reject_invalid_or_inconsistent_values() -> None:
    invalid = (
        {"available": True, "connections": -1, "connection_limit": 100},
        {"available": True, "connections": 1, "active_connections": 2, "connection_limit": 100},
        {"available": True, "connections": 1, "connection_limit": 0},
        {"available": True, "connections": True, "connection_limit": 100},
    )
    for values in invalid:
        try:
            DatabaseMetrics(**values)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected invalid database metrics to be rejected")


def test_metrics_render_unlabelled_per_process_database_pool_gauges() -> None:
    output = MetricsRegistry().render_prometheus(database_pool=DatabasePoolMetrics(
        available=True,
        size=5,
        checked_in=2,
        checked_out=4,
        overflow=1,
        checkout_wait_count=2,
        checkout_wait_sum_seconds=0.25,
        checkout_wait_bucket_counts=(1,) * len(DATABASE_POOL_WAIT_BUCKETS),
        checkout_timeouts_total=1,
    ))

    assert "taximobile_database_pool_metrics_available 1" in output
    assert "taximobile_database_pool_size 5" in output
    assert "taximobile_database_pool_checked_in 2" in output
    assert "taximobile_database_pool_checked_out 4" in output
    assert "taximobile_database_pool_overflow 1" in output
    assert 'taximobile_database_pool_checkout_wait_seconds_bucket{le="0.001"} 1' in output
    assert 'taximobile_database_pool_checkout_wait_seconds_bucket{le="+Inf"} 2' in output
    assert "taximobile_database_pool_checkout_wait_seconds_sum 0.25" in output
    assert "taximobile_database_pool_checkout_wait_seconds_count 2" in output
    assert "taximobile_database_pool_checkout_timeouts_total 1" in output
    assert "connection_id" not in output


def test_unavailable_database_pool_metrics_omit_stale_values() -> None:
    output = MetricsRegistry().render_prometheus(
        database_pool=DatabasePoolMetrics(available=False)
    )

    assert "taximobile_database_pool_metrics_available 0" in output
    assert "taximobile_database_pool_checked_out" not in output


def test_database_pool_metrics_reject_invalid_or_inconsistent_values() -> None:
    for values in (
        {"available": True, "size": 0},
        {"available": True, "size": 5, "checked_in": 6},
        {"available": True, "size": 5, "checked_out": -1},
        {"available": True, "size": 5, "overflow": True},
        {
            "available": True,
            "size": 5,
            "checkout_wait_count": 1,
            "checkout_wait_bucket_counts": (1,),
        },
        {
            "available": True,
            "size": 5,
            "checkout_wait_count": 1,
            "checkout_wait_bucket_counts": (1, 0) + (0,) * 12,
        },
        {
            "available": True,
            "size": 5,
            "checkout_wait_count": 1,
            "checkout_timeouts_total": 2,
        },
        {
            "available": True,
            "size": 5,
            "checkout_wait_sum_seconds": float("inf"),
        },
    ):
        try:
            DatabasePoolMetrics(**values)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected invalid database pool metrics to be rejected")
