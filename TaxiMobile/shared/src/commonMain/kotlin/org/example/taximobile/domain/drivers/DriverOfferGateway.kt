package org.example.taximobile.domain.drivers

import org.example.taximobile.domain.rides.Coordinates

data class DriverRideOffer(
    val id: String,
    val rideId: String,
    val pickup: Coordinates,
    val estimatedPickupDistanceMeters: Int? = null,
    val estimatedPickupTimeSeconds: Int? = null,
    val estimatedFareAmount: String? = null,
    val estimatedFareCurrency: String? = null,
    val matchingAlgorithmVersion: String? = null,
    val issuedAt: String,
    val expiresAt: String,
    val serverTimeAtFetch: String,
)

/** Driver offers are backend-issued and expire independently of client state. */
interface DriverOfferGateway {
    suspend fun currentOffers(): List<DriverRideOffer>
    suspend fun accept(offerId: String)
    suspend fun decline(offerId: String, reason: String)
}
