package org.example.taximobile.domain.drivers

import org.example.taximobile.domain.rides.Coordinates

enum class DriverAvailabilityStatus {
    OFFLINE,
    AVAILABLE,
    PAUSED,
    OFFERED_RIDE,
    EN_ROUTE,
    AT_PICKUP,
    ON_RIDE,
}

data class DriverApplication(
    val displayName: String,
    val verificationStatus: String,
    val accountStatus: String,
)

data class DriverAvailability(val status: DriverAvailabilityStatus, val activeVehicleId: String?)

data class DriverVehicle(
    val id: String,
    val make: String,
    val model: String,
    val color: String,
    val status: String,
    val verificationStatus: String,
)

/** Privacy-minimized, backend-reviewed professional credential metadata. */
data class DriverCredential(
    val id: String,
    val type: String,
    val status: String,
    val issuedAt: String? = null,
    val expiresAt: String? = null,
)

data class VehicleRegistration(
    val make: String,
    val model: String,
    val year: Int,
    val color: String,
    val registrationNumber: String,
)

/** Commands return the server-confirmed availability, never an optimistic local state. */
interface DriverGateway {
    suspend fun apply(displayName: String): DriverApplication
    suspend fun profile(): DriverApplication
    suspend fun verificationStatus(): String
    suspend fun submitVerification(): String
    suspend fun currentAvailability(): DriverAvailability
    suspend fun goOnline(): DriverAvailability
    suspend fun goOffline(): DriverAvailability
    suspend fun credentials(): List<DriverCredential>
    suspend fun vehicles(): List<DriverVehicle>
    suspend fun registerVehicle(vehicle: VehicleRegistration): DriverVehicle
    suspend fun selectActiveVehicle(vehicleId: String): DriverAvailability
    suspend fun deactivateVehicle(vehicleId: String): DriverVehicle
    suspend fun updateLocation(location: Coordinates, observedAt: String)
}
