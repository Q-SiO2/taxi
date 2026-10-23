package org.example.taximobile.domain.drivers

import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue
import org.example.taximobile.domain.rides.Coordinates

class DriverLocationObservationTest {
    private val point = Coordinates(33.5731, -7.5898)
    private val now = 1_728_000_000_000L

    @Test
    fun recent_precise_native_fix_is_usable() {
        assertTrue(DriverLocationObservation(point, now - 8_000, 12.0).isUsableAt(now))
    }

    @Test
    fun stale_delayed_and_future_fixes_are_rejected() {
        assertFalse(DriverLocationObservation(point, now - 120_000, 8.0).isUsableAt(now))
        assertFalse(DriverLocationObservation(point, now - 31_000, 8.0).isUsableAt(now))
        assertFalse(DriverLocationObservation(point, now + 6_000, 8.0).isUsableAt(now))
    }

    @Test
    fun invalid_coordinates_and_accuracy_are_rejected() {
        assertFalse(DriverLocationObservation(Coordinates(Double.NaN, 0.0), now, 8.0).isUsableAt(now))
        assertFalse(DriverLocationObservation(Coordinates(91.0, 0.0), now, 8.0).isUsableAt(now))
        assertFalse(DriverLocationObservation(point, now, Double.NaN).isUsableAt(now))
        assertFalse(DriverLocationObservation(point, now, -1.0).isUsableAt(now))
        assertFalse(DriverLocationObservation(point, now, 101.0).isUsableAt(now))
    }
}
