package org.example.taximobile.data.safety

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
import org.example.taximobile.data.network.newIdempotencyKey
import org.example.taximobile.domain.safety.SafetyCategory
import org.example.taximobile.domain.safety.SafetyGateway
import org.example.taximobile.domain.safety.SafetyReport

class KtorSafetyGateway(
    private val client: HttpClient,
    private val api: ApiConfiguration,
    private val accessToken: suspend () -> String,
) : SafetyGateway {
    override suspend fun reports(): List<SafetyReport> = request {
        val response = client.get(api.endpoint("safety/reports")) {
            header(HttpHeaders.Authorization, "Bearer ${accessToken()}")
        }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) {
            throw ApiRequestException(response.status.value, "The server could not load safety reports.")
        }
        response.body<SafetyReportListResponse>().items.map { it.toDomain() }
    }

    override suspend fun createReport(
        rideId: String,
        category: SafetyCategory,
        description: String,
    ) {
        require(category != SafetyCategory.UNKNOWN)
        request {
            val response = client.post(api.endpoint("safety/reports")) {
                header(HttpHeaders.Authorization, "Bearer ${accessToken()}")
                header("Idempotency-Key", newIdempotencyKey())
                contentType(ContentType.Application.Json)
                setBody(SafetyReportRequest(rideId, category.name, description))
            }
            if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
            if (!response.status.isSuccess()) {
                throw ApiRequestException(response.status.value, "The server could not create this safety report.")
            }
        }
    }

    private suspend fun <T> request(block: suspend () -> T): T = try {
        block()
    } catch (error: AuthenticationRejectedException) {
        throw error
    } catch (error: ApiRequestException) {
        throw error
    } catch (_: Exception) {
        throw AuthenticationNetworkException()
    }
}

@Serializable
private data class SafetyReportRequest(
    @SerialName("ride_id") val rideId: String,
    val category: String,
    val description: String,
)

@Serializable
internal data class SafetyReportListResponse(val items: List<SafetyReportResponse>)

@Serializable
internal data class SafetyReportResponse(
    val id: String,
    @SerialName("ride_id") val rideId: String,
    val category: String,
    val status: String,
    @SerialName("created_at") val createdAt: String,
    @SerialName("latest_public_message") val latestPublicMessage: String? = null,
    @SerialName("updated_at") val updatedAt: String? = null,
) {
    fun toDomain() = SafetyReport(
        id = id,
        rideId = rideId,
        category = SafetyCategory.entries.firstOrNull { it.name == category } ?: SafetyCategory.UNKNOWN,
        status = status,
        createdAt = createdAt,
        latestPublicMessage = latestPublicMessage,
        updatedAt = updatedAt,
    )
}
