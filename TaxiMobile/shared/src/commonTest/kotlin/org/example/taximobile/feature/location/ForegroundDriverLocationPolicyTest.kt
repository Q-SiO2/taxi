package org.example.taximobile.feature.location

import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue
import org.example.taximobile.domain.drivers.DriverAvailabilityStatus

class ForegroundDriverLocationPolicyTest {
    @Test
    fun sampling_starts_immediately_and_uses_state_specific_intervals() {
        val policy = ForegroundDriverLocationPolicy(
            availableIntervalMillis = 15_000,
            activeRideIntervalMillis = 10_000,
        )

        assertTrue(policy.shouldRequest(1_000, DriverAvailabilityStatus.AVAILABLE, true, true, false, false))
        assertFalse(policy.shouldRequest(15_999, DriverAvailabilityStatus.AVAILABLE, true, true, false, false))
        assertTrue(policy.shouldRequest(16_000, DriverAvailabilityStatus.AVAILABLE, true, true, false, false))

        assertFalse(policy.shouldRequest(25_999, DriverAvailabilityStatus.EN_ROUTE, true, true, false, false))
        assertTrue(policy.shouldRequest(31_000, DriverAvailabilityStatus.EN_ROUTE, true, true, false, false))
        assertFalse(policy.shouldRequest(40_999, DriverAvailabilityStatus.EN_ROUTE, true, true, false, false))
        assertTrue(policy.shouldRequest(41_000, DriverAvailabilityStatus.EN_ROUTE, true, true, false, false))
    }

    @Test
    fun offline_background_disconnected_and_busy_states_never_sample() {
        val policy = ForegroundDriverLocationPolicy()

        assertFalse(policy.shouldRequest(1_000, DriverAvailabilityStatus.OFFLINE, true, true, false, false))
        assertFalse(policy.shouldRequest(1_000, DriverAvailabilityStatus.AVAILABLE, false, true, false, false))
        assertFalse(policy.shouldRequest(1_000, DriverAvailabilityStatus.AVAILABLE, true, false, false, false))
        assertFalse(policy.shouldRequest(1_000, DriverAvailabilityStatus.AVAILABLE, true, true, true, false))
        assertFalse(policy.shouldRequest(1_000, DriverAvailabilityStatus.AVAILABLE, true, true, false, true))
    }

    @Test
    fun foreground_return_rearms_an_immediate_observation() {
        val policy = ForegroundDriverLocationPolicy()

        assertTrue(policy.shouldRequest(1_000, DriverAvailabilityStatus.AVAILABLE, true, true, false, false))
        assertFalse(policy.shouldRequest(2_000, DriverAvailabilityStatus.AVAILABLE, false, true, false, false))
        assertTrue(policy.shouldRequest(2_001, DriverAvailabilityStatus.AVAILABLE, true, true, false, false))
    }

    @Test
    fun unavailable_platform_location_uses_a_bounded_backoff() {
        val policy = ForegroundDriverLocationPolicy(
            availableIntervalMillis = 15_000,
            unavailableBackoffMillis = 60_000,
        )

        assertTrue(policy.shouldRequest(1_000, DriverAvailabilityStatus.AVAILABLE, true, true, false, false))
        policy.recordUnavailable(2_000)
        assertFalse(policy.shouldRequest(61_999, DriverAvailabilityStatus.AVAILABLE, true, true, false, false))
        assertTrue(policy.shouldRequest(62_000, DriverAvailabilityStatus.AVAILABLE, true, true, false, false))
    }
}
