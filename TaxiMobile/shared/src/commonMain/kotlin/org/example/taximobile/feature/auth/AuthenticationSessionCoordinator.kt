package org.example.taximobile.feature.auth

import org.example.taximobile.data.auth.AuthenticationGateway
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
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
    private val refreshCommitTimeoutMillis: Long = 30_000,
) {
    init { require(refreshCommitTimeoutMillis in 1L..30_000L) }
    // Concurrent reconnect/foreground/push restores must not rotate the same
    // refresh credential twice. This mutex owns credentials, not business commands.
    private val sessionMutex = Mutex()
    // Credential ownership changes on login/end, not ordinary token rotation.
    // Separate from the hint generation: refreshing must not invalidate its
    // own advisory read, while a queued login/logout must invalidate it now.
    private val credentialOwnerEpoch = MutableStateFlow(0L)
    /** Local navigation ownership only; ordinary token rotation keeps this epoch. */
    val localSessionOwnerEpoch: Long get() = credentialOwnerEpoch.value
    private var validatedAccount: CurrentAccount? = null
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
        credentialOwnerEpoch.update { it + 1 }
        mutableLifetime.update { current ->
            current.copy(
                generation = current.generation + if (current.active) 1 else 0,
                active = false,
                ending = true,
            )
        }
    }

    private fun sessionAvailable(replaced: Boolean = false, expectedOwner: Long? = null) {
        mutableLifetime.update { current ->
            if (!current.ending && (expectedOwner == null || expectedOwner == credentialOwnerEpoch.value) &&
                (replaced || !current.active)
            ) {
                LocalSessionLifetime(current.generation + 1, true)
            } else current
        }
    }

    suspend fun restore(): AuthenticationState = sessionMutex.withLock { restoreSession() }

    /**
     * Only for advisory reads; NEVER pass ride/payment/availability mutations.
     * The existing credential mutex prevents a different login from replacing
     * the token provider between authorization and the read. A caller's staged
     * login/logout changes the epoch before waiting for that mutex, so a late
     * result cannot reopen hints or publish another account's projection.
     * The callback must not call restore/login/logout (the mutex is not reentrant).
     */
    suspend fun <T> readWithSessionRecovery(read: suspend (CurrentAccount) -> T): T {
        // Capture before queuing, not after the mutex admits us: an old UI read
        // waiting behind another operation must not adopt a newly staged login.
        val owner = credentialOwnerEpoch.value
        return sessionMutex.withLock { readWithOwnedSessionRecovery(owner, read) }
    }

    private suspend fun <T> readWithOwnedSessionRecovery(
        owner: Long,
        read: suspend (CurrentAccount) -> T,
    ): T {
        val originalAccountId = validatedAccount?.id
        var refreshAttempted = false
        fun requireOwner() {
            if (owner != credentialOwnerEpoch.value || mutableLifetime.value.ending) {
                stopLiveUpdates()
                throw AuthenticationRejectedException()
            }
        }
        suspend fun authorize(expectedAccountId: String?): CurrentAccount {
            requireOwner()
            val restored = restoreSession(allowRefresh = !refreshAttempted) { refreshAttempted = true }
            requireOwner()
            val account = when (restored) {
                is AuthenticationState.Authenticated -> restored.account
                is AuthenticationState.Failure -> {
                    if (restored.message.resource == Res.string.message_network_unavailable) {
                        throw AuthenticationNetworkException()
                    }
                    throw ApiRequestException(503, "The session could not be restored.")
                }
                else -> throw AuthenticationRejectedException()
            }
            if (expectedAccountId != null && account.id != expectedAccountId) {
                rejectReadAndClearCredentials()
            }
            return account
        }
        val account = authorize(originalAccountId)
        val result = try {
            read(account)
        } catch (_: AuthenticationRejectedException) {
            // A token can be rejected after preflight. Revalidate/refresh once
            // and repeat only this caller-declared read; no generic HTTP retry.
            val recovered = authorize(account.id)
            try {
                read(recovered)
            } catch (_: AuthenticationRejectedException) {
                rejectReadAndClearCredentials()
            }
        }
        requireOwner()
        return result
    }

    private suspend fun rejectReadAndClearCredentials(): Nothing {
        if (clearLocalSessionLocked() is AuthenticationState.Failure) {
            // A failed protected-store clear is not successful sign-out.
            throw ApiRequestException(503, "The local session could not be cleared.")
        }
        throw AuthenticationRejectedException()
    }

    private suspend fun restoreSession(
        allowRefresh: Boolean = true,
        onRefreshAttempt: () -> Unit = {},
    ): AuthenticationState {
        // A queued account switch fences every activation, including the gap
        // between persisting a rotated pair and validating its principal.
        val owner = credentialOwnerEpoch.value
        return try {
            val tokens = tokenStore.tokens() ?: run {
                validatedAccount = null
                stopLiveUpdates()
                return AuthenticationState.Unauthenticated
            }
            try {
                authenticated(gateway.currentAccount(tokens.accessToken), owner)
            } catch (_: AuthenticationRejectedException) {
                if (!allowRefresh) {
                    clearLocalSessionLocked()
                } else {
                    onRefreshAttempt()
                    refreshOrSignOut(tokens.refreshToken, owner)
                }
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
        credentialOwnerEpoch.update { it + 1 }
        stopLiveUpdates()
        return sessionMutex.withLock {
            validatedAccount = null
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
            validatedAccount = null
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
        validatedAccount = null
        AuthenticationState.Unauthenticated
    } catch (_: SecureTokenStorageException) {
        AuthenticationState.Failure(message(Res.string.message_session_restore_failed))
    }

    private suspend fun refreshOrSignOut(refreshToken: String, owner: Long): AuthenticationState {
        return try {
            // The server consumes a refresh credential before its response can
            // reach us. A UI/subscription cancellation must not discard that
            // issued pair and then cause reuse of the old token. Only this
            // bounded credential phase is protected, never business commands.
            val refreshed = withContext(NonCancellable) {
                withTimeoutOrNull(refreshCommitTimeoutMillis) {
                    val issued = gateway.refresh(refreshToken)
                    try {
                        tokenStore.save(issued.accessToken, issued.refreshToken)
                    } catch (error: SecureTokenStorageException) {
                        stopLiveUpdates()
                        bestEffortLogout(issued.accessToken)
                        throw error
                    }
                    issued
                } ?: throw AuthenticationNetworkException()
            }
            // Persisting credentials does not authorize a cancelled observer to
            // publish a principal or reactivate subscriptions.
            currentCoroutineContext().ensureActive()
            sessionAvailable(replaced = true, expectedOwner = owner)
            authenticated(gateway.currentAccount(refreshed.accessToken), owner)
        } catch (_: AuthenticationRejectedException) {
            val cleared = clearLocalSessionLocked()
            currentCoroutineContext().ensureActive()
            cleared
        } catch (_: AuthenticationNetworkException) {
            currentCoroutineContext().ensureActive()
            AuthenticationState.Failure(message(Res.string.message_network_unavailable))
        } catch (_: ApiRequestException) {
            currentCoroutineContext().ensureActive()
            AuthenticationState.Failure(message(Res.string.message_session_restore_failed))
        } catch (_: SecureTokenStorageException) {
            stopLiveUpdates()
            currentCoroutineContext().ensureActive()
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

    private fun authenticated(account: CurrentAccount, owner: Long? = null): AuthenticationState {
        validatedAccount = account
        sessionAvailable(expectedOwner = owner)
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
