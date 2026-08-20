package org.example.taximobile.data.auth

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
import org.example.taximobile.data.network.ApiRequestException
import org.example.taximobile.domain.auth.AccountRole
import org.example.taximobile.domain.auth.CurrentAccount
import org.example.taximobile.domain.auth.SessionTokens

class KtorAuthenticationGateway(
    private val client: HttpClient,
    private val api: ApiConfiguration,
) : AuthenticationGateway {
    override suspend fun register(
        displayName: String,
        email: String?,
        phoneNumber: String?,
        password: String,
    ) = networkRequest {
        val response = client.post(api.endpoint("auth/register")) {
            contentType(ContentType.Application.Json)
            setBody(RegisterRequest(displayName, email, phoneNumber, password))
        }
        response.throwForFailure()
    }

    override suspend fun login(identifier: String, password: String, deviceLabel: String?): SessionTokens = networkRequest {
        val response = client.post(api.endpoint("auth/login")) {
            contentType(ContentType.Application.Json)
            setBody(LoginRequest(identifier, password, deviceLabel))
        }
        response.tokensOrThrow()
    }

    override suspend fun refresh(refreshToken: String): SessionTokens = networkRequest {
        val response = client.post(api.endpoint("auth/refresh")) {
            contentType(ContentType.Application.Json)
            setBody(RefreshRequest(refreshToken))
        }
        response.tokensOrThrow()
    }

    override suspend fun logout(accessToken: String) = networkRequest {
        val response = client.post(api.endpoint("auth/logout")) {
            header(HttpHeaders.Authorization, "Bearer $accessToken")
        }
        response.throwForFailure()
    }

    override suspend fun currentAccount(accessToken: String): CurrentAccount = networkRequest {
        val response = client.get(api.endpoint("me")) {
            header(HttpHeaders.Authorization, "Bearer $accessToken")
        }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        response.throwForFailure()
        val account = response.body<AccountResponse>()
        CurrentAccount(
            id = account.id,
            roles = account.roles.mapNotNull { value -> AccountRole.entries.find { it.name == value } }.toSet(),
            displayName = account.profile.displayName,
        )
    }

    private suspend fun <T> networkRequest(block: suspend () -> T): T = try {
        block()
    } catch (error: AuthenticationRejectedException) {
        throw error
    } catch (error: ApiRequestException) {
        throw error
    } catch (error: Exception) {
        throw AuthenticationNetworkException()
    }

    private suspend fun io.ktor.client.statement.HttpResponse.tokensOrThrow(): SessionTokens {
        if (status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        throwForFailure()
        val response = body<TokenResponse>()
        return SessionTokens(response.accessToken, response.refreshToken)
    }

    private fun io.ktor.client.statement.HttpResponse.throwForFailure() {
        if (!status.isSuccess()) throw ApiRequestException(status.value, "The server could not complete this request.")
    }
}

@Serializable
private data class LoginRequest(
    val identifier: String,
    val password: String,
    @SerialName("device_label") val deviceLabel: String?,
)

@Serializable
private data class RegisterRequest(
    @SerialName("display_name") val displayName: String,
    val email: String?,
    @SerialName("phone_number") val phoneNumber: String?,
    val password: String,
)

@Serializable
private data class RefreshRequest(@SerialName("refresh_token") val refreshToken: String)

@Serializable
private data class TokenResponse(
    @SerialName("access_token") val accessToken: String,
    @SerialName("refresh_token") val refreshToken: String,
)

@Serializable
private data class AccountResponse(
    val id: String,
    val roles: List<String>,
    val profile: ProfileResponse,
)

@Serializable
private data class ProfileResponse(@SerialName("display_name") val displayName: String)
