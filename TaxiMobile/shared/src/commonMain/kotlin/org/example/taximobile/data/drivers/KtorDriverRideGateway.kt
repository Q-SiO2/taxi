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
import kotlinx.serialization.json.JsonPrimitive
import org.example.taximobile.core.network.ApiConfiguration
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.data.auth.AuthenticationRejectedException
import org.example.taximobile.data.network.ApiRequestException
import org.example.taximobile.data.network.newIdempotencyKey
import org.example.taximobile.domain.drivers.DriverRideGateway
import org.example.taximobile.domain.drivers.DriverEarningItem
import org.example.taximobile.domain.drivers.DriverEarnings
import org.example.taximobile.domain.drivers.DriverRideSummary
import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.domain.rides.RideStatus

class KtorDriverRideGateway(
    private val client: HttpClient,
    private val api: ApiConfiguration,
    private val accessToken: suspend () -> String,
) : DriverRideGateway {
    override suspend fun rides(): List<DriverRideSummary> = request {
        val response = client.get(api.endpoint("drivers/me/rides")) { authorize() }
        response.driverRideListOrThrow()
    }

    override suspend fun earnings(): DriverEarnings = request {
        val response = client.get(api.endpoint("drivers/me/earnings")) { authorize() }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not load driver earnings.")
        response.body<DriverEarningsResponse>().let {
            DriverEarnings(
                currency = it.currency,
                gross = it.gross.content,
                fees = it.fees.content,
                adjustments = it.adjustments.content,
                net = it.net.content,
                settledThrough = it.settledThrough,
                count = it.count,
                items = it.items.map { item -> item.toDomain() },
            )
        }
    }

    override suspend fun markEnRoute(rideId: String): DriverRideSummary = transition(rideId, "en-route")
    override suspend fun markArrived(rideId: String): DriverRideSummary = transition(rideId, "arrived")
    override suspend fun start(rideId: String): DriverRideSummary = transition(rideId, "start")

    override suspend fun cancel(rideId: String, reason: String): DriverRideSummary {
        val idempotencyKey = newIdempotencyKey()
        return idempotentRequest {
            val response = client.post(api.endpoint("rides/$rideId/driver-cancel")) {
                authorize()
                header("Idempotency-Key", idempotencyKey)
                contentType(ContentType.Application.Json)
                setBody(CancellationRequest(reason))
            }
            if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
            if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not cancel this ride.")
            response.body<DriverRideResponse>().let { DriverRideSummary(it.id, RideStatus.valueOf(it.status), it.completedAt) }
        }
    }

    override suspend fun complete(rideId: String, location: Coordinates): DriverRideSummary {
        val idempotencyKey = newIdempotencyKey()
        return idempotentRequest {
            val response = client.post(api.endpoint("rides/$rideId/complete")) {
                authorize()
                header("Idempotency-Key", idempotencyKey)
                contentType(ContentType.Application.Json)
                setBody(CompletionRequest(location.latitude, location.longitude))
            }
            if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
            if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not complete this ride.")
            val completed = response.body<CompletionResponse>()
            DriverRideSummary(completed.rideId, RideStatus.valueOf(completed.status))
        }
    }

    override suspend fun settleCash(rideId: String) {
        val idempotencyKey = newIdempotencyKey()
        idempotentRequest {
            client.post(api.endpoint("rides/$rideId/payments/cash/settle")) {
                authorize()
                header("Idempotency-Key", idempotencyKey)
            }.throwForFailure()
        }
    }

    private suspend fun transition(rideId: String, action: String): DriverRideSummary = request {
        val response = client.post(api.endpoint("rides/$rideId/$action")) { authorize() }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not update this ride.")
        val ride = response.body<TransitionResponse>()
        DriverRideSummary(ride.rideId, RideStatus.valueOf(ride.status))
    }

    private suspend fun io.ktor.client.request.HttpRequestBuilder.authorize() {
        header(HttpHeaders.Authorization, "Bearer ${accessToken()}")
    }

    private fun io.ktor.client.statement.HttpResponse.throwForFailure() {
        if (status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!status.isSuccess()) throw ApiRequestException(status.value, "The server could not settle this payment.")
    }

    private suspend fun io.ktor.client.statement.HttpResponse.driverRideListOrThrow(): List<DriverRideSummary> {
        if (status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!status.isSuccess()) throw ApiRequestException(status.value, "The server could not load driver rides.")
        return body<DriverRideListResponse>().items.map { DriverRideSummary(it.id, RideStatus.valueOf(it.status), it.completedAt) }
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
private data class DriverRideListResponse(val items: List<DriverRideResponse>)

@Serializable
private data class DriverRideResponse(
    val id: String,
    val status: String,
    @SerialName("completed_at") val completedAt: String? = null,
)

@Serializable
internal data class DriverEarningsResponse(
    val currency: String,
    val gross: JsonPrimitive,
    val fees: JsonPrimitive,
    val adjustments: JsonPrimitive,
    val net: JsonPrimitive,
    @SerialName("settled_through") val settledThrough: String? = null,
    val count: Int = 0,
    val items: List<DriverEarningItemResponse> = emptyList(),
)

@Serializable
internal data class DriverEarningItemResponse(
    val id: String,
    @SerialName("ride_id") val rideId: String,
    val gross: JsonPrimitive,
    val fees: JsonPrimitive,
    val adjustments: JsonPrimitive,
    val net: JsonPrimitive,
    val currency: String,
    @SerialName("settled_at") val settledAt: String,
) {
    fun toDomain() = DriverEarningItem(
        id = id,
        rideId = rideId,
        gross = gross.content,
        fees = fees.content,
        adjustments = adjustments.content,
        net = net.content,
        currency = currency,
        settledAt = settledAt,
    )
}

@Serializable
private data class TransitionResponse(@SerialName("ride_id") val rideId: String, val status: String)

@Serializable
private data class CompletionRequest(val latitude: Double, val longitude: Double)

@Serializable
private data class CancellationRequest(val reason: String)

@Serializable
private data class CompletionResponse(@SerialName("ride_id") val rideId: String, val status: String)
