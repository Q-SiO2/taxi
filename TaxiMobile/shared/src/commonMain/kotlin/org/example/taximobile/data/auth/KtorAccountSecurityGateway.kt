package org.example.taximobile.data.auth

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.delete
import io.ktor.client.request.get
import io.ktor.client.request.header
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.HttpHeaders
import io.ktor.http.contentType
import io.ktor.http.isSuccess
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import org.example.taximobile.core.network.ApiConfiguration
import org.example.taximobile.data.network.ApiRequestException
import org.example.taximobile.domain.auth.AccountRecoveryCodes
import org.example.taximobile.domain.auth.AccountSession
import org.example.taximobile.domain.auth.AccountSessionRevocation

class KtorAccountSecurityGateway(
    private val client: HttpClient,
    private val api: ApiConfiguration,
    private val accessToken: suspend () -> String,
) : AccountSecurityGateway {
    override suspend fun resetPassword(
        identifier: String,
        recoveryCode: String,
        newPassword: String,
    ) = networkRequest {
        client.post(api.endpoint("auth/recovery/reset")) {
            contentType(ContentType.Application.Json)
            setBody(AccountRecoveryResetRequest(identifier, recoveryCode, newPassword))
        }.throwForPublicFailure()
    }

    override suspend fun recoveryCodes(currentPassword: String): AccountRecoveryCodes =
        authenticatedRequest { token ->
            val response = client.post(api.endpoint("auth/recovery-codes")) {
                header(HttpHeaders.Authorization, "Bearer $token")
                contentType(ContentType.Application.Json)
                setBody(RecoveryCodesRequest(currentPassword))
            }
            response.throwForAuthenticatedFailure()
            response.body<RecoveryCodesResponse>().let {
                AccountRecoveryCodes(it.codes, it.expiresAt)
            }
        }

    override suspend fun sessions(): List<AccountSession> = authenticatedRequest { token ->
        val response = client.get(api.endpoint("auth/sessions")) {
            header(HttpHeaders.Authorization, "Bearer $token")
        }
        response.throwForAuthenticatedFailure()
        response.body<AccountSessionListResponse>().items.map { it.toDomain() }
    }

    override suspend fun revokeSession(sessionId: String): AccountSessionRevocation =
        authenticatedRequest { token ->
            val response = client.delete(api.endpoint("auth/sessions/$sessionId")) {
                header(HttpHeaders.Authorization, "Bearer $token")
            }
            response.throwForAuthenticatedFailure()
            AccountSessionRevocation(response.body<AccountSessionRevokeResponse>().currentSession)
        }

    override suspend fun changePassword(currentPassword: String, newPassword: String) =
        authenticatedRequest { token ->
            client.post(api.endpoint("auth/password/change")) {
                header(HttpHeaders.Authorization, "Bearer $token")
                contentType(ContentType.Application.Json)
                setBody(PasswordChangeRequest(currentPassword, newPassword))
            }.throwForAuthenticatedFailure()
        }

    private suspend fun <T> authenticatedRequest(block: suspend (String) -> T): T =
        networkRequest { block(accessToken()) }

    private suspend fun <T> networkRequest(block: suspend () -> T): T = try {
        block()
    } catch (error: AuthenticationRejectedException) {
        throw error
    } catch (error: ApiRequestException) {
        throw error
    } catch (error: Exception) {
        throw AuthenticationNetworkException()
    }

    private suspend fun io.ktor.client.statement.HttpResponse.throwForPublicFailure() {
        if (!status.isSuccess()) {
            throw ApiRequestException(status.value, "The server could not complete this request.")
        }
    }

    private suspend fun io.ktor.client.statement.HttpResponse.throwForAuthenticatedFailure() {
        if (!status.isSuccess()) {
            // An endpoint-level 401 can mean an invalid re-authentication
            // password. The coordinator restores the bearer session before
            // deciding whether to keep the account screen or sign out.
            throw ApiRequestException(status.value, "The server could not complete this request.")
        }
    }
}

@Serializable
private data class AccountRecoveryResetRequest(
    val identifier: String,
    @SerialName("recovery_code") val recoveryCode: String,
    @SerialName("new_password") val newPassword: String,
)

@Serializable
private data class RecoveryCodesRequest(
    @SerialName("current_password") val currentPassword: String,
)

@Serializable
private data class RecoveryCodesResponse(
    val codes: List<String>,
    @SerialName("expires_at") val expiresAt: String,
)

@Serializable
private data class AccountSessionListResponse(val items: List<AccountSessionResponse>)

@Serializable
private data class AccountSessionResponse(
    val id: String,
    @SerialName("device_label") val deviceLabel: String?,
    val current: Boolean,
    @SerialName("created_at") val createdAt: String,
    @SerialName("expires_at") val expiresAt: String,
) {
    fun toDomain() = AccountSession(id, deviceLabel, current, createdAt, expiresAt)
}

@Serializable
private data class AccountSessionRevokeResponse(
    @SerialName("current_session") val currentSession: Boolean,
)

@Serializable
private data class PasswordChangeRequest(
    @SerialName("current_password") val currentPassword: String,
    @SerialName("new_password") val newPassword: String,
)
