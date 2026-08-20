package org.example.taximobile.data.drivers

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
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.data.auth.AuthenticationRejectedException
import org.example.taximobile.data.network.ApiRequestException
import org.example.taximobile.domain.drivers.DriverOfferGateway
import org.example.taximobile.domain.drivers.DriverRideOffer
import org.example.taximobile.domain.rides.Coordinates

class KtorDriverOfferGateway(
    private val client: HttpClient,
    private val api: ApiConfiguration,
    private val accessToken: suspend () -> String,
) : DriverOfferGateway {
    override suspend fun currentOffers(): List<DriverRideOffer> = request {
        val response = client.get(api.endpoint("drivers/me/ride-offers")) { authorize() }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not load ride offers.")
        val payload = response.body<OfferListResponse>()
        payload.offers.map {
            DriverRideOffer(
                id = it.id,
                rideId = it.rideId,
                pickup = Coordinates(it.pickup.latitude, it.pickup.longitude),
                estimatedPickupDistanceMeters = it.estimatedPickupDistanceMeters,
                estimatedPickupTimeSeconds = it.estimatedPickupTimeSeconds,
                estimatedFareAmount = it.estimatedFare?.amount,
                estimatedFareCurrency = it.estimatedFare?.currency,
                matchingAlgorithmVersion = it.matchingAlgorithmVersion,
                issuedAt = it.issuedAt,
                expiresAt = it.expiresAt,
                serverTimeAtFetch = payload.serverTime,
            )
        }
    }

    override suspend fun accept(offerId: String) = request {
        client.post(api.endpoint("ride-offers/$offerId/accept")) { authorize() }.throwForFailure()
    }

    override suspend fun decline(offerId: String, reason: String) = request {
        client.post(api.endpoint("ride-offers/$offerId/decline")) {
            authorize()
            contentType(ContentType.Application.Json)
            setBody(OfferDeclineRequest(reason))
        }.throwForFailure()
    }

    private suspend fun io.ktor.client.request.HttpRequestBuilder.authorize() {
        header(HttpHeaders.Authorization, "Bearer ${accessToken()}")
    }

    private fun io.ktor.client.statement.HttpResponse.throwForFailure() {
        if (status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!status.isSuccess()) throw ApiRequestException(status.value, "The server could not complete this offer action.")
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
private data class OfferListResponse(
    @SerialName("server_time") val serverTime: String,
    val offers: List<OfferResponse>,
)

@Serializable
private data class OfferResponse(
    val id: String,
    @SerialName("ride_id") val rideId: String,
    val pickup: CoordinateResponse,
    @SerialName("estimated_pickup_distance_meters") val estimatedPickupDistanceMeters: Int? = null,
    @SerialName("estimated_pickup_time_seconds") val estimatedPickupTimeSeconds: Int? = null,
    @SerialName("estimated_fare") val estimatedFare: OfferFareResponse? = null,
    @SerialName("matching_algorithm_version") val matchingAlgorithmVersion: String? = null,
    @SerialName("issued_at") val issuedAt: String,
    @SerialName("expires_at") val expiresAt: String,
)

@Serializable
private data class CoordinateResponse(val latitude: Double, val longitude: Double)

@Serializable
private data class OfferFareResponse(val amount: String, val currency: String)

@Serializable
private data class OfferDeclineRequest(val reason: String)
