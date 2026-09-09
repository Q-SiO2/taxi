package org.example.taximobile.data.network

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.http.isSuccess
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import org.example.taximobile.core.network.ApiConfiguration
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.domain.system.ClientCompatibility
import org.example.taximobile.domain.system.ClientCompatibilityGateway
import org.example.taximobile.domain.system.ClientCompatibilityStatus

class KtorClientCompatibilityGateway(
    private val client: HttpClient,
    private val api: ApiConfiguration,
) : ClientCompatibilityGateway {
    override suspend fun check(): ClientCompatibility = try {
        val response = client.get(api.endpoint("client-compatibility"))
        if (!response.status.isSuccess()) {
            throw ApiRequestException(
                response.status.value,
                "The server could not verify this client build.",
            )
        }
        val body = response.body<ClientCompatibilityResponse>()
        ClientCompatibility(
            status = ClientCompatibilityStatus.entries.firstOrNull { it.name == body.status }
                ?: throw ApiRequestException(500, "The server returned an unknown compatibility state."),
            minimumVersion = body.minimumVersion,
            recommendedVersion = body.recommendedVersion,
            policyRevision = body.policyRevision,
            apiVersion = body.apiVersion,
        )
    } catch (error: ApiRequestException) {
        throw error
    } catch (error: Exception) {
        throw AuthenticationNetworkException()
    }
}

@Serializable
private data class ClientCompatibilityResponse(
    val status: String,
    @SerialName("minimum_version") val minimumVersion: String,
    @SerialName("recommended_version") val recommendedVersion: String,
    @SerialName("policy_revision") val policyRevision: String,
    @SerialName("api_version") val apiVersion: String,
)

