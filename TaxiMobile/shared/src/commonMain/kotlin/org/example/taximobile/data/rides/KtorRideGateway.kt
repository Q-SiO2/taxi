package org.example.taximobile.data.rides

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.request.header
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.HttpHeaders
import io.ktor.http.HttpStatusCode
import io.ktor.http.contentType
import io.ktor.http.isSuccess
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import org.example.taximobile.core.network.ApiConfiguration
import org.example.taximobile.data.auth.AuthenticationRejectedException
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.data.network.ApiRequestException
import org.example.taximobile.data.network.newIdempotencyKey
import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.domain.rides.AssignedDriver
import org.example.taximobile.domain.rides.AssignedVehicle
import org.example.taximobile.domain.rides.FareEstimate
import org.example.taximobile.domain.rides.FareComponent
import org.example.taximobile.domain.rides.FinalRideFare
import org.example.taximobile.domain.rides.LastKnownDriverLocation
import org.example.taximobile.domain.rides.RideGateway
import org.example.taximobile.domain.rides.RideRating
import org.example.taximobile.domain.rides.RideReceipt
import org.example.taximobile.domain.rides.RideStatus
import org.example.taximobile.domain.rides.RideSummary

class KtorRideGateway(
    private val client: HttpClient,
    private val api: ApiConfiguration,
    private val accessToken: suspend () -> String,
) : RideGateway {
    override suspend fun estimateRide(pickup: Coordinates, destination: Coordinates): FareEstimate = request {
        val response = client.post(api.endpoint("rides/estimate")) {
            authorize()
            contentType(ContentType.Application.Json)
            setBody(
                RideEstimateRequest(
                    pickup = pickup.toRequest(),
                    destination = destination.toRequest(),
                )
            )
        }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) {
            throw ApiRequestException(response.status.value, "The server could not estimate this ride.")
        }
        val estimate = response.body<RideEstimateResponse>().estimate
        FareEstimate(estimate.amount, estimate.currency, estimate.pricingRuleVersion)
    }

    override suspend fun currentRide(id: String): RideSummary = request {
        val response = client.get(api.endpoint("rides/$id")) { authorize() }
        response.rideOrThrow()
    }

    override suspend fun finalFare(id: String): FinalRideFare = request {
        val response = client.get(api.endpoint("rides/$id/fare")) { authorize() }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not load this receipt.")
        response.body<FareResponse>().toFinalFare()
    }

    override suspend fun receipt(id: String): RideReceipt = request {
        val response = client.get(api.endpoint("rides/$id/receipt")) { authorize() }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not load this receipt.")
        response.body<RideReceiptResponse>().let {
            RideReceipt(it.rideId, it.completedAt, it.fare.toFinalFare(), it.payment.method, it.payment.status)
        }
    }

    override suspend fun listRides(): List<RideSummary> = request {
        val response = client.get(api.endpoint("rides")) { authorize() }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not load rides.")
        response.body<RideListResponse>().items.map { it.toSummary() }
    }

    override suspend fun requestRide(pickup: Coordinates, destination: Coordinates): RideSummary {
        val idempotencyKey = newIdempotencyKey()
        return idempotentRequest {
            val response = client.post(api.endpoint("rides")) {
                authorize()
                header("Idempotency-Key", idempotencyKey)
                contentType(ContentType.Application.Json)
                setBody(RideRequest(pickup.toRequest(), destination.toRequest()))
            }
            response.rideOrThrow()
        }
    }

    override suspend fun cancelRide(id: String, reason: String): RideSummary {
        val idempotencyKey = newIdempotencyKey()
        return idempotentRequest {
            val response = client.post(api.endpoint("rides/$id/cancel")) {
                authorize()
                header("Idempotency-Key", idempotencyKey)
                contentType(ContentType.Application.Json)
                setBody(CancellationRequest(reason))
            }
            response.rideOrThrow()
        }
    }

    override suspend fun ratings(id: String): List<RideRating> = request {
        val response = client.get(api.endpoint("rides/$id/ratings")) { authorize() }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not load ride feedback.")
        response.body<RideRatingListResponse>().items.map { RideRating(it.id, it.score, it.comment) }
    }

    override suspend fun submitRating(id: String, score: Int, comment: String?): RideRating = request {
        val response = client.post(api.endpoint("rides/$id/rating")) {
            authorize()
            contentType(ContentType.Application.Json)
            setBody(RideRatingRequest(score, comment))
        }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not submit your feedback.")
        response.body<RideRatingResponse>().let { RideRating(it.id, it.score, it.comment) }
    }

    private suspend fun io.ktor.client.request.HttpRequestBuilder.authorize() {
        header(HttpHeaders.Authorization, "Bearer ${accessToken()}")
    }

    private suspend fun io.ktor.client.statement.HttpResponse.rideOrThrow(): RideSummary {
        if (status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!status.isSuccess()) throw ApiRequestException(status.value, "The server could not complete this ride request.")
        val ride = body<RideResponse>()
        return ride.toSummary()
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

    private suspend fun <T> idempotentRequest(block: suspend () -> T): T = try {
        block()
    } catch (error: AuthenticationRejectedException) {
        throw error
    } catch (error: ApiRequestException) {
        throw error
    } catch (_: Exception) {
        try {
            block()
        } catch (retryError: AuthenticationRejectedException) {
            throw retryError
        } catch (retryError: ApiRequestException) {
            throw retryError
        } catch (_: Exception) {
            throw AuthenticationNetworkException()
        }
    }
}

@Serializable
private data class CoordinateRequest(val latitude: Double, val longitude: Double, val address: String? = null)

private fun Coordinates.toRequest() = CoordinateRequest(latitude, longitude, address?.trim()?.takeIf(String::isNotEmpty))

@Serializable
private data class RideRequest(val pickup: CoordinateRequest, val destination: CoordinateRequest)

@Serializable
private data class RideEstimateRequest(val pickup: CoordinateRequest, val destination: CoordinateRequest)

@Serializable
private data class CancellationRequest(val reason: String)

@Serializable
private data class RideRatingRequest(val score: Int, val comment: String? = null)

@Serializable
private data class RideResponse(
    val id: String,
    val status: String,
    @SerialName("completed_at") val completedAt: String? = null,
    val pickup: CoordinateResponse,
    val destination: CoordinateResponse,
    val driver: AssignedDriverResponse? = null,
    @SerialName("last_known_driver_location")
    val lastKnownDriverLocation: LastKnownDriverLocationResponse? = null,
) {
    fun toSummary() = RideSummary(
        id = id,
        status = RideStatus.valueOf(status),
        completedAt = completedAt,
        driver = driver?.let {
            AssignedDriver(it.displayName, AssignedVehicle(it.vehicle.make, it.vehicle.model, it.vehicle.color, it.vehicle.taxiIdentifier))
        },
        lastKnownDriverLocation = lastKnownDriverLocation?.toDomain(),
        pickup = pickup.toDomain(),
        destination = destination.toDomain(),
    )
}

@Serializable
internal data class RideListResponse(val items: List<RideListItemResponse>)

@Serializable
internal data class RideListItemResponse(
    val id: String,
    val status: String,
    @SerialName("completed_at") val completedAt: String? = null,
    val driver: AssignedDriverResponse? = null,
    val pickup: CoordinateResponse,
    val destination: CoordinateResponse,
) {
    fun toSummary() = RideSummary(
        id = id,
        status = RideStatus.valueOf(status),
        completedAt = completedAt,
        driver = driver?.let {
            AssignedDriver(it.displayName, AssignedVehicle(it.vehicle.make, it.vehicle.model, it.vehicle.color, it.vehicle.taxiIdentifier))
        },
        pickup = pickup.toDomain(),
        destination = destination.toDomain(),
    )
}

@Serializable
internal data class AssignedDriverResponse(
    @SerialName("display_name") val displayName: String,
    val vehicle: AssignedVehicleResponse,
)

@Serializable
internal data class AssignedVehicleResponse(
    val make: String,
    val model: String,
    val color: String,
    @SerialName("taxi_identifier") val taxiIdentifier: String? = null,
)

@Serializable
private data class LastKnownDriverLocationResponse(
    val latitude: Double,
    val longitude: Double,
    @SerialName("observed_at") val observedAt: String,
    @SerialName("accuracy_meters") val accuracyMeters: Double? = null,
) {
    fun toDomain() = LastKnownDriverLocation(
        coordinates = Coordinates(latitude, longitude),
        observedAt = observedAt,
        accuracyMeters = accuracyMeters,
    )
}

@Serializable
private data class RideEstimateResponse(val estimate: FareEstimateResponse)

@Serializable
private data class FareEstimateResponse(
    val amount: String,
    val currency: String,
    @SerialName("pricing_rule_version") val pricingRuleVersion: String,
)

@Serializable
private data class FareResponse(
    val amount: String,
    val currency: String,
    @SerialName("pricing_rule_version") val pricingRuleVersion: String? = null,
    val components: List<FareComponentResponse> = emptyList(),
) {
    fun toFinalFare() = FinalRideFare(
        amount = amount,
        currency = currency,
        pricingRuleVersion = pricingRuleVersion,
        components = components.map { FareComponent(it.code, it.label, it.amount) },
    )
}

@Serializable
private data class FareComponentResponse(val code: String, val label: String, val amount: String)

@Serializable
private data class RideReceiptResponse(
    @SerialName("ride_id") val rideId: String,
    @SerialName("completed_at") val completedAt: String,
    val fare: FareResponse,
    val payment: PaymentReceiptResponse,
)

@Serializable
private data class PaymentReceiptResponse(val method: String, val status: String)

@Serializable
private data class RideRatingListResponse(val items: List<RideRatingResponse>)

@Serializable
private data class RideRatingResponse(
    val id: String,
    val score: Int,
    val comment: String? = null,
)

@Serializable
internal data class CoordinateResponse(
    val latitude: Double,
    val longitude: Double,
    val address: String? = null,
) {
    fun toDomain() = Coordinates(latitude, longitude, address?.trim()?.takeIf(String::isNotEmpty))
}
