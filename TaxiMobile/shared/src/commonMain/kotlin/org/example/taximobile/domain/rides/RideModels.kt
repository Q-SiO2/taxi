package org.example.taximobile.domain.rides

enum class RideStatus {
    REQUESTED,
    MATCHING,
    ACCEPTED,
    DRIVER_EN_ROUTE,
    DRIVER_ARRIVED,
    IN_PROGRESS,
    COMPLETED,
    CANCELLED,
    UNMATCHED,
}

data class RideSummary(
    val id: String,
    val status: RideStatus,
    val completedAt: String? = null,
    val driver: AssignedDriver? = null,
    val lastKnownDriverLocation: LastKnownDriverLocation? = null,
    val pickup: Coordinates? = null,
    val destination: Coordinates? = null,
)

data class AssignedDriver(val displayName: String, val vehicle: AssignedVehicle)

data class AssignedVehicle(val make: String, val model: String, val color: String, val taxiIdentifier: String?)

/** A single backend-authorized active-ride observation; never presented as a live stream. */
data class LastKnownDriverLocation(
    val coordinates: Coordinates,
    val observedAt: String,
    val accuracyMeters: Double? = null,
)

data class FareEstimate(
    val amount: String,
    val currency: String,
    val pricingRuleVersion: String,
)

data class FareComponent(val code: String, val label: String, val amount: String)

data class FinalRideFare(
    val amount: String,
    val currency: String,
    val pricingRuleVersion: String? = null,
    val components: List<FareComponent> = emptyList(),
)

/** A passenger-facing read of backend-finalized fare and payment facts. */
data class RideReceipt(
    val rideId: String,
    val completedAt: String,
    val fare: FinalRideFare,
    val paymentMethod: String,
    val paymentStatus: String,
)

/** Feedback returned by the backend for a ride participant; no user IDs are exposed. */
data class RideRating(
    val id: String,
    val score: Int,
    val comment: String?,
)

/** The client renders backend-confirmed state; it does not transition rides locally. */
interface RideGateway {
    suspend fun estimateRide(pickup: Coordinates, destination: Coordinates): FareEstimate
    suspend fun listRides(): List<RideSummary>
    suspend fun currentRide(id: String): RideSummary
    suspend fun finalFare(id: String): FinalRideFare
    suspend fun receipt(id: String): RideReceipt
    suspend fun requestRide(pickup: Coordinates, destination: Coordinates): RideSummary
    suspend fun cancelRide(id: String, reason: String): RideSummary
    suspend fun ratings(id: String): List<RideRating>
    suspend fun submitRating(id: String, score: Int, comment: String?): RideRating
}

data class Coordinates(
    val latitude: Double,
    val longitude: Double,
    /** Optional backend-returned display text; coordinates remain authoritative. */
    val address: String? = null,
)
