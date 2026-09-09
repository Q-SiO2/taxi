package org.example.taximobile.domain.drivers

import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.domain.rides.FareEconomics
import org.example.taximobile.domain.rides.FixedRouteRideSummary
import org.example.taximobile.domain.rides.RideServiceType

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
    /** Backend-calculated allocation used to make acceptance informed. */
    val economics: FareEconomics? = null,
    val serviceType: RideServiceType = RideServiceType.ON_DEMAND,
    val fixedRoute: FixedRouteRideSummary? = null,
)

/** Driver offers are backend-issued and expire independently of client state. */
interface DriverOfferGateway {
    suspend fun currentOffers(): List<DriverRideOffer>
    suspend fun accept(offerId: String)
    suspend fun decline(offerId: String, reason: String)
}
