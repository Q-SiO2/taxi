import asyncio
import json
import logging
from io import StringIO

import pytest

from taximobile_api.core.logging import JsonFormatter
from taximobile_api.core.config import Settings
from taximobile_api.core.metrics import MetricsRegistry
from taximobile_api.workers.application import BackgroundWorkerRuntime
from taximobile_api.workers.runtime import run_polling_processor


class StopLoop(Exception):
    pass


async def stop_after_iteration(_: float) -> None:
    raise StopLoop


@pytest.mark.asyncio
async def test_worker_runtime_records_successful_bounded_batch() -> None:
    class Processor:
        async def process_once(self) -> int:
            return 3

    metrics = MetricsRegistry()
    with pytest.raises(StopLoop):
        await run_polling_processor(
            worker="matching",
            processor=Processor(),
            poll_seconds=1,
            metrics=metrics,
            sleep=stop_after_iteration,
        )

    output = metrics.render_prometheus()
    assert 'taximobile_worker_iterations_total{worker="matching",outcome="success"} 1' in output
    assert 'taximobile_worker_iterations_total{worker="matching",outcome="error"} 0' in output
    assert 'taximobile_worker_items_processed_total{worker="matching"} 3' in output


@pytest.mark.asyncio
async def test_worker_runtime_records_safe_failure_without_exception_message() -> None:
    class Processor:
        async def process_once(self) -> int:
            raise RuntimeError("private-provider-token-must-not-appear")

    metrics = MetricsRegistry()
    logger = logging.getLogger("taximobile_api.worker-test")
    output_stream = StringIO()
    handler = logging.StreamHandler(output_stream)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    try:
        with pytest.raises(StopLoop):
            await run_polling_processor(
                worker="outbox",
                processor=Processor(),
                poll_seconds=1,
                metrics=metrics,
                sleep=stop_after_iteration,
                logger=logger,
            )
    finally:
        logger.removeHandler(handler)

    output = metrics.render_prometheus()
    assert 'taximobile_worker_iterations_total{worker="outbox",outcome="error"} 1' in output
    assert 'taximobile_worker_items_processed_total{worker="outbox"} 0' in output
    log_payload = json.loads(output_stream.getvalue())
    assert log_payload["message"] == "worker_iteration_failed"
    assert log_payload["worker"] == "outbox"
    assert log_payload["error_type"] == "RuntimeError"
    assert "private-provider-token-must-not-appear" not in output_stream.getvalue()


@pytest.mark.asyncio
async def test_worker_runtime_turns_invalid_processor_result_into_retry_failure() -> None:
    class Processor:
        async def process_once(self) -> int:
            return -1

    metrics = MetricsRegistry()
    logger = logging.getLogger("taximobile_api.invalid-worker-result-test")
    logger.addHandler(logging.NullHandler())
    logger.propagate = False
    with pytest.raises(StopLoop):
        await run_polling_processor(
            worker="matching",
            processor=Processor(),
            poll_seconds=1,
            metrics=metrics,
            sleep=stop_after_iteration,
            logger=logger,
        )

    output = metrics.render_prometheus()
    assert 'taximobile_worker_iterations_total{worker="matching",outcome="success"} 0' in output
    assert 'taximobile_worker_iterations_total{worker="matching",outcome="error"} 1' in output


@pytest.mark.asyncio
async def test_worker_runtime_propagates_cancellation_without_retrying() -> None:
    class Processor:
        async def process_once(self) -> int:
            raise asyncio.CancelledError

    metrics = MetricsRegistry()
    with pytest.raises(asyncio.CancelledError):
        await run_polling_processor(
            worker="matching",
            processor=Processor(),
            poll_seconds=1,
            metrics=metrics,
            sleep=stop_after_iteration,
        )

    output = metrics.render_prometheus()
    assert 'taximobile_worker_iterations_total{worker="matching",outcome="success"} 0' in output
    assert 'taximobile_worker_iterations_total{worker="matching",outcome="error"} 0' in output


@pytest.mark.asyncio
async def test_background_worker_supervisor_owns_all_loops_and_stops_them(monkeypatch) -> None:
    started: set[str] = set()
    block = asyncio.Event()

    def loop(name: str):
        async def run(*_args):
            started.add(name)
            await block.wait()
        return run

    monkeypatch.setattr("taximobile_api.workers.application.run_outbox_processor", loop("outbox"))
    monkeypatch.setattr("taximobile_api.workers.application.run_matching_processor", loop("matching"))
    monkeypatch.setattr("taximobile_api.workers.application.run_credential_lifecycle_processor", loop("credentials"))
    monkeypatch.setattr("taximobile_api.workers.application.run_scheduling_processor", loop("scheduling"))
    monkeypatch.setattr("taximobile_api.workers.application.run_analytics_processor", loop("analytics"))
    monkeypatch.setattr(
        "taximobile_api.workers.application.run_case_alert_processor",
        loop("case_alerts"),
    )
    monkeypatch.setattr(
        "taximobile_api.workers.application.run_case_retention_processor",
        loop("case_retention"),
    )
    monkeypatch.setattr(
        "taximobile_api.workers.application.run_driver_document_retention_processor",
        loop("driver_document_retention"),
    )

    class Publisher:
        async def publish_ride_refresh(self, *_args):
            return None

    runtime = BackgroundWorkerRuntime(
        sessions=object(),  # type: ignore[arg-type]
        settings=Settings.from_environment(),
        live_event_publisher=Publisher(),
        push_provider=None,
    )
    runtime.start(MetricsRegistry())
    await asyncio.sleep(0)

    assert runtime.is_running
    assert started == {
        "matching",
        "outbox",
        "credentials",
        "scheduling",
        "analytics",
        "case_alerts",
        "case_retention",
        "driver_document_retention",
    }

    await runtime.stop()
    assert not runtime.is_running
