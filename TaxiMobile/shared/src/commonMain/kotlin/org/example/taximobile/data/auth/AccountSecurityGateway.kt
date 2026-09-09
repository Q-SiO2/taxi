package org.example.taximobile.data.auth

import org.example.taximobile.domain.auth.AccountRecoveryCodes
import org.example.taximobile.domain.auth.AccountSession
import org.example.taximobile.domain.auth.AccountSessionRevocation

/**
 * Provider-independent account recovery and session-control boundary.
 * Implementations must never log passwords, recovery codes, or bearer tokens.
 */
interface AccountSecurityGateway {
    suspend fun resetPassword(identifier: String, recoveryCode: String, newPassword: String)
    suspend fun recoveryCodes(currentPassword: String): AccountRecoveryCodes
    suspend fun sessions(): List<AccountSession>
    suspend fun revokeSession(sessionId: String): AccountSessionRevocation
    suspend fun changePassword(currentPassword: String, newPassword: String)
}

