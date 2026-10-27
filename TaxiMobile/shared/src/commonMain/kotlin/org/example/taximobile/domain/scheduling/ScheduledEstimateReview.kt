package org.example.taximobile.domain.scheduling

import kotlin.time.Instant
import org.example.taximobile.domain.rides.Coordinates

/** Bind displayed review to inputs; the server still decides price and eligibility. */
fun ScheduledBookingEstimate.matchesPointRequest(
    requestedTime: String,
    requestedCityId: String?,
    requestedPickup: Coordinates,
    requestedDestination: Coordinates,
): Boolean = hasKnownContext() && serviceType == "ON_DEMAND" && fixedRouteDirectionVersionId == null &&
    (requestedCityId == null || requestedCityId == cityId) && sameInstant(requestedTime, scheduledFor) &&
    samePoint(requestedPickup, pickup) && samePoint(requestedDestination, destination)

fun ScheduledBookingEstimate.matchesFixedRouteRequest(requestedTime: String, directionVersionId: String): Boolean =
    hasKnownContext() && serviceType == "FIXED_ROUTE" && directionVersionId.isNotBlank() &&
        fixedRouteDirectionVersionId == directionVersionId && sameInstant(requestedTime, scheduledFor) &&
        pickup.isValidPoint() && destination.isValidPoint()

private fun ScheduledBookingEstimate.hasKnownContext(): Boolean =
    cityId.isNotBlank() && operatorId.isNotBlank() && paymentMethod == "CASH"

private fun sameInstant(requested: String, returned: String): Boolean = try {
    Instant.parse(requested) == Instant.parse(returned)
} catch (_: IllegalArgumentException) {
    false
}

// Address labels can be normalized by the server; coordinate identity cannot.
private fun samePoint(requested: Coordinates, returned: Coordinates): Boolean =
    requested.isValidPoint() && returned.isValidPoint() &&
        requested.latitude == returned.latitude && requested.longitude == returned.longitude

private fun Coordinates.isValidPoint(): Boolean =
    latitude.isFinite() && longitude.isFinite() && latitude in -90.0..90.0 && longitude in -180.0..180.0
