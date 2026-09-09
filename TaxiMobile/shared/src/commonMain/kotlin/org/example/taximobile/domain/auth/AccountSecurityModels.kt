package org.example.taximobile.domain.auth

/** One backend-owned login session. Token material is never exposed to UI state. */
data class AccountSession(
    val id: String,
    val deviceLabel: String?,
    val current: Boolean,
    val createdAt: String,
    val expiresAt: String,
)

/** Offline secrets returned exactly once after password re-authentication. */
data class AccountRecoveryCodes(
    val codes: List<String>,
    val expiresAt: String,
)

data class AccountSessionRevocation(
    val currentSession: Boolean,
)

