"""Bounded, low-cardinality instrumentation for the async database pool."""

from threading import Lock
from time import monotonic

from sqlalchemy.exc import TimeoutError as SqlAlchemyTimeoutError
from sqlalchemy.pool import AsyncAdaptedQueuePool

from taximobile_api.core.metrics import DATABASE_POOL_WAIT_BUCKETS


class InstrumentedAsyncAdaptedQueuePool(AsyncAdaptedQueuePool):
    """Record connection checkout waits without connection or caller identity."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._taximobile_metrics_lock = Lock()
        self._taximobile_wait_count = 0
        self._taximobile_wait_sum_seconds = 0.0
        self._taximobile_wait_bucket_counts = [0] * len(DATABASE_POOL_WAIT_BUCKETS)
        self._taximobile_timeouts_total = 0

    def _record_checkout_wait(self, elapsed_seconds: float, *, timed_out: bool) -> None:
        elapsed = max(0.0, elapsed_seconds)
        with self._taximobile_metrics_lock:
            self._taximobile_wait_count += 1
            self._taximobile_wait_sum_seconds += elapsed
            if timed_out:
                self._taximobile_timeouts_total += 1
            for index, upper_bound in enumerate(DATABASE_POOL_WAIT_BUCKETS):
                if elapsed <= upper_bound:
                    self._taximobile_wait_bucket_counts[index] += 1

    def _do_get(self):
        started = monotonic()
        try:
            connection = super()._do_get()
        except SqlAlchemyTimeoutError:
            self._record_checkout_wait(monotonic() - started, timed_out=True)
            raise
        else:
            self._record_checkout_wait(monotonic() - started, timed_out=False)
            return connection

    def taximobile_wait_snapshot(self) -> tuple[int, float, tuple[int, ...], int]:
        """Return one internally consistent cumulative snapshot."""

        with self._taximobile_metrics_lock:
            return (
                self._taximobile_wait_count,
                self._taximobile_wait_sum_seconds,
                tuple(self._taximobile_wait_bucket_counts),
                self._taximobile_timeouts_total,
            )
