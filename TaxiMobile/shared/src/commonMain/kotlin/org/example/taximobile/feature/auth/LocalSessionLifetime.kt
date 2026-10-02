package org.example.taximobile.feature.auth

/**
 * Ephemeral subscription ownership, not a token, account ID or authorization.
 * A new credential pair or local sign-out invalidates the previous generation.
 * Only the backend can decide whether the underlying session is still valid.
 * Ending is part of the same atomic value so a late restore cannot reactivate it.
 */
data class LocalSessionLifetime(
    val generation: Long = 0,
    val active: Boolean = false,
    val ending: Boolean = false,
)
