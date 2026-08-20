package org.example.taximobile.data.passengers

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.request.header
import io.ktor.client.request.patch
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
import org.example.taximobile.domain.passengers.PassengerProfile
import org.example.taximobile.domain.passengers.PassengerProfileGateway

class KtorPassengerProfileGateway(
    private val client: HttpClient,
    private val api: ApiConfiguration,
    private val accessToken: suspend () -> String,
) : PassengerProfileGateway {
    override suspend fun profile(): PassengerProfile = request {
        val response = client.get(api.endpoint("passenger/profile")) { authorize() }
        response.profileOrThrow()
    }

    override suspend fun updateDisplayName(displayName: String): PassengerProfile = request {
        val response = client.patch(api.endpoint("passenger/profile")) {
            authorize()
            contentType(ContentType.Application.Json)
            setBody(PassengerProfileUpdateRequest(displayName.trim()))
        }
        response.profileOrThrow()
    }

    private suspend fun io.ktor.client.request.HttpRequestBuilder.authorize() {
        header(HttpHeaders.Authorization, "Bearer ${accessToken()}")
    }

    private suspend fun io.ktor.client.statement.HttpResponse.profileOrThrow(): PassengerProfile {
        if (status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!status.isSuccess()) throw ApiRequestException(status.value, "The server could not update this profile.")
        return body<PassengerProfileResponse>().let { PassengerProfile(it.id, it.displayName) }
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
private data class PassengerProfileResponse(
    val id: String,
    @SerialName("display_name") val displayName: String,
)

@Serializable
private data class PassengerProfileUpdateRequest(@SerialName("display_name") val displayName: String)
