package org.example.taximobile.feature.app

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import org.example.taximobile.domain.drivers.DriverAvailabilityStatus
import org.example.taximobile.domain.rides.RideStatus
import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.feature.ui.components.StatusTone
import org.example.taximobile.feature.driver.driverAvailabilityResource
import org.example.taximobile.feature.driver.driverAvailabilityTone
import org.example.taximobile.feature.passenger.passengerStatusTone

class RidePresentationMappingTest {
    @Test
    fun passenger_ride_statuses_have_explicit_semantic_tones() {
        assertEquals(StatusTone.Accent, RideStatus.MATCHING.passengerStatusTone())
        assertEquals(StatusTone.Info, RideStatus.DRIVER_EN_ROUTE.passengerStatusTone())
        assertEquals(StatusTone.Info, RideStatus.IN_PROGRESS.passengerStatusTone())
        assertEquals(StatusTone.Success, RideStatus.COMPLETED.passengerStatusTone())
        assertEquals(StatusTone.Neutral, RideStatus.CANCELLED.passengerStatusTone())
        assertEquals(StatusTone.Info, RideStatus.UNMATCHED.passengerStatusTone())
    }

    @Test
    fun driver_availability_has_text_and_not_color_only() {
        assertEquals(
            DriverAvailabilityStatus.entries.size,
            DriverAvailabilityStatus.entries.map { it.driverAvailabilityResource() }.toSet().size,
        )
        assertEquals(StatusTone.Success, DriverAvailabilityStatus.AVAILABLE.driverAvailabilityTone())
        assertEquals(StatusTone.Warning, DriverAvailabilityStatus.OFFERED_RIDE.driverAvailabilityTone())
        assertEquals(StatusTone.Neutral, DriverAvailabilityStatus.OFFLINE.driverAvailabilityTone())
        assertEquals(StatusTone.Info, DriverAvailabilityStatus.ON_RIDE.driverAvailabilityTone())
    }

    @Test
    fun shared_coordinate_parser_rejects_invalid_or_out_of_range_values() {
        assertEquals(Coordinates(33.5731, -7.5898), validCoordinates("33.5731", "-7.5898"))
        assertNull(validCoordinates("north", "-7.5"))
        assertNull(validCoordinates("91", "0"))
        assertNull(validCoordinates("0", "181"))
    }

    @Test
    fun route_summary_formatting_is_stable_at_boundaries() {
        assertEquals("0.0", formatKilometers(0))
        assertEquals("1.0", formatKilometers(1_000))
        assertEquals(1, formatMinutes(0))
        assertEquals(2, formatMinutes(90))
    }
}
