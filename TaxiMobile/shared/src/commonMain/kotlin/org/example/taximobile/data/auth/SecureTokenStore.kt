package org.example.taximobile.data.auth

/**
 * Platform implementations must use the operating system's protected
 * credential facility. Refresh tokens must never be placed in normal app
 * preferences, UI state, analytics, or logs.
 */
interface SecureTokenStore {
    suspend fun tokens(): StoredTokens?
    suspend fun save(accessToken: String, refreshToken: String)
    suspend fun clear()
}

data class StoredTokens(
    val accessToken: String,
    val refreshToken: String,
)
