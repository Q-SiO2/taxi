package org.example.taximobile.domain.drivers

import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.domain.rides.RideStatus

data class DriverRideSummary(val id: String, val status: RideStatus, val completedAt: String? = null)

/** Amounts are rendered exactly as supplied by the authoritative accounting API. */
data class DriverEarnings(
    val currency: String,
    val gross: String,
    val fees: String,
    val adjustments: String,
    val net: String,
    val settledThrough: String? = null,
    val count: Int = 0,
    val items: List<DriverEarningItem> = emptyList(),
)

data class DriverEarningItem(
    val id: String,
    val rideId: String,
    val gross: String,
    val fees: String,
    val adjustments: String,
    val net: String,
    val currency: String,
    val settledAt: String,
)

enum class DriverRideAction { EN_ROUTE, ARRIVED, START }

interface DriverRideGateway {
    suspend fun rides(): List<DriverRideSummary>
    suspend fun earnings(): DriverEarnings
    suspend fun markEnRoute(rideId: String): DriverRideSummary
    suspend fun markArrived(rideId: String): DriverRideSummary
    suspend fun start(rideId: String): DriverRideSummary
    suspend fun cancel(rideId: String, reason: String): DriverRideSummary
    suspend fun complete(rideId: String, location: Coordinates): DriverRideSummary
    suspend fun settleCash(rideId: String)
}
