package org.example.taximobile.domain.passengers

/** The authenticated passenger's minimal editable service identity. */
data class PassengerProfile(val id: String, val displayName: String)

/**
 * Profile operations are account-scoped. The server, not a supplied profile
 * identifier, determines which passenger record may be read or changed.
 */
interface PassengerProfileGateway {
    suspend fun profile(): PassengerProfile
    suspend fun updateDisplayName(displayName: String): PassengerProfile
}
