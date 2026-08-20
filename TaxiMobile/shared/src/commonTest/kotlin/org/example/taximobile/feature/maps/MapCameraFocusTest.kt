package org.example.taximobile.feature.maps

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import org.example.taximobile.domain.rides.Coordinates

class MapCameraFocusTest {
    private val pickup = Coordinates(33.5731, -7.5898)
    private val destination = Coordinates(33.5899, -7.6039)

    @Test
    fun `selected endpoints are focused before a route exists`() {
        assertEquals(
            listOf(pickup, destination),
            mapCameraFocusPoints(pickup, destination, null, emptyList()),
        )
    }

    @Test
    fun `empty state focuses the documented default context area`() {
        assertEquals(
            listOf(DefaultTaxiMobileMapCenter),
            mapCameraFocusPoints(null, null, null, emptyList()),
        )
    }

    @Test
    fun `backend route geometry defines the focus when available`() {
        val route = listOf(
            pickup,
            Coordinates(33.5800, -7.6100),
            destination,
        )
        assertEquals(route, mapCameraFocusPoints(null, null, null, route))
    }

    @Test
    fun `last known driver position is included without replacing route geometry`() {
        val driverLocation = Coordinates(33.5700, -7.6200)
        val route = listOf(pickup, destination)

        assertEquals(
            route + driverLocation,
            mapCameraFocusPoints(pickup, destination, driverLocation, route),
        )
    }

    @Test
    fun `bounds use coordinate extrema regardless of route order`() {
        assertEquals(
            MapCameraBounds(west = -7.6100, south = 33.5731, east = -7.5898, north = 33.5899),
            mapCameraBounds(listOf(destination, pickup, Coordinates(33.5800, -7.6100))),
        )
    }

    @Test
    fun `one focus point does not invent a bounding area`() {
        assertNull(mapCameraBounds(listOf(pickup)))
    }
}
