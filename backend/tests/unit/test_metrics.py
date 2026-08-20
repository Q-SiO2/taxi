from taximobile_api.core.metrics import MetricsRegistry, OutboxMetrics


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
        )
    )

    assert "taximobile_outbox_metrics_available 1" in output
    assert "taximobile_outbox_pending_events 7" in output
    assert "taximobile_outbox_dead_letter_events 2" in output
    assert "taximobile_outbox_locked_events 1" in output
    assert "taximobile_outbox_oldest_pending_age_seconds 12.5" in output
    assert "resource_id" not in output
    assert "payload" not in output


def test_unavailable_outbox_metrics_do_not_report_misleading_zero_counts() -> None:
    output = MetricsRegistry().render_prometheus(outbox=OutboxMetrics(available=False))

    assert "taximobile_outbox_metrics_available 0" in output
    assert "taximobile_outbox_pending_events" not in output
    assert "taximobile_outbox_dead_letter_events" not in output
