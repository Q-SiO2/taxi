import pytest

from taximobile_api.db.pool import InstrumentedAsyncAdaptedQueuePool


def test_pool_wait_snapshot_is_cumulative_bounded_and_identity_free() -> None:
    pool = InstrumentedAsyncAdaptedQueuePool(
        lambda: object(),
        pool_size=1,
        max_overflow=0,
        timeout=1,
    )

    pool._record_checkout_wait(0.004, timed_out=False)
    pool._record_checkout_wait(0.2, timed_out=True)

    count, wait_sum, buckets, timeouts = pool.taximobile_wait_snapshot()
    assert count == 2
    assert wait_sum == pytest.approx(0.204)
    assert buckets == (0, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2)
    assert timeouts == 1
