package org.example.taximobile.data.auth

import org.example.taximobile.domain.auth.CurrentAccount
import org.example.taximobile.domain.auth.SessionTokens

/**
 * Versioned backend boundary for authentication. Implementations must send
 * credentials only over the configured API transport and never log them.
 */
interface AuthenticationGateway {
    suspend fun register(
        displayName: String,
        email: String?,
        phoneNumber: String?,
        password: String,
    )
    suspend fun login(identifier: String, password: String, deviceLabel: String?): SessionTokens
    suspend fun refresh(refreshToken: String): SessionTokens
    suspend fun logout(accessToken: String)
    suspend fun currentAccount(accessToken: String): CurrentAccount
}

/** A definitive backend rejection (401/invalid session), not a transport failure. */
class AuthenticationRejectedException : Exception()

/** A recoverable transport failure; callers must retain a known session. */
class AuthenticationNetworkException : Exception()
