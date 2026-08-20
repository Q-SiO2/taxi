package org.example.taximobile.feature.passenger

import kotlin.test.Test
import kotlin.test.assertEquals
import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.domain.rides.RideStatus
import org.example.taximobile.domain.rides.RideSummary

class RecentDestinationsTest {
    @Test
    fun `completed destinations retain history order and duplicate coordinates are removed`() {
        val station = Coordinates(33.5890, -7.5910, "Casa Voyageurs")
        val market = Coordinates(33.5730, -7.6150, "Central Market")
        val rides = listOf(
            RideSummary("newest", RideStatus.COMPLETED, destination = station),
            RideSummary("cancelled", RideStatus.CANCELLED, destination = market),
            RideSummary("duplicate", RideStatus.COMPLETED, destination = station.copy(address = "Station")),
            RideSummary("older", RideStatus.COMPLETED, destination = market),
        )

        assertEquals(listOf(station, market), recentPassengerDestinations(rides))
    }

    @Test
    fun `suggestions are bounded and a nonpositive limit is empty`() {
        val rides = (1..5).map {
            RideSummary("ride-$it", RideStatus.COMPLETED, destination = Coordinates(it.toDouble(), -7.0))
        }

        assertEquals(3, recentPassengerDestinations(rides).size)
        assertEquals(emptyList(), recentPassengerDestinations(rides, limit = 0))
    }
}
