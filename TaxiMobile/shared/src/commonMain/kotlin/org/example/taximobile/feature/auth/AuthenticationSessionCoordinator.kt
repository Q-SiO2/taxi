package org.example.taximobile.feature.auth

import org.example.taximobile.data.auth.AuthenticationGateway
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.data.auth.AuthenticationRejectedException
import org.example.taximobile.data.auth.SecureTokenStore
import org.example.taximobile.data.auth.SecureTokenStorageException
import org.example.taximobile.data.network.ApiRequestException
import org.example.taximobile.domain.auth.CurrentAccount
import org.example.taximobile.feature.ui.text.UiMessage
import org.jetbrains.compose.resources.StringResource
import taximobile.shared.generated.resources.Res
import taximobile.shared.generated.resources.message_invalid_credentials
import taximobile.shared.generated.resources.message_network_unavailable
import taximobile.shared.generated.resources.message_registration_conflict
import taximobile.shared.generated.resources.message_registration_failed
import taximobile.shared.generated.resources.message_registration_invalid
import taximobile.shared.generated.resources.message_registration_rate_limited
import taximobile.shared.generated.resources.message_session_restore_failed
import taximobile.shared.generated.resources.message_sign_in_failed

/**
 * Orchestrates secure-token restoration without exposing token values to UI
 * state. Backend rejections clear the session; transport failures do not.
 */
class AuthenticationSessionCoordinator(
    private val gateway: AuthenticationGateway,
    private val tokenStore: SecureTokenStore,
) {
    suspend fun restore(): AuthenticationState {
        return try {
            val tokens = tokenStore.tokens() ?: return AuthenticationState.Unauthenticated
            try {
                authenticated(gateway.currentAccount(tokens.accessToken))
            } catch (_: AuthenticationRejectedException) {
                refreshOrSignOut(tokens.refreshToken)
            } catch (_: AuthenticationNetworkException) {
                AuthenticationState.Failure(message(Res.string.message_network_unavailable))
            } catch (_: ApiRequestException) {
                AuthenticationState.Failure(message(Res.string.message_session_restore_failed))
            }
        } catch (_: SecureTokenStorageException) {
            AuthenticationState.Failure(message(Res.string.message_session_restore_failed))
        }
    }

    suspend fun login(identifier: String, password: String, deviceLabel: String?): AuthenticationState {
        var issuedAccessToken: String? = null
        return try {
            val tokens = gateway.login(identifier, password, deviceLabel)
            issuedAccessToken = tokens.accessToken
            tokenStore.save(tokens.accessToken, tokens.refreshToken)
            authenticated(gateway.currentAccount(tokens.accessToken))
        } catch (_: SecureTokenStorageException) {
            issuedAccessToken?.let { bestEffortLogout(it) }
            AuthenticationState.Failure(message(Res.string.message_sign_in_failed))
        } catch (_: AuthenticationRejectedException) {
            AuthenticationState.Failure(message(Res.string.message_invalid_credentials))
        } catch (_: AuthenticationNetworkException) {
            AuthenticationState.Failure(message(Res.string.message_network_unavailable))
        } catch (_: ApiRequestException) {
            AuthenticationState.Failure(message(Res.string.message_sign_in_failed))
        }
    }

    suspend fun register(
        displayName: String,
        email: String?,
        phoneNumber: String?,
        password: String,
    ): AuthenticationState = try {
        gateway.register(displayName, email, phoneNumber, password)
        AuthenticationState.Unauthenticated
    } catch (_: AuthenticationNetworkException) {
        AuthenticationState.Failure(message(Res.string.message_network_unavailable))
    } catch (error: ApiRequestException) {
        AuthenticationState.Failure(registrationFailureMessage(error.statusCode))
    }

    suspend fun logout(): AuthenticationState {
        val tokens = try {
            tokenStore.tokens()
        } catch (_: SecureTokenStorageException) {
            null
        }
        try {
            tokenStore.clear()
        } catch (_: SecureTokenStorageException) {
            return AuthenticationState.Failure(message(Res.string.message_session_restore_failed))
        }
        if (tokens != null) {
            bestEffortLogout(tokens.accessToken)
        }
        return AuthenticationState.Unauthenticated
    }

    /** Clear already-revoked local credentials without issuing another command. */
    suspend fun clearLocalSession(): AuthenticationState = try {
        tokenStore.clear()
        AuthenticationState.Unauthenticated
    } catch (_: SecureTokenStorageException) {
        AuthenticationState.Failure(message(Res.string.message_session_restore_failed))
    }

    private suspend fun refreshOrSignOut(refreshToken: String): AuthenticationState {
        var issuedAccessToken: String? = null
        return try {
            val refreshed = gateway.refresh(refreshToken)
            issuedAccessToken = refreshed.accessToken
            tokenStore.save(refreshed.accessToken, refreshed.refreshToken)
            authenticated(gateway.currentAccount(refreshed.accessToken))
        } catch (_: AuthenticationRejectedException) {
            clearLocalSession()
        } catch (_: AuthenticationNetworkException) {
            AuthenticationState.Failure(message(Res.string.message_network_unavailable))
        } catch (_: ApiRequestException) {
            AuthenticationState.Failure(message(Res.string.message_session_restore_failed))
        } catch (_: SecureTokenStorageException) {
            issuedAccessToken?.let { bestEffortLogout(it) }
            AuthenticationState.Failure(message(Res.string.message_session_restore_failed))
        }
    }

    private suspend fun bestEffortLogout(accessToken: String) {
        try {
            gateway.logout(accessToken)
        } catch (_: AuthenticationNetworkException) {
            // Local credential deletion is still required while offline.
        } catch (_: AuthenticationRejectedException) {
            // The server session is already invalid.
        } catch (_: ApiRequestException) {
            // Local credential deletion still wins over a server-side failure.
        }
    }

    private fun authenticated(account: CurrentAccount): AuthenticationState = AuthenticationState.Authenticated(account)
}

internal fun registrationFailureMessage(statusCode: Int): UiMessage = when (statusCode) {
    409 -> message(Res.string.message_registration_conflict)
    422 -> message(Res.string.message_registration_invalid)
    429 -> message(Res.string.message_registration_rate_limited)
    else -> message(Res.string.message_registration_failed)
}

private fun message(resource: StringResource): UiMessage = UiMessage(resource)
