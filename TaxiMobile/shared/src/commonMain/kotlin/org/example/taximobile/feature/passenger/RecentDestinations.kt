package org.example.taximobile.feature.passenger

import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.domain.rides.RideStatus
import org.example.taximobile.domain.rides.RideSummary

/**
 * Derives bounded suggestions from the backend-authorized history already held
 * in memory. Failed/cancelled requests are excluded, and no separate client
 * location history is created.
 */
internal fun recentPassengerDestinations(
    rides: List<RideSummary>,
    limit: Int = 3,
): List<Coordinates> = rides.asSequence()
    .filter { it.status == RideStatus.COMPLETED }
    .mapNotNull(RideSummary::destination)
    .distinctBy { it.latitude to it.longitude }
    .take(limit.coerceAtLeast(0))
    .toList()
