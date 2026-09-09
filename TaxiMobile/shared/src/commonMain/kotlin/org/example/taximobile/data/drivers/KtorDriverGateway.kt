package org.example.taximobile.data.drivers

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.request.delete
import io.ktor.client.request.header
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.HttpHeaders
import io.ktor.http.HttpStatusCode
import io.ktor.http.ContentType
import io.ktor.http.contentType
import io.ktor.http.isSuccess
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import org.example.taximobile.core.network.ApiConfiguration
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.data.auth.AuthenticationRejectedException
import org.example.taximobile.data.network.ApiRequestException
import org.example.taximobile.domain.drivers.DriverAvailabilityStatus
import org.example.taximobile.domain.drivers.DriverAvailability
import org.example.taximobile.domain.drivers.DriverApplication
import org.example.taximobile.domain.drivers.DriverCredential
import org.example.taximobile.domain.drivers.DriverGateway
import org.example.taximobile.domain.drivers.DriverVehicle
import org.example.taximobile.domain.drivers.VehicleRegistration
import org.example.taximobile.domain.rides.Coordinates

class KtorDriverGateway(
    private val client: HttpClient,
    private val api: ApiConfiguration,
    private val accessToken: suspend () -> String,
) : DriverGateway {
    override suspend fun apply(displayName: String): DriverApplication = request {
        val response = client.post(api.endpoint("drivers/apply")) {
            authorize()
            contentType(ContentType.Application.Json)
            setBody(DriverApplicationRequest(displayName))
        }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not submit the driver application.")
        response.body<DriverProfileResponse>().toApplication()
    }

    override suspend fun profile(): DriverApplication = request {
        val response = client.get(api.endpoint("drivers/me")) { authorize() }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not load your driver profile.")
        response.body<DriverProfileResponse>().toApplication()
    }

    override suspend fun verificationStatus(): String = request {
        val response = client.get(api.endpoint("drivers/me/verification")) { authorize() }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not load verification status.")
        response.body<VerificationResponse>().status
    }

    override suspend fun submitVerification(): String = request {
        val response = client.post(api.endpoint("drivers/me/verification")) { authorize() }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not submit verification.")
        response.body<VerificationResponse>().status
    }

    override suspend fun currentAvailability(): DriverAvailability = request {
        client.get(api.endpoint("drivers/me/availability")) { authorize() }.availabilityOrThrow()
    }

    override suspend fun goOnline(cityId: String?, serviceType: String): DriverAvailability = request {
        client.post(api.endpoint("drivers/me/availability/online")) {
            authorize()
            contentType(ContentType.Application.Json)
            setBody(OnlineAvailabilityRequest(cityId, serviceType))
        }.availabilityOrThrow()
    }

    override suspend fun goOffline(): DriverAvailability = request {
        client.post(api.endpoint("drivers/me/availability/offline")) { authorize() }.availabilityOrThrow()
    }

    override suspend fun credentials(): List<DriverCredential> = request {
        val response = client.get(api.endpoint("drivers/me/credentials")) { authorize() }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not load credentials.")
        response.body<DriverCredentialListResponse>().credentials.map { it.toDomain() }
    }

    override suspend fun vehicles(): List<DriverVehicle> = request {
        val response = client.get(api.endpoint("drivers/me/vehicles")) { authorize() }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not load vehicles.")
        response.body<VehicleListResponse>().vehicles.map { it.toDomain() }
    }

    override suspend fun registerVehicle(vehicle: VehicleRegistration): DriverVehicle = request {
        val response = client.post(api.endpoint("drivers/me/vehicles")) {
            authorize()
            contentType(ContentType.Application.Json)
            setBody(
                VehicleCreateRequest(
                    vehicle.make,
                    vehicle.model,
                    vehicle.year,
                    vehicle.color,
                    vehicle.registrationNumber,
                    vehicle.taxiIdentifier,
                    vehicle.passengerCapacity,
                ),
            )
        }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not register this vehicle.")
        response.body<VehicleResponse>().toDomain()
    }

    override suspend fun selectActiveVehicle(vehicleId: String): DriverAvailability = request {
        val response = client.post(api.endpoint("drivers/me/active-vehicle")) {
            authorize()
            contentType(ContentType.Application.Json)
            setBody(ActiveVehicleRequest(vehicleId))
        }
        response.availabilityOrThrow()
    }

    override suspend fun deactivateVehicle(vehicleId: String): DriverVehicle = request {
        val response = client.delete(api.endpoint("drivers/me/vehicles/$vehicleId")) { authorize() }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not deactivate this vehicle.")
        response.body<VehicleResponse>().toDomain()
    }

    override suspend fun updateLocation(location: Coordinates, observedAt: String) = request {
        val response = client.post(api.endpoint("drivers/me/location")) {
            authorize()
            contentType(ContentType.Application.Json)
            setBody(LocationUpdateRequest(location.latitude, location.longitude, observedAt))
        }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not update driver location.")
    }

    private suspend fun io.ktor.client.request.HttpRequestBuilder.authorize() {
        header(HttpHeaders.Authorization, "Bearer ${accessToken()}")
    }

    private suspend fun io.ktor.client.statement.HttpResponse.availabilityOrThrow(): DriverAvailability {
        if (status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!status.isSuccess()) throw ApiRequestException(status.value, "The server could not change availability.")
        return body<AvailabilityResponse>().let {
            DriverAvailability(
                status = DriverAvailabilityStatus.valueOf(it.status),
                activeVehicleId = it.vehicleId,
                cityId = it.cityId,
                serviceType = it.serviceType,
            )
        }
    }

    private suspend fun <T> request(block: suspend () -> T): T = try {
        block()
    } catch (error: AuthenticationRejectedException) {
        throw error
    } catch (error: ApiRequestException) {
        throw error
    } catch (error: Exception) {
        throw AuthenticationNetworkException()
    }
}

@Serializable
private data class AvailabilityResponse(
    val status: String,
    @SerialName("vehicle_id") val vehicleId: String? = null,
    @SerialName("city_id") val cityId: String? = null,
    @SerialName("service_type") val serviceType: String? = null,
)

@Serializable
private data class OnlineAvailabilityRequest(
    @SerialName("city_id") val cityId: String? = null,
    @SerialName("service_type") val serviceType: String,
)

@Serializable
private data class DriverApplicationRequest(@SerialName("display_name") val displayName: String)

@Serializable
private data class DriverProfileResponse(
    @SerialName("display_name") val displayName: String,
    @SerialName("verification_status") val verificationStatus: String,
    @SerialName("account_status") val accountStatus: String,
) {
    fun toApplication() = DriverApplication(displayName, verificationStatus, accountStatus)
}

@Serializable
private data class VerificationResponse(val status: String)

@Serializable
internal data class DriverCredentialListResponse(val credentials: List<DriverCredentialResponse>)

@Serializable
internal data class DriverCredentialResponse(
    val id: String,
    val type: String,
    val status: String,
    @SerialName("issued_at") val issuedAt: String? = null,
    @SerialName("expires_at") val expiresAt: String? = null,
) {
    fun toDomain() = DriverCredential(id, type, status, issuedAt, expiresAt)
}

@Serializable
private data class LocationUpdateRequest(
    val latitude: Double,
    val longitude: Double,
    @SerialName("observed_at") val observedAt: String,
)

@Serializable
private data class VehicleListResponse(val vehicles: List<VehicleResponse>)

@Serializable
private data class VehicleResponse(
    val id: String,
    val make: String,
    val model: String,
    val color: String,
    val status: String,
    @SerialName("verification_status") val verificationStatus: String,
) {
    fun toDomain() = DriverVehicle(id, make, model, color, status, verificationStatus)
}

@Serializable
private data class VehicleCreateRequest(
    val make: String,
    val model: String,
    val year: Int,
    val color: String,
    @SerialName("registration_number") val registrationNumber: String,
    @SerialName("taxi_identifier") val taxiIdentifier: String? = null,
    @SerialName("passenger_capacity") val passengerCapacity: Int? = null,
)

@Serializable
private data class ActiveVehicleRequest(@SerialName("vehicle_id") val vehicleId: String)
