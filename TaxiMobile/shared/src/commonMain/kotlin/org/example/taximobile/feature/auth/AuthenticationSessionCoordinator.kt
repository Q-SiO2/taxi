package org.example.taximobile.feature.auth

import org.example.taximobile.data.auth.AuthenticationGateway
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
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
    // Concurrent reconnect/foreground/push restores must not rotate the same
    // refresh credential twice. This mutex owns credentials, not business commands.
    private val sessionMutex = Mutex()
    private val mutableLifetime = MutableStateFlow(LocalSessionLifetime())
    val liveSessionLifetime: StateFlow<LocalSessionLifetime> = mutableLifetime.asStateFlow()

    /** Stop hints immediately, before logout waits for any network cleanup. */
    fun stopLiveUpdates() {
        mutableLifetime.update { current ->
            if (current.active) current.copy(generation = current.generation + 1, active = false) else current
        }
    }

    /** Late/queued REST restores may not reopen hints while logout cleanup waits. */
    fun beginSessionEnd() {
        mutableLifetime.update { current ->
            current.copy(
                generation = current.generation + if (current.active) 1 else 0,
                active = false,
                ending = true,
            )
        }
    }

    private fun sessionAvailable(replaced: Boolean = false) {
        mutableLifetime.update { current ->
            if (!current.ending && (replaced || !current.active)) {
                LocalSessionLifetime(current.generation + 1, true)
            } else current
        }
    }

    suspend fun restore(): AuthenticationState = sessionMutex.withLock { restoreSession() }

    private suspend fun restoreSession(): AuthenticationState {
        return try {
            val tokens = tokenStore.tokens() ?: run {
                stopLiveUpdates()
                return AuthenticationState.Unauthenticated
            }
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
            stopLiveUpdates()
            AuthenticationState.Failure(message(Res.string.message_session_restore_failed))
        }
    }

    suspend fun login(identifier: String, password: String, deviceLabel: String?): AuthenticationState {
        stopLiveUpdates()
        return sessionMutex.withLock {
            mutableLifetime.update { it.copy(ending = false) }
            loginSession(identifier, password, deviceLabel)
        }
    }

    private suspend fun loginSession(identifier: String, password: String, deviceLabel: String?): AuthenticationState {
        var issuedAccessToken: String? = null
        return try {
            val tokens = gateway.login(identifier, password, deviceLabel)
            issuedAccessToken = tokens.accessToken
            tokenStore.save(tokens.accessToken, tokens.refreshToken)
            sessionAvailable(replaced = true)
            authenticated(gateway.currentAccount(tokens.accessToken))
        } catch (_: SecureTokenStorageException) {
            stopLiveUpdates()
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
        beginSessionEnd()
        return sessionMutex.withLock {
            try { logoutSession() } finally { mutableLifetime.update { it.copy(ending = false) } }
        }
    }

    private suspend fun logoutSession(): AuthenticationState {
        stopLiveUpdates()
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
    suspend fun clearLocalSession(): AuthenticationState {
        beginSessionEnd()
        return sessionMutex.withLock {
            try { clearLocalSessionLocked() } finally { mutableLifetime.update { it.copy(ending = false) } }
        }
    }

    private suspend fun clearLocalSessionLocked(): AuthenticationState = try {
        stopLiveUpdates()
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
            sessionAvailable(replaced = true)
            authenticated(gateway.currentAccount(refreshed.accessToken))
        } catch (_: AuthenticationRejectedException) {
            clearLocalSessionLocked()
        } catch (_: AuthenticationNetworkException) {
            AuthenticationState.Failure(message(Res.string.message_network_unavailable))
        } catch (_: ApiRequestException) {
            AuthenticationState.Failure(message(Res.string.message_session_restore_failed))
        } catch (_: SecureTokenStorageException) {
            stopLiveUpdates()
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

    private fun authenticated(account: CurrentAccount): AuthenticationState {
        sessionAvailable()
        return AuthenticationState.Authenticated(account)
    }
}

internal fun registrationFailureMessage(statusCode: Int): UiMessage = when (statusCode) {
    409 -> message(Res.string.message_registration_conflict)
    422 -> message(Res.string.message_registration_invalid)
    429 -> message(Res.string.message_registration_rate_limited)
    else -> message(Res.string.message_registration_failed)
}

private fun message(resource: StringResource): UiMessage = UiMessage(resource)
