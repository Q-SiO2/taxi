package org.example.taximobile.feature.maps

import org.example.taximobile.domain.rides.Coordinates

internal val DefaultTaxiMobileMapCenter = Coordinates(33.5731, -7.5898)

/** Provider-neutral camera input shared by the Android and iOS MapLibre views. */
internal data class MapCameraBounds(
    val west: Double,
    val south: Double,
    val east: Double,
    val north: Double,
)

/**
 * Prefer the backend route when it is available so the entire guided journey
 * remains visible. Before routing, focus the selected endpoints instead.
 */
internal fun mapCameraFocusPoints(
    pickup: Coordinates?,
    destination: Coordinates?,
    driverLocation: Coordinates?,
    routeGeometry: List<Coordinates>,
): List<Coordinates> {
    val journey = if (routeGeometry.size >= 2) routeGeometry else listOfNotNull(pickup, destination)
    val points = (journey + listOfNotNull(driverLocation)).distinct()
    return points.ifEmpty { listOf(DefaultTaxiMobileMapCenter) }
}

internal fun mapCameraBounds(points: List<Coordinates>): MapCameraBounds? {
    if (points.size < 2) return null
    return MapCameraBounds(
        west = points.minOf(Coordinates::longitude),
        south = points.minOf(Coordinates::latitude),
        east = points.maxOf(Coordinates::longitude),
        north = points.maxOf(Coordinates::latitude),
    )
}
