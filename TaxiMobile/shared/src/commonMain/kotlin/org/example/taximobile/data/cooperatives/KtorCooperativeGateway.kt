package org.example.taximobile.data.cooperatives

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.request.header
import io.ktor.http.HttpHeaders
import io.ktor.http.HttpStatusCode
import io.ktor.http.isSuccess
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import org.example.taximobile.core.network.ApiConfiguration
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.data.auth.AuthenticationRejectedException
import org.example.taximobile.data.network.ApiRequestException
import org.example.taximobile.domain.cooperatives.CooperativeGateway
import org.example.taximobile.domain.cooperatives.CooperativeMembership

class KtorCooperativeGateway(
    private val client: HttpClient,
    private val api: ApiConfiguration,
    private val accessToken: suspend () -> String,
) : CooperativeGateway {
    override suspend fun currentMembership(): CooperativeMembership? = try {
        val response = client.get(api.endpoint("cooperative/membership")) {
            header(HttpHeaders.Authorization, "Bearer ${accessToken()}")
        }
        when {
            response.status == HttpStatusCode.NotFound -> null
            response.status == HttpStatusCode.Unauthorized -> throw AuthenticationRejectedException()
            !response.status.isSuccess() -> throw ApiRequestException(
                response.status.value,
                "The server could not load cooperative membership.",
            )
            else -> response.body<CooperativeMembershipResponse>().toDomain()
        }
    } catch (error: AuthenticationRejectedException) {
        throw error
    } catch (error: ApiRequestException) {
        throw error
    } catch (_: Exception) {
        throw AuthenticationNetworkException()
    }
}

@Serializable
internal data class CooperativeMembershipResponse(
    @SerialName("cooperative_id") val cooperativeId: String,
    @SerialName("cooperative_name") val cooperativeName: String,
    val status: String,
    @SerialName("joined_at") val joinedAt: String? = null,
    @SerialName("membership_number") val membershipNumber: String? = null,
) {
    fun toDomain() = CooperativeMembership(cooperativeId, cooperativeName, status, joinedAt, membershipNumber)
}
