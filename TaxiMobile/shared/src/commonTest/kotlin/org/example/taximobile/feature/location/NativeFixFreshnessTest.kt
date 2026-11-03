package org.example.taximobile.feature.location

import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class NativeFixFreshnessTest {
    @Test fun cached_or_same_instant_fix_is_not_a_new_observation() {
        assertFalse(nativeFixAcquiredAfterRequest(10, 9, 11))
        assertFalse(nativeFixAcquiredAfterRequest(10, 10, 11))
    }
    @Test fun a_fix_acquired_after_the_request_is_accepted() {
        assertTrue(nativeFixAcquiredAfterRequest(10, 11, 12))
    }
    @Test fun future_and_invalid_monotonic_facts_are_rejected() {
        assertFalse(nativeFixAcquiredAfterRequest(10, 12, 11))
        assertFalse(nativeFixAcquiredAfterRequest(-1, 0, 1))
        assertFalse(nativeFixAcquiredAfterRequest(0, -1, 1))
    }
    @Test fun delayed_delivery_does_not_make_an_old_fix_fresh() {
        assertTrue(nativeFixAcquiredAfterRequest(0, 1, 30_000_000_001L))
        assertFalse(nativeFixAcquiredAfterRequest(0, 1, 30_000_000_002L))
    }
}
