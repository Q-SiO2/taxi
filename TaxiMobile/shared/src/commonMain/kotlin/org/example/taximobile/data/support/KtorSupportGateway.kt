package org.example.taximobile.data.support

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
import kotlinx.serialization.Serializable
import org.example.taximobile.core.network.ApiConfiguration
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.data.auth.AuthenticationRejectedException
import org.example.taximobile.data.network.ApiRequestException
import org.example.taximobile.data.network.newIdempotencyKey
import org.example.taximobile.domain.support.SupportCategory
import org.example.taximobile.domain.support.SupportGateway
import org.example.taximobile.domain.support.SupportTicket

class KtorSupportGateway(
    private val client: HttpClient,
    private val api: ApiConfiguration,
    private val accessToken: suspend () -> String,
) : SupportGateway {
    override suspend fun tickets(): List<SupportTicket> = request {
        val response = client.get(api.endpoint("support/tickets")) {
            header(HttpHeaders.Authorization, "Bearer ${accessToken()}")
        }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not load support tickets.")
        response.body<SupportTicketListResponse>().items.map {
            SupportTicket(
                it.id,
                SupportCategory.valueOf(it.category),
                it.subject,
                it.status,
                it.createdAt,
                it.latestPublicMessage,
                it.updatedAt,
            )
        }
    }

    override suspend fun createTicket(
        category: SupportCategory,
        subject: String,
        description: String,
        rideId: String?,
    ) {
        request {
            val response = client.post(api.endpoint("support/tickets")) {
                header(HttpHeaders.Authorization, "Bearer ${accessToken()}")
                header("Idempotency-Key", newIdempotencyKey())
                contentType(ContentType.Application.Json)
                setBody(SupportTicketRequest(category.name, subject, description, rideId))
            }
            if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
            if (!response.status.isSuccess()) {
                throw ApiRequestException(response.status.value, "The server could not create this support ticket.")
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
private data class SupportTicketRequest(
    val category: String,
    val subject: String,
    val description: String,
    @kotlinx.serialization.SerialName("ride_id") val rideId: String? = null,
)

@Serializable private data class SupportTicketListResponse(val items: List<SupportTicketResponse>)
@Serializable private data class SupportTicketResponse(
    val id: String,
    val category: String,
    val subject: String,
    val status: String,
    @kotlinx.serialization.SerialName("created_at") val createdAt: String,
    @kotlinx.serialization.SerialName("latest_public_message") val latestPublicMessage: String? = null,
    @kotlinx.serialization.SerialName("updated_at") val updatedAt: String? = null,
)
